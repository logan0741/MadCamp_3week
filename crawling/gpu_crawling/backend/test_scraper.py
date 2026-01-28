"""
Quick test script for Musinsa scraper
"""
import asyncio
import json
from services.scraper import scrape_musinsa_product, resolve_onelink_url

async def test_scraper():
    # Test 1: OneLink URL resolution
    print("=" * 50)
    print("Test 1: Resolving OneLink URL")
    print("=" * 50)
    onelink_url = "https://musinsa.onelink.me/ANAQ/nz6i135t"
    
    try:
        resolved = await resolve_onelink_url(onelink_url)
        print(f"Original: {onelink_url}")
        print(f"Resolved: {resolved}")
    except Exception as e:
        print(f"Error resolving URL: {e}")
    
    # Test 2: Full scraping with direct URL
    print("\n" + "=" * 50)
    print("Test 2: Scraping Musinsa product")
    print("=" * 50)
    
    # Use a direct Musinsa URL for faster test
    direct_url = "https://www.musinsa.com/products/4316145"
    
    try:
        result = await scrape_musinsa_product(direct_url, "4316145")
        
        print(f"\n✅ Scraping completed!")
        print(f"Product ID: {result.get('product_id')}")
        print(f"Title: {result.get('title')}")
        print(f"Brand: {result.get('brand')}")
        print(f"Price: {result.get('price'):,}원" if result.get('price') else "Price: None")
        print(f"Original Price: {result.get('original_price'):,}원" if result.get('original_price') else "Original: None")
        print(f"Discount: {result.get('discount_rate')}%" if result.get('discount_rate') else "Discount: None")
        print(f"Thumbnail: {result.get('thumbnail_url')[:60]}..." if result.get('thumbnail_url') else "Thumbnail: None")
        print(f"Images: {len(result.get('image_urls', []))} found")
        
        # Save result to JSON for inspection
        with open("test_scrape_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📁 Full result saved to: test_scrape_result.json")
        
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scraper())
