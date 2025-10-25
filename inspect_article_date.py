#!/usr/bin/env python3
"""
Inspect a CoinDesk article to find the date structure
"""
import requests
from bs4 import BeautifulSoup

url = 'https://www.coindesk.com/markets/2025/10/25/xrp-leads-gains-on-ripple-moves-bitcoin-holds-usd111k-as-uptober-dud-heads-for-last-week'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("Fetching article...")
resp = requests.get(url, headers=headers, timeout=20)
print(f"Status: {resp.status_code}")
print()

soup = BeautifulSoup(resp.content, 'lxml')

# Look for all time tags
print("=" * 80)
print("ALL <time> TAGS:")
print("=" * 80)
time_tags = soup.find_all('time')
print(f"Found {len(time_tags)} time tags")
for i, tag in enumerate(time_tags, 1):
    print(f"\n{i}. Tag: {tag}")
    print(f"   datetime attribute: {tag.get('datetime')}")
    print(f"   text: {tag.get_text(strip=True)}")

# Look for meta tags with dates
print("\n" + "=" * 80)
print("META TAGS WITH DATES:")
print("=" * 80)
for prop in ['article:published_time', 'article:modified_time', 'og:published_time', 'published_time']:
    meta = soup.find('meta', property=prop) or soup.find('meta', {'name': prop})
    if meta:
        print(f"{prop}: {meta.get('content')}")

# Look for script tags with structured data (JSON-LD)
print("\n" + "=" * 80)
print("JSON-LD STRUCTURED DATA:")
print("=" * 80)
scripts = soup.find_all('script', type='application/ld+json')
if scripts:
    print(f"Found {len(scripts)} JSON-LD scripts")
    for i, script in enumerate(scripts[:2], 1):
        print(f"\n{i}. Content preview:")
        print(script.string[:500] if script.string else "No content")
else:
    print("No JSON-LD found")

