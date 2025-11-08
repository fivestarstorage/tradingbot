#!/usr/bin/env python3
"""
Test script to verify news fetching and scrolling works correctly
"""

import sys
import json
from datetime import datetime, timezone, timedelta
from app.binance_square_scraper import BinanceSquareScraper
from app.db import get_db
from app.news_service import fetch_and_store_news, scrape_binance_square

def test_binance_scraper():
    """Test Binance Square scraper with scrolling"""
    print("\n" + "="*80)
    print("🧪 TESTING BINANCE SQUARE SCRAPER")
    print("="*80 + "\n")
    
    scraper = BinanceSquareScraper(headless=False)  # Run visible to see scrolling
    
    try:
        # Test fetching BTC articles
        print("📰 Fetching BTC articles from Binance Square...")
        articles = scraper.fetch_articles("BTC", max_articles=10)
        
        print(f"\n✅ Successfully fetched {len(articles)} articles")
        print("\n" + "-"*80)
        print("📝 ARTICLE DETAILS:")
        print("-"*80 + "\n")
        
        for idx, article in enumerate(articles, 1):
            print(f"Article #{idx}:")
            print(f"  Title: {article.get('title', 'N/A')[:100]}")
            print(f"  Content: {article.get('content', 'N/A')[:150]}...")
            print(f"  Author: {article.get('author', 'N/A')}")
            print(f"  Published: {article.get('published_date', 'N/A')}")
            print(f"  Source: {article.get('source', 'N/A')}")
            print(f"  URL: {article.get('url', 'N/A')[:80]}")
            print()
        
        # Verify scroll worked by checking timestamps
        print("\n" + "-"*80)
        print("⏰ TIMESTAMP VERIFICATION:")
        print("-"*80 + "\n")
        
        now = datetime.now(timezone.utc)
        fifteen_min_ago = now - timedelta(minutes=15)
        
        within_window = 0
        for article in articles:
            pub_date = article.get('published_date')
            if pub_date:
                if isinstance(pub_date, str):
                    # Try to parse it
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        continue
                
                age_minutes = (now - pub_date).total_seconds() / 60
                within_15min = pub_date >= fifteen_min_ago
                
                print(f"  Article: {article.get('title', 'N/A')[:50]}")
                print(f"    Age: {age_minutes:.1f} minutes")
                print(f"    Within 15min window: {'✅' if within_15min else '❌'}")
                
                if within_15min:
                    within_window += 1
        
        print(f"\n📊 {within_window}/{len(articles)} articles within 15-minute window")
        
        return len(articles) > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        scraper.close_driver()


def test_news_service():
    """Test the news service integration"""
    print("\n" + "="*80)
    print("🧪 TESTING NEWS SERVICE (Binance Square)")
    print("="*80 + "\n")
    
    try:
        db = next(get_db())
        
        # Test scraping Binance Square
        print("📰 Scraping Binance Square news...")
        articles_data = scrape_binance_square()
        
        print(f"\n✅ Successfully scraped {len(articles_data)} articles from Binance Square")
        print("\n" + "-"*80)
        print("📝 ARTICLE SUMMARY:")
        print("-"*80 + "\n")
        
        for idx, article in enumerate(articles_data[:5], 1):  # Show first 5
            print(f"Article #{idx}:")
            print(f"  Title: {article.get('title', 'N/A')[:80]}")
            print(f"  Coin: {article.get('coin', 'N/A')}")
            print(f"  Published: {article.get('published_date', 'N/A')}")
            print(f"  Source: {article.get('source', 'N/A')}")
            print(f"  Content preview: {article.get('content', 'N/A')[:100]}...")
            print()
        
        # Now test storing in DB
        print("\n📦 Testing full fetch and store...")
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            fetch_and_store_news(db, api_key)
            print("✅ News fetched and stored successfully")
        else:
            print("⚠️ No API key, skipping storage test")
        
        return len(articles_data) > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🚀 STARTING NEWS & SCROLL FUNCTION TESTS\n")
    
    results = {
        "binance_scraper": False,
        "news_service": False
    }
    
    # Test 1: Binance Square Scraper with Scrolling
    results["binance_scraper"] = test_binance_scraper()
    
    # Test 2: News Service Integration
    results["news_service"] = test_news_service()
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - Review output above")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

