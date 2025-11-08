#!/usr/bin/env python3
"""
Test script to mimic the full scrape + store flow
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.binance_square_scraper import BinanceSquareScraper
from app.db import SessionLocal, engine
from app.models import NewsArticle, Base
from datetime import datetime, timezone

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def test_full_flow():
    print("="*80)
    print("🧪 TESTING FULL SCRAPE + STORE FLOW FOR BNB")
    print("="*80)
    
    db = SessionLocal()
    scraper = BinanceSquareScraper(headless=True)
    
    try:
        coin = 'BNB'
        print(f"\n🔍 Scraping Binance Square for #{coin}...")
        articles = scraper.fetch_articles(coin, max_articles=20, time_window_minutes=15)
        
        print(f"\n📊 Found {len(articles)} articles")
        
        if articles:
            print(f"\n💾 Storing articles in database...")
            stored_count = 0
            
            # Store articles in database (deduplicate by post_id)
            for article in articles:
                post_id = article.get('post_id')
                
                # Skip if no post_id or already exists
                if post_id:
                    existing = db.query(NewsArticle).filter(
                        NewsArticle.news_url == article.get('url')
                    ).first()
                    
                    if existing:
                        print(f"  ⏭ Skipping duplicate: {article.get('title', 'N/A')[:50]}")
                        continue
                
                # Extract sentiment from content (look for Bullish/Bearish)
                content = article.get('content', '')
                sentiment = 'NEUTRAL'
                if 'Bullish' in content:
                    sentiment = 'BULLISH'
                elif 'Bearish' in content:
                    sentiment = 'BEARISH'
                
                news_article = NewsArticle(
                    title=article.get('title', '')[:200],  # Limit title length
                    news_url=article.get('url', ''),
                    text=content,  # Use content field, not text
                    source_name='Binance Square',
                    sentiment=sentiment,
                    tickers=coin,  # Tag with the coin we searched for
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    date=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(news_article)
                stored_count += 1
                print(f"  ✅ Storing: [{sentiment}] {article.get('title', 'N/A')[:60]}...")
            
            db.commit()
            print(f"\n✅ Successfully stored {stored_count} new articles")
            
            # Verify they're in the database
            print(f"\n🔍 Verifying storage...")
            recent = db.query(NewsArticle).filter(
                NewsArticle.tickers == coin,
                NewsArticle.source_name == 'Binance Square'
            ).order_by(NewsArticle.created_at.desc()).limit(5).all()
            
            print(f"Found {len(recent)} recent articles for {coin}:")
            for art in recent:
                print(f"  - [{art.sentiment}] {art.title[:60]}... (Text: {len(art.text)} chars)")
        
        else:
            print("\n⚠️  No articles found within 15-minute window")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close_driver()
        db.close()
        print("\n✅ Test complete")

if __name__ == '__main__':
    test_full_flow()

