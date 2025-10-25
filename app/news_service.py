import os
import re
import json
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from openai import OpenAI
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
        
        prompt = f"""Analyze this crypto news article and extract information in JSON format.

Title: {title}

Content: {content[:2000]}

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
                {"role": "system", "content": "You are a crypto news analyst. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
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


