import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.getcwd())

from services.scraper import scrape_musinsa_product
from services.product_service import ProductService
from core.database import SessionLocal

async def test_scraping_logic():
    print("🚀 Starting Scraping Test...")
    
    # Test URL (Musinsa Product)
    test_url = "https://www.musinsa.com/products/4316145" # Example ID
    
    print(f"Testing URL: {test_url}")
    
    try:
        # 1. Scrape Logic
        result = await scrape_musinsa_product(test_url, "4316145")
        
        if result.get("title"):
            print(f"✅ Scraping Success!")
            print(f"Title: {result['title']}")
            print(f"Price: {result['price']}")
            print(f"Brand: {result['brand']}")
        else:
            print("❌ Scraping returned empty data.")
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_scraping_logic())
