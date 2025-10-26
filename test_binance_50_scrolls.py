#!/usr/bin/env python3
"""
Test Binance Square scraper with 50 scrolls
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.news_service import scrape_binance_square

print("=" * 80)
print("Testing Binance Square Scraper (50 Scrolls)")
print("=" * 80)

try:
    articles = scrape_binance_square()
    
    print("\n" + "=" * 80)
    print(f"RESULT: Scraped {len(articles)} articles")
    print("=" * 80)
    
    if articles:
        print("\nFirst 15 articles:")
        for i, article in enumerate(articles[:15], 1):
            tickers = ', '.join(article['tickers']) if article['tickers'] else 'None'
            print(f"{i}. {article['title'][:60]}")
            print(f"   Tickers: {tickers} | Sentiment: {article['sentiment']}")
    else:
        print("\n⚠️  No articles scraped")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

