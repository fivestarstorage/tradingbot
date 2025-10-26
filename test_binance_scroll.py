#!/usr/bin/env python3
"""
Test Binance Square scraper to verify it loads more posts
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.news_service import scrape_binance_square

print("=" * 80)
print("Testing Binance Square Scraper (Enhanced Scrolling)")
print("=" * 80)

try:
    articles = scrape_binance_square()
    
    print("\n" + "=" * 80)
    print(f"RESULT: Scraped {len(articles)} articles")
    print("=" * 80)
    
    if articles:
        print("\nFirst 10 articles:")
        for i, article in enumerate(articles[:10], 1):
            print(f"\n{i}. {article['title'][:70]}")
            print(f"   Tickers: {', '.join(article['tickers']) or 'None'}")
            print(f"   Time: {article['timestamp']}")
    else:
        print("\n⚠️  No articles scraped")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

