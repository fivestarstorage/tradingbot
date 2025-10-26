#!/usr/bin/env python3
"""
Test the integrated Binance Square scraper in the news service.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.news_service import scrape_binance_square, parse_relative_timestamp
from datetime import datetime

def test_relative_timestamp():
    """Test the relative timestamp parser"""
    print("=" * 80)
    print("Testing Relative Timestamp Parser")
    print("=" * 80)
    
    test_cases = [
        "38m",
        "6h",
        "2d",
        "45s",
        "1h",
        "30m"
    ]
    
    now = datetime.utcnow()
    
    for test in test_cases:
        result = parse_relative_timestamp(test)
        diff = now - result
        print(f"  {test:5} -> {result.strftime('%Y-%m-%d %H:%M:%S')} (diff: {diff})")
    
    print()

def test_binance_square():
    """Test the Binance Square scraper"""
    print("=" * 80)
    print("Testing Binance Square Scraper")
    print("=" * 80)
    
    articles = scrape_binance_square()
    
    print(f"\n{'=' * 80}")
    print(f"RESULTS: {len(articles)} articles scraped")
    print("=" * 80)
    
    if articles:
        print("\nFirst 3 articles:")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Source: {article['source_name']}")
            print(f"   Date: {article['date']}")
            print(f"   Sentiment: {article['sentiment']}")
            print(f"   Tickers: {', '.join(article['tickers']) or 'None'}")
            print(f"   URL: {article['news_url']}")
        
        # Check if articles are sorted by date (newest first)
        dates = [a['date'] for a in articles]
        is_sorted = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
        print(f"\n✓ Articles sorted newest to oldest: {is_sorted}")
        
        # Show date range
        if len(articles) > 1:
            oldest = min(dates)
            newest = max(dates)
            print(f"✓ Date range: {oldest.strftime('%Y-%m-%d %H:%M')} to {newest.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("❌ No articles scraped!")
    
    return articles

if __name__ == '__main__':
    test_relative_timestamp()
    articles = test_binance_square()
    
    print(f"\n{'=' * 80}")
    print("Test Complete!")
    print("=" * 80)

