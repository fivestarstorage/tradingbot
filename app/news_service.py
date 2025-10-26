import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from openai import OpenAI
from .models import NewsArticle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

CRYPTO_NEWS_URL = os.getenv(
    'CRYPTONEWS_URL',
    'https://cryptonews-api.com/api/v1/category?section=alltickers&items=20&page=1'
)

COINDESK_NEWS_URL = 'https://www.coindesk.com/latest-crypto-news'
COINTELEGRAPH_NEWS_URL = 'https://cointelegraph.com/rss'


def parse_date(date_str: str):
    try:
        # Example: Fri, 24 Oct 2025 22:30:41 -0400
        # Parse with timezone, then convert to UTC and make naive for consistent DB storage
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        # Convert to UTC and strip timezone (SQLite loses tz info anyway)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        try:
            # Fallback for ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return None


def extract_article_content(article_url: str, headers: dict):
    """
    Fetches and extracts content from a single CoinDesk article.
    Returns (content, published_date, image_url) or (None, None, None) on failure.
    """
    try:
        resp = requests.get(article_url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'lxml')
        
        # Extract article content
        content = ''
        
        # Try to find article body - CoinDesk typically uses article tag or specific divs
        article_body = soup.find('article') or soup.find('div', class_=lambda x: x and 'article' in str(x).lower())
        
        if article_body:
            # Get all paragraph tags
            paragraphs = article_body.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # If no content found, try a more general approach
        if not content:
            paragraphs = soup.find_all('p')
            # Filter out navigation/footer paragraphs
            content = ' '.join([p.get_text(strip=True) for p in paragraphs[:20] if len(p.get_text(strip=True)) > 50])
        
        # Extract published date/time from JSON-LD structured data
        published_date = None
        try:
            # Find JSON-LD script tag
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script and json_ld_script.string:
                data = json.loads(json_ld_script.string)
                # Extract datePublished or dateModified
                date_str = data.get('datePublished') or data.get('dateModified')
                if date_str:
                    # Parse ISO format datetime
                    published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # Convert to UTC and make naive
                    published_date = published_date.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception as e:
            # Fallback: try time tag
            try:
                time_tag = soup.find('time', {'datetime': True})
                if time_tag:
                    date_str = time_tag.get('datetime')
                    if date_str:
                        published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        published_date = published_date.astimezone(timezone.utc).replace(tzinfo=None)
            except:
                pass
        
        # Extract image
        image_url = ''
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '')
        
        return content[:3000], published_date, image_url  # Limit content to 3000 chars for AI analysis
        
    except Exception as e:
        print(f"Error extracting article content from {article_url}: {e}")
        return None, None, None


def analyze_article_with_ai(title: str, content: str):
    """
    Uses OpenAI to analyze article sentiment and extract crypto tickers.
    Returns (sentiment, tickers_list) or (None, []) on failure.
    """
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return None, []
        
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Analyze this crypto news article with HEIGHTENED SENSITIVITY.

Title: {title}

Content: {content[:2000]}

Be VERY OPINIONATED and SENSITIVE:
- ANY positive language, growth, gains, adoption, bullish signs = "Positive"
- ANY negative language, losses, concerns, warnings, bearish signs = "Negative"
- ONLY use "Neutral" if completely factual with no direction

Provide:
1. sentiment: "Positive", "Negative", or "Neutral"
2. tickers: List of cryptocurrency symbols mentioned (e.g., ["BTC", "ETH", "XRP"])

