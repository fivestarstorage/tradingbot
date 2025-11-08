#!/usr/bin/env python3
"""
Community Tips Service
Scrapes Binance Square hashtags and extracts trending coins with sentiment
"""

import os
import re
import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from openai import OpenAI

from .models import CommunityTip
from .db import get_db

# Binance Square hashtag URLs to scrape
HASHTAG_URLS = [
    "https://www.binance.com/en/square/hashtag/writetoearnupgrade?displayName=WriteToEarnUpgrade",
    "https://www.binance.com/en/square/hashtag/marketrebound?displayName=MarketRebound",
    "https://www.binance.com/en/square/hashtag/cpiwatch?displayName=CPIWatch",
]


class TipsScraper:
    """Scraper for Binance Square hashtag pages"""
    
    def __init__(self, headless=True):
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        self.driver = None
    
    def start_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(options=self.options)
    
    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def scrape_hashtag_page(self, url: str, max_posts: int = 20) -> List[Dict]:
        """
        Scrape a single hashtag page for posts within the last 10 minutes
        
        Returns:
            List of post dictionaries with content, author, timestamp
        """
        posts = []
        
        try:
            self.start_driver()
            
            print(f"📰 Scraping: {url}")
            self.driver.get(url)
            time.sleep(5)  # Initial load
            
            # Dismiss cookie banners
            try:
                cookie_buttons = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Accept') or contains(text(), 'accept')]")
                for btn in cookie_buttons[:2]:
                    try:
                        btn.click()
                        time.sleep(1)
                        break
                    except:
                        pass
            except:
                pass
            
            # Click "Latest" tab if available
            print("  🔍 Looking for 'Latest' tab...")
            latest_clicked = False
            try:
                # Wait a bit for page to fully load
                time.sleep(2)
                
                # Try multiple methods to find Latest tab
                latest_buttons = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Latest') or contains(text(), 'latest')]")
                
                print(f"  Found {len(latest_buttons)} elements with 'Latest' text")
                
                for btn in latest_buttons:
                    try:
                        if btn.is_displayed() and 'latest' in btn.text.lower() and len(btn.text.strip()) < 20:
                            print(f"  Attempting to click: '{btn.text}'")
                            
                            # Try regular click first
                            try:
                                btn.click()
                                latest_clicked = True
                                print("  ✅ Clicked 'Latest' tab (regular click)")
                                time.sleep(3)
                                break
                            except:
                                # Try JavaScript click as fallback
                                try:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    latest_clicked = True
                                    print("  ✅ Clicked 'Latest' tab (JavaScript click)")
                                    time.sleep(3)
                                    break
                                except:
                                    continue
                    except:
                        continue
                
                if not latest_clicked:
                    print("  ⚠️  Could not click Latest tab, using default view")
                    
            except Exception as e:
                print(f"  ⚠️  Error finding Latest tab: {e}")
                print("  Using default view")
            
            # Scroll to load more posts (5 scrolls)
            print("  📜 Scrolling to load more posts...")
            for i in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Extract posts
            now = datetime.now(timezone.utc)
            ten_min_ago = now - timedelta(minutes=10)
            
            # Try multiple selectors
            selectors = [
                "article",
                "[class*='post']",
                "[class*='Post']",
                "[class*='feed']",
                "[class*='Feed']",
                "[class*='item']",
                "div[class*='css-']",
            ]
            
            all_elements = []
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > len(all_elements):
                    all_elements = elements
            
            print(f"  Found {len(all_elements)} potential post elements")
            
            posts_checked = 0
            posts_too_old = 0
            
            for element in all_elements[:max_posts * 3]:  # Check more elements
                try:
                    text = element.text.strip()
                    
                    if not text or len(text) < 20:
                        continue
                    
                    posts_checked += 1
                    
                    # Extract timestamp
                    post_time = self._parse_timestamp(text)
                    
                    # Only include posts from last 10 minutes
                    if post_time and post_time >= ten_min_ago:
                        post = {
                            'content': text,
                            'timestamp': post_time.isoformat(),
                            'url': url,
                            'source': self._extract_hashtag_name(url)
                        }
                        posts.append(post)
                        
                        age_minutes = (now - post_time).total_seconds() / 60
                        print(f"  ✓ Post ({age_minutes:.1f}m ago): {text[:60]}...")
                        
                        if len(posts) >= max_posts:
                            break
                    elif post_time and post_time < ten_min_ago:
                        # Post is too old
                        posts_too_old += 1
                    elif not post_time:
                        # No timestamp found, include anyway (might be new)
                        post = {
                            'content': text,
                            'timestamp': now.isoformat(),
                            'url': url,
                            'source': self._extract_hashtag_name(url)
                        }
                        posts.append(post)
                        print(f"  ✓ Post (no timestamp): {text[:60]}...")
                        
                        if len(posts) >= max_posts:
                            break
                    
                except Exception as e:
                    continue
            
            print(f"  📊 Stats: {posts_checked} posts checked, {posts_too_old} too old (>10min), {len(posts)} collected")
            print(f"  ✅ Scraped {len(posts)} posts from {url}")
            return posts
            
        except Exception as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return []
    
    def scrape_all_hashtags(self) -> List[Dict]:
        """Scrape all configured hashtag URLs"""
        all_posts = []
        
        for url in HASHTAG_URLS:
            posts = self.scrape_hashtag_page(url)
            all_posts.extend(posts)
        
        self.close_driver()
        return all_posts
    
    def _parse_timestamp(self, text: str) -> Optional[datetime]:
        """Parse relative timestamp from post text (e.g., '5m', '1h', '30s')"""
        try:
            import re
            
            # Look for patterns like "5m", "1h", "30s", "2d"
            patterns = [
                (r'(\d+)\s*s(?:ec)?(?:ond)?(?:s)?\s*ago', 'seconds'),
                (r'(\d+)\s*m(?:in)?(?:ute)?(?:s)?\s*ago', 'minutes'),
                (r'(\d+)\s*h(?:our)?(?:s)?\s*ago', 'hours'),
                (r'(\d+)\s*d(?:ay)?(?:s)?\s*ago', 'days'),
                # Without "ago"
                (r'(\d+)\s*s$', 'seconds'),
                (r'(\d+)\s*m$', 'minutes'),
                (r'(\d+)\s*h$', 'hours'),
                (r'(\d+)\s*d$', 'days'),
            ]
            
            now = datetime.now(timezone.utc)
            
            for pattern, unit in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = int(match.group(1))
                    
                    if unit == 'seconds':
                        return now - timedelta(seconds=value)
                    elif unit == 'minutes':
                        return now - timedelta(minutes=value)
                    elif unit == 'hours':
                        return now - timedelta(hours=value)
                    elif unit == 'days':
                        return now - timedelta(days=value)
            
            return None
            
        except:
            return None
    
    def _extract_hashtag_name(self, url: str) -> str:
        """Extract hashtag name from URL"""
        try:
            match = re.search(r'hashtag/([^?]+)', url)
            if match:
                return f"#{match.group(1)}"
            return url
        except:
            return url


