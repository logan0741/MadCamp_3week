"""
Musinsa Product Scraper using Playwright
"""
from playwright.async_api import async_playwright
from typing import Dict, Optional
import re


async def scrape_musinsa_product(url: str, musinsa_id: str) -> Dict:
    """
    Scrape product information from Musinsa website
    
    Args:
        url: Full product URL
        musinsa_id: Extracted product ID
    
    Returns:
        Dict with title, brand, thumbnail_url, price, discount_rate
    """
    result = {
        "title": None,
        "brand": None,
        "thumbnail_url": None,
        "price": None,
        "discount_rate": None
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Navigate to product page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for main content
            await page.wait_for_selector('.product_title, .product-detail__title', timeout=10000)
            
            # Extract title
            title_selectors = [
                '.product_title__name',
                '.product-detail__name',
                '.product_title',
                'h1.title'
            ]
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        result["title"] = await element.inner_text()
                        break
                except:
                    continue
            
            # Extract brand
            brand_selectors = [
                '.product_title__brand',
                '.product-detail__brand',
                '.brand_name'
            ]
            for selector in brand_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        result["brand"] = await element.inner_text()
                        break
                except:
                    continue
            
            # Extract thumbnail
            img_selectors = [
                '.product_gallery_item img',
                '.product-detail__image img',
                '.product_image img',
                '.swiper-slide img'
            ]
            for selector in img_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        result["thumbnail_url"] = await element.get_attribute('src')
                        if result["thumbnail_url"] and not result["thumbnail_url"].startswith('http'):
                            result["thumbnail_url"] = 'https:' + result["thumbnail_url"]
                        break
                except:
                    continue
            
            # Extract price
            price_selectors = [
                '.product_price__price',
                '.product-detail__price',
                '.price_now',
                '.product_price span:last-child'
            ]
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.inner_text()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+', price_text)
                        if price_match:
                            result["price"] = int(price_match.group().replace(',', ''))
                        break
                except:
                    continue
            
            # Extract discount rate
            discount_selectors = [
                '.product_price__rate',
                '.product-detail__discount',
                '.discount_rate'
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
            
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
        # Return partial results even on error
    
    return result


async def scrape_current_price(url: str) -> Optional[Dict]:
    """
    Scrape only the current price for daily price logging
    
    Returns:
        Dict with price and discount_rate, or None if failed
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(2000)  # Wait for dynamic content
            
            result = {"price": None, "discount_rate": None}
            
            # Try to get price
            price_selectors = [
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
            
            # Try to get discount
            discount_selectors = [
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
