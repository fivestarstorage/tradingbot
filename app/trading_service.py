from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from core.binance_client import BinanceClient
from .models import Trade, Position
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 28

# SMS notifications
try:
    from .twilio_notifier import TwilioNotifier
except ImportError:
    TwilioNotifier = None


class TradingService:
    def __init__(self, client: BinanceClient):
        self.client = client
        # Initialize SMS notifier
        self.sms_notifier = TwilioNotifier() if TwilioNotifier else None

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
        # Apply exchange filters (LOT_SIZE, MIN_NOTIONAL)
        step_size, min_qty, min_notional = self._get_symbol_filters(symbol)
        raw_qty = Decimal(str(usdt_amount)) / Decimal(str(price))
        quantity = self._floor_to_step(raw_qty, step_size)
        # Ensure >= min_qty
        if quantity < min_qty:
            # Not enough to meet minimum quantity
            return None
        # Ensure notional >= min_notional
        notional = quantity * Decimal(str(price))
        if min_notional and notional < min_notional:
            # Try increasing by one step if within budget, else fail
            alt_qty = self._floor_to_step((Decimal(str(min_notional)) / Decimal(str(price))), step_size)
            if alt_qty * Decimal(str(price)) <= Decimal(str(usdt_amount)) and alt_qty >= min_qty:
                quantity = alt_qty
            else:
                return None
        order = self.client.place_market_order(symbol, 'BUY', quantity)
        if not order:
            return None
        trade = Trade(
            symbol=symbol,
            side='BUY',
            quantity=float(quantity),
            price=float(price),
            notional=float(Decimal(str(price)) * quantity),
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
        
        # Send SMS notification
        if self.sms_notifier:
            try:
                self.sms_notifier.send_trade_notification({
                    'action': 'BUY',
                    'symbol': symbol,
                    'price': float(price),
                    'quantity': float(quantity),
                    'amount': float(usdt_amount),
                    'bot_name': 'API Trading Bot',
                    'reasoning': f'Bought {symbol} via API'
                })
            except Exception as e:
                print(f"SMS notification error: {e}")
        
        return trade

    def sell_market(self, db: Session, symbol: str, quantity: float) -> Optional[Trade]:
        price = self.client.get_current_price(symbol)
        if not price or price <= 0:
            return None
        step_size, min_qty, min_notional = self._get_symbol_filters(symbol)
        qty_dec = Decimal(str(quantity))
        qty_dec = self._floor_to_step(qty_dec, step_size)
        if qty_dec < min_qty:
            return None
        if min_notional and (qty_dec * Decimal(str(price)) < min_notional):
            return None
        order = self.client.place_market_order(symbol, 'SELL', float(qty_dec))
        if not order:
            return None
        trade = Trade(
            symbol=symbol,
            side='SELL',
            quantity=float(qty_dec),
            price=float(price),
            notional=float(Decimal(str(price)) * qty_dec),
            binance_order_id=str(order.get('orderId')),
            status=order.get('status', 'FILLED'),
            meta=order
        )
        db.add(trade)
        # close latest open position for symbol
        pos = db.query(Position).filter(Position.symbol == symbol, Position.status == 'OPEN').order_by(Position.opened_at.desc()).first()
        profit = 0.0
        profit_pct = 0.0
        if pos:
            pos.status = 'CLOSED'
            pos.closed_at = None
            # Calculate profit
            if pos.entry_price:
                profit = (float(price) - float(pos.entry_price)) * float(qty_dec)
                profit_pct = ((float(price) - float(pos.entry_price)) / float(pos.entry_price)) * 100
        db.commit()
        
        # Send SMS notification
        if self.sms_notifier:
            try:
                self.sms_notifier.send_trade_notification({
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': float(price),
                    'quantity': float(qty_dec),
                    'amount': float(price) * float(qty_dec),
                    'bot_name': 'API Trading Bot',
                    'profit': profit,
                    'profit_percent': profit_pct,
                    'reasoning': f'Sold {symbol} via API'
                })
            except Exception as e:
                print(f"SMS notification error: {e}")
        
        return trade

    def _get_symbol_filters(self, symbol: str) -> Tuple[Decimal, Decimal, Optional[Decimal]]:
        """Return (step_size, min_qty, min_notional) as Decimals."""
        try:
            info = self.client.client.get_symbol_info(symbol)
            step = Decimal('0.000001')
            minq = Decimal('0')
            minnot = None
            for f in info.get('filters', []):
                if f.get('filterType') == 'LOT_SIZE':
                    step = Decimal(str(f.get('stepSize', '0.000001')))
                    minq = Decimal(str(f.get('minQty', '0')))
                if f.get('filterType') in ('MIN_NOTIONAL','NOTIONAL'):
                    mn = f.get('minNotional') or f.get('notional')
                    if mn is not None:
                        minnot = Decimal(str(mn))
            return (step, minq, minnot)
        except Exception:
            return (Decimal('0.000001'), Decimal('0'), None)

    def _floor_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return value.quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
        steps = (value / step).to_integral_value(rounding=ROUND_DOWN)
        return steps * step


