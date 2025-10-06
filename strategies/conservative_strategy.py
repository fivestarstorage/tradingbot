"""
Conservative Strategy - Quality Over Quantity

Best for: Risk-averse traders, volatile coins
Logic: Very strict requirements, only the best setups
Expects: 5-15 trades per 100 days
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import logging

logger = logging.getLogger(__name__)


class ConservativeStrategy:
    """Ultra-selective, only trades perfect setups"""
    
    def __init__(self):
        self.name = "Conservative"
        logger.info("Conservative Strategy initialized (Ultra-selective)")
    
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
        
        # RSI
        df['rsi'] = RSIIndicator(close=close, window=14).rsi()
        
        # MACD
        macd = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        
        # ADX
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        
        # EMAs - All timeframes must align
        df['ema_9'] = EMAIndicator(close=close, window=9).ema_indicator()
        df['ema_21'] = EMAIndicator(close=close, window=21).ema_indicator()
        df['ema_50'] = EMAIndicator(close=close, window=50).ema_indicator()
        df['ema_200'] = EMAIndicator(close=close, window=200).ema_indicator()
        
        # Volume
        df['volume_ma'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        
        # OBV
        df['obv'] = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df['obv_ema'] = df['obv'].ewm(span=20).mean()
        
        # ATR
        df['atr'] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # Perfect alignment check
        df['all_emas_bullish'] = (
            (df['ema_9'] > df['ema_21']) &
            (df['ema_21'] > df['ema_50']) &
            (df['ema_50'] > df['ema_200'])
        )
        
        df['all_emas_bearish'] = (
            (df['ema_9'] < df['ema_21']) &
            (df['ema_21'] < df['ema_50']) &
            (df['ema_50'] < df['ema_200'])
        )
        
        return df
    
    def generate_signal(self, df):
        if df is None or len(df) < 2:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        obv = latest['obv']
        obv_ema = latest['obv_ema']
        all_emas_bullish = latest['all_emas_bullish']
        all_emas_bearish = latest['all_emas_bearish']
        atr_percent = latest['atr_percent']
        atr_value = latest['atr']
        price = latest['close']
        
        if pd.isna(rsi) or pd.isna(adx):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # BUY: PERFECT setup required
        perfect_buy = (
            rsi < 35 and  # Oversold
            macd > macd_signal and  # MACD bullish
            previous['macd'] <= previous['macd_signal'] and  # Fresh crossover
            adx > 25 and  # Strong trend
            latest['adx_pos'] > latest['adx_neg'] and  # Bullish trend
            volume_ratio > 1.5 and  # Good volume
            obv > obv_ema and  # OBV bullish
            all_emas_bullish and  # ALL EMAs aligned
            atr_percent < 7  # Not too volatile
        )
        
        if perfect_buy:
            signal = 'BUY'
            confidence = 95
            reasons.append('Perfect bullish setup')
            reasons.append(f'RSI {rsi:.0f}, MACD cross, ADX {adx:.0f}, All EMAs aligned')
        
        # SELL: PERFECT setup required
        perfect_sell = (
            rsi > 65 and  # Overbought
            macd < macd_signal and  # MACD bearish
            previous['macd'] >= previous['macd_signal'] and  # Fresh crossover
            adx > 25 and  # Strong trend
            latest['adx_neg'] > latest['adx_pos'] and  # Bearish trend
            volume_ratio > 1.5 and  # Good volume
            obv < obv_ema and  # OBV bearish
            all_emas_bearish and  # ALL EMAs aligned
            atr_percent < 7  # Not too volatile
        )
        
        if perfect_sell:
            signal = 'SELL'
            confidence = 95
            reasons.append('Perfect bearish setup')
            reasons.append(f'RSI {rsi:.0f}, MACD cross, ADX {adx:.0f}, All EMAs aligned')
        
        # Position sizing - Conservative
        position_mult = 0.5  # Always 50%
        
        # Wider stops (give room)
        stop_distance = atr_value * 4
        take_profit_distance = atr_value * 8
        
        if signal == 'BUY':
            stop_loss = price - stop_distance
            take_profit = price + take_profit_distance
        else:
            stop_loss = 0
            take_profit = 0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons if reasons else [f'No perfect setup (RSI {rsi:.0f}, ADX {adx:.0f})'],
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
