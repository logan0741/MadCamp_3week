import httpx
import asyncio
import os

# Configuration
BACKEND_URL = "http://localhost:8000"

async def run_e2e_test():
    print(f"🚀 Starting E2E Price Tracker Test on {BACKEND_URL}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Health Check
        print(f"\n1. Checking Health...")
        health_resp = await client.get(f"{BACKEND_URL}/health")
        if health_resp.status_code == 200:
            print("   ✅ Health Check Passed")
        else:
            print(f"   ❌ Health Check Failed: {health_resp.status_code}")
            return

        # 2. Add/Scrape Product (via scraping a new URL or just checking list)
        # Since we don't have a direct 'add product' endpoint exposed in v1 (it's usually done via search or request)
        # Let's check the product list first
        print(f"\n2. Checking Product List...")
        products_resp = await client.get(f"{BACKEND_URL}/api/v1/products/") # Verify correct endpoint in products.py next
        
        # NOTE: If the list is empty, we might need a way to add one.
        # Assuming the verify_backend_core.py script ran first, there should be at least one product.
        
        if products_resp.status_code == 200:
            products = products_resp.json()
            print(f"   ✅ Got {len(products)} products")
            if products:
                print(f"   Example: {products[0]['title']} - {products[0]['current_price']}")
                
                test_product_id = products[0]['id']
                
                # 3. Check Price History
                print(f"\n3. Checking Price History for Product {test_product_id}...")
                history_resp = await client.get(f"{BACKEND_URL}/api/v1/products/{test_product_id}/history")
                
                if history_resp.status_code == 200:
                    history = history_resp.json()
                    print(f"   ✅ History retrieved: {len(history['history'])} records")
                else:
                    print(f"   ❌ History Check Failed: {history_resp.status_code}")

                # 4. Filter Options (if available)
                # print(f"\n4. Checking Filter Options...")
                # filters_resp = await client.get(f"{BACKEND_URL}/api/v1/products/filters")
                # if filters_resp.status_code == 200:
                #    print("   ✅ Filters retrieved")
                
            else:
                print("   ⚠️ No products found. Run verify_backend_core.py first or implement product addition.")
        else:
             # Try without trailing slash
             products_resp = await client.get(f"{BACKEND_URL}/api/v1/products")
             if products_resp.status_code == 200:
                 print("   ✅ Got products (without trailing slash)")
             else:
                 print(f"   ❌ Product List Failed: {products_resp.status_code}")

        # 5. Admin Scheduler Status
        print(f"\n5. Checking Scheduler Status...")
        scheduler_resp = await client.get(f"{BACKEND_URL}/admin/scheduler-status")
        if scheduler_resp.status_code == 200:
            status = scheduler_resp.json()
            print(f"   ✅ Scheduler Running: {status['is_running']}")
            print(f"   📅 Jobs: {len(status['jobs'])}")
        else:
            print(f"   ❌ Scheduler Check Failed: {scheduler_resp.status_code}")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