Respond with valid JSON in this format:
{{
  "sentiment": "Positive",
  "tickers": ["BTC", "ETH"]
}}"""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are an AGGRESSIVE crypto sentiment analyzer. Be very opinionated and pick sides. AVOID Neutral unless truly ambiguous. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5  # Increased for more opinionated responses
        )
        
        result = json.loads(response.choices[0].message.content)
        sentiment = result.get('sentiment', 'Neutral')
        tickers = result.get('tickers', [])
        
        return sentiment, tickers
        
    except Exception as e:
        print(f"Error analyzing article with AI: {e}")
        return "Neutral", []  # Default to Neutral if AI analysis fails


def scrape_coindesk_news():
    """
    Scrapes latest crypto news from CoinDesk with full article analysis.
    Returns a list of article dictionaries.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(COINDESK_NEWS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'lxml')
        articles = []
        
        # CoinDesk uses links with class 'content-card-title' for article titles
        article_links = soup.find_all('a', class_='content-card-title')
        
        # Limit to first 10 articles to avoid too many API calls
        article_links = article_links[:10]
        
        print(f"Found {len(article_links)} CoinDesk articles to process...")
        
        for idx, link_elem in enumerate(article_links, 1):
            try:
                # Extract article URL
                article_url = link_elem.get('href', '')
                if article_url and not article_url.startswith('http'):
                    article_url = f"https://www.coindesk.com{article_url}"
                
                if not article_url or 'coindesk.com' not in article_url:
                    continue
                
                # Extract title from h2/h3/h4 within the link
                title_elem = link_elem.find(['h2', 'h3', 'h4'])
                title = title_elem.get_text(strip=True) if title_elem else ''
                if not title:
                    continue
                
                print(f"  [{idx}/{len(article_links)}] Processing: {title[:60]}...")
                
                # Fetch full article content
                content, published_date, image_url = extract_article_content(article_url, headers)
                
                if not content:
                    print(f"    ⚠️  Could not extract content, skipping")
                    continue
                
                # Analyze with AI
                sentiment, tickers = analyze_article_with_ai(title, content)
                
                # Build article dictionary
                article_data = {
                    'news_url': article_url,
                    'title': title,
                    'text': content[:500],  # Store first 500 chars as description
                    'image_url': image_url,
                    'source_name': 'CoinDesk',
                    'date': published_date,  # Proper datetime object
                    'type': 'Article',
                    'sentiment': sentiment,
                    'tickers': tickers
                }
                
                articles.append(article_data)
                print(f"    ✓ Sentiment: {sentiment}, Tickers: {', '.join(tickers) if tickers else 'None'}")
                
            except Exception as e:
                print(f"  ✗ Error processing article: {e}")
                continue
        
        print(f"✓ Scraped {len(articles)} CoinDesk articles with AI analysis")
        return articles
        
    except Exception as e:
        print(f"Error scraping CoinDesk: {e}")
        return []


