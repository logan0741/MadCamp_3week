import asyncio
import sys
import os
import logging

print(f"DEBUG: sys.executable: {sys.executable}")
print(f"DEBUG: sys.path: {sys.path}")

# Add project root and backend to python path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.database import SessionLocal, engine, Base
from domain.entities import Product, PriceLog
from services.product_service import ProductService
from services.scheduler import price_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_backend_core():
    print("🚀 Starting Backend Core Verification...")
    
    # 1. Initialize Database
    try:
        print("\n1. Initializing Database...")
        # Create tables if not exist
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return

    # 2. Add Test Product
    test_musinsa_id = "4316145" # Using the one from test_scraper.py
    test_url = f"https://www.musinsa.com/products/{test_musinsa_id}"
    
    try:
        print(f"\n2. Adding/Checking Test Product ({test_musinsa_id})...")
        
        # Check if exists
        product = ProductService.get_product_by_musinsa_id(db, test_musinsa_id)
        
        if not product:
            print("   Product not found, creating new one...")
            # We need to scrape first to get info, or just mock it for this test if scraper is flaky?
            # Let's try to actually scrape to verify scraper integration
            from services.scraper import scrape_musinsa_product
            print("   Scraping product info...")
            product_info = await scrape_musinsa_product(test_url, test_musinsa_id)
            
            if not product_info.get("title"):
                 print("   ❌ Scraping failed, cannot create product.")
                 return
            
            product = ProductService.create_product(db, test_musinsa_id, test_url, product_info)
            print(f"   ✅ Created product: {product.title}")
        else:
            print(f"   ✅ Product already exists: {product.title}")

    except Exception as e:
        print(f"   ❌ Product creation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Test Price Logging (Scheduler Logic)
    try:
        print(f"\n3. Testing Price Update Logic for Product ID {product.id}...")
        
        # Manually trigger update for this single product
        result = await price_scheduler.update_single_product(product.id)
        
        if result:
            print(f"   ✅ Price update successful: {result['price']} won")
            
            # Verify it's in DB
            latest_price = ProductService.get_latest_price(db, product.id)
            if latest_price and latest_price.price == result['price']:
                print("   ✅ DB verification successful: PriceLog found")
            else:
                print("   ❌ DB verification failed: Latest price mismatch or missing")
        else:
            print("   ❌ Price update returned None (Scraping failed?)")

    except Exception as e:
        print(f"   ❌ Price update test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(verify_backend_core())
