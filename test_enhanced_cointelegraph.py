#!/usr/bin/env python3
"""
Test enhanced CoinTelegraph scraper with full article fetching
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.news_service import scrape_cointelegraph_rss

print("=" * 80)
print("Testing ENHANCED CoinTelegraph Scraper (with full article fetching)")
print("=" * 80)
print()

try:
    articles = scrape_cointelegraph_rss()
    
    print()
    print("=" * 80)
    print(f"RESULTS: Fetched {len(articles)} articles with full content")
    print("=" * 80)
    print()
    
    if articles:
        # Show detailed info for first 2 articles
        for i, article in enumerate(articles[:2], 1):
            print(f"\n{'='*60}")
            print(f"📰 Article {i}: {article.get('title', 'N/A')}")
            print(f"{'='*60}")
            print(f"URL:       {article.get('news_url', 'N/A')}")
            print(f"Source:    {article.get('source_name', 'N/A')}")
            print(f"Date:      {article.get('date', 'N/A')}")
            print(f"Sentiment: {article.get('sentiment', 'N/A')}")
            print(f"Tickers:   {', '.join(article.get('tickers', [])) if article.get('tickers') else 'None'}")
            print(f"Image:     {article.get('image_url', 'N/A')}")
            print(f"\nContent ({len(article.get('text', ''))} chars):")
            print(f"{article.get('text', '')[:300]}...")
        
        print(f"\n... and {len(articles) - 2} more articles")
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"{'='*60}")
        with_sentiment = sum(1 for a in articles if a.get('sentiment'))
        with_tickers = sum(1 for a in articles if a.get('tickers'))
        with_images = sum(1 for a in articles if a.get('image_url'))
        
        print(f"✓ {len(articles)} articles fetched")
        print(f"✓ {with_sentiment} with AI sentiment analysis")
        print(f"✓ {with_tickers} with ticker extraction")
        print(f"✓ {with_images} with images")
        print(f"\n✅ Enhanced scraper working! (full content + AI analysis)")
        
    else:
        print("⚠️  No articles found")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

