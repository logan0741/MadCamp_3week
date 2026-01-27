"""
Test OneLink URL scraping
"""
import asyncio
from scraper import scrape_musinsa_product

async def test():
    url = 'https://musinsa.onelink.me/ANAQ/nz6i135t'
    print(f"Testing OneLink: {url}\n")
    
    result = await scrape_musinsa_product(url, 'onelink_test')
    
    print("=== Result ===")
    print(f"Title: {result.get('title')}")
    print(f"Brand: {result.get('brand')}")
    print(f"Price: {result.get('price'):,}원" if result.get('price') else "Price: None")
    print(f"Original: {result.get('original_price'):,}원" if result.get('original_price') else "Original: None")
    print(f"Discount: {result.get('discount_rate')}%")
    print(f"Images: {len(result.get('image_urls', []))}")
    print(f"Product ID: {result.get('product_id')}")

asyncio.run(test())
