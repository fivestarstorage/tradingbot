#!/usr/bin/env python3
"""
Try to find Binance's news API endpoint
"""
import requests
import json

# Binance likely has an API endpoint for their news
# Let's try common patterns

endpoints_to_try = [
    'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageSize=20',
    'https://www.binance.com/bapi/composite/v1/public/square/news/list?pageSize=20',
    'https://www.binance.com/api/v1/public/square/news',
    'https://www.binance.com/gateway-api/v1/public/cms/article/list/query',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Origin': 'https://www.binance.com',
    'Referer': 'https://www.binance.com/en/square/news/all'
}

print("Trying to find Binance news API endpoint...\n")

for url in endpoints_to_try:
    print(f"Trying: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  ✓ Got JSON response!")
                print(f"  Keys: {list(data.keys())}")
                
                # Save sample
                with open('/tmp/binance_api_response.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Response saved to /tmp/binance_api_response.json")
                
                # Try to find articles/news in response
                if 'data' in data:
                    print(f"  Data type: {type(data['data'])}")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"  ✓ Found {len(data['data'])} items!")
                        print(f"  First item keys: {list(data['data'][0].keys())[:10]}")
                        break
                        
            except json.JSONDecodeError:
                print(f"  ✗ Not JSON")
        else:
            print(f"  ✗ Failed")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()

print("\nAlternative: We could use Binance Blog RSS if available:")
rss_url = "https://www.binance.com/en/blog/rss.xml"
print(f"Trying: {rss_url}")
try:
    resp = requests.get(rss_url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✓ RSS feed available!")
        with open('/tmp/binance_rss.xml', 'wb') as f:
            f.write(resp.content)
        print("✓ Saved to /tmp/binance_rss.xml")
except Exception as e:
    print(f"✗ {e}")