def extract_coins_with_ai(posts: List[Dict], api_key: str) -> List[Dict]:
    """
    Use AI to analyze posts and extract trending coins with sentiment
    
    Returns:
        List of coin dictionaries with sentiment analysis
    """
    if not posts:
        return []
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Prepare posts text for AI
        posts_text = "\n\n---\n\n".join([
            f"Source: {post['source']}\nContent: {post['content'][:500]}"
            for post in posts[:50]  # Limit to 50 posts
        ])
        
        prompt = f"""Analyze these Binance Square community posts and extract trending cryptocurrency coins.

Posts:
{posts_text}

For each coin that users are enthusiastically discussing, provide:
1. Coin symbol (e.g., BTC, ETH, SOL)
2. Coin full name
3. Sentiment score (0-100, where 100 is extremely bullish)
4. Enthusiasm score (0-100, how excited/energetic users are)
5. Sentiment label (BULLISH, BEARISH, NEUTRAL)
6. Brief summary of community opinion
7. Why this coin is trending
8. Notable post excerpts (2-3 most interesting quotes)

Focus on coins that:
- Users think will rise/moon/pump
- Have strong positive sentiment
- Are being discussed with enthusiasm and conviction
- Show signs of potential growth

Return ONLY a JSON array of coins, no other text:
[
  {{
    "coin": "BTC",
    "coin_name": "Bitcoin",
    "sentiment_score": 85,
    "enthusiasm_score": 90,
    "sentiment_label": "BULLISH",
    "community_summary": "...",
    "trending_reason": "...",
    "post_snippets": ["...", "..."]
  }}
]

If no coins are being discussed enthusiastically, return an empty array: []"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a crypto sentiment analyst extracting trending coins from community discussions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            coins = json.loads(json_match.group(0))
            return coins
        
        return []
        
    except Exception as e:
        print(f"❌ Error analyzing with AI: {e}")
        return []


def fetch_coin_price_data(coin: str) -> Dict:
    """Fetch current price data for a coin from Binance API with 1h, 24h, and 7d changes"""
    try:
        import requests
        
        symbol = f"{coin}USDT"
        
        # Get 24h ticker data
        url_24h = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        response_24h = requests.get(url_24h, timeout=5)
        
        if response_24h.status_code != 200:
            return {}
        
        data_24h = response_24h.json()
        current_price = float(data_24h.get('lastPrice', 0))
        
        result = {
            'current_price': current_price,
            'price_change_24h': float(data_24h.get('priceChangePercent', 0)),
            'volume_24h': float(data_24h.get('volume', 0)),
        }
        
        # Get 1h price change using klines
        try:
            url_1h = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=2"
            response_1h = requests.get(url_1h, timeout=5)
            if response_1h.status_code == 200:
                klines = response_1h.json()
                if len(klines) >= 2:
                    # klines format: [open_time, open, high, low, close, volume, ...]
                    price_1h_ago = float(klines[-2][4])  # Close price of previous hour
                    if price_1h_ago > 0:
                        price_change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
                        result['price_change_1h'] = price_change_1h
        except:
            pass
        
        # Get 7d price change using klines
        try:
            url_7d = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=8"
            response_7d = requests.get(url_7d, timeout=5)
            if response_7d.status_code == 200:
                klines = response_7d.json()
                if len(klines) >= 8:
                    # Get price from 7 days ago
                    price_7d_ago = float(klines[-8][4])  # Close price of 7 days ago
                    if price_7d_ago > 0:
                        price_change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
                        result['price_change_7d'] = price_change_7d
        except:
            pass
        
        return result
        
    except Exception as e:
        print(f"Error fetching price for {coin}: {e}")
        return {}


def update_or_create_tip(db: Session, coin_data: Dict, sources: List[str]) -> CommunityTip:
    """Update existing tip or create new one"""
    
    coin = coin_data['coin'].upper()
    
    # Check if tip already exists
    existing_tip = db.query(CommunityTip).filter(CommunityTip.coin == coin).first()
    
    if existing_tip:
        # Update existing tip
        existing_tip.mention_count += 1
        
        # Update sentiment (weighted average: 70% new, 30% old)
        new_sentiment = coin_data['sentiment_score']
        existing_tip.sentiment_score = (new_sentiment * 0.7) + (existing_tip.sentiment_score * 0.3)
        
        # Update enthusiasm (weighted average)
        new_enthusiasm = coin_data.get('enthusiasm_score', 50)
        existing_tip.enthusiasm_score = (new_enthusiasm * 0.7) + (existing_tip.enthusiasm_score * 0.3)
        
        existing_tip.sentiment_label = coin_data.get('sentiment_label', 'NEUTRAL')
        existing_tip.community_summary = coin_data.get('community_summary', '')
        existing_tip.trending_reason = coin_data.get('trending_reason', '')
        
        # Add new sources
        existing_sources = json.loads(existing_tip.sources) if existing_tip.sources else []
        all_sources = list(set(existing_sources + sources))
        existing_tip.sources = json.dumps(all_sources)
        
        # Add new snippets
        existing_snippets = json.loads(existing_tip.post_snippets) if existing_tip.post_snippets else []
        new_snippets = coin_data.get('post_snippets', [])
        all_snippets = (existing_snippets + new_snippets)[-10:]  # Keep last 10
        existing_tip.post_snippets = json.dumps(all_snippets)
        
        # Reset decay factor (activity refreshes the tip)
        existing_tip.decay_factor = 1.0
        existing_tip.last_updated = datetime.now(timezone.utc)
        
        # Update price data
        price_data = fetch_coin_price_data(coin)
        if price_data:
            existing_tip.current_price = price_data.get('current_price')
            existing_tip.price_change_1h = price_data.get('price_change_1h')
            existing_tip.price_change_24h = price_data.get('price_change_24h')
            existing_tip.price_change_7d = price_data.get('price_change_7d')
            existing_tip.volume_24h = price_data.get('volume_24h')
        
        print(f"  ↻ Updated tip for {coin} (mentions: {existing_tip.mention_count}, sentiment: {existing_tip.sentiment_score:.1f})")
        return existing_tip
    else:
        # Create new tip
        price_data = fetch_coin_price_data(coin)
        
        tip = CommunityTip(
            coin=coin,
            coin_name=coin_data.get('coin_name', coin),
            sentiment_score=coin_data['sentiment_score'],
            sentiment_label=coin_data.get('sentiment_label', 'NEUTRAL'),
            mention_count=1,
            enthusiasm_score=coin_data.get('enthusiasm_score', 50),
            community_summary=coin_data.get('community_summary', ''),
            trending_reason=coin_data.get('trending_reason', ''),
            sources=json.dumps(sources),
            post_snippets=json.dumps(coin_data.get('post_snippets', [])),
            current_price=price_data.get('current_price'),
            price_change_1h=price_data.get('price_change_1h'),
            price_change_24h=price_data.get('price_change_24h'),
            price_change_7d=price_data.get('price_change_7d'),
            volume_24h=price_data.get('volume_24h'),
            decay_factor=1.0
        )
        
        db.add(tip)
        print(f"  + Created new tip for {coin} (sentiment: {tip.sentiment_score:.1f})")
        return tip


def apply_sentiment_decay(db: Session):
    """
    Apply decay to sentiment scores over time
    Tips that aren't reinforced will gradually lose sentiment strength
    """
    try:
        now = datetime.now(timezone.utc)
        decay_rate = 0.05  # 5% decay per 10 minutes
        
        # Get all tips
        tips = db.query(CommunityTip).all()
        
        for tip in tips:
            # Calculate time since last update (in 10-minute intervals)
            # Handle both timezone-aware and naive datetimes from database
            last_updated = tip.last_updated
            if last_updated.tzinfo is None:
                # If naive, treat it as UTC
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            
            time_delta = now - last_updated
            intervals = time_delta.total_seconds() / 600  # 600 seconds = 10 minutes
            
            if intervals > 0:
                # Apply exponential decay
                new_decay = tip.decay_factor * ((1 - decay_rate) ** intervals)
                tip.decay_factor = max(0.1, new_decay)  # Minimum 10% decay factor
        
        db.commit()
        print(f"✅ Applied decay to {len(tips)} tips")
        
    except Exception as e:
        print(f"❌ Error applying decay: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()


def fetch_and_analyze_tips(db: Session, api_key: str):
    """
    Main function to scrape hashtags, analyze posts, and update tips
    Should be run every 10 minutes
    """
    try:
        print("\n" + "="*80)
        print("🎯 FETCHING COMMUNITY TIPS")
        print("="*80)
        
        # Step 1: Apply decay to existing tips
        print("\n⏰ Applying sentiment decay...")
        apply_sentiment_decay(db)
        
        # Step 2: Scrape all hashtag pages
        print("\n📰 Scraping Binance Square hashtags...")
        scraper = TipsScraper(headless=True)
        posts = scraper.scrape_all_hashtags()
        
        if not posts:
            print("⚠️ No posts found")
            return
        
        print(f"\n✅ Scraped {len(posts)} total posts")
        
        # Step 3: Extract coins with AI
        print("\n🤖 Analyzing posts with AI...")
        coins = extract_coins_with_ai(posts, api_key)
        
        if not coins:
            print("⚠️ No trending coins found")
            return
        
        print(f"\n✅ Found {len(coins)} trending coins")
        
        # Step 4: Update or create tips
        print("\n💾 Updating tips database...")
        sources = list(set([post['source'] for post in posts]))
        
        for coin_data in coins:
            try:
                update_or_create_tip(db, coin_data, sources)
            except Exception as e:
                print(f"  ❌ Error processing {coin_data.get('coin', 'unknown')}: {e}")
        
        db.commit()
        
        print("\n" + "="*80)
        print(f"✅ COMPLETED: Updated {len(coins)} tips")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error in fetch_and_analyze_tips: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()


def get_top_tips(db: Session, limit: int = 20) -> List[Dict]:
    """
    Get top trending tips sorted by effective sentiment
    
    Effective sentiment = sentiment_score * decay_factor * enthusiasm_score
    """
    try:
        tips = db.query(CommunityTip).order_by(
            CommunityTip.last_updated.desc()
        ).limit(limit * 2).all()  # Get more than needed for sorting
        
        # Calculate effective score and sort
        tips_with_scores = []
        for tip in tips:
            effective_score = tip.sentiment_score * tip.decay_factor * (tip.enthusiasm_score / 100)
            tips_with_scores.append((tip, effective_score))
        
        # Sort by effective score
        tips_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return [tip.to_dict() for tip, score in tips_with_scores[:limit]]
        
    except Exception as e:
        print(f"❌ Error getting tips: {e}")
        return []

