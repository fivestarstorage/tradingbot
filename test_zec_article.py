#!/usr/bin/env python3
"""
Test if ZEC article from CPIWatch is being detected
"""

from app.tips_service import TipsScraper
import os

def test_zec_article():
    print("\n" + "="*80)
    print("🧪 TESTING ZEC ARTICLE DETECTION")
    print("="*80 + "\n")
    
    scraper = TipsScraper(headless=False)  # Visible browser to see what's happening
    
    # Test the CPIWatch URL specifically
    url = "https://www.binance.com/en/square/hashtag/cpiwatch?displayName=CPIWatch"
    
    print(f"📰 Scraping CPIWatch for ZEC article...")
    print(f"🔗 URL: {url}\n")
    
    posts = scraper.scrape_hashtag_page(url, max_posts=50)  # Get more posts
    
    print(f"\n✅ Found {len(posts)} total posts\n")
    
    # Search for ZEC mentions
    zec_posts = []
    for idx, post in enumerate(posts, 1):
        content = post.get('content', '').upper()
        if 'ZEC' in content or '$ZEC' in content or 'ZCASH' in content.upper():
            zec_posts.append(post)
            print(f"🎯 POST #{idx} - ZEC MENTIONED!")
            print(f"   Timestamp: {post.get('timestamp', 'N/A')}")
            print(f"   Content: {post.get('content', '')[:200]}...")
            print()
    
    if zec_posts:
        print(f"✅ SUCCESS: Found {len(zec_posts)} posts mentioning ZEC!")
        print(f"\nℹ️  These posts should be sent to AI for analysis.")
        
        # Test AI extraction with these posts
        print("\n" + "-"*80)
        print("🤖 Testing AI extraction on ZEC posts...")
        print("-"*80 + "\n")
        
        from app.tips_service import extract_coins_with_ai
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            coins = extract_coins_with_ai(zec_posts, api_key)
            
            print(f"✅ AI extracted {len(coins)} coins\n")
            
            for coin in coins:
                print(f"💎 {coin.get('coin')} ({coin.get('coin_name', 'N/A')})")
                print(f"   Sentiment: {coin.get('sentiment_label')} ({coin.get('sentiment_score')}/100)")
                print(f"   Reason: {coin.get('trending_reason', 'N/A')[:100]}...")
                print()
            
            # Check if ZEC was extracted
            zec_found = any(c.get('coin', '').upper() == 'ZEC' for c in coins)
            if zec_found:
                print("🎉 SUCCESS: ZEC was extracted by AI!")
            else:
                print("⚠️  WARNING: ZEC was mentioned in posts but NOT extracted by AI")
                print("   This might be because the AI filtered it out based on sentiment/context")
        else:
            print("⚠️  No OPENAI_API_KEY, skipping AI test")
    else:
        print("❌ FAILURE: No posts mentioning ZEC were found!")
        print("\nPossible reasons:")
        print("  1. The post is older than 10 minutes")
        print("  2. The 'Latest' tab wasn't clicked (using 'Hot' posts)")
        print("  3. The post text wasn't captured correctly")
        print("  4. The scraper couldn't find the post element")
        
        print(f"\nℹ️  Showing all posts found:")
        for idx, post in enumerate(posts[:10], 1):  # Show first 10
            print(f"\n  Post #{idx}:")
            print(f"  {post.get('content', '')[:150]}...")


if __name__ == "__main__":
    test_zec_article()

