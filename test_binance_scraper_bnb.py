#!/usr/bin/env python3
"""
Test script to see what the Binance Square scraper returns for BNB
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.binance_square_scraper import BinanceSquareScraper
import json

def test_scraper():
    print("="*80)
    print("🧪 TESTING BINANCE SQUARE SCRAPER FOR BNB")
    print("="*80)
    print()
    
    # Initialize scraper (headless=False so we can see what's happening)
    scraper = BinanceSquareScraper(headless=False)
    
    try:
        # Scrape BNB hashtag
        print("📰 Scraping https://www.binance.com/en/square/hashtag/BNB...")
        articles = scraper.fetch_articles('BNB', max_articles=10, time_window_minutes=15)
        
        print()
        print("="*80)
        print(f"✅ SCRAPING COMPLETE - Found {len(articles)} articles")
        print("="*80)
        print()
        
        if articles:
            for idx, article in enumerate(articles, 1):
                print(f"\n📄 Article {idx}:")
                print(f"  Title: {article.get('title', 'N/A')[:100]}")
                print(f"  URL: {article.get('url', 'N/A')}")
                print(f"  Content: {article.get('content', 'N/A')[:150]}...")
                print(f"  Sentiment: {article.get('sentiment', 'N/A')}")
                print(f"  Text length: {len(article.get('text', ''))}")
                print(f"  Raw keys: {list(article.keys())}")
            
            # Save to JSON for inspection
            with open('test_scrape_output.json', 'w') as f:
                json.dump(articles, f, indent=2)
            print(f"\n💾 Full output saved to: test_scrape_output.json")
        else:
            print("⚠️  No articles found!")
            print("   Possible reasons:")
            print("   - No posts in last 15 minutes on #BNB")
            print("   - Scraper couldn't extract content")
            print("   - Website structure changed")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close_driver()
        print("\n✅ Test complete")

if __name__ == '__main__':
    test_scraper()

