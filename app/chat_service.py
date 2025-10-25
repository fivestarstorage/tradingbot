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
            'get_news': self._get_news,
            'get_trending': self._get_trending,
            'recommend_from_news': self._recommend_from_news,
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
            "Valid tools: get_overview, get_positions, get_signals, get_news, get_trending, recommend_from_news, verify_buy, verify_sell, buy, sell.\n"
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

    def handle_history(self, db: Session, messages: list[dict]) -> Dict[str, Any]:
        """Memory-aware handler that takes full chat history.
        messages: [{role: 'user'|'assistant', content: str}, ...]
        """
        # If no OpenAI, fallback to last message heuristic
        if self.client is None:
            last = ''
            for m in reversed(messages or []):
                if m.get('role') == 'user':
                    last = m.get('content','')
                    break
            return self.handle(db, last)

        tools = {
            'get_overview': self._get_overview,
            'get_positions': self._get_positions,
            'get_signals': self._get_signals,
            'get_news': self._get_news,
            'get_trending': self._get_trending,
            'recommend_from_news': self._recommend_from_news,
            'verify_buy': self._verify_buy,
            'verify_sell': self._verify_sell,
            'buy': self._buy,
            'sell': self._sell,
        }

        system = (
            "You are a crypto trading assistant for a Binance + news-driven bot. "
            "Maintain conversation context. When a tool is needed, respond with JSON only in this schema:\n"
            "{\n  \"reply\": string,\n  \"tool\": string | null,\n  \"args\": object | null\n}\n"
            "Valid tools: get_overview, get_positions, get_signals, get_news, get_trending, recommend_from_news, verify_buy, verify_sell, buy, sell.\n"
            "For buy/sell/verify_* require: symbol (e.g., BTCUSDT). For buy also require usdt (number). For sell require quantity (number)."
        )

        chat_msgs = [{'role':'system','content': system}] + [
            {'role': m.get('role'), 'content': m.get('content','')} for m in (messages or [])
        ]
        chat = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=chat_msgs
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

    def _get_news(self, db: Session, args: Dict[str, Any]):
        limit = int(args.get('limit', 20))
        rows = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(limit).all()
        return [
            {
                'title': n.title,
                'url': n.news_url,
                'tickers': n.tickers,
                'sentiment': n.sentiment,
                'time': (n.date or n.created_at).isoformat() if (n.date or n.created_at) else None
            } for n in rows
        ]

    def _get_trending(self, db: Session, args: Dict[str, Any]):
        hours = int(args.get('hours', 6))
        limit = int(args.get('limit', 10))
        return compute_trending(db, hours=hours, limit=limit)

    def _recommend_from_news(self, db: Session, args: Dict[str, Any]):
        # Pick the top trending ticker and propose an action
        hours = int(args.get('hours', 6))
        per_trade_usdt = float(os.getenv('AUTO_TRADE_USDT', '25'))
        trending = compute_trending(db, hours=hours, limit=1)
        if not trending:
            return {'recommendation': 'HOLD', 'reason': 'No trending tickers found', 'symbol': None}
        top = trending[0]
        ticker = top['ticker']
        symbol = f"{ticker}USDT"
        # basic heuristic: positive score -> BUY, negative -> SELL/HOLD
        if top['score'] > 0:
            action = 'BUY'
            confidence = min(90, 50 + top['score'] * 5)
        elif top['score'] < 0:
            action = 'SELL'
            confidence = min(90, 50 + abs(top['score']) * 5)
        else:
            action = 'HOLD'
            confidence = 50
        reason = f"Top trending {ticker} with score {top['score']} (pos {top['positive']}/neg {top['negative']})."
        # verify trade feasibility if BUY
        verify = None
        if action == 'BUY':
            verify = self.trading.verify_buy(symbol, per_trade_usdt)
        return {
            'symbol': symbol,
            'ticker': ticker,
            'action': action,
            'confidence': int(confidence),
            'reason': reason,
            'verify': verify,
            'suggested_usdt': per_trade_usdt
        }

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


