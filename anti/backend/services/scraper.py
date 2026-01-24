"""
Musinsa Product Scraper using Playwright Network Interception
- Handles OneLink share URLs (musinsa.onelink.me)
- Captures internal API responses for reliable data extraction
- Bypasses bot detection with realistic user simulation
"""
from playwright.async_api import async_playwright, Response
from typing import Dict, Optional, List
import re
import json
import asyncio


async def resolve_onelink_url(url: str) -> str:
    """
    Resolve Musinsa OneLink share URL to actual product URL
    
    Args:
        url: OneLink URL like https://musinsa.onelink.me/ANAQ/xxx
        
    Returns:
        Actual product URL like https://www.musinsa.com/products/xxx
    """
    if 'onelink.me' not in url and 'musinsa.app.link' not in url:
        return url
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
            )
            page = await context.new_page()
            
            # Follow redirects to get final URL
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            final_url = page.url
            
            await browser.close()
            return final_url
    except Exception as e:
        print(f"Failed to resolve OneLink URL: {e}")
        return url


def extract_musinsa_id_from_url(url: str) -> Optional[str]:
    """
    Extract product ID from various Musinsa URL formats
    """
    patterns = [
        r'/products/(\d+)',           # New format: /products/123456
        r'/app/goods/(\d+)',          # Old format: /app/goods/123456
        r'goodsNo=(\d+)',             # Query param format
        r'/(\d+)\?',                  # Number before query
        r'/(\d+)$'                    # Number at end
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


async def scrape_musinsa_with_interception(url: str, musinsa_id: str) -> Dict:
    """
    Scrape Musinsa product using Network Interception
    
    This approach captures the actual API responses from Musinsa's internal APIs,
    which is more reliable than DOM scraping.
    
    Args:
        url: Full product URL (can be OneLink or direct URL)
        musinsa_id: Extracted product ID
        
    Returns:
        Dict with title, brand, thumbnail_url, image_urls, price, original_price, discount_rate
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
    
    # Store captured API data
    captured_data = {
        "product_info": None,
        "images": []
    }
    
    async def handle_response(response: Response):
        """Intercept and capture API responses"""
        try:
            url = response.url
            
            # Capture product detail API response
            if '/api/goods/' in url or '/api/product/' in url or 'goods' in url:
                if response.status == 200:
                    try:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            data = await response.json()
                            if isinstance(data, dict):
                                # Store product data
                                if 'data' in data:
                                    captured_data["product_info"] = data.get('data', data)
                                else:
                                    captured_data["product_info"] = data
                    except:
                        pass
                        
            # Capture image URLs from any image-related API
            if ('image' in url.lower() or 'cdn' in url.lower()) and '.jpg' in url.lower():
                if url not in captured_data["images"]:
                    captured_data["images"].append(url)
                    
        except Exception as e:
            pass
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR'
            )
            page = await context.new_page()
            
            # Set up network interception
            page.on('response', handle_response)
            
            # Navigate with realistic behavior
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Simulate human-like scrolling to trigger lazy-loaded content
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.5)
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.5)
            
            # Wait for content to load
            await asyncio.sleep(1)
            
            # Try to extract from captured API data first
            if captured_data["product_info"]:
                info = captured_data["product_info"]
                result["title"] = info.get("goodsNm") or info.get("name") or info.get("productName")
                result["brand"] = info.get("brandNm") or info.get("brand") or info.get("brandName")
                result["price"] = info.get("goodsPrice") or info.get("price") or info.get("salePrice")
                result["original_price"] = info.get("normalPrice") or info.get("originPrice") or info.get("consumerPrice")
                result["discount_rate"] = info.get("discountRate") or info.get("saleRate")
                
                # Get images from API
                if "imageList" in info:
                    result["image_urls"] = [img.get("imageUrl") or img.get("url") for img in info["imageList"]]
                elif "images" in info:
                    result["image_urls"] = info["images"] if isinstance(info["images"], list) else [info["images"]]
            
            # Fallback to DOM scraping if API capture failed
            if not result["title"]:
                # Title extraction
                title_selectors = [
                    '[class*="product_title"] [class*="name"]',
                    '[class*="ProductName"]',
                    'h1[class*="title"]',
                    '.product-detail__name',
                    'span.text-body_13px_bold'
                ]
                for selector in title_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            result["title"] = (await element.inner_text()).strip()
                            break
                    except:
                        continue
            
            if not result["brand"]:
                # Brand extraction
                brand_selectors = [
                    '[class*="product_title"] a[class*="brand"]',
                    '[class*="BrandName"]',
                    '.product-detail__brand',
                    'a.text-body_13px_semi'
                ]
                for selector in brand_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            result["brand"] = (await element.inner_text()).strip()
                            break
                    except:
                        continue
            
            # Image extraction from DOM
            if not result["image_urls"]:
                img_selectors = [
                    'div[class*="gallery"] img',
                    'div[class*="swiper"] img[src*="cdn"]',
                    'div[class*="product"] img[src*="musinsa"]',
                    '.product-img img'
                ]
                for selector in img_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            src = await element.get_attribute('src')
                            if src:
                                if not src.startswith('http'):
                                    src = 'https:' + src
                                # Get high resolution version
                                src = re.sub(r'_\d+\.', '_500.', src)
                                if src not in result["image_urls"]:
                                    result["image_urls"].append(src)
                        if result["image_urls"]:
                            break
                    except:
                        continue
            
            # Add captured CDN images
            for img_url in captured_data["images"]:
                if img_url not in result["image_urls"]:
                    result["image_urls"].append(img_url)
            
            # Set thumbnail
            if result["image_urls"] and not result["thumbnail_url"]:
                result["thumbnail_url"] = result["image_urls"][0]
            
            # Price extraction from DOM
            if not result["price"]:
                price_selectors = [
                    '[class*="price"] [class*="final"]',
                    '[class*="ProductPrice"]',
                    'span[class*="price-now"]',
                    '.product-price__price'
                ]
                for selector in price_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            price_text = await element.inner_text()
                            price_match = re.search(r'[\d,]+', price_text)
                            if price_match:
                                result["price"] = int(price_match.group().replace(',', ''))
                                break
                    except:
                        continue
            
            # Original price extraction
            if not result["original_price"]:
                orig_selectors = [
                    '[class*="price"] [class*="origin"]',
                    '[class*="OriginPrice"]',
                    '.product-price__origin'
                ]
                for selector in orig_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            price_text = await element.inner_text()
                            price_match = re.search(r'[\d,]+', price_text)
                            if price_match:
                                result["original_price"] = int(price_match.group().replace(',', ''))
                                break
                    except:
                        continue
            
            # Discount extraction
            if not result["discount_rate"]:
                discount_selectors = [
                    '[class*="discount"]',
                    '[class*="rate"]',
                    '.product-price__rate'
                ]
                for selector in discount_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            discount_text = await element.inner_text()
                            discount_match = re.search(r'(\d+)%?', discount_text)
                            if discount_match:
                                result["discount_rate"] = int(discount_match.group(1))
                                break
                    except:
                        continue
            
            # Calculate discount rate if we have both prices
            if result["original_price"] and result["price"] and not result["discount_rate"]:
                if result["original_price"] > result["price"]:
                    result["discount_rate"] = int(
                        ((result["original_price"] - result["price"]) / result["original_price"]) * 100
                    )
            
            await browser.close()
            
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
    
    return result


async def scrape_musinsa_product(url: str, musinsa_id: str) -> Dict:
    """
    Main entry point for Musinsa scraping
    Handles OneLink URLs and uses Network Interception
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
        # Even for direct URLs, ensure we have the correct ID
        extracted_id = extract_musinsa_id_from_url(url)
        if extracted_id:
            musinsa_id = extracted_id
    
    # Use the interception-based scraper
    result = await scrape_musinsa_with_interception(resolved_url, musinsa_id)
    
    # Ensure product_id is set in result
    result["product_id"] = musinsa_id
    
    return result


async def scrape_current_price(url: str) -> Optional[Dict]:
    """
    Quick price check for daily logging (lighter version)
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Resolve OneLink if needed
            if 'onelink.me' in url:
                url = await resolve_onelink_url(url)
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(2)
            
            result = {"price": None, "discount_rate": None}
            
            # Price selectors
            price_selectors = [
                '[class*="price"] [class*="final"]',
                '.product_price__price',
                '.product-detail__price',
                '.price_now'
            ]
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.inner_text()
                        price_match = re.search(r'[\d,]+', price_text)
                        if price_match:
                            result["price"] = int(price_match.group().replace(',', ''))
                        break
                except:
                    continue
            
            # Discount selectors
            discount_selectors = [
                '[class*="discount"]',
                '.product_price__rate',
                '.product-detail__discount'
            ]
            for selector in discount_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        discount_text = await element.inner_text()
                        discount_match = re.search(r'(\d+)%?', discount_text)
                        if discount_match:
                            result["discount_rate"] = int(discount_match.group(1))
                        break
                except:
                    continue
            
            await browser.close()
            
            if result["price"]:
                return result
            return None
            
    except Exception as e:
        print(f"Price scraping error: {e}")
        return None