def scrape_cointelegraph_rss():
    """
    Fetches latest crypto news from CoinTelegraph RSS feed.
    Returns a list of article dictionaries.
    """
    try:
        import xml.etree.ElementTree as ET
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(COINTELEGRAPH_NEWS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        
        # Parse RSS XML
        root = ET.fromstring(resp.content)
        articles = []
        
        # Find all items in the RSS feed
        items = root.findall('.//item')[:10]  # Limit to 10 most recent
        
        print(f"Found {len(items)} CoinTelegraph articles to process...")
        
        for idx, item in enumerate(items, 1):
            try:
                # Extract RSS fields
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                pub_date_elem = item.find('pubDate')
                
                title = title_elem.text if title_elem is not None else ''
                article_url = link_elem.text if link_elem is not None else ''
                description = desc_elem.text if desc_elem is not None else ''
                pub_date_str = pub_date_elem.text if pub_date_elem is not None else ''
                
                if not title or not article_url:
                    continue
                
                # Clean HTML from description
                desc_soup = BeautifulSoup(description, 'html.parser')
                clean_desc = desc_soup.get_text(strip=True)
                
                print(f"  [{idx}/{len(items)}] Processing: {title[:60]}...")
                
                # Parse date from RSS first
                published_date = None
                if pub_date_str:
                    try:
                        # RSS date format: "Fri, 25 Oct 2025 12:00:00 GMT"
                        published_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                    except:
                        try:
                            # Alternative format with timezone offset
                            published_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                            published_date = published_date.replace(tzinfo=None)
                        except:
                            pass
                
                # Fetch full article content for better analysis
                full_content, article_pub_date, image_url = extract_article_content(article_url, headers)
                
                # Use article's published date if found, otherwise use RSS date
                if article_pub_date:
                    published_date = article_pub_date
                
                if not full_content:
                    print(f"    ⚠️  Could not extract full content, using RSS description")
                    full_content = clean_desc
                
                # Analyze with AI using full content
                sentiment, tickers = analyze_article_with_ai(title, full_content)
                
                # Build article dictionary
                article_data = {
                    'news_url': article_url,
                    'title': title,
                    'text': full_content[:500],  # First 500 chars of full content
                    'image_url': image_url,  # Image from article
                    'source_name': 'CoinTelegraph',
                    'date': published_date or datetime.now(timezone.utc),
                    'type': 'Article',
                    'sentiment': sentiment,
                    'tickers': tickers
                }
                
                articles.append(article_data)
                print(f"    ✓ Sentiment: {sentiment}, Tickers: {', '.join(tickers) if tickers else 'None'}")
                
            except Exception as e:
                print(f"  ✗ Error processing article: {e}")
                continue
        
        print(f"✓ Scraped {len(articles)} CoinTelegraph articles with AI analysis")
        return articles
        
    except Exception as e:
        print(f"Error scraping CoinTelegraph RSS: {e}")
        return []


def parse_relative_timestamp(relative_time: str):
    """
    Converts relative timestamps like "38m", "6h", "2d" to absolute datetime.
    Returns datetime object (UTC naive for consistent storage).
    """
    try:
        # Remove whitespace
        relative_time = relative_time.strip().lower()
        
        # Extract number and unit
        match = re.match(r'(\d+)([smhd])', relative_time)
        if not match:
            # Fallback to current time if we can't parse
            return datetime.now(timezone.utc)
        
        value = int(match.group(1))
        unit = match.group(2)
        
        now = datetime.now(timezone.utc)
        
        if unit == 's':  # seconds
            return now - timedelta(seconds=value)
        elif unit == 'm':  # minutes
            return now - timedelta(minutes=value)
        elif unit == 'h':  # hours
            return now - timedelta(hours=value)
        elif unit == 'd':  # days
            return now - timedelta(days=value)
        else:
            return now
    except Exception:
        return datetime.now(timezone.utc)


def scrape_binance_square():
    """
    Scrapes latest posts from Binance Square using Selenium.
    Returns a list of article dictionaries with sentiment and tickers analyzed by AI.
    """
    driver = None
    try:
        print("[Binance Square] Starting scrape...")
        
        # Setup Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        print("[Binance Square] Initializing Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        print("[Binance Square] Chrome driver initialized successfully")
        
        # Navigate to Binance Square
        url = "https://www.binance.com/en/square"
        driver.get(url)
        
        # Wait for content to load
        time.sleep(5)
        
        # Scroll down extensively to load many posts
        print("[Binance Square] Scrolling to load more posts (this may take ~60 seconds)...")
        last_count = 0
        no_new_posts_count = 0
        
        for i in range(50):  # Increased to 50 scrolls
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1.2)  # Balanced delay
            
            # Check progress every 5 scrolls
            if i % 5 == 0:
                temp_soup = BeautifulSoup(driver.page_source, 'lxml')
                temp_cards = temp_soup.select('div.feed-card')
                current_count = len(temp_cards)
                print(f"[Binance Square] After {i+1} scrolls: {current_count} posts loaded")
                
                # Stop early if no new posts are loading (reached the end)
                if current_count == last_count:
                    no_new_posts_count += 1
                    if no_new_posts_count >= 3:  # If no new posts after 3 checks (15 scrolls)
                        print(f"[Binance Square] No new posts loading, stopping early at scroll {i+1}")
                        break
                else:
                    no_new_posts_count = 0
                    last_count = current_count
        
        # Parse HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all feed cards
        feed_cards = soup.select('div.feed-card')
        print(f"[Binance Square] Final count: {len(feed_cards)} posts")
        
        articles = []
        
        # Get OpenAI client for sentiment analysis
        openai_key = os.getenv('OPENAI_API_KEY')
        client = OpenAI(api_key=openai_key) if openai_key else None
        
        for idx, card in enumerate(feed_cards[:50], 1):  # Increased to 50 posts
            try:
                # Extract content
                content_elem = card.select_one('[class*="content"]') or card.select_one('p')
                if content_elem:
                    full_text = content_elem.get_text().strip()
                else:
                    # Fallback: get all text
                    all_text = card.get_text().strip()
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    if len(lines) < 2:
                        continue
                    full_text = ' '.join(lines[1:])  # Skip first line (usually author)
                
                if len(full_text) < 20:
                    continue
                
                # Create title (first 100 chars)
                title = full_text[:100] + ('...' if len(full_text) > 100 else '')
                
                # Extract URL - look for post ID in various places
                article_url = None
                
                # Try to find post ID from data attributes or links
                post_elem = card.find_parent('[data-bn-type]') or card
                
                # Look for links with /square/post/ pattern
                post_links = card.select('a[href*="/square/post/"]')
                if post_links:
                    href = post_links[0].get('href')
                    article_url = f"https://www.binance.com{href}" if href.startswith('/') else href
                
                # Fallback: try to extract post ID from any data attribute
                if not article_url:
                    for elem in card.find_all(attrs={'data-id': True}):
                        post_id = elem.get('data-id')
                        if post_id:
                            article_url = f"https://www.binance.com/en/square/post/{post_id}"
                            break
                
                # Last fallback: use profile link but mark as fallback
                if not article_url:
                    link_elem = card.select_one('a[href*="/square/"]')
                    if link_elem and link_elem.get('href'):
                        href = link_elem.get('href')
                        # Try to extract post ID from the page's other elements
                        article_url = f"{url}#post-{idx}"  # Fallback URL
                
                # Extract timestamp
                time_elem = card.select_one('[class*="time"]') or card.select_one('time')
                if time_elem:
                    relative_time = time_elem.get_text().strip()
                    published_date = parse_relative_timestamp(relative_time)
                else:
                    published_date = datetime.now(timezone.utc)
                
                # Use OpenAI to analyze sentiment and extract tickers
                sentiment = 'Neutral'
                tickers = []
                
                # Extract tickers using regex first (from both title and content)
                # Match $SYMBOL or common crypto symbols
                ticker_pattern = r'\$([A-Z]{2,10})\b'
                combined_text = f"{title} {full_text}"
                matches = re.findall(ticker_pattern, combined_text)
                tickers = list(set(matches))
                
                # Also look for common crypto names without $ symbol
                common_cryptos = {
                    'BITCOIN': 'BTC', 'BTC': 'BTC',
                    'ETHEREUM': 'ETH', 'ETH': 'ETH',
                    'SOLANA': 'SOL', 'SOL': 'SOL',
                    'RIPPLE': 'XRP', 'XRP': 'XRP',
                    'DOGE': 'DOGE', 'DOGECOIN': 'DOGE',
                    'SHIB': 'SHIB', 'SHIBA': 'SHIB',
                    'CARDANO': 'ADA', 'ADA': 'ADA',
                    'MATIC': 'MATIC', 'POLYGON': 'MATIC',
                    'AVAX': 'AVAX', 'AVALANCHE': 'AVAX'
                }
                combined_upper = combined_text.upper()
                for name, ticker in common_cryptos.items():
                    if re.search(r'\b' + name + r'\b', combined_upper):
                        if ticker not in tickers:
                            tickers.append(ticker)
                
                if client:
                    try:
                        # Use OpenAI for sentiment and ticker extraction in one call
                        response = client.chat.completions.create(
                            model='gpt-4o-mini',
                            messages=[
                                {
                                    'role': 'system',
                                    'content': 'You are an AGGRESSIVE crypto sentiment analyzer. Be VERY SENSITIVE and opinionated. Even slight positive language = Positive. Even slight negative language = Negative. AVOID Neutral unless truly ambiguous. Extract: 1) sentiment (Positive/Negative/Neutral) and 2) crypto tickers. Return JSON: {"sentiment": "...", "tickers": ["...", "..."]}. Always respond with valid JSON.'
                                },
                                {
                                    'role': 'user',
                                    'content': f"Analyze this crypto post with HEIGHTENED SENSITIVITY:\n\n{full_text[:500]}"
                                }
                            ],
                            temperature=0.5,  # Increased for more varied responses
                            max_tokens=150
                        )
                        result = response.choices[0].message.content.strip()
                        try:
                            data = json.loads(result)
                            if data.get('sentiment') in ['Positive', 'Negative', 'Neutral']:
                                sentiment = data['sentiment']
                            if isinstance(data.get('tickers'), list):
                                for t in data['tickers']:
                                    if t and t not in tickers:
                                        tickers.append(t)
                        except:
                            # Fallback: just extract sentiment
                            if 'positive' in result.lower() or 'bullish' in result.lower() or 'up' in result.lower():
                                sentiment = 'Positive'
                            elif 'negative' in result.lower() or 'bearish' in result.lower() or 'down' in result.lower():
                                sentiment = 'Negative'
                    except Exception as e:
                        print(f"  ⚠️  AI analysis failed for post {idx}: {e}")
                        sentiment = 'Neutral'
                
                article_data = {
                    'news_url': article_url,
                    'title': title,
                    'text': full_text[:500],
                    'image_url': None,  # Binance Square doesn't easily expose images
                    'source_name': 'Binance Square',
                    'date': published_date,
                    'type': 'Post',
                    'sentiment': sentiment,
                    'tickers': tickers
                }
                
                articles.append(article_data)
                print(f"  {idx}. {title[:60]} | Sentiment: {sentiment} | Tickers: {', '.join(tickers) or 'None'}")
                
            except Exception as e:
                print(f"  ✗ Error processing post {idx}: {e}")
                continue
        
        # Sort by date (newest first)
        articles.sort(key=lambda x: x['date'], reverse=True)
        
        print(f"[Binance Square] ✓ Scraped {len(articles)} posts (sorted newest to oldest)")
        return articles
        
    except Exception as e:
        print(f"[Binance Square] Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Always close the driver
        if driver:
            try:
                driver.quit()
                print("[Binance Square] Chrome driver closed")
            except Exception as e:
                print(f"[Binance Square] Error closing driver: {e}")


def fetch_and_store_news(db: Session, api_key: str):
    items = []
    
    # Fetch from crypto news API (only if key is provided)
    if api_key and api_key.strip():
        try:
            params = { 'token': api_key }
            resp = requests.get(CRYPTO_NEWS_URL, params=params, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
            items = payload.get('data', [])
            print(f"[News] Fetched {len(items)} from CryptoNews API")
        except Exception as e:
            print(f"[News] CryptoNews API error (skipping): {e}")
            items = []
    else:
        print("[News] CryptoNews API key not set, skipping...")
    
    # Also fetch from CoinDesk
    coindesk_items = scrape_coindesk_news()
    items.extend(coindesk_items)
    
    # Also fetch from CoinTelegraph RSS
    cointelegraph_items = scrape_cointelegraph_rss()
    items.extend(cointelegraph_items)
    
    # Also fetch from Binance Square (with error handling - Selenium can be flaky)
    try:
        binance_square_items = scrape_binance_square()
        items.extend(binance_square_items)
        print(f"[News] Fetched {len(binance_square_items)} from Binance Square")
    except Exception as e:
        print(f"[News] Binance Square scraping failed (skipping): {e}")
        import traceback
        traceback.print_exc()
    
    inserted = 0
    skipped = 0
    updated = 0

    for item in items:
        news_url = item.get('news_url')
        if not news_url:
            continue
        # dedup by unique news_url
        existing = db.query(NewsArticle).filter(NewsArticle.news_url == news_url).first()
        if existing:
            # Upsert: update fields if missing or changed (fix stale records)
            changed = False
            # update date if not set
            new_dt = parse_date(item.get('date'))
            # Always normalize stored date from raw if available (handle naive vs aware)
            if new_dt:
                try:
                    need_update = False
                    if not existing.date:
                        need_update = True
                    elif existing.date.tzinfo is None:
                        # treat stored as UTC naive; compare in UTC
                        need_update = (existing.date.replace(tzinfo=timezone.utc) != new_dt.astimezone(timezone.utc))
                    else:
                        need_update = (existing.date != new_dt)
                    if need_update:
                        existing.date = new_dt
                        changed = True
                except Exception:
                    # best effort set
                    existing.date = new_dt
                    changed = True
            # update sentiment/title/text/tickers if changed
            if item.get('sentiment') and item.get('sentiment') != existing.sentiment:
                existing.sentiment = item.get('sentiment')
                changed = True
            if item.get('title') and item.get('title') != existing.title:
                existing.title = item.get('title')
                changed = True
            if item.get('text') and item.get('text') != existing.text:
                existing.text = item.get('text')
                changed = True
            tickers = ','.join(item.get('tickers') or [])
            if tickers and tickers != (existing.tickers or ''):
                existing.tickers = tickers
                changed = True
            if changed:
                db.add(existing)
                updated += 1
            else:
                skipped += 1
            continue
        tickers = item.get('tickers') or []
        
        # Prepare raw data - convert datetime to string for JSON serialization
        raw_data = item.copy()
        if raw_data.get('date') and isinstance(raw_data['date'], datetime):
            raw_data['date'] = raw_data['date'].isoformat()
        
        art = NewsArticle(
            news_url=news_url,
            image_url=item.get('image_url'),
            title=item.get('title') or '',
            text=item.get('text') or '',
            source_name=item.get('source_name'),
            date=parse_date(item.get('date')),
            sentiment=item.get('sentiment'),
            type=item.get('type'),
            tickers=','.join(tickers),
            raw=raw_data
        )
        db.add(art)
        inserted += 1

    if inserted or updated:
        db.commit()

    return { 'inserted': inserted, 'updated': updated, 'skipped': skipped, 'total': len(items) }


