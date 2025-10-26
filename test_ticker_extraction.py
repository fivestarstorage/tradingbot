#!/usr/bin/env python3
"""
Test ticker extraction from Binance Square (without saving to DB)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.news_service import scrape_binance_square

print("=" * 80)
print("Testing Ticker Extraction from Binance Square")
print("=" * 80)

try:
    articles = scrape_binance_square()
    
    print(f"\n✅ Scraped {len(articles)} articles")
    
    articles_with_tickers = [a for a in articles if a['tickers']]
    print(f"📊 Articles with tickers: {len(articles_with_tickers)}")
    
    if articles_with_tickers:
        print("\n📋 Sample articles with tickers:")
        for i, article in enumerate(articles_with_tickers[:10], 1):
            print(f"\n{i}. {article['title'][:70]}")
            print(f"   Tickers: {', '.join(article['tickers'])}")
            print(f"   Sentiment: {article['sentiment']}")
    else:
        print("\n⚠️  No articles with tickers found!")
        print("\nSample titles (first 5):")
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article['title'][:80]}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

