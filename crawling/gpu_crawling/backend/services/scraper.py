"""
Musinsa Product Scraper using Playwright Network Interception
- Handles OneLink share URLs (musinsa.onelink.me)
- Extracts data from Next.js __NEXT_DATA__ for reliability
- Bypasses bot detection with realistic user simulation
"""
from playwright.async_api import async_playwright, Response
from typing import Dict, Optional, List
import re
import json
import asyncio
import httpx
from urllib.parse import urljoin

from services.musinsa_proxy import proxify_url, proxy_headers, is_proxy_enabled, httpx_proxies


def _extract_category_info(meta: Dict) -> Dict[str, Optional[str]]:
    """Extract category path and main/sub category names from meta."""
    category = meta.get("category") or {}
    depth_names = [
        category.get("categoryDepth1Name"),
        category.get("categoryDepth2Name"),
        category.get("categoryDepth3Name"),
        category.get("categoryDepth4Name"),
    ]
    parts = [name for name in depth_names if name]

    if not parts:
        base_path = meta.get("baseCategoryFullPath") or ""
        parts = [p.strip() for p in base_path.split(">") if p.strip()]

    category_path = " > ".join(parts) if parts else None
    category_main = parts[0] if parts else None
    category_sub = parts[-1] if parts else None

    return {
        "category_path": category_path,
        "category_main": category_main,
        "category_sub": category_sub,
    }


async def scrape_with_httpx(url: str, musinsa_id: str) -> Dict:
    """
    Fast scraper using httpx - works better in Docker environments.
    Falls back to Playwright if this fails.
    """
    result = {
        "title": None,
        "brand": None,
        "thumbnail_url": None,
        "image_urls": [],
        "price": None,
        "original_price": None,
        "discount_rate": None,
        "product_id": musinsa_id
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.musinsa.com/',
    }
    headers.update(proxy_headers())

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            proxies=httpx_proxies(),
        ) as client:
            response = await client.get(proxify_url(url), headers=headers)

            if response.status_code == 200:
                html = response.text

                # Extract __NEXT_DATA__ from HTML
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
                if match:
                    next_data = json.loads(match.group(1))
                    page_props = next_data.get("props", {}).get("pageProps", {})
                    meta = page_props.get("meta", {}).get("data", {})

                    if meta:
                        result["product_id"] = str(meta.get("goodsNo", musinsa_id))
                        result["title"] = meta.get("goodsNm")

                        brand_info = meta.get("brandInfo", {})
                        result["brand"] = brand_info.get("brandName") or meta.get("brand")

                        price_info = meta.get("goodsPrice", {})
                        print(f"🔍 [DEBUG] Price Info: {price_info}")  # Added Log
                        result["price"] = price_info.get("salePrice")
                        result["original_price"] = price_info.get("normalPrice")
                        result["discount_rate"] = price_info.get("discountRate")

                        thumbnail = meta.get("thumbnailImageUrl", "")
                        if thumbnail:
                            if not thumbnail.startswith("http"):
                                thumbnail = "https://image.msscdn.net" + thumbnail
                            result["thumbnail_url"] = thumbnail

                        goods_images = meta.get("goodsImages", [])
                        for img in goods_images:
                            img_url = img.get("imageUrl", "")
                            if img_url:
                                if not img_url.startswith("http"):
                                    img_url = "https://image.msscdn.net" + img_url
                                result["image_urls"].append(img_url)

                        if not result["image_urls"] and result["thumbnail_url"]:
                            result["image_urls"] = [result["thumbnail_url"]]

                        # Category info
                        result.update(_extract_category_info(meta))

                        # Style/target info from meta
                        result["style_no"] = meta.get("styleNo")
                        result["gender_tags"] = meta.get("genders") or meta.get("sex")

                        print(f"✅ [httpx] Extracted: {result['title']}")
                        return result
    except Exception as e:
        print(f"[httpx] Scraping failed: {e}")

    return result


