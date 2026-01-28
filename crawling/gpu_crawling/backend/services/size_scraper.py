"""
Musinsa size scraper (best-effort).

Tries multiple endpoints and extracts size measurements from JSON/HTML.
Falls back gracefully if size data is not accessible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
import re

import httpx

from services.musinsa_proxy import proxify_url, proxy_headers, httpx_proxies
import logging

logger = logging.getLogger(__name__)


_CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _CACHE_DIR / "size_cache.json"
_CACHE_TTL_HOURS = 24


MEASUREMENT_ALIASES: Dict[str, Iterable[str]] = {
    "length": ["length", "총장", "기장", "총길이"],
    "shoulder": ["shoulder", "어깨"],
    "chest": ["chest", "가슴", "품", "가슴단면"],
    "bust": ["bust", "가슴둘레"],
    "sleeve": ["sleeve", "소매", "소매길이"],
    "waist": ["waist", "허리"],
    "hip": ["hip", "엉덩이", "힙"],
    "inseam": ["inseam", "인심", "밑위"],
}

SIZE_LABEL_KEYS = [
    "size",
    "sizeName",
    "size_name",
    "sizeLabel",
    "label",
    "name",
    "option",
    "optionName",
    "optName",
    "sz",
    "value",
    "title",
]


@dataclass
class SizeScrapeResult:
    sizes: Dict[str, Dict[str, float]]
    source: Optional[str] = None
    updated_at: Optional[str] = None


def _normalize_size_label(label: str) -> str:
    label = label.strip()
    if not label:
        return label
    return label.upper()


def _normalize_measurement_key(key: str) -> Optional[str]:
    key_lower = key.lower()
    for normalized, aliases in MEASUREMENT_ALIASES.items():
        for alias in aliases:
            if alias in key_lower:
                return normalized
    return None


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", " ")
        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
    return None


def _extract_measurements(node: Any) -> Dict[str, float]:
    measurements: Dict[str, float] = {}

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                normalized = _normalize_measurement_key(str(key))
                if normalized:
                    parsed = _parse_number(val)
                    if parsed is not None:
                        measurements[normalized] = parsed
                walk(val)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(node)
    return measurements


def _extract_size_label(item: Dict[str, Any]) -> Optional[str]:
    for key in SIZE_LABEL_KEYS:
        if key in item and isinstance(item[key], str):
            return _normalize_size_label(item[key])

    for value in item.values():
        if isinstance(value, str):
            candidate = value.strip()
            if re.fullmatch(r"[A-Za-z]{1,4}", candidate) or re.fullmatch(r"\d{2,3}", candidate):
                return _normalize_size_label(candidate)
    return None


def _parse_size_list(items: List[Any]) -> Dict[str, Dict[str, float]]:
    sizes: Dict[str, Dict[str, float]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        size_label = _extract_size_label(item)
        if not size_label:
            continue
        measurements = _extract_measurements(item)
        if measurements:
            sizes[size_label] = measurements
    return sizes


def _parse_table_object(obj: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    header_keys = None
    rows = None

    for header_key in ("header", "headers", "columns"):
        if header_key in obj and isinstance(obj[header_key], list):
            header_keys = obj[header_key]
            break

    for row_key in ("rows", "values", "data", "items"):
        if row_key in obj and isinstance(obj[row_key], list):
            rows = obj[row_key]
            break

    if not header_keys or not rows:
        return {}

    normalized_headers = [str(h) for h in header_keys]
    sizes: Dict[str, Dict[str, float]] = {}

    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != len(normalized_headers):
            continue
        row_dict = dict(zip(normalized_headers, row))
        size_label = _extract_size_label(row_dict)
        if not size_label:
            continue
        measurements = _extract_measurements(row_dict)
        if measurements:
            sizes[size_label] = measurements
    return sizes


def extract_size_table(data: Any) -> Dict[str, Dict[str, float]]:
    candidates: List[Tuple[int, Dict[str, Dict[str, float]]]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            sizes = _parse_size_list(node)
            if sizes:
                score = sum(len(m) for m in sizes.values()) + len(sizes) * 2
                candidates.append((score, sizes))
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            table_sizes = _parse_table_object(node)
            if table_sizes:
                score = sum(len(m) for m in table_sizes.values()) + len(table_sizes) * 2
                candidates.append((score, table_sizes))
            for value in node.values():
                walk(value)

    walk(data)

    if not candidates:
        return {}
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _load_cache() -> Dict[str, Any]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def get_cached_sizes(product_id: int | str) -> Optional[SizeScrapeResult]:
    cache = _load_cache()
    entry = cache.get(str(product_id))
    if not entry:
        return None
    updated_at = entry.get("updated_at")
    if updated_at:
        try:
            ts = datetime.fromisoformat(updated_at)
            if datetime.utcnow() - ts > timedelta(hours=_CACHE_TTL_HOURS):
                return None
        except Exception:
            pass
    return SizeScrapeResult(
        sizes=entry.get("sizes", {}),
        source=entry.get("source"),
        updated_at=entry.get("updated_at"),
    )


def save_cached_sizes(product_id: int | str, result: SizeScrapeResult) -> None:
    cache = _load_cache()
    cache[str(product_id)] = {
        "sizes": result.sizes,
        "source": result.source,
        "updated_at": result.updated_at,
    }
    _save_cache(cache)


def _build_candidate_requests(product_id: str) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
    return [
        (f"https://goods-detail.musinsa.com/api/goods/{product_id}", None),
        (f"https://goods-detail.musinsa.com/api/goods/{product_id}/size", None),
        (f"https://goods-detail.musinsa.com/api/goods/{product_id}/sizes", None),
        (f"https://goods-detail.musinsa.com/api/goods/{product_id}/detail", None),
        (f"https://api.musinsa.com/api2/goods/{product_id}", None),
        (f"https://api.musinsa.com/api2/goods/{product_id}/size", None),
        (f"https://www.musinsa.com/api2/goods/{product_id}/size", None),
        (f"https://www.musinsa.com/app/goods/{product_id}", None),
        (f"https://www.musinsa.com/products/{product_id}", None),
    ]


def _parse_next_data_from_html(html: str) -> Optional[Any]:
    match = re.search(r'__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


async def _try_fetch_sizes_from_url(
    client: httpx.AsyncClient,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    referer: Optional[str] = None,
) -> Tuple[Dict[str, Dict[str, float]], Optional[str]]:
    headers = {
        "User-Agent": "Mozilla/5.0",
    }
    if referer:
        headers["Referer"] = referer
    headers.update(proxy_headers())

    try:
        response = await client.get(
            proxify_url(url),
            params=params,
            headers=headers,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        logger.warning(f"Size scrape request failed: {url} ({exc})")
        return {}, None
    content_type = response.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            data = response.json()
        except Exception:
            return {}, None
        sizes = extract_size_table(data)
        if sizes:
            return sizes, url
    if "text/html" in content_type:
        data = _parse_next_data_from_html(response.text)
        if data:
            sizes = extract_size_table(data)
            if sizes:
                return sizes, url
    return {}, None


async def scrape_musinsa_sizes(
    product_id: str,
    product_url: Optional[str] = None,
    use_playwright: bool = False,
) -> SizeScrapeResult:
    """
    Best-effort size scrape. Returns empty sizes if not found.
    """
    async with httpx.AsyncClient(timeout=12.0, proxies=httpx_proxies()) as client:
        for url, params in _build_candidate_requests(product_id):
            sizes, source = await _try_fetch_sizes_from_url(
                client,
                url=url,
                params=params,
                referer=product_url or f"https://www.musinsa.com/products/{product_id}",
            )
            if sizes:
                return SizeScrapeResult(
                    sizes=sizes,
                    source=source,
                    updated_at=datetime.utcnow().isoformat(),
                )

        if product_url:
            sizes, source = await _try_fetch_sizes_from_url(
                client,
                url=product_url,
                referer=product_url,
            )
            if sizes:
                return SizeScrapeResult(
                    sizes=sizes,
                    source=source,
                    updated_at=datetime.utcnow().isoformat(),
                )

    if use_playwright:
        sizes = await _scrape_sizes_via_playwright(product_url or f"https://www.musinsa.com/products/{product_id}")
        if sizes:
            return SizeScrapeResult(
                sizes=sizes,
                source="playwright-intercept",
                updated_at=datetime.utcnow().isoformat(),
            )

    return SizeScrapeResult(sizes={}, source=None, updated_at=datetime.utcnow().isoformat())


async def _scrape_sizes_via_playwright(url: str) -> Dict[str, Dict[str, float]]:
    """
    Optional: use Playwright to intercept XHR responses and extract size data.
    Requires playwright + browser installed.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        logger.warning(f"Playwright not available for size scraping: {exc}")
        return {}

    results: List[Dict[str, Dict[str, float]]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="ko-KR",
        )
        page = await context.new_page()

        async def handle_response(response) -> None:
            try:
                if "application/json" not in (response.headers.get("content-type") or ""):
                    return
                data = await response.json()
                sizes = extract_size_table(data)
                if sizes:
                    results.append(sizes)
            except Exception:
                return

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            await browser.close()
            return {}

        # Try clicking size tab if present
        for label in ("사이즈", "SIZE", "size"):
            try:
                await page.get_by_text(label, exact=False).click(timeout=1500)
                break
            except Exception:
                continue

        await page.wait_for_timeout(2000)
        await browser.close()

    if not results:
        return {}

    # Choose the result with most measurements
    scored = [(sum(len(m) for m in sizes.values()), sizes) for sizes in results]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]
