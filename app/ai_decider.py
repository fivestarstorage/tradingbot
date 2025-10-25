import os
from typing import Dict, Any, List
from openai import OpenAI
from sqlalchemy.orm import Session
from .models import NewsArticle, Signal


SYSTEM_PROMPT = (
    "You are a crypto trading assistant. Given a batch of recent news items, "
    "decide one action per target symbol: BUY, SELL or HOLD. Be conservative unless "
    "multiple articles support the same direction. Include confidence 0-100 and a brief reasoning."
)


class AIDecider:
    def __init__(self, model: str = None):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    def decide(self, db: Session, symbols: List[str], lookback_minutes: int = 60) -> List[Signal]:
        # fetch latest articles for symbols by ticker field containment
        # naive: filter by substring in tickers column
        articles = db.query(NewsArticle).order_by(NewsArticle.date.desc()).limit(200).all()
        relevant = [a for a in articles if any(s.replace('USDT','') in (a.tickers or '') for s in symbols)]
        if not relevant:
            return []

        items = [
            {
                'title': a.title,
                'sentiment': a.sentiment,
                'source': a.source_name,
                'date': a.date.isoformat() if a.date else None,
                'tickers': a.tickers,
                'url': a.news_url,
                'summary': (a.text or '')[:500]
            }
            for a in relevant[:30]
        ]

        user_msg = {
            'role': 'user',
            'content': (
                "Symbols: " + ", ".join(symbols) + "\n" +
                "News JSON: " + str(items) + "\n" +
                "Return a JSON list with objects {symbol, action, confidence, reasoning, ref_url}."
            )
        }

        chat = self.client.chat.completions.create(
            model=self.model,
            messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, user_msg],
            temperature=0.2
        )
        content = chat.choices[0].message.content

        try:
            import json
            decisions = json.loads(content)
        except Exception:
            decisions = []

        signals: List[Signal] = []
        for d in decisions:
            sig = Signal(
                symbol=d.get('symbol'),
                action=d.get('action', 'HOLD'),
                confidence=int(d.get('confidence', 0)),
                reasoning=d.get('reasoning', ''),
                ref_article_url=d.get('ref_url'),
                meta=d
            )
            db.add(sig)
            signals.append(sig)
        if signals:
            db.commit()
        return signals


