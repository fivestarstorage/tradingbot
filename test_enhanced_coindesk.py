#!/usr/bin/env python3
"""
Test script for enhanced CoinDesk scraper with AI analysis
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.news_service import scrape_coindesk_news

def test_enhanced_scraper():
    print("=" * 80)
    print("🧠 TESTING ENHANCED COINDESK SCRAPER WITH AI ANALYSIS")
    print("=" * 80)
    print()
    
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in .env")
        print("   AI analysis will not work without this key")
        print()
        return
    
    print("Fetching and analyzing articles from CoinDesk...")
    print("This will take a while as we fetch each article and analyze it with AI")
    print()
    
    articles = scrape_coindesk_news()
    
    if not articles:
        print("❌ No articles found!")
        return
    
    print()
    print("=" * 80)
    print(f"✅ SUCCESSFULLY PROCESSED {len(articles)} ARTICLES")
    print("=" * 80)
    print()
    
    for i, article in enumerate(articles, 1):
        print(f"📰 Article {i}:")
        print(f"   Title: {article.get('title', 'N/A')[:70]}...")
        print(f"   URL: {article.get('news_url', 'N/A')}")
        print(f"   Published: {article.get('date', 'N/A')}")
        print(f"   Sentiment: {article.get('sentiment', 'N/A')}")
        print(f"   Tickers: {', '.join(article.get('tickers', [])) or 'None'}")
        print(f"   Content Length: {len(article.get('text', ''))} chars")
        print(f"   Has Image: {'Yes' if article.get('image_url') else 'No'}")
        print()
    
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    sentiments = {}
    all_tickers = set()
    
    for article in articles:
        sentiment = article.get('sentiment')
        if sentiment:
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        tickers = article.get('tickers', [])
        all_tickers.update(tickers)
    
    print(f"Sentiment Breakdown:")
    for sentiment, count in sentiments.items():
        print(f"  {sentiment}: {count}")
    
    print()
    print(f"Unique Tickers Found: {', '.join(sorted(all_tickers)) if all_tickers else 'None'}")
    print()
    print(f"Articles with Dates: {sum(1 for a in articles if a.get('date'))}/{len(articles)}")
    print(f"Articles with Images: {sum(1 for a in articles if a.get('image_url'))}/{len(articles)}")
    print()

if __name__ == '__main__':
    test_enhanced_scraper()

