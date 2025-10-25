from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from core.binance_client import BinanceClient
from .models import Trade, Position


class TradingService:
    def __init__(self, client: BinanceClient):
        self.client = client

    def verify_buy(self, symbol: str, usdt_required: float) -> Dict[str, Any]:
        usdt = self.client.get_account_balance('USDT') or {'free': 0.0}
        symbol_info = self.client.get_symbol_info(symbol)
        is_tradeable = self.client.is_symbol_tradeable(symbol)
        return {
            'has_funds': usdt.get('free', 0.0) >= usdt_required,
            'available_usdt': usdt.get('free', 0.0),
            'symbol_ok': symbol_info is not None,
            'is_tradeable': is_tradeable
        }

    def verify_sell(self, symbol: str) -> Dict[str, Any]:
        asset = symbol.replace('USDT', '')
        bal = self.client.get_account_balance(asset) or {'free': 0.0}
        return {
            'has_asset': bal.get('free', 0.0) > 0,
            'available_asset': bal.get('free', 0.0)
        }

    def buy_market(self, db: Session, symbol: str, usdt_amount: float) -> Optional[Trade]:
        price = self.client.get_current_price(symbol)
        if not price or price <= 0:
            return None
        quantity = usdt_amount / price
        quantity = float(quantity)
        quantity = self._format_quantity(symbol, quantity)
        order = self.client.place_market_order(symbol, 'BUY', quantity)
        if not order:
            return None
        trade = Trade(
            symbol=symbol,
            side='BUY',
            quantity=quantity,
            price=price,
            notional=price * quantity,
            binance_order_id=str(order.get('orderId')),
            status=order.get('status', 'FILLED'),
            meta=order
        )
        db.add(trade)
        # open position (single position per symbol)
        pos = Position(
            symbol=symbol,
            side='LONG',
            entry_price=price,
            quantity=quantity,
            status='OPEN'
        )
        db.add(pos)
        db.commit()
        return trade

    def sell_market(self, db: Session, symbol: str, quantity: float) -> Optional[Trade]:
        quantity = self._format_quantity(symbol, float(quantity))
        price = self.client.get_current_price(symbol)
        if not price or price <= 0:
            return None
        order = self.client.place_market_order(symbol, 'SELL', quantity)
        if not order:
            return None
        trade = Trade(
            symbol=symbol,
            side='SELL',
            quantity=quantity,
            price=price,
            notional=price * quantity,
            binance_order_id=str(order.get('orderId')),
            status=order.get('status', 'FILLED'),
            meta=order
        )
        db.add(trade)
        # close latest open position for symbol
        pos = db.query(Position).filter(Position.symbol == symbol, Position.status == 'OPEN').order_by(Position.opened_at.desc()).first()
        if pos:
            pos.status = 'CLOSED'
            pos.closed_at = None
        db.commit()
        return trade

    def _format_quantity(self, symbol: str, quantity: float) -> float:
        try:
            return float(f"{quantity:.6f}")
        except Exception:
            return quantity


