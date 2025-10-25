#!/usr/bin/env python3
"""
Test script for CoinTelegraph RSS scraper
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.news_service import scrape_cointelegraph_rss

def test_cointelegraph_scraper():
    print("=" * 80)
    print("Testing CoinTelegraph RSS Scraper")
    print("=" * 80)
    print()
    
    try:
        articles = scrape_cointelegraph_rss()
        
        print()
        print("=" * 80)
        print(f"RESULTS: Found {len(articles)} articles")
        print("=" * 80)
        print()
        
        if articles:
            for i, article in enumerate(articles, 1):
                print(f"\n📰 Article {i}:")
                print(f"  Title: {article.get('title', 'N/A')}")
                print(f"  URL: {article.get('news_url', 'N/A')}")
                print(f"  Source: {article.get('source_name', 'N/A')}")
                print(f"  Sentiment: {article.get('sentiment', 'N/A')}")
                print(f"  Tickers: {', '.join(article.get('tickers', [])) if article.get('tickers') else 'None'}")
                print(f"  Date: {article.get('date', 'N/A')}")
                print(f"  Content preview: {article.get('text', '')[:100]}...")
        else:
            print("⚠️  No articles found")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return len(articles) > 0

if __name__ == "__main__":
    success = test_cointelegraph_scraper()
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")
    sys.exit(0 if success else 1)

