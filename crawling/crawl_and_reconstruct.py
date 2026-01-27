#!/usr/bin/env python3
"""
Crawl Musinsa product data (images + sizes) and run reconstruction.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime
import shutil
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from PIL import Image


AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
TEST_OUTPUT_ROOT = AI_ROOT / "test_artifacts"
FRONTEND_PUBLIC_ROOT = REPO_ROOT / "frontend" / "public" / "test_artifacts"
sys.path.insert(0, str(AI_ROOT))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from models.garment import GarmentTextureProcessor
from models.scaling import GarmentSizeScaler
from models.smplx import StandardMannequin
from models.export import export_dressed_mannequin


try:
    from size_scraper import scrape_musinsa_sizes
except Exception as exc:  # pragma: no cover
    scrape_musinsa_sizes = None
    logger.warning(f"size_scraper unavailable: {exc}")


def _extract_next_data(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r'__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def _normalize_image_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return "https://image.msscdn.net" + url


def fetch_product_info(url: str) -> Dict[str, Any]:
    resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=12.0)
    resp.raise_for_status()

    next_data = _extract_next_data(resp.text)
    if not next_data:
        raise RuntimeError("Failed to parse __NEXT_DATA__ from product page")

    page_props = next_data.get("props", {}).get("pageProps", {})
    meta = page_props.get("meta", {}).get("data", {})
    if not meta:
        raise RuntimeError("No meta.data found in __NEXT_DATA__")

    product_id = str(meta.get("goodsNo") or meta.get("goodsNoStr") or "")
    title = meta.get("goodsNm")

    image_urls: List[str] = []
    for img in meta.get("goodsImages", []) or []:
        image_url = img.get("imageUrl", "")
        if image_url:
            image_urls.append(_normalize_image_url(image_url))

    if not image_urls and meta.get("thumbnailImageUrl"):
        image_urls.append(_normalize_image_url(meta["thumbnailImageUrl"]))

    return {
        "product_id": product_id,
        "title": title,
        "image_urls": image_urls,
    }


def select_front_back(image_urls: List[str], front_idx: int, back_idx: int) -> Tuple[str, str]:
    if not image_urls:
        raise RuntimeError("No image URLs found")
    front_idx = max(0, min(front_idx, len(image_urls) - 1))
    back_idx = max(0, min(back_idx, len(image_urls) - 1))
    if len(image_urls) == 1:
        return image_urls[0], image_urls[0]
    if front_idx == back_idx:
        back_idx = 1 if front_idx == 0 and len(image_urls) > 1 else back_idx
    return image_urls[front_idx], image_urls[back_idx]


def download_image(url: str, path: Path) -> Path:
    resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20.0)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return path


def select_size_measurements(
    sizes: Dict[str, Dict[str, float]],
    size_label: Optional[str],
) -> Dict[str, float]:
    if not sizes:
        return {}
    if size_label:
        label = size_label.strip().upper()
        if label in sizes:
            return sizes[label]
    return next(iter(sizes.values()))


async def _scrape_sizes(product_id: str, product_url: str, use_playwright: bool) -> Dict[str, Dict[str, float]]:
    if scrape_musinsa_sizes is None:
        return {}
    result = await scrape_musinsa_sizes(product_id=product_id, product_url=product_url, use_playwright=use_playwright)
    return result.sizes


def run_pipeline(
    front_img: Image.Image,
    back_img: Image.Image,
    garment_type: str,
    target_cm: Dict[str, float],
    height_cm: float,
    weight_kg: float,
    output_dir: Path,
) -> Path:
    texture_processor = GarmentTextureProcessor()
    textures = texture_processor.process(front_img, back_img, garment_type)

    output_dir.mkdir(parents=True, exist_ok=True)
    front_path = output_dir / "front_texture.png"
    back_path = output_dir / "back_texture.png"
    atlas_path = output_dir / "uv_atlas.png"

    textures["front_texture"].save(front_path, format="PNG")
    textures["back_texture"].save(back_path, format="PNG")
    textures["uv_atlas"].save(atlas_path, format="PNG")

    scaler = GarmentSizeScaler()
    template_mesh = scaler.load_template_mesh(garment_type)
    scaled_mesh = scaler.scale_mesh(template_mesh, garment_type, target_cm)

    mannequin = StandardMannequin()
    mannequin_mesh = mannequin.get_mesh(height_cm=height_cm, weight_kg=weight_kg)

    glb_path = output_dir / "garment.glb"
    export_dressed_mannequin(
        mannequin_mesh=mannequin_mesh,
        garment_mesh=scaled_mesh,
        garment_texture=textures["uv_atlas"],
        output_path=glb_path,
    )

    return glb_path


def _publish_to_frontend(output_dir: Path, category: str, date_tag: str, run_id: str) -> None:
    target_dir = FRONTEND_PUBLIC_ROOT / category / date_tag / run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in output_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, target_dir / item.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Musinsa product and run reconstruction test.")
    parser.add_argument("--url", required=True, help="Musinsa product URL")
    parser.add_argument("--garment-type", default="top", help="top/pants/dress/skirt")
    parser.add_argument("--size", default=None, help="Size label (e.g. M)")
    parser.add_argument("--front-index", type=int, default=0, help="Front image index")
    parser.add_argument("--back-index", type=int, default=1, help="Back image index")
    parser.add_argument("--height-cm", type=float, default=170)
    parser.add_argument("--weight-kg", type=float, default=65)
    parser.add_argument("--use-playwright", action="store_true", help="Try Playwright for size scraping")
    parser.add_argument("--publish-to-frontend", action="store_true", help="Copy outputs to frontend/public/test_artifacts")
    args = parser.parse_args()

    product = fetch_product_info(args.url)
    product_id = product["product_id"] or "unknown"
    image_urls = product["image_urls"]

    front_url, back_url = select_front_back(image_urls, args.front_index, args.back_index)

    date_tag = datetime.now().strftime("%Y%m%d")
    run_id = f"{product_id}_{datetime.now().strftime('%H%M%S')}"
    output_dir = TEST_OUTPUT_ROOT / "crawled" / date_tag / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    product_info_path = output_dir / "product.json"
    product_info_path.write_text(json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8")

    front_path = download_image(front_url, output_dir / "front.jpg")
    back_path = download_image(back_url, output_dir / "back.jpg")

    sizes: Dict[str, Dict[str, float]] = asyncio.run(
        _scrape_sizes(product_id, args.url, args.use_playwright)
    )
    size_data_path = output_dir / "sizes.json"
    size_data_path.write_text(json.dumps(sizes, ensure_ascii=False, indent=2), encoding="utf-8")

    target_cm = select_size_measurements(sizes, args.size)

    front_img = Image.open(front_path)
    back_img = Image.open(back_path)

    glb_path = run_pipeline(
        front_img=front_img,
        back_img=back_img,
        garment_type=args.garment_type,
        target_cm=target_cm,
        height_cm=args.height_cm,
        weight_kg=args.weight_kg,
        output_dir=output_dir,
    )

    if args.publish_to_frontend:
        _publish_to_frontend(output_dir, "crawled", date_tag, run_id)

    logger.info(f"Saved outputs to: {output_dir}")
    logger.info(f"GLB: {glb_path}")


if __name__ == "__main__":
    main()
