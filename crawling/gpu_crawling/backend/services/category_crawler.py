"""
Category Crawler - seed recommendation candidates from Musinsa categories.
Uses Musinsa public PLP API with browser-like headers.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import json

import httpx
from sqlalchemy.orm import Session

from domain.entities import Product, User
from services.scraper import scrape_musinsa_product
from services.product_enricher import enrich_product_info
from services.product_service import ProductService
from services.style_analyzer import extract_style_tags
from services.personal_color import get_recommended_palette
from services.color_analyzer import (
    PCCSColor,
    analyze_rgb_color,
    calculate_color_distance,
    determine_color_temperature,
    hex_to_rgb,
)
from services.recommendation_service import extract_category_from_path
from services.musinsa_proxy import proxify_url, proxy_headers, httpx_proxies


DEFAULT_CATEGORY_CODES = {
    "상의": "001",
    "아우터": "002",
    "바지": "003",
}


def _build_headers(referer: str) -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.musinsa.com",
        "Referer": referer,
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


async def _fetch_top_categories() -> Dict[str, str]:
    url = "https://api.musinsa.com/api2/dp/v1/categories"
    params = {"gf": "A"}
    headers = _build_headers("https://www.musinsa.com/")
    headers.update(proxy_headers())
    try:
        timeout = httpx.Timeout(connect=4.0, read=8.0, write=8.0, pool=8.0)
        async with httpx.AsyncClient(timeout=timeout, proxies=httpx_proxies()) as client:
            resp = await client.get(proxify_url(url), params=params, headers=headers)
        if resp.status_code != 200:
            return DEFAULT_CATEGORY_CODES
        data = resp.json()
        items = data.get("data", {}).get("list", [])
        mapping = {}
        for item in items:
            title = item.get("categoryTitle")
            code = item.get("categoryCode")
            if title and code:
                mapping[title] = code
        for key, code in DEFAULT_CATEGORY_CODES.items():
            mapping.setdefault(key, code)
        return mapping
    except Exception:
        return DEFAULT_CATEGORY_CODES


async def fetch_category_goods(category_code: str, page: int = 1, size: int = 60) -> List[Dict]:
    url = "https://api.musinsa.com/api2/dp/v1/plp/goods"
    params = {
        "gf": "A",
        "sortCode": "POPULAR",
        "category": category_code,
        "size": size,
        "testGroup": "",
        "caller": "CATEGORY",
        "page": page,
        "seen": 0,
        "seenAds": "",
    }
    referer = f"https://www.musinsa.com/categories/item/{category_code}"
    headers = _build_headers(referer)
    headers.update(proxy_headers())
    try:
        timeout = httpx.Timeout(connect=4.0, read=8.0, write=8.0, pool=8.0)
        async with httpx.AsyncClient(timeout=timeout, proxies=httpx_proxies()) as client:
            resp = await client.get(proxify_url(url), params=params, headers=headers)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", {}).get("list", []) or []
    except httpx.HTTPError:
        return []


def _parse_json_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


def _get_source_styles(source: Product) -> List[str]:
    return _parse_json_list(source.style_tags)


def _pccs_from_info(info: Dict) -> Optional[PCCSColor]:
    if info.get("pccs_hue") is None or info.get("pccs_value") is None or info.get("pccs_chroma") is None:
        return None
    return PCCSColor(
        hue=float(info.get("pccs_hue")),
        value=float(info.get("pccs_value")),
        chroma=float(info.get("pccs_chroma")),
        tone=info.get("pccs_tone") or "g",
        hex_color=info.get("primary_color_hex") or "#000000",
    )


def _palette_to_pccs(palette_hex: List[str]) -> List[PCCSColor]:
    colors = []
    for hex_color in palette_hex:
        try:
            r, g, b = hex_to_rgb(hex_color)
            colors.append(analyze_rgb_color(r, g, b))
        except Exception:
            continue
    return colors


def _matches_style(source_styles: List[str], candidate_styles: List[str]) -> bool:
    if not source_styles:
        return True
    if not candidate_styles:
        return False
    return bool(set(source_styles) & set(candidate_styles))


def _matches_tone(
    candidate_color: Optional[PCCSColor],
    tone_preference: Optional[str],
    candidate_temperature: Optional[str],
) -> bool:
    if not tone_preference or tone_preference == "neutral":
        return True
    if candidate_temperature:
        return candidate_temperature in (tone_preference, "neutral")
    if candidate_color:
        temp = determine_color_temperature(candidate_color.hue)
        return temp in (tone_preference, "neutral")
    return True


def _matches_palette(
    candidate_color: Optional[PCCSColor],
    palette_colors: List[PCCSColor],
    distance_threshold: float,
) -> bool:
    if not palette_colors or not candidate_color:
        return True
    distances = [calculate_color_distance(candidate_color, p) for p in palette_colors]
    return min(distances) <= distance_threshold


async def seed_recommendation_candidates(
    db: Session,
    source_product: Product,
    user: Optional[User],
    max_pages: int = 2,
    max_items_per_category: int = 24,
    palette_distance_threshold: float = 0.4,
) -> Dict[str, object]:
    """
    Crawl Musinsa categories and store style/color-enriched products.
    Returns summary counts per category.
    """
    source_category_raw = source_product.category_main or getattr(source_product, "category_path", "") or ""
    source_category = extract_category_from_path(source_category_raw)[0]
    source_category_musinsa = "바지" if source_category == "하의" else source_category

    category_codes = await _fetch_top_categories()
    target_categories = [name for name in DEFAULT_CATEGORY_CODES.keys() if name != source_category_musinsa]

    source_styles = _get_source_styles(source_product)
    tone_preference = user.personal_color_tone if user else None
    palette_hex = get_recommended_palette(
        base_tone=user.personal_color_tone if user else None,
        season=user.personal_color_season if user else None,
        tone_type=user.personal_color_type if user else None,
    )
    palette_pccs = _palette_to_pccs(palette_hex)

    results: Dict[str, Dict[str, int]] = {}
    total_saved = 0

    for category_name in target_categories:
        category_code = category_codes.get(category_name)
        if not category_code:
            continue

        saved = 0
        inspected = 0

        for page in range(1, max_pages + 1):
            goods_list = await fetch_category_goods(category_code, page=page)
            if not goods_list:
                break

            for goods in goods_list:
                if saved >= max_items_per_category:
                    break

                goods_no = goods.get("goodsNo")
                goods_name = goods.get("goodsName") or ""
                if not goods_no:
                    continue

                inspected += 1

                # Quick style prefilter (do not skip if no style tags found)
                quick_styles = extract_style_tags(goods_name)
                if source_styles and quick_styles and not _matches_style(source_styles, quick_styles):
                    continue

                product = ProductService.get_product_by_musinsa_id(db, str(goods_no))
                product_info = None

                if product and product.pccs_hue is not None and product.style_tags:
                    candidate_styles = _parse_json_list(product.style_tags)
                    candidate_color = None
                    if product.pccs_hue is not None and product.pccs_value is not None and product.pccs_chroma is not None:
                        candidate_color = PCCSColor(
                            hue=float(product.pccs_hue),
                            value=float(product.pccs_value),
                            chroma=float(product.pccs_chroma),
                            tone=product.pccs_tone or "g",
                            hex_color=product.primary_color_hex or "#000000",
                        )
                    candidate_temp = product.color_temperature
                else:
                    url = goods.get("goodsLinkUrl") or f"https://www.musinsa.com/products/{goods_no}"
                    product_info = await scrape_musinsa_product(url, str(goods_no))
                    product_info["source_url"] = url
                    product_info = await enrich_product_info(product_info)
                    candidate_styles = product_info.get("style_tags") or []
                    candidate_color = _pccs_from_info(product_info)
                    candidate_temp = product_info.get("color_temperature")

                if not _matches_style(source_styles, candidate_styles):
                    continue
                if not _matches_tone(candidate_color, tone_preference, candidate_temp):
                    continue
                if not _matches_palette(candidate_color, palette_pccs, palette_distance_threshold):
                    continue

                if product_info:
                    if product:
                        product = ProductService.update_product_from_info(db, product, product_info)
                    else:
                        product = ProductService.create_product(
                            db,
                            str(goods_no),
                            product_info.get("source_url") or f"https://www.musinsa.com/products/{goods_no}",
                            product_info,
                        )
                saved += 1
                total_saved += 1

            if saved >= max_items_per_category:
                break

        results[category_name] = {
            "inspected": inspected,
            "saved": saved,
        }

    return {
        "source_category": source_category_musinsa,
        "target_categories": target_categories,
        "total_saved": total_saved,
        "categories": results,
    }
