"""
Debug script to capture page HTML and analyze structure
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_page():
    url = "https://www.musinsa.com/products/4316145"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='ko-KR'
        )
        page = await context.new_page()
        
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Wait for content
        await asyncio.sleep(3)
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Get URL after redirects
        final_url = page.url
        print(f"Final URL: {final_url}")
        
        # Try to find key elements
        print("\n=== Looking for elements ===")
        
        # Check for common selectors
        selectors_to_check = [
            # Title selectors
            ('h1', 'h1 tag'),
            ('h2', 'h2 tag'),
            ('[class*="title"]', 'title class'),
            ('[class*="name"]', 'name class'),
            ('[class*="product"]', 'product class'),
            # Price selectors
            ('[class*="price"]', 'price class'),
            ('[class*="Price"]', 'Price class'),
            # Brand selectors
            ('[class*="brand"]', 'brand class'),
            ('[class*="Brand"]', 'Brand class'),
            # Image selectors
            ('img[src*="cdn"]', 'cdn image'),
            ('img[src*="musinsa"]', 'musinsa image'),
        ]
        
        for selector, name in selectors_to_check:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ {name}: {len(elements)} found")
                    # Get first element text/attribute
                    first = elements[0]
                    text = await first.inner_text() if await first.inner_text() else None
                    if text:
                        print(f"   First text: {text[:100]}")
            except Exception as e:
                pass
        
        # Save HTML for analysis
        html = await page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n📁 HTML saved to: debug_page.html ({len(html)} bytes)")
        
        # Take screenshot
        await page.screenshot(path="debug_page.png")
        print("📸 Screenshot saved to: debug_page.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
