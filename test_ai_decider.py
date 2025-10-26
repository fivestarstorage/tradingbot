#!/usr/bin/env python3
"""
Test AI Decider to see why signals aren't being created
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal
from app.ai_decider import AIDecider
from app.models import NewsArticle, Signal
from datetime import datetime, timedelta

def test_ai_decider():
    print("=" * 80)
    print("Testing AI Decider")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Get recent news (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_news = db.query(NewsArticle).filter(
            NewsArticle.created_at >= recent_cutoff
        ).all()
        
        print(f"\n📰 Found {len(recent_news)} news articles in last 24h")
        
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
        print(f"\n🎯 Extracted {len(symbols)} unique tickers")
        print(f"   Top 10: {', '.join(symbols[:10])}")
        print(f"\n   Most mentioned: {sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]}")
        
        # Check existing signals
        existing_signals = db.query(Signal).count()
        print(f"\n📊 Existing signals in database: {existing_signals}")
        
        # Run AI Decider
        print(f"\n🤖 Running AI Decider with {len(symbols)} symbols...")
        ai_decider = AIDecider()
        signals = ai_decider.decide(db, symbols)
        
        print(f"\n✅ AI Decider returned {len(signals)} signals")
        
        if signals:
            print("\n📋 Signals created:")
            for i, sig in enumerate(signals[:10], 1):
                print(f"   {i}. {sig.symbol}: {sig.action} ({sig.confidence}%) - {(sig.reasoning or '')[:60]}")
            if len(signals) > 10:
                print(f"   ... and {len(signals) - 10} more")
        else:
            print("\n⚠️  No signals were created!")
            print("\nDebugging info:")
            print(f"   - OpenAI Key configured: {bool(os.getenv('OPENAI_API_KEY'))}")
            print(f"   - Total symbols to analyze: {len(symbols)}")
            print(f"   - Recent news articles: {len(recent_news)}")
            
            # Check if any articles have sentiment
            with_sentiment = [a for a in recent_news if a.sentiment]
            print(f"   - Articles with sentiment: {len(with_sentiment)}")
            
            if with_sentiment:
                print(f"\n   Sample articles with sentiment:")
                for article in with_sentiment[:3]:
                    print(f"      - {article.title[:50]}")
                    print(f"        Tickers: {article.tickers}")
                    print(f"        Sentiment: {article.sentiment}")
        
        # Check final signal count in DB
        final_signals = db.query(Signal).count()
        print(f"\n📊 Final signals in database: {final_signals} (was {existing_signals})")
        print(f"   New signals added: {final_signals - existing_signals}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_ai_decider()

