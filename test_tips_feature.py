#!/usr/bin/env python3
"""
Comprehensive test script for the Tips feature
Tests scraping, AI analysis, database storage, and API endpoints
"""

import sys
import os
import json
from datetime import datetime, timezone
from app.db import get_db
from app.tips_service import (
    TipsScraper,
    extract_coins_with_ai,
    fetch_and_analyze_tips,
    get_top_tips,
    update_or_create_tip,
    fetch_coin_price_data
)
from app.models import CommunityTip


def test_scraper():
    """Test the Binance Square hashtag scraper"""
    print("\n" + "="*80)
    print("🧪 TEST 1: BINANCE SQUARE HASHTAG SCRAPER")
    print("="*80 + "\n")
    
    try:
        scraper = TipsScraper(headless=False)  # Visible to see scrolling
        
        # Test scraping one URL
        url = "https://www.binance.com/en/square/hashtag/marketrebound?displayName=MarketRebound"
        print(f"📰 Scraping: {url}")
        
        posts = scraper.scrape_hashtag_page(url, max_posts=10)
        
        print(f"\n✅ Scraped {len(posts)} posts")
        
        if posts:
            print("\n📝 Sample posts:")
            for idx, post in enumerate(posts[:3], 1):
                print(f"\nPost #{idx}:")
                print(f"  Source: {post['source']}")
                print(f"  Timestamp: {post['timestamp']}")
                print(f"  Content: {post['content'][:150]}...")
        
        return len(posts) > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_analysis():
    """Test AI coin extraction from posts"""
    print("\n" + "="*80)
    print("🧪 TEST 2: AI COIN EXTRACTION")
    print("="*80 + "\n")
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return False
        
        # Create sample posts
        sample_posts = [
            {
                'source': '#MarketRebound',
                'content': 'BTC is looking bullish! Strong support at 95k, expecting breakout to 100k soon. Very excited about this move! 🚀',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'source': '#CPIWatch',
                'content': 'ETH showing incredible strength. The fundamentals are solid and the price action is amazing. Going to moon! 🌙',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            {
                'source': '#WriteToEarnUpgrade',
                'content': 'SOL ecosystem is on fire! Solana is the future of crypto. Price will skyrocket. Already bought more!',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
        ]
        
        print("📊 Analyzing sample posts with AI...")
        coins = extract_coins_with_ai(sample_posts, api_key)
        
        print(f"\n✅ Extracted {len(coins)} coins")
        
        if coins:
            print("\n💎 Extracted coins:")
            for coin in coins:
                print(f"\n{coin['coin']} ({coin.get('coin_name', 'N/A')})")
                print(f"  Sentiment: {coin.get('sentiment_label')} ({coin.get('sentiment_score')}/100)")
                print(f"  Enthusiasm: {coin.get('enthusiasm_score')}/100")
                print(f"  Reason: {coin.get('trending_reason', 'N/A')[:100]}...")
        
        return len(coins) > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_operations():
    """Test database storage and retrieval"""
    print("\n" + "="*80)
    print("🧪 TEST 3: DATABASE OPERATIONS")
    print("="*80 + "\n")
    
    try:
        db = next(get_db())
        
        # Test creating a tip
        print("📝 Creating test tip...")
        test_coin_data = {
            'coin': 'TEST',
            'coin_name': 'Test Coin',
            'sentiment_score': 85.5,
            'sentiment_label': 'BULLISH',
            'enthusiasm_score': 90.0,
            'community_summary': 'Test community is very enthusiastic',
            'trending_reason': 'Testing the tips feature',
            'post_snippets': ['Test snippet 1', 'Test snippet 2']
        }
        
        tip = update_or_create_tip(db, test_coin_data, ['#Test'])
        db.commit()
        
        print(f"✅ Created tip for {tip.coin}")
        print(f"  Sentiment: {tip.sentiment_score:.1f}")
        print(f"  Enthusiasm: {tip.enthusiasm_score:.1f}")
        
        # Test retrieving tips
        print("\n📚 Retrieving all tips...")
        tips = get_top_tips(db, limit=10)
        
        print(f"✅ Retrieved {len(tips)} tips")
        
        if tips:
            print("\n📋 Top tips:")
            for tip_dict in tips[:3]:
                print(f"\n{tip_dict['coin']}")
                print(f"  Effective Sentiment: {tip_dict['effective_sentiment']:.1f}")
                print(f"  Mentions: {tip_dict['mention_count']}")
        
        # Clean up test data
        db.query(CommunityTip).filter(CommunityTip.coin == 'TEST').delete()
        db.commit()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_price_fetching():
    """Test fetching price data from Binance"""
    print("\n" + "="*80)
    print("🧪 TEST 4: PRICE DATA FETCHING")
    print("="*80 + "\n")
    
    try:
        print("💰 Fetching BTC price data...")
        price_data = fetch_coin_price_data('BTC')
        
        if price_data:
            print(f"✅ BTC Price Data:")
            print(f"  Current Price: ${price_data.get('current_price', 0):,.2f}")
            print(f"  24h Change: {price_data.get('price_change_24h', 0):.2f}%")
            print(f"  24h Volume: {price_data.get('volume_24h', 0):,.0f}")
            return True
        else:
            print("❌ No price data returned")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline():
    """Test the complete tips pipeline"""
    print("\n" + "="*80)
    print("🧪 TEST 5: FULL PIPELINE (Scrape → Analyze → Store)")
    print("="*80 + "\n")
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return False
        
        db = next(get_db())
        
        print("🚀 Running full tips pipeline...")
        print("This will:")
        print("  1. Scrape all 3 Binance Square hashtags")
        print("  2. Extract coins with AI")
        print("  3. Fetch price data")
        print("  4. Store in database with sentiment tracking")
        print()
        
        fetch_and_analyze_tips(db, api_key)
        
        print("\n📊 Checking results...")
        tips = get_top_tips(db, limit=10)
        
        print(f"\n✅ Pipeline complete! {len(tips)} tips in database")
        
        if tips:
            print("\n🏆 Top 5 Tips:")
            for idx, tip in enumerate(tips[:5], 1):
                print(f"\n{idx}. {tip['coin']} ({tip.get('coin_name', 'N/A')})")
                print(f"   Sentiment: {tip['sentiment_score']:.1f} ({tip['sentiment_label']})")
                print(f"   Enthusiasm: {tip['enthusiasm_score']:.1f}")
                print(f"   Mentions: {tip['mention_count']}")
                if tip.get('current_price'):
                    print(f"   Price: ${tip['current_price']:,.2f}")
                print(f"   Reason: {tip.get('trending_reason', 'N/A')[:80]}...")
        
        return len(tips) > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test the API endpoints"""
    print("\n" + "="*80)
    print("🧪 TEST 6: API ENDPOINTS")
    print("="*80 + "\n")
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        
        # Test GET /api/tips
        print("📡 Testing GET /api/tips...")
        response = requests.get(f"{base_url}/api/tips?limit=5", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response OK")
            print(f"   Count: {data.get('count', 0)}")
            
            if data.get('tips'):
                print(f"\n   Sample tip: {data['tips'][0]['coin']}")
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
        
        # Test GET /api/tips/{coin}
        if data.get('tips') and len(data['tips']) > 0:
            coin = data['tips'][0]['coin']
            print(f"\n📡 Testing GET /api/tips/{coin}...")
            response = requests.get(f"{base_url}/api/tips/{coin}", timeout=10)
            
            if response.status_code == 200:
                tip_data = response.json()
                print(f"✅ Got tip for {coin}")
            else:
                print(f"❌ Failed to get tip for {coin}")
                return False
        
        print("\n✅ All API tests passed")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server")
        print("   Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀 "*20)
    print("COMMUNITY TIPS FEATURE - COMPREHENSIVE TEST SUITE")
    print("🚀 "*20 + "\n")
    
    results = {}
    
    # Run tests
    print("⚠️  Some tests may take a few minutes...")
    print()
    
    # Test 1: Scraper
    results['scraper'] = test_scraper()
    
    # Test 2: AI Analysis
    results['ai_analysis'] = test_ai_analysis()
    
    # Test 3: Database
    results['database'] = test_database_operations()
    
    # Test 4: Price Fetching
    results['price_fetching'] = test_price_fetching()
    
    # Test 5: Full Pipeline
    results['full_pipeline'] = test_full_pipeline()
    
    # Test 6: API Endpoints
    results['api_endpoints'] = test_api_endpoints()
    
    # Print Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name:20s}: {status}")
    
    all_passed = all(results.values())
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print("\n" + "="*80)
    if all_passed:
        print(f"🎉 ALL {total_count} TESTS PASSED!")
    else:
        print(f"⚠️  {passed_count}/{total_count} TESTS PASSED")
    print("="*80 + "\n")
    
    print("\n📝 NEXT STEPS:")
    print("  1. Check the database for stored tips")
    print("  2. Open the frontend and click the 'Tips' button")
    print("  3. Verify tips appear in the sidebar")
    print("  4. Click 'Refresh' to manually trigger scraping")
    print("  5. Set up a cron job to run every 10 minutes:")
    print("     */10 * * * * cd /path/to/tradingbot && python3 -c 'from app.db import get_db; from app.tips_service import fetch_and_analyze_tips; import os; db = next(get_db()); fetch_and_analyze_tips(db, os.getenv(\"OPENAI_API_KEY\"))'")
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

