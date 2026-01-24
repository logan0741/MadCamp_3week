"""
Analyze HTML to find correct selectors
"""
import re

with open('debug_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find price-related patterns
print('=== Looking for price patterns ===')
price_patterns = re.findall(r'class="([^"]*(?:price|Price)[^"]*)"', html)
for p in list(set(price_patterns))[:15]:
    print(f'  {p}')

# Find title patterns  
print('\n=== Looking for title/name patterns ===')
title_patterns = re.findall(r'class="([^"]*(?:title|name|Title|Name)[^"]*)"', html)
for p in list(set(title_patterns))[:15]:
    print(f'  {p}')

# Find brand patterns
print('\n=== Looking for brand patterns ===')
brand_patterns = re.findall(r'class="([^"]*(?:brand|Brand)[^"]*)"', html)
for p in list(set(brand_patterns))[:15]:
    print(f'  {p}')

# Find the actual text content around prices
print('\n=== Looking for price values ===')
# Pattern for Korean won format
prices = re.findall(r'>(\d{1,3}(?:,\d{3})+)<|>(\d{1,3}(?:,\d{3})+)원<', html)
flat_prices = [p for pair in prices for p in pair if p]
for p in list(set(flat_prices))[:10]:
    print(f'  {p}원')

# Look for __NEXT_DATA__ which Next.js apps often use
print('\n=== Looking for Next.js data ===')
if '__NEXT_DATA__' in html:
    print('  Found __NEXT_DATA__ script!')
    # Extract it
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
    if match:
        import json
        try:
            data = json.loads(match.group(1))
            # Save for inspection
            with open('next_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print('  Saved to next_data.json')
        except:
            print('  Could not parse JSON')
else:
    print('  No __NEXT_DATA__ found')

# Look for product info in meta tags
print('\n=== Meta tags ===')
meta_patterns = re.findall(r'<meta[^>]*property="og:([^"]*)"[^>]*content="([^"]*)"', html)
for prop, content in meta_patterns:
    if any(x in prop.lower() for x in ['title', 'price', 'image', 'description']):
        print(f'  og:{prop}: {content[:80]}')
