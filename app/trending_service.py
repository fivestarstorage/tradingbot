from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from .models import NewsArticle


def compute_trending(db: Session, hours: int = 6, limit: int = 15):
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = db.query(NewsArticle).filter(NewsArticle.created_at >= since).order_by(NewsArticle.created_at.desc()).all()
    counts = Counter()
    pos = defaultdict(int)
    neg = defaultdict(int)
    for a in rows:
        if not a.tickers:
            continue
        for tk in a.tickers.split(','):
            t = tk.strip().upper()
            if not t:
                continue
            counts[t] += 1
            if (a.sentiment or '').lower().startswith('pos'):
                pos[t] += 1
            elif (a.sentiment or '').lower().startswith('neg'):
                neg[t] += 1
    items = []
    for t, c in counts.most_common(limit * 2):
        items.append({
            'ticker': t,
            'mentions': c,
            'positive': pos[t],
            'negative': neg[t],
            'score': pos[t] - neg[t]
        })
    items.sort(key=lambda x: (x['score'], x['mentions']), reverse=True)
    return items[:limit]


