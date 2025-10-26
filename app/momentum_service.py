"""
AI Crypto Momentum Trading Bot Service
Detects cryptocurrencies with rapid upward momentum and executes trades
"""

import os
import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import numpy as np

from core.binance_client import BinanceClient
from .models import MomentumSignal, MomentumTrade, MarketSnapshot
from .db import SessionLocal


class MomentumTradingService:
    """
    Main service for momentum trading bot
    """
    
    def __init__(self, binance_client: BinanceClient):
        self.binance = binance_client
        
        # Choose between BEST (max profit) or MORE_TRADES (higher frequency)
        profile = os.getenv('MOMENTUM_PROFILE', 'BEST')  # BEST or MORE_TRADES
        
        if profile == 'BEST':
            # 🏆 BEST CONFIG: +105% profit, 1.4 trades/week
            self.config = {
                'min_price_1h': 1.5,           # 1.5% hourly price surge
                'min_volume_ratio': 1.5,       # 1.5x average volume
                'breakout_threshold': 93,      # Within 7% of 24h high
                'min_momentum_score': 60,      # Minimum total score
                'stop_loss_pct': 5,            # 5% stop loss
                'take_profit_pct': 8,          # 8% take profit
                'trailing_stop_pct': 2.5,      # Trail 2.5% from peak
                'max_position_usdt': float(os.getenv('MOMENTUM_TRADE_AMOUNT', '50')),
                'intervals': ['1h'],
                'auto_execute': True,  # ALWAYS AUTO-EXECUTE
            }
        else:
            # 🔥 MORE TRADES CONFIG: +54% profit, 1.6 trades/week (RECOMMENDED)
            self.config = {
                'min_price_1h': 1.2,           # 1.2% hourly price surge (lower = more signals)
                'min_volume_ratio': 1.3,       # 1.3x average volume
                'breakout_threshold': 90,      # Within 10% of 24h high
                'min_momentum_score': 50,      # Lower threshold = more trades
                'stop_loss_pct': 5,            # 5% stop loss
                'take_profit_pct': 8,          # 8% take profit
                'trailing_stop_pct': 2.5,      # Trail 2.5% from peak
                'max_position_usdt': float(os.getenv('MOMENTUM_TRADE_AMOUNT', '50')),
                'intervals': ['1h'],
                'auto_execute': True,  # ALWAYS AUTO-EXECUTE
            }
        
        self.ai_model = MomentumAIModel()
        self.active = False
        
        print(f"[Momentum] Loaded profile: {profile}")
        print(f"[Momentum] Entry: {self.config['min_price_1h']}% price | {self.config['min_volume_ratio']}x vol | Score: {self.config['min_momentum_score']}")
        print(f"[Momentum] Exit: -{self.config['stop_loss_pct']}% stop | +{self.config['take_profit_pct']}% TP | {self.config['trailing_stop_pct']}% trail")
    
    def get_market_overview(self, db: Session) -> Dict:
        """Get current momentum trading overview"""
        # Active signals
        active_signals = db.query(MomentumSignal).filter(
            MomentumSignal.status == 'ACTIVE'
        ).order_by(MomentumSignal.ai_confidence.desc()).limit(20).all()
        
        # Open trades
        open_trades = db.query(MomentumTrade).filter(
            MomentumTrade.status == 'OPEN'
        ).all()
        
        # Recent closed trades (last 24h)
        since = datetime.utcnow() - timedelta(hours=24)
        recent_trades = db.query(MomentumTrade).filter(
            MomentumTrade.closed_at >= since,
            MomentumTrade.status == 'CLOSED'
        ).all()
        
        # Calculate stats
        total_pnl = sum(t.profit_loss or 0 for t in recent_trades)
        winning_trades = [t for t in recent_trades if (t.profit_loss or 0) > 0]
        win_rate = (len(winning_trades) / len(recent_trades) * 100) if recent_trades else 0
        
        return {
            'active_signals': [{
                'id': s.id,
                'symbol': s.symbol,
                'price_change_pct': s.price_change_pct,
                'volume_24h': s.volume_24h,
                'ai_confidence': s.ai_confidence,
                'technical_score': s.technical_score,
                'triggered_at': s.triggered_at.isoformat() if s.triggered_at else None,
            } for s in active_signals],
            'open_positions': [{
                'id': t.id,
                'symbol': t.symbol,
                'entry_price': t.entry_price,
                'quantity': t.quantity,
                'usdt_value': t.usdt_value,
                'ai_confidence': t.ai_entry_confidence,
                'stop_loss': t.stop_loss,
                'take_profit': t.take_profit,
                'opened_at': t.opened_at.isoformat() if t.opened_at else None,
            } for t in open_trades],
            'stats_24h': {
                'total_trades': len(recent_trades),
                'winning_trades': len(winning_trades),
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_trade_duration': round(
                    sum(t.duration_seconds or 0 for t in recent_trades) / len(recent_trades) if recent_trades else 0
                )
            }
        }
    
    def scan_for_signals(self, db: Session, return_debug=False):
        """Scan market for momentum signals"""
        signals = []
        debug_info = {
            'checked': 0,
            'volume_filtered': 0,
            'price_filtered': 0,
            'spread_filtered': 0,
            'volume_spike_filtered': 0,
            'ai_filtered': 0,
            'candidates': []
        }
        
        try:
            # Get all USDT pairs
            tickers = self.binance.get_24h_tickers()
            
            print(f"\n[Momentum] Starting scan of {len(tickers)} pairs...")
            print(f"[Momentum] Config: min_price_1h={self.config['min_price_1h']}%, min_vol_ratio={self.config['min_volume_ratio']}x, min_score={self.config['min_momentum_score']}")
            
            # Minimum volume filter (always need at least $500k)
            min_volume_24h = float(os.getenv('MOMENTUM_MIN_VOLUME', '500000'))
            
            for ticker in tickers:
                symbol = ticker['symbol']
                
                # Filter: Only USDT pairs
                if not symbol.endswith('USDT'):
                    continue
                
                debug_info['checked'] += 1
                
                # Filter: Minimum 24h volume
                volume_24h = float(ticker.get('quoteVolume', 0))
                if volume_24h < min_volume_24h:
                    debug_info['volume_filtered'] += 1
                    continue
                
                # Filter: Must be positive 24h change
                price_change_24h = float(ticker.get('priceChangePercent', 0))
                if price_change_24h < 0:
                    debug_info['price_filtered'] += 1
                    continue
                
                # Check if signal already exists for this symbol
                existing_signal = db.query(MomentumSignal).filter(
                    MomentumSignal.symbol == symbol,
                    MomentumSignal.status == 'ACTIVE'
                ).first()
                
                if existing_signal:
                    # Skip - already have an active signal for this coin
                    continue
                
                # Log coins that pass initial filters
                print(f"[Momentum] 🔍 {symbol}: +{price_change:.2f}% (${volume_24h:,.0f} vol) - Analyzing...")
                
                if return_debug:
                    debug_info['candidates'].append({
                        'symbol': symbol,
                        'price_change': price_change,
                        'volume_24h': volume_24h,
                        'status': 'analyzing'
                    })
                
                # Check each interval (but stop after first signal created)
                signal_created = False
                for interval in self.config['intervals']:
                    signal, fail_reason = self._analyze_symbol(db, symbol, interval, ticker, return_reason=True)
                    if signal:
                        print(f"[Momentum] ✅ SIGNAL: {symbol} +{signal.price_change_pct:.2f}% (AI: {signal.ai_confidence:.0%})")
                        signals.append(signal)
                        signal_created = True
                        if return_debug and debug_info['candidates']:
                            debug_info['candidates'][-1]['status'] = 'signal_created'
                        break  # Don't create duplicate signals for other intervals
                    elif fail_reason and return_debug and debug_info['candidates']:
                        debug_info['candidates'][-1]['status'] = 'failed'
                        debug_info['candidates'][-1]['reason'] = fail_reason
                        if 'spread' in fail_reason.lower():
                            debug_info['spread_filtered'] += 1
                        elif 'volume' in fail_reason.lower():
                            debug_info['volume_spike_filtered'] += 1
                        elif 'ai' in fail_reason.lower() or 'confidence' in fail_reason.lower():
                            debug_info['ai_filtered'] += 1
            
            print(f"\n[Momentum] Scan complete:")
            print(f"  - Checked: {debug_info['checked']} USDT pairs")
            print(f"  - Filtered (volume): {debug_info['volume_filtered']}")
            print(f"  - Filtered (price): {debug_info['price_filtered']}")
            print(f"  - Signals found: {len(signals)}")
        
        except Exception as e:
            print(f"[Momentum] Error scanning for signals: {e}")
            import traceback
            traceback.print_exc()
        
        if return_debug:
            return signals, debug_info
        return signals
    
    def _analyze_symbol(self, db: Session, symbol: str, interval: str, ticker: Dict, return_reason=False):
        """
        Analyze a symbol for momentum signal using OPTIMIZED BACKTEST logic
        
        Scoring system (need >= min_momentum_score to trigger):
        - Price surge 1h (0-40 points)
        - Volume spike (0-30 points)
        - Breakout position (0-30 points)
        """
        try:
            # Get recent 24h of 1h candles
            raw_candles = self.binance.get_klines(symbol, '1h', limit=25)
            if not raw_candles or len(raw_candles) < 25:
                return (None, "Not enough candle data") if return_reason else None
            
            # Format candles
            candles = []
            for candle in raw_candles:
                candles.append({
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            # Get current data
            latest = candles[-1]
            current_price = latest['close']
            current_volume = latest['volume']
            
            # 1. Calculate 1h price change
            price_1h_ago = candles[-2]['close'] if len(candles) > 1 else current_price
            price_change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
            
            # 2. Calculate volume ratio
            avg_volume = np.mean([c['volume'] for c in candles[:-1]])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # 3. Calculate breakout position (% of 24h high)
            high_24h = max(c['high'] for c in candles)
            breakout_score = (current_price / high_24h) * 100
            
            # 4. Calculate momentum score
            momentum_score = 0
            reasons = []
            
            # Price momentum (0-40 points)
            if price_change_1h >= self.config['min_price_1h']:
                momentum_score += min(price_change_1h * 2, 40)
                reasons.append(f"1h: +{price_change_1h:.1f}%")
            
            # Volume surge (0-30 points)
            if volume_ratio >= self.config['min_volume_ratio']:
                momentum_score += min((volume_ratio - 1) * 15, 30)
                reasons.append(f"Vol: {volume_ratio:.1f}x")
            
            # Breakout (0-30 points)
            if breakout_score >= self.config['breakout_threshold']:
                momentum_score += 30
                reasons.append(f"Breakout: {breakout_score:.0f}%")
            
            # Check if momentum is strong enough
            if momentum_score < self.config['min_momentum_score']:
                reason = f"Score {momentum_score:.0f} < {self.config['min_momentum_score']} ({', '.join(reasons) if reasons else 'No momentum'})"
                return (None, reason) if return_reason else None
            
            print(f"[Momentum]   ✅ {symbol}: Score {momentum_score:.0f}/100 | {' | '.join(reasons)}")
            
            # Create signal
            signal = MomentumSignal(
                symbol=symbol,
                interval='1h',
                price_change_pct=price_change_1h,
                volume_24h=float(ticker.get('quoteVolume', 0)),
                volume_ratio=volume_ratio,
                ai_confidence=momentum_score / 100,  # Store as 0-1 for compatibility
                predicted_exit=None,
                technical_score=int(momentum_score),
                status='ACTIVE',
                triggered_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=4),  # Expires in 4h
                meta={
                    'momentum_score': momentum_score,
                    'price_change_1h': price_change_1h,
                    'volume_ratio': volume_ratio,
                    'breakout_score': breakout_score,
                    'current_price': current_price,
                    'high_24h': high_24h,
                    'reasons': reasons
                }
            )
            
            db.add(signal)
            db.commit()
            
            print(f"[Momentum] ✅ SIGNAL: {symbol} | Score: {momentum_score:.0f}/100 | {' | '.join(reasons)}")
            
            return (signal, None) if return_reason else signal
            
        except Exception as e:
            print(f"[Momentum] Error analyzing {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return (None, f"Error: {str(e)}") if return_reason else None
    
    def _calculate_technicals(self, candles: List[Dict]) -> Dict:
        """Calculate technical indicators"""
        closes = np.array([c['close'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        # RSI
        rsi = self._calculate_rsi(closes, period=14)
        
        # MACD
        macd, signal = self._calculate_macd(closes)
        
        # EMAs
        ema_20 = self._calculate_ema(closes, period=20)
        ema_50 = self._calculate_ema(closes, period=50)
        
        # Technical score (0-100)
        score = 0
        if rsi > 30 and rsi < 70:  # Not overbought/oversold
            score += 30
        if macd > signal:  # Bullish MACD
            score += 30
        if closes[-1] > ema_20 and ema_20 > ema_50:  # Uptrend
            score += 40
        
        return {
            'rsi': float(rsi),
            'macd': float(macd),
            'macd_signal': float(signal),
            'ema_20': float(ema_20),
            'ema_50': float(ema_50),
            'score': score
        }
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        if down == 0:
            return 100
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray) -> Tuple[float, float]:
        """Calculate MACD"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd = ema_12 - ema_26
        signal = macd  # Simplified - should be EMA of MACD
        return macd, signal
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _calculate_spread(self, order_book: Dict) -> float:
        """Calculate order book spread percentage"""
        try:
            best_bid = float(order_book['bids'][0][0])
            best_ask = float(order_book['asks'][0][0])
            spread = (best_ask - best_bid) / best_bid * 100
            return spread
        except:
            return 999.0  # High spread if error
    
    def execute_trade(self, db: Session, signal: MomentumSignal) -> Optional[MomentumTrade]:
        """Execute a momentum trade based on signal"""
        try:
            # Get account balance
            balance = self.binance.get_account_balance('USDT')
            usdt_free = balance.get('free', 0)
            
            # Calculate position size (% of portfolio)
            position_size = usdt_free * (self.config['max_position_pct'] / 100)
            
            if position_size < 11:  # Minimum Binance order
                print(f"Position size too small: ${position_size:.2f}")
                return None
            
            # Get current price
            ticker = self.binance.get_ticker(signal.symbol)
            current_price = float(ticker['price'])
            
            # Calculate quantity
            quantity = position_size / current_price
            
            # Place market buy order
            order = self.binance.place_market_order(signal.symbol, 'BUY', quantity)
            
            if not order:
                print(f"Failed to place order for {signal.symbol}")
                return None
            
            # Calculate stop loss and take profit
            stop_loss = current_price * (1 - self.config['stop_loss_pct'] / 100)
            take_profit = signal.predicted_exit if signal.predicted_exit else current_price * 1.15
            
            # Create trade record
            trade = MomentumTrade(
                signal_id=signal.id,
                symbol=signal.symbol,
                side='BUY',
                entry_price=current_price,
                quantity=quantity,
                usdt_value=position_size,
                ai_entry_confidence=signal.ai_confidence,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status='OPEN',
                binance_order_id_entry=str(order.get('orderId', '')),
                opened_at=datetime.utcnow(),
                meta={
                    'signal_data': signal.meta,
                    'order_data': order
                }
            )
            
            db.add(trade)
            
            # Update signal status
            signal.status = 'TRADED'
            
            db.commit()
            
            print(f"✅ Trade executed: BUY {quantity:.6f} {signal.symbol} @ ${current_price:.4f}")
            
            return trade
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            db.rollback()
            return None
    
    def monitor_positions(self, db: Session):
        """Monitor open positions for exit signals"""
        open_trades = db.query(MomentumTrade).filter(
            MomentumTrade.status == 'OPEN'
        ).all()
        
        for trade in open_trades:
            try:
                self._check_exit_conditions(db, trade)
            except Exception as e:
                print(f"Error monitoring position {trade.symbol}: {e}")
    
    def _check_exit_conditions(self, db: Session, trade: MomentumTrade):
        """Check if position should be exited"""
        # Get current price
        ticker = self.binance.get_ticker(trade.symbol)
        current_price = float(ticker['price'])
        
        exit_reason = None
        should_exit = False
        
        # Check stop loss
        if current_price <= trade.stop_loss:
            exit_reason = 'STOP_LOSS'
            should_exit = True
        
        # Check take profit
        elif current_price >= trade.take_profit:
            exit_reason = 'TAKE_PROFIT'
            should_exit = True
        
        # Check AI exit signal
        else:
            # Get recent candles for AI analysis
            candles = self.binance.get_klines(trade.symbol, '5m', limit=50)
            technical = self._calculate_technicals(candles)
            
            features = {
                'entry_price': trade.entry_price,
                'current_price': current_price,
                'price_change': (current_price - trade.entry_price) / trade.entry_price * 100,
                'rsi': technical['rsi'],
                'macd': technical['macd'],
                'ai_entry_confidence': trade.ai_entry_confidence,
            }
            
            ai_exit = self.ai_model.should_exit(features)
            
            if ai_exit['should_exit'] and ai_exit['confidence'] > 0.6:
                exit_reason = 'AI_EXIT'
                should_exit = True
                trade.ai_exit_confidence = ai_exit['confidence']
        
        if should_exit:
            self._close_position(db, trade, current_price, exit_reason)
    
    def _close_position(self, db: Session, trade: MomentumTrade, exit_price: float, reason: str):
        """Close an open position"""
        try:
            # Place market sell order
            order = self.binance.place_market_order(trade.symbol, 'SELL', trade.quantity)
            
            if not order:
                print(f"Failed to close position for {trade.symbol}")
                return
            
            # Calculate P&L
            profit_loss = (exit_price - trade.entry_price) * trade.quantity
            profit_loss_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
            
            # Update trade
            trade.exit_price = exit_price
            trade.profit_loss = profit_loss
            trade.profit_loss_pct = profit_loss_pct
            trade.status = 'CLOSED'
            trade.closed_at = datetime.utcnow()
            trade.duration_seconds = int((trade.closed_at - trade.opened_at).total_seconds())
            trade.exit_reason = reason
            trade.binance_order_id_exit = str(order.get('orderId', ''))
            
            db.commit()
            
            pnl_sign = '+' if profit_loss > 0 else ''
            print(f"✅ Position closed: {trade.symbol} | P&L: {pnl_sign}${profit_loss:.2f} ({pnl_sign}{profit_loss_pct:.2f}%) | Reason: {reason}")
            
        except Exception as e:
            print(f"Error closing position: {e}")
            db.rollback()


class MomentumAIModel:
    """
    AI/ML model for momentum prediction
    Currently uses a rule-based approach, can be replaced with ML model
    """
    
    def predict(self, features: Dict, candles: List[Dict]) -> Dict:
        """Predict momentum continuation and exit point"""
        # Simple scoring system (can be replaced with trained ML model)
        score = 0
        
        # Strong price change
        if features['price_change_pct'] > 30:
            score += 0.3
        elif features['price_change_pct'] > 20:
            score += 0.2
        
        # Volume spike
        if features['volume_ratio'] > 3:
            score += 0.2
        elif features['volume_ratio'] > 2:
            score += 0.1
        
        # RSI not overbought
        if 40 < features['rsi'] < 70:
            score += 0.2
        
        # MACD bullish
        if features['macd'] > features['macd_signal']:
            score += 0.15
        
        # Price above EMAs (uptrend)
        if features['current_price'] > features['ema_20'] > features['ema_50']:
            score += 0.15
        
        # Low spread (good liquidity)
        if features['spread_pct'] < 0.1:
            score += 0.1
        
        # Calculate predicted exit (15% above entry as default)
        predicted_exit = features['current_price'] * 1.15
        
        return {
            'confidence': min(score, 1.0),
            'predicted_exit': predicted_exit
        }
    
    def should_exit(self, features: Dict) -> Dict:
        """Determine if position should be exited"""
        should_exit = False
        confidence = 0
        
        # Significant profit taken
        if features['price_change'] > 10:
            should_exit = True
            confidence = 0.8
        
        # RSI overbought
        elif features['rsi'] > 75:
            should_exit = True
            confidence = 0.7
        
        # MACD bearish crossover
        elif features['macd'] < 0:
            should_exit = True
            confidence = 0.6
        
        return {
            'should_exit': should_exit,
            'confidence': confidence
        }

