import os
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from .models import NewsArticle

CRYPTO_NEWS_URL = os.getenv(
    'CRYPTONEWS_URL',
    'https://cryptonews-api.com/api/v1/category?section=alltickers&items=100&page=1'
)

COINDESK_NEWS_URL = 'https://www.coindesk.com/latest-crypto-news'


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


def scrape_coindesk_news():
    """
    Scrapes latest crypto news from CoinDesk.
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
        
        for link_elem in article_links:
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
                
                # Find the parent container to get associated metadata
                parent = link_elem.find_parent('div', class_='flex flex-col')
                
                description = ''
                date_str = None
                image_url = ''
                
                if parent:
                    # Extract description - look for p tag with specific classes
                    desc_elem = parent.find('p', class_=lambda x: x and 'font-body' in x)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                    
                    # Extract time - look for span with metadata class
                    time_elem = parent.find('span', class_=lambda x: x and 'font-metadata' in x)
                    if time_elem:
                        date_str = time_elem.get_text(strip=True)
                    
                    # Try to find image in the parent's parent (sibling structure)
                    grandparent = parent.find_parent('div')
                    if grandparent:
                        img_elem = grandparent.find('img', class_=lambda x: x and 'content-card-image' in x)
                        if img_elem:
                            # Try various image source attributes
                            image_url = img_elem.get('src', '') or img_elem.get('data-src', '')
                            # Handle Next.js image URLs
                            if image_url and '/_next/image?url=' in image_url:
                                # Extract the actual image URL from Next.js wrapper
                                try:
                                    import urllib.parse
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(image_url).query)
                                    if 'url' in parsed:
                                        image_url = parsed['url'][0]
                                except:
                                    pass
                
                # Build article dictionary
                article_data = {
                    'news_url': article_url,
                    'title': title,
                    'text': description,
                    'image_url': image_url,
                    'source_name': 'CoinDesk',
                    'date': date_str,  # This will be relative time like "5 minutes ago"
                    'type': 'Article',
                    'sentiment': None,  # We don't have sentiment from scraping
                    'tickers': []  # Could potentially extract from title/text later
                }
                
                articles.append(article_data)
                
            except Exception as e:
                print(f"Error parsing CoinDesk article: {e}")
                continue
        
        print(f"Scraped {len(articles)} articles from CoinDesk")
        return articles
        
    except Exception as e:
        print(f"Error scraping CoinDesk: {e}")
        return []


def fetch_and_store_news(db: Session, api_key: str):
    # Fetch from crypto news API
    params = { 'token': api_key }
    resp = requests.get(CRYPTO_NEWS_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    items = payload.get('data', [])
    
    # Also fetch from CoinDesk
    coindesk_items = scrape_coindesk_news()
    items.extend(coindesk_items)
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
            raw=item
        )
        db.add(art)
        inserted += 1

    if inserted or updated:
        db.commit()

    return { 'inserted': inserted, 'updated': updated, 'skipped': skipped, 'total': len(items) }


