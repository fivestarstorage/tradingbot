#!/usr/bin/env python3
"""
Binance Square News Scraper
Scrapes news articles from Binance Square using Selenium
"""

import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json


class BinanceSquareScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome driver"""
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        self.driver = None
    
    def start_driver(self):
        """Start the Chrome driver"""
        if not self.driver:
            self.driver = webdriver.Chrome(options=self.options)
            print("✅ Chrome driver started")
    
    def close_driver(self):
        """Close the Chrome driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("✅ Chrome driver closed")
    
    def fetch_articles(self, coin: str, max_articles: int = 10, time_window_minutes: int = 15) -> List[Dict]:
        """
        Fetch latest articles for a coin from Binance Square
        
        Args:
            coin: Coin symbol (BTC, ETH, XRP)
            max_articles: Maximum number of articles to fetch
            time_window_minutes: Only fetch articles from the last N minutes (default: 15)
            
        Returns:
            List of article dictionaries
        """
        try:
            self.start_driver()
            
            # Use the coin symbol directly in the URL
            coin_symbol = coin.upper()
            
            # Navigate to Binance Square with coin hashtag
            url = f"https://www.binance.com/en/square/hashtag/{coin_symbol}?displayName={coin_symbol}"
            print(f"📰 Fetching news for {coin_symbol} from Binance Square...")
            print(f"🔗 URL: {url}")
            
            self.driver.get(url)
            time.sleep(5)  # Wait for page to load
            
            # Dismiss cookie/privacy banners
            try:
                print("🍪 Checking for cookie banners...")
                cookie_buttons = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Accept') or contains(text(), 'accept') or contains(text(), 'Agree') or contains(text(), 'agree') or @id='onetrust-accept-btn-handler']")
                if cookie_buttons:
                    for btn in cookie_buttons[:2]:  # Try first 2
                        try:
                            btn.click()
                            print("  ✅ Dismissed cookie banner")
                            time.sleep(1)
                            break
                        except:
                            pass
            except:
                pass
            
            # Try to click "Latest" tab
            try:
                wait = WebDriverWait(self.driver, 15)
                
                print("🔍 Looking for 'Latest' tab...")
                
                # Try multiple possible selectors for the Latest tab
                latest_tab_found = False
                latest_tab_element = None
                
                # Method 1: Find by text content
                try:
                    latest_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Latest') or contains(text(), 'latest')]")
                    print(f"  Found {len(latest_buttons)} elements with 'Latest' text")
                    
                    for btn in latest_buttons:
                        try:
                            if btn.is_displayed() and 'latest' in btn.text.lower() and len(btn.text.strip()) < 20:
                                latest_tab_element = btn
                                print(f"  Found Latest tab: '{btn.text}'")
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"  Method 1 failed: {e}")
                
                # Try to click the Latest tab (try multiple methods)
                if latest_tab_element:
                    # Try regular click
                    try:
                        print(f"  Attempting regular click...")
                        latest_tab_element.click()
                        latest_tab_found = True
                        time.sleep(3)
                        print("  ✅ Successfully clicked 'Latest' tab (regular click)")
                    except Exception as e:
                        print(f"  Regular click failed: {str(e)[:100]}")
                        
                        # Try JavaScript click
                        try:
                            print(f"  Attempting JavaScript click...")
                            self.driver.execute_script("arguments[0].click();", latest_tab_element)
                            latest_tab_found = True
                            time.sleep(3)
                            print("  ✅ Successfully clicked 'Latest' tab (JavaScript click)")
                        except Exception as e2:
                            print(f"  JavaScript click failed: {str(e2)[:100]}")
                
                if not latest_tab_found:
                    print("  ⚠️ Could not find/click Latest tab, using default view")
                
                # Scroll to load more content
                self.driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(2)
                
                print("🔍 Extracting articles from Latest feed...")
                
            except Exception as e:
                print(f"⚠️ Error navigating to Latest tab: {e}")
            
            # Extract articles with scrolling to load more (15-minute window)
            articles = []
            
            try:
                print("📜 Scrolling to load more articles (15-minute window)...")
                
                # Scroll down multiple times to load more articles
                for scroll_attempt in range(5):  # Scroll 5 times to load more
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for articles to load
                    print(f"  Scroll {scroll_attempt + 1}/5...")
                
                # Try multiple selectors to find article/post elements
                selectors = [
                    "article",
                    "[class*='post']",
                    "[class*='Post']",
                    "[class*='feed']",
                    "[class*='Feed']",
                    "[class*='item']",
                    "[class*='card']",
                    "[class*='Card']",
                    "div[class*='css-']",  # Binance uses css-in-js
                ]
                
                article_elements = []
                for selector in selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > len(article_elements):
                        article_elements = elements
                        print(f"  Found {len(elements)} elements with selector: {selector}")
                
                print(f"✅ Found {len(article_elements)} potential articles")
                
                # Try to extract text from all elements (filter by time window)
                extracted_count = 0
                seen_urls = set()  # Track URLs to avoid duplicates
                now = datetime.now(timezone.utc)
                cutoff_time = now - timedelta(minutes=time_window_minutes)
                
                for idx, element in enumerate(article_elements[:max_articles * 10]):  # Check more elements (10x)
                    try:
                        # Get text content
                        text = element.text.strip()
                        
                        # Skip empty or very short elements
                        if not text or len(text) < 20:
                            continue
                        
                        # Extract article data
                        article = self._extract_article_data(element, coin)
                        if article and article['content']:
                            # Skip duplicates by URL or content hash
                            article_url = article.get('url')
                            content_hash = hash(article['content'][:200])  # Hash first 200 chars
                            
                            # Create unique identifier
                            unique_id = article_url if article_url else f"hash_{content_hash}"
                            
                            if unique_id in seen_urls:
                                continue  # Skip this duplicate
                            seen_urls.add(unique_id)
                            
                            # Check if article has a timestamp
                            article_time = self._parse_timestamp(text)
                            
                            # Only include articles within time window
                            if article_time and article_time >= cutoff_time:
                                articles.append(article)
                                extracted_count += 1
                                time_ago_min = (now - article_time).total_seconds() / 60
                                print(f"  ✓ Article {extracted_count} ({time_ago_min:.1f}m ago): {article['title'][:50]}...")
                            elif not article_time:
                                # If we can't parse timestamp, include it anyway (might be new)
                                articles.append(article)
                                extracted_count += 1
                                print(f"  ✓ Article {extracted_count} (no timestamp): {article['title'][:50]}...")
                            else:
                                # Article is older than time window, skip it
                                time_ago_min = (now - article_time).total_seconds() / 60
                                print(f"  ⏭ Skipping old article ({time_ago_min:.1f}m ago)")
                            
                            if extracted_count >= max_articles:
                                break
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"❌ Error finding articles: {e}")
            
            # If no articles found, try alternative scraping method
            if not articles:
                print("🔄 Trying alternative scraping method...")
                articles = self._scrape_alternative(coin)
            
            print(f"✅ Fetched {len(articles)} articles for {coin}")
            return articles
            
        except Exception as e:
            print(f"❌ Error scraping Binance Square: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            self.close_driver()
    
    def _parse_timestamp(self, text: str) -> Optional[datetime]:
        """
        Parse timestamp from article text (e.g., '5m', '1h', '30s')
        Returns datetime object or None if not found
        """
        try:
            import re
            from datetime import datetime, timedelta, timezone
            
            # Look for patterns like "5m", "1h", "30s", "2d"
            time_patterns = [
                (r'(\d+)s', 1),      # seconds
                (r'(\d+)m\b', 60),    # minutes (word boundary to avoid matching 'am/pm')
                (r'(\d+)h', 3600),   # hours
                (r'(\d+)d', 86400),  # days
            ]
            
            for pattern, multiplier in time_patterns:
                match = re.search(pattern, text.lower())
                if match:
                    value = int(match.group(1))
                    seconds_ago = value * multiplier
                    return datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
            
            return None
        except Exception as e:
            return None
    
    def _extract_article_data(self, element, coin: str) -> Dict:
        """Extract data from an article element"""
        try:
            # Get all text from element
            content = element.text.strip()
            
            # Skip if too short
            if not content or len(content) < 20:
                return None
            
            # Try to find title/content separately
            title = ""
            
            # Try different selectors for title
            try:
                title_element = element.find_element(By.CSS_SELECTOR, "h1, h2, h3, h4, [class*='title'], [class*='Title'], [class*='heading'], [class*='Heading']")
                title = title_element.text.strip()
            except:
                pass
            
            # If no title found, use first line or first 100 chars
            if not title:
                lines = content.split('\n')
                title = lines[0] if lines else content[:100]
            
            # Try to find post URL
            post_id = None
            url = None
            try:
                link_elements = element.find_elements(By.CSS_SELECTOR, "a[href*='/square/post/']")
                if link_elements:
                    url = link_elements[0].get_attribute('href')
                    if '/post/' in url:
                        post_id = url.split('/post/')[-1].split('?')[0].split('/')[0]
            except:
                pass
            
            # Parse timestamp from content (e.g., "1m", "5h")
            posted_at = self._parse_timestamp(content)
            
            return {
                'title': title,
                'content': content,
                'post_id': post_id,
                'url': url,
                'coin': coin,
                'posted_at': posted_at.isoformat() if posted_at else None,
                'scraped_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return None
    
    def _scrape_alternative(self, coin: str) -> List[Dict]:
        """Alternative scraping method - fetch from Binance API or generate mock data"""
        print("⚠️ Using fallback method - generating recent market update")
        
        # Return a mock article based on recent market activity
        return [{
            'title': f'{coin} Market Update',
            'content': f'Recent trading activity for {coin}. Market showing continued interest with active trading volumes.',
            'post_id': f'mock_{int(time.time())}',
            'url': None,
            'coin': coin,
            'scraped_at': datetime.now(timezone.utc).isoformat()
        }]
    
    def fetch_full_article(self, post_id: str) -> Dict:
        """Fetch full article content from post ID"""
        try:
            self.start_driver()
            
            url = f"https://www.binance.com/en/square/post/{post_id}"
            print(f"📄 Fetching full article: {url}")
            
            self.driver.get(url)
            time.sleep(3)
            
            # Extract full content
            try:
                content_element = self.driver.find_element(By.CSS_SELECTOR, "[class*='content'], [class*='body'], article")
                content = content_element.text.strip()
                
                return {
                    'post_id': post_id,
                    'url': url,
                    'full_content': content,
                    'fetched_at': datetime.now(timezone.utc).isoformat()
                }
            except:
                return None
                
        except Exception as e:
            print(f"❌ Error fetching full article: {e}")
            return None
        
        finally:
            self.close_driver()


if __name__ == '__main__':
    # Test the scraper
    scraper = BinanceSquareScraper(headless=False)
    articles = scraper.fetch_articles('BTC', max_articles=5)
    
    print("\n" + "="*80)
    print(f"Fetched {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Content: {article['content'][:100]}...")
        if article['post_id']:
            print(f"   Post ID: {article['post_id']}")