async def resolve_onelink_url(url: str) -> str:
    """
    Resolve Musinsa OneLink share URL to actual product URL
    """
    if 'onelink.me' not in url and 'musinsa.app.link' not in url:
        return url
    # Prefer proxy-based resolution when outbound HTTPS is blocked
    if is_proxy_enabled():
        current = url
        headers = proxy_headers()
        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=15.0,
                proxies=httpx_proxies(),
            ) as client:
                for _ in range(6):
                    resp = await client.get(proxify_url(current), headers=headers)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("location")
                        if not location:
                            break
                        current = urljoin(current, location)
                        continue
                    break
            return current
        except Exception as e:
            print(f"Failed to resolve OneLink via proxy: {e}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            final_url = page.url
            
            await browser.close()
            return final_url
    except Exception as e:
        print(f"Failed to resolve OneLink URL: {e}")
        return url


def extract_musinsa_id_from_url(url: str) -> Optional[str]:
    """Extract product ID from various Musinsa URL formats"""
    patterns = [
        r'/products/(\d+)',
        r'/app/goods/(\d+)',
        r'goodsNo=(\d+)',
        r'/(\d+)\?',
        r'/(\d+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


async def scrape_musinsa_with_next_data(url: str, musinsa_id: str) -> Dict:
    """
    Scrape Musinsa product using Next.js __NEXT_DATA__
    
    This is the most reliable method - Next.js apps embed all SSR data
    in a script tag that we can easily parse.
    """
    result = {
        "title": None,
        "brand": None,
        "thumbnail_url": None,
        "image_urls": [],
        "price": None,
        "original_price": None,
        "discount_rate": None,
        "product_id": musinsa_id
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR'
            )
            page = await context.new_page()
            
            # Navigate with realistic behavior (use domcontentloaded for faster response)
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)

            # Wait for __NEXT_DATA__ script to be available (with fallback)
            try:
                await page.wait_for_selector('script#__NEXT_DATA__', timeout=15000)
            except Exception:
                # If selector wait fails, give it a bit more time
                await asyncio.sleep(1)
            
            # Try to extract __NEXT_DATA__ - the goldmine!
            try:
                next_data_script = await page.query_selector('script#__NEXT_DATA__')
                if next_data_script:
                    next_data_text = await next_data_script.inner_text()
                    next_data = json.loads(next_data_text)
                    
                    # Navigate to product data
                    page_props = next_data.get("props", {}).get("pageProps", {})
                    meta = page_props.get("meta", {}).get("data", {})
                    
                    if meta:
                        # Extract product info
                        result["product_id"] = str(meta.get("goodsNo", musinsa_id))
                        result["title"] = meta.get("goodsNm")
                        
                        # Brand info
                        brand_info = meta.get("brandInfo", {})
                        result["brand"] = brand_info.get("brandName") or meta.get("brand")
                        
                        # Price info from goodsPrice
                        price_info = meta.get("goodsPrice", {})
                        print(f"🔍 [DEBUG] NEXT_DATA Price Info: {price_info}")  # Added Log
                        result["price"] = price_info.get("salePrice")
                        result["original_price"] = price_info.get("normalPrice")
                        result["discount_rate"] = price_info.get("discountRate")
                        
                        # Thumbnail
                        thumbnail = meta.get("thumbnailImageUrl", "")
                        if thumbnail:
                            if not thumbnail.startswith("http"):
                                thumbnail = "https://image.msscdn.net" + thumbnail
                            result["thumbnail_url"] = thumbnail
                        
                        # All product images
                        goods_images = meta.get("goodsImages", [])
                        for img in goods_images:
                            img_url = img.get("imageUrl", "")
                            if img_url:
                                if not img_url.startswith("http"):
                                    img_url = "https://image.msscdn.net" + img_url
                                result["image_urls"].append(img_url)
                        
                        # If no gallery images, use thumbnail
                        if not result["image_urls"] and result["thumbnail_url"]:
                            result["image_urls"] = [result["thumbnail_url"]]

                        # Category info
                        result.update(_extract_category_info(meta))

                        # Style/target info from meta
                        result["style_no"] = meta.get("styleNo")
                        result["gender_tags"] = meta.get("genders") or meta.get("sex")

                        print(f"✅ Extracted from __NEXT_DATA__: {result['title']}")
                        
            except Exception as e:
                print(f"Failed to parse __NEXT_DATA__: {e}")
            
            # Fallback to DOM scraping if __NEXT_DATA__ failed
            if not result["title"]:
                print("Falling back to DOM scraping...")
                
                # Title from meta og:title or page title
                try:
                    og_title = await page.query_selector('meta[property="og:title"]')
                    if og_title:
                        title = await og_title.get_attribute('content')
                        if title:
                            # Clean up title (remove " - 무신사" suffix)
                            result["title"] = re.sub(r'\s*-\s*사이즈.*$', '', title)
                except:
                    pass
                
                # Price from visible elements
                try:
                    price_elements = await page.query_selector_all('[class*="price"], [class*="Price"]')
                    for el in price_elements:
                        text = await el.inner_text()
                        price_match = re.search(r'([\d,]+)원?', text)
                        if price_match:
                            price_val = int(price_match.group(1).replace(',', ''))
                            if price_val > 0:
                                if not result["price"] or price_val < result["price"]:
                                    result["price"] = price_val
                                if price_val > (result["original_price"] or 0):
                                    result["original_price"] = price_val
                except:
                    pass
            
            await browser.close()
            
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
    
    return result


async def scrape_musinsa_product(url: str, musinsa_id: str) -> Dict:
    """
    Main entry point for Musinsa scraping
    Handles OneLink URLs and uses Next.js data extraction
    Strategy: Try httpx first (fast), fallback to Playwright (reliable)
    """
    resolved_url = url

    # Resolve OneLink URLs first
    if 'onelink.me' in url or 'musinsa.app.link' in url:
        resolved_url = await resolve_onelink_url(url)

        # Extract real product ID from resolved URL
        real_id = extract_musinsa_id_from_url(resolved_url)
        if real_id:
            musinsa_id = real_id
    else:
        # Ensure we have the correct ID
        extracted_id = extract_musinsa_id_from_url(url)
        if extracted_id:
            musinsa_id = extracted_id

    # Try httpx first (faster, works better in Docker)
    result = await scrape_with_httpx(resolved_url, musinsa_id)

    # If httpx failed to get title, fallback to Playwright (skip when proxy is enabled)
    if not result.get("title") and not is_proxy_enabled():
        print("[httpx] Failed, falling back to Playwright...")
        result = await scrape_musinsa_with_next_data(resolved_url, musinsa_id)

    # Ensure product_id is set
    result["product_id"] = musinsa_id

    return result


async def scrape_current_price(url: str) -> Optional[Dict]:
    """Quick price check for daily logging"""
    try:
        # Resolve OneLink if needed
        if 'onelink.me' in url:
            url = await resolve_onelink_url(url)
        
        result = await scrape_with_httpx(url, "")
        if not result.get("price"):
            result = await scrape_musinsa_with_next_data(url, "")
        
        if result.get("price"):
            return {
                "price": result["price"],
                "discount_rate": result.get("discount_rate")
            }
        return None
        
    except Exception as e:
        print(f"Price scraping error: {e}")
        return None
