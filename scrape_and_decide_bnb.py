#!/usr/bin/env python3
"""
Simple script: Scrape BNB posts from Binance Square and make AI trading decision
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.binance_square_scraper import BinanceSquareScraper
from dotenv import load_dotenv
import openai
from datetime import datetime

load_dotenv()

def analyze_with_ai(articles):
    """
    Feed articles to OpenAI and get trading decision
    Returns: {'decision': 'BUY/SELL/HOLD', 'score': 0-100, 'reasoning': str}
    """
    
    # Prepare content for AI
    articles_text = ""
    for i, art in enumerate(articles, 1):
        content = art.get('content', '')[:500]  # Limit each article
        articles_text += f"\n\n--- Post {i} ---\n{content}"
    
    prompt = f"""You are a crypto trading AI analyzing recent Binance Square posts about BNB.

RECENT POSTS FROM BINANCE SQUARE (last 15 minutes):
{articles_text}

Based on the SENTIMENT and ENTHUSIASM in these posts, provide a trading recommendation.

Respond in this EXACT format:
DECISION: [BUY/SELL/HOLD]
SCORE: [0-100 where 0=extremely bearish, 50=neutral, 100=extremely bullish]
REASONING: [One paragraph explanation]

Consider:
- Positive/bullish language → Higher score, potentially BUY
- Negative/bearish language → Lower score, potentially SELL  
- Mixed or low enthusiasm → HOLD
- Look for actual trading sentiment, not just generic mentions
"""

    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a crypto trading analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        # Parse response
        lines = result.strip().split('\n')
        decision = "HOLD"
        score = 50
        reasoning = ""
        
        for line in lines:
            if line.startswith('DECISION:'):
                decision = line.split(':', 1)[1].strip()
            elif line.startswith('SCORE:'):
                score_text = line.split(':', 1)[1].strip()
                # Extract number from text like "75" or "75/100"
                import re
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    score = int(score_match.group(1))
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
        
        # Get remaining reasoning if multiline
        if 'REASONING:' in result:
            reasoning_start = result.index('REASONING:') + len('REASONING:')
            reasoning = result[reasoning_start:].strip()
        
        return {
            'decision': decision,
            'score': score,
            'reasoning': reasoning,
            'raw_response': result
        }
        
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return {
            'decision': 'HOLD',
            'score': 50,
            'reasoning': f'Error getting AI decision: {e}',
            'raw_response': ''
        }


def main():
    print("="*80)
    print("🤖 BNB TRADING DECISION - Based on Binance Square Sentiment")
    print("="*80)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Scrape Binance Square
    print("📰 STEP 1: Scraping Binance Square for #BNB (last 15 minutes)...")
    print("-"*80)
    
    scraper = BinanceSquareScraper(headless=True)
    
    try:
        articles = scraper.fetch_articles('BNB', max_articles=20, time_window_minutes=15)
        
        if not articles:
            print("⚠️  No posts found in the last 15 minutes!")
            print("   Decision: HOLD (no data)")
            return
        
        print(f"✅ Found {len(articles)} posts within last 15 minutes\n")
        
        # Show each article
        print("📋 ARTICLES:")
        print("-"*80)
        for i, art in enumerate(articles, 1):
            title = art.get('title', 'N/A')
            content_preview = art.get('content', '')[:150].replace('\n', ' ')
            url = art.get('url', 'N/A')
            posted_at = art.get('posted_at', 'Unknown')
            
            # Extract sentiment from content
            content_full = art.get('content', '')
            sentiment = 'NEUTRAL'
            if 'Bullish' in content_full:
                sentiment = '🟢 BULLISH'
            elif 'Bearish' in content_full:
                sentiment = '🔴 BEARISH'
            else:
                sentiment = '⚪ NEUTRAL'
            
            print(f"\n{i}. {sentiment}")
            print(f"   Title: {title[:80]}")
            print(f"   Preview: {content_preview}...")
            print(f"   Posted: {posted_at}")
            print(f"   URL: {url}")
        
        print("\n" + "="*80)
        print("🤖 STEP 2: Feeding to AI for Trading Decision...")
        print("-"*80)
        
        # Step 2: Get AI decision
        ai_result = analyze_with_ai(articles)
        
        # Step 3: Display results
        print()
        print("="*80)
        print("📊 TRADING DECISION")
        print("="*80)
        print()
        print(f"🎯 DECISION: {ai_result['decision']}")
        print(f"📈 SENTIMENT SCORE: {ai_result['score']}/100")
        print()
        print(f"💡 REASONING:")
        print(f"   {ai_result['reasoning']}")
        print()
        print("="*80)
        
        # Recommendation
        if ai_result['decision'] == 'BUY':
            print("✅ RECOMMENDATION: Consider opening a LONG position on BNB")
        elif ai_result['decision'] == 'SELL':
            print("❌ RECOMMENDATION: Consider opening a SHORT position or closing LONG")
        else:
            print("⏸️  RECOMMENDATION: Wait for clearer signals before trading")
        
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close_driver()


if __name__ == '__main__':
    main()

