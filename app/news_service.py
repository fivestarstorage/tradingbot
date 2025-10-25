import os
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from .models import NewsArticle

CRYPTO_NEWS_URL = os.getenv(
    'CRYPTONEWS_URL',
    'https://cryptonews-api.com/api/v1/category?section=alltickers&items=100&page=1'
)


def parse_date(date_str: str):
    try:
        # Example: Fri, 24 Oct 2025 22:30:41 -0400
        return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
    except Exception:
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            return None


def fetch_and_store_news(db: Session, api_key: str):
    params = { 'token': api_key }
    resp = requests.get(CRYPTO_NEWS_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    items = payload.get('data', [])
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
            # Always normalize stored date from raw if available
            if new_dt and (not existing.date or existing.date != new_dt):
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


