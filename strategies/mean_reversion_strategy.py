"""
Mean Reversion Strategy - Buy Dips, Sell Rips

Best for: Ranging/sideways markets, good for volatile coins
Logic: Buy when oversold, sell when overbought
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import logging

logger = logging.getLogger(__name__)


class MeanReversionStrategy:
    """Buy extreme dips, sell extreme pumps"""
    
    def __init__(self):
        self.name = "Mean Reversion"
        logger.info("Mean Reversion Strategy initialized")
    
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
        
        # RSI
        df['rsi'] = RSIIndicator(close=close, window=14).rsi()
        
        # Bollinger Bands (key for mean reversion)
        bb = BollingerBands(close=close, window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr'] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # ADX (avoid trending markets)
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx.adx()
        
        # EMA
        df['ema_20'] = EMAIndicator(close=close, window=20).ema_indicator()
        
        return df
    
    def generate_signal(self, df):
        if df is None or len(df) < 2:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        latest = df.iloc[-1]
        
        rsi = latest['rsi']
        bb_position = latest['bb_position']
        adx = latest['adx']
        price = latest['close']
        atr_percent = latest['atr_percent']
        atr_value = latest['atr']
        
        if pd.isna(rsi) or pd.isna(bb_position):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        # Only trade in ranging markets (ADX < 25)
        if adx > 25:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'risk': {},
                'reasons': [f'Trending market (ADX {adx:.0f}) - mean reversion not suitable']
            }
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # BUY: Extreme oversold
        if rsi < 20 and bb_position < 0.1:
            signal = 'BUY'
            confidence = 80
            reasons.append(f'Extreme oversold (RSI {rsi:.0f}, BB {bb_position:.2f})')
        elif rsi < 30 and bb_position < 0.2:
            signal = 'BUY'
            confidence = 60
            reasons.append(f'Oversold (RSI {rsi:.0f})')
        
        # SELL: Extreme overbought
        elif rsi > 80 and bb_position > 0.9:
            signal = 'SELL'
            confidence = 80
            reasons.append(f'Extreme overbought (RSI {rsi:.0f}, BB {bb_position:.2f})')
        elif rsi > 70 and bb_position > 0.8:
            signal = 'SELL'
            confidence = 60
            reasons.append(f'Overbought (RSI {rsi:.0f})')
        
        # Position sizing
        position_mult = 0.6 if atr_percent < 5 else 0.4
        
        # Quick exits for mean reversion
        stop_distance = atr_value * 2.5
        take_profit_distance = atr_value * 3  # Quick profits
        
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
            'indicators': {'rsi': float(rsi), 'price': float(price)}
        }
    
    def analyze(self, klines):
        df = self.process_klines(klines)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        df = self.calculate_indicators(df)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        return self.generate_signal(df)
