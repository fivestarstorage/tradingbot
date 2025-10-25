import os
import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from openai import OpenAI
from .models import Position, Trade, Signal, NewsArticle
from .trending_service import compute_trending


class ChatService:
    def __init__(self, binance_client, trading_service):
        self.binance = binance_client
        self.trading = trading_service
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    def handle(self, db: Session, message: str) -> Dict[str, Any]:
        tools = {
            'get_overview': self._get_overview,
            'get_positions': self._get_positions,
            'get_signals': self._get_signals,
            'get_trending': self._get_trending,
            'verify_buy': self._verify_buy,
            'verify_sell': self._verify_sell,
            'buy': self._buy,
            'sell': self._sell,
        }

        # If no OpenAI, use a simple rule-based response
        if self.client is None:
            lower = message.lower()
            if 'trending' in lower:
                return {'text': 'Top trending tickers (6h):', 'data': tools['get_trending'](db, {})}
            if 'position' in lower:
                return {'text': 'Current open positions:', 'data': tools['get_positions'](db, {})}
            if 'signal' in lower:
                return {'text': 'Recent signals:', 'data': tools['get_signals'](db, {})}
            return {'text': 'I can help with overview, positions, signals, trending, and verifying or placing simple buy/sell orders.'}

        system = (
            "You are a crypto trading assistant for a Binance + news-driven bot. "
            "When the user asks something, decide if a tool should be called. "
            "Respond with JSON only in the following schema: \n"
            "{\n  \"reply\": string,\n  \"tool\": string | null,\n  \"args\": object | null\n}\n"
            "Valid tools: get_overview, get_positions, get_signals, get_trending, verify_buy, verify_sell, buy, sell.\n"
            "For buy/sell/verify_* require: symbol (e.g., BTCUSDT). For buy also require usdt (number). For sell require quantity (number)."
        )
        chat = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                { 'role': 'system', 'content': system },
                { 'role': 'user', 'content': message }
            ]
        )
        content = chat.choices[0].message.content
        try:
            decision = json.loads(content)
        except Exception:
            decision = {'reply': content, 'tool': None, 'args': None}

        tool = decision.get('tool')
        args = decision.get('args') or {}
        if tool in tools:
            try:
                result = tools[tool](db, args)
                return {'text': decision.get('reply', ''), 'tool': tool, 'result': result}
            except Exception as e:
                return {'text': f"Tool '{tool}' failed: {e}", 'error': True}
        return {'text': decision.get('reply', content)}

    # Tools
    def _get_overview(self, db: Session, args: Dict[str, Any]):
        try:
            usdt = self.binance.get_account_balance('USDT') or {'free': 0.0, 'locked': 0.0}
        except Exception:
            usdt = {'free': 0.0, 'locked': 0.0}
        open_positions = db.query(Position).filter(Position.status == 'OPEN').count()
        recent_trades = db.query(Trade).count()
        return {'usdt': usdt, 'open_positions': open_positions, 'trades': recent_trades}

    def _get_positions(self, db: Session, args: Dict[str, Any]):
        pos = db.query(Position).filter(Position.status == 'OPEN').all()
        return [
            {'symbol': p.symbol, 'qty': p.quantity, 'entry': p.entry_price, 'opened_at': p.opened_at.isoformat()}
            for p in pos
        ]

    def _get_signals(self, db: Session, args: Dict[str, Any]):
        sigs = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
        return [
            {'symbol': s.symbol, 'action': s.action, 'confidence': s.confidence, 'created_at': s.created_at.isoformat()}
            for s in sigs
        ]

    def _get_trending(self, db: Session, args: Dict[str, Any]):
        hours = int(args.get('hours', 6))
        limit = int(args.get('limit', 10))
        return compute_trending(db, hours=hours, limit=limit)

    def _verify_buy(self, db: Session, args: Dict[str, Any]):
        symbol = (args.get('symbol') or '').upper()
        usdt = float(args.get('usdt') or 0)
        return self.trading.verify_buy(symbol, usdt)

    def _verify_sell(self, db: Session, args: Dict[str, Any]):
        symbol = (args.get('symbol') or '').upper()
        return self.trading.verify_sell(symbol)

    def _buy(self, db: Session, args: Dict[str, Any]):
        symbol = (args.get('symbol') or '').upper()
        usdt = float(args.get('usdt') or 0)
        check = self.trading.verify_buy(symbol, usdt)
        if not (check['has_funds'] and check['is_tradeable'] and check['symbol_ok']):
            return {'ok': False, 'verify': check}
        trade = self.trading.buy_market(db, symbol, usdt)
        return {'ok': trade is not None, 'trade_id': trade.id if trade else None}

    def _sell(self, db: Session, args: Dict[str, Any]):
        symbol = (args.get('symbol') or '').upper()
        qty = float(args.get('quantity') or 0)
        check = self.trading.verify_sell(symbol)
        if not check['has_asset']:
            return {'ok': False, 'verify': check}
        trade = self.trading.sell_market(db, symbol, qty)
        return {'ok': trade is not None, 'trade_id': trade.id if trade else None}


