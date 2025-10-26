#!/usr/bin/env python3
"""
Manually test the force refresh flow
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal
from app.news_service import fetch_and_store_news
from app.ai_decider import AIDecider
from app.models import NewsArticle, Signal
from datetime import datetime, timedelta

def test_force_refresh():
    print("=" * 80)
    print("Testing Force Refresh Flow")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Step 1: Fetch news
        print("\n[1/3] Fetching news...")
        api_key = os.getenv('CRYPTONEWS_API_KEY', '')
        stats = fetch_and_store_news(db, api_key)
        print(f"   ✓ Total: {stats.get('total', 0)}")
        print(f"   ✓ Inserted: {stats.get('inserted', 0)}")
        print(f"   ✓ Updated: {stats.get('updated', 0)}")
        print(f"   ✓ Skipped: {stats.get('skipped', 0)}")
        
        # Step 2: Extract tickers from recent news
        print("\n[2/3] Extracting tickers from recent news...")
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_news = db.query(NewsArticle).filter(
            NewsArticle.created_at >= recent_cutoff
        ).all()
        
        print(f"   ✓ Found {len(recent_news)} articles in last 24h")
        
        # Extract unique tickers
        all_tickers = set()
        ticker_counts = {}
        for article in recent_news:
            if article.tickers:
                tickers = [t.strip().upper() for t in article.tickers.split(',') if t.strip()]
                for ticker in tickers:
                    all_tickers.add(ticker)
                    if not ticker.endswith('USDT'):
                        all_tickers.add(f"{ticker}USDT")
                    ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        symbols = sorted(list(all_tickers))
        print(f"   ✓ Extracted {len(symbols)} unique tickers")
        
        if symbols:
            print(f"   ✓ Top 10: {', '.join(symbols[:10])}")
            top_mentioned = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   ✓ Most mentioned: {top_mentioned}")
        else:
            print("   ⚠️  No tickers found!")
            print("\n   Checking sample articles:")
            for i, article in enumerate(recent_news[:5], 1):
                print(f"      {i}. {article.title[:60]}")
                print(f"         Tickers: '{article.tickers}'")
                print(f"         Sentiment: {article.sentiment}")
        
        # Step 3: Run AI Decider
        print("\n[3/3] Running AI Decider...")
        if not symbols:
            print("   ⚠️  Skipping AI Decider - no tickers found")
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
            print(f"   Using fallback watchlist: {', '.join(symbols)}")
        
        ai_decider = AIDecider()
        signals = ai_decider.decide(db, symbols)
        
        print(f"   ✓ AI Decider returned {len(signals)} signals")
        
        if signals:
            print("\n   📋 Signals created:")
            for i, sig in enumerate(signals[:10], 1):
                print(f"      {i}. {sig.symbol}: {sig.action} ({sig.confidence}%) - {(sig.reasoning or '')[:60]}")
            if len(signals) > 10:
                print(f"      ... and {len(signals) - 10} more")
        else:
            print("\n   ⚠️  No signals were created!")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✓ News articles: {len(recent_news)} (last 24h)")
        print(f"✓ Tickers extracted: {len(symbols)}")
        print(f"✓ Signals created: {len(signals)}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_force_refresh()

