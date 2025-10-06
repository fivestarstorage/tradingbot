"""
Breakout Strategy - Catch Strong Moves

Best for: Trending markets, momentum plays
Logic: Buy breakouts above resistance, sell breakdowns
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import logging

logger = logging.getLogger(__name__)


class BreakoutStrategy:
    """Trade breakouts of consolidation ranges"""
    
    def __init__(self):
        self.name = "Breakout"
        logger.info("Breakout Strategy initialized")
    
    def process_klines(self, klines):
        if not klines or len(klines) == 0:
            return None
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    
    def calculate_indicators(self, df):
        if df is None or len(df) < 50:
            return None
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Recent highs/lows for breakout detection
        df['high_20'] = high.rolling(window=20).max()
        df['low_20'] = low.rolling(window=20).min()
        
        # RSI
        df['rsi'] = RSIIndicator(close=close, window=14).rsi()
        
        # ADX (need strong trend)
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        
        # Volume
        df['volume_ma'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        
        # ATR
        df['atr'] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # EMA
        df['ema_50'] = EMAIndicator(close=close, window=50).ema_indicator()
        
        # Bollinger Bands (for squeeze detection)
        bb = BollingerBands(close=close, window=20, window_dev=2)
        df['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg() * 100
        
        return df
    
    def generate_signal(self, df):
        if df is None or len(df) < 2:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        price = latest['close']
        high_20 = previous['high_20']  # Use previous to avoid lookahead
        low_20 = previous['low_20']
        rsi = latest['rsi']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        atr_percent = latest['atr_percent']
        atr_value = latest['atr']
        bb_width = latest['bb_width']
        
        if pd.isna(high_20) or pd.isna(adx):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # BUY: Breakout above 20-period high
        if price > high_20 * 1.005:  # 0.5% above high
            confidence += 30
            reasons.append(f'Breakout above {high_20:.2f}')
            
            # Strong volume confirmation
            if volume_ratio > 2.0:
                confidence += 30
                reasons.append(f'Strong volume ({volume_ratio:.1f}x)')
            elif volume_ratio > 1.5:
                confidence += 15
            
            # Trend strength
            if adx > 25 and latest['adx_pos'] > latest['adx_neg']:
                confidence += 20
                reasons.append(f'Strong uptrend (ADX {adx:.0f})')
            
            # Not too overbought
            if rsi < 70:
                confidence += 15
            
            # BB squeeze (consolidation before breakout)
            if bb_width < 5:
                confidence += 10
                reasons.append('BB squeeze detected')
            
            if confidence >= 60:
                signal = 'BUY'
        
        # SELL: Breakdown below 20-period low
        elif price < low_20 * 0.995:  # 0.5% below low
            confidence += 30
            reasons.append(f'Breakdown below {low_20:.2f}')
            
            if volume_ratio > 2.0:
                confidence += 30
                reasons.append(f'Strong volume ({volume_ratio:.1f}x)')
            elif volume_ratio > 1.5:
                confidence += 15
            
            if adx > 25 and latest['adx_neg'] > latest['adx_pos']:
                confidence += 20
                reasons.append(f'Strong downtrend (ADX {adx:.0f})')
            
            if rsi > 30:
                confidence += 15
            
            if confidence >= 60:
                signal = 'SELL'
        
        # Position sizing
        position_mult = 0.7 if atr_percent < 5 else 0.5
        
        # Wider stops for breakouts (let them run)
        stop_distance = atr_value * 3
        take_profit_distance = atr_value * 6
        
        if signal == 'BUY':
            stop_loss = price - stop_distance
            take_profit = price + take_profit_distance
        else:
            stop_loss = 0
            take_profit = 0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'risk': {
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'position_multiplier': position_mult,
                'atr_value': float(atr_value)
            },
            'indicators': {'rsi': float(rsi), 'price': float(price), 'adx': float(adx)}
        }
    
    def analyze(self, klines):
        df = self.process_klines(klines)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        df = self.calculate_indicators(df)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        return self.generate_signal(df)
