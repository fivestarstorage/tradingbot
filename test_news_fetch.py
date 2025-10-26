#!/usr/bin/env python3
"""
Test the news fetch function to verify it's working correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal
from app.news_service import fetch_and_store_news

print("=" * 80)
print("Testing News Fetch Function")
print("=" * 80)

db = SessionLocal()

# Get the CryptoNews API key from environment
api_key = os.getenv('CRYPTONEWS_API_KEY', '')

print(f"\nCryptoNews API Key: {'✅ Set' if api_key else '❌ Not set'}")
print("\nStarting news fetch...")
print("-" * 80)

try:
    result = fetch_and_store_news(db, api_key)
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Total fetched: {result.get('total', 0)}")
    print(f"Inserted: {result.get('inserted', 0)}")
    print(f"Updated: {result.get('updated', 0)}")
    print(f"Skipped: {result.get('skipped', 0)}")
    print("=" * 80)
    
    if result.get('total', 0) > 0:
        print("\n✅ News fetch completed successfully!")
    else:
        print("\n⚠️  No news fetched - check if sources are working")
    
except Exception as e:
    print(f"\n❌ Error during news fetch: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

