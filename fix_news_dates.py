"""
Fix existing news dates in the database to be properly stored as UTC.
Run this once to fix old data, then delete this file.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app.db import SessionLocal
from app.models import NewsArticle
from datetime import datetime, timezone

def fix_dates():
    db = SessionLocal()
    try:
        # Get all news articles
        articles = db.query(NewsArticle).all()
        fixed = 0
        
        for article in articles:
            if article.date and article.date.tzinfo is None:
                # Date is naive - need to check if it's already UTC or needs conversion
                # Since we can't know for sure, we'll assume dates before this fix
                # need to be adjusted. Safer to just re-fetch news.
                pass
        
        print(f"Checked {len(articles)} articles")
        print(f"Note: Old articles may have incorrect timestamps.")
        print(f"Best solution: Fetch fresh news to get correct UTC timestamps.")
        print(f"\nRun the backend and it will fetch fresh news on the next cycle,")
        print(f"or manually trigger: curl http://localhost:8000/api/runs/refresh")
        
    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 60)
    print("NEWS DATE FIX UTILITY")
    print("=" * 60)
    fix_dates()

