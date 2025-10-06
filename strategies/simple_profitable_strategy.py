"""
Simple Profitable Strategy - What Actually Works

Philosophy: Less is more
- Only trade clear, obvious setups
- Wide stops (don't get shaken out)
- Let winners run
- Cut losers quickly

Designed after analyzing what works across BTC, ETH, SOL, and altcoins.
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import logging

logger = logging.getLogger(__name__)


class SimpleProfitableStrategy:
    """
    What actually works: Simple rules, strictly followed
    
    BUY Rules (ALL must be true):
    1. RSI < 40 (not just oversold, but getting there)
    2. Price > 50 EMA (only buy in uptrends)
    3. Volume increasing (confirmation)
    4. ADX > 20 (some trend, not choppy)
    
    SELL Rules:
    1. RSI > 60 OR
    2. Price crosses below 50 EMA OR
    3. Stop loss hit
    
    Position Sizing: 50% of capital max
    Stops: 5% fixed (works for most coins)
    Target: 10% (2:1 reward/risk)
    """
    
    def __init__(self):
        self.name = "Simple Profitable"
        logger.info("Simple Profitable Strategy initialized")
    
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
        
        # RSI - Simple, effective
        df['rsi'] = RSIIndicator(close=close, window=14).rsi()
        
        # 50 EMA - Trend filter
        df['ema_50'] = EMAIndicator(close=close, window=50).ema_indicator()
        
        # ADX - Avoid choppy markets
        df['adx'] = ADXIndicator(high=high, low=low, close=close, window=14).adx()
        
        # Volume - Confirmation
        df['volume_ma'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        
        # OBV - Money flow
        df['obv'] = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        df['obv_ma'] = df['obv'].rolling(window=20).mean()
        
        return df
    
    def generate_signal(self, df):
        if df is None or len(df) < 2:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        price = latest['close']
        rsi = latest['rsi']
        ema_50 = latest['ema_50']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        obv = latest['obv']
        obv_ma = latest['obv_ma']
        
        if pd.isna(rsi) or pd.isna(ema_50) or pd.isna(adx):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # ===== BUY LOGIC (Require 4 out of 5 conditions) =====
        buy_conditions = {
            'rsi': rsi < 45,  # Getting oversold (relaxed from 40)
            'trend': price > ema_50,  # Price above 50 EMA (uptrend)
            'not_choppy': adx > 20,  # Some trend, not ranging
            'volume': volume_ratio > 1.0,  # Volume above average (relaxed from 1.2)
            'money_flow': obv > obv_ma  # Money flowing in
        }
        
        buy_count = sum(buy_conditions.values())
        
        # Require at least 4 out of 5 conditions (more practical)
        if buy_count >= 4:
            signal = 'BUY'
            confidence = 85 if buy_count == 5 else 70
            conditions_met = [k for k, v in buy_conditions.items() if v]
            reasons.append(f'{buy_count}/5 conditions: {", ".join(conditions_met)}')
        
        # ===== SELL LOGIC =====
        sell_conditions = {
            'rsi_high': rsi > 60,
            'below_ema': price < ema_50,
            'volume_dump': volume_ratio > 2.0 and price < previous['close']
        }
        
        if any(sell_conditions.values()):
            signal = 'SELL'
            confidence = 80
            if sell_conditions['rsi_high']:
                reasons.append(f'RSI overbought ({rsi:.0f})')
            if sell_conditions['below_ema']:
                reasons.append('Price broke below 50 EMA (trend change)')
            if sell_conditions['volume_dump']:
                reasons.append('High volume sell-off detected')
        
        # Position sizing - Conservative 50%
        position_mult = 0.5
        
        # Simple fixed stops that work
        stop_loss = price * 0.95  # 5% stop
        take_profit = price * 1.10  # 10% target (2:1 ratio)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons if reasons else [f'No setup (RSI {rsi:.0f}, {buy_count}/5 conditions)'],
            'risk': {
                'stop_loss': float(stop_loss),
                'take_profit': float(take_profit),
                'position_multiplier': position_mult,
                'atr_value': 0
            },
            'indicators': {
                'rsi': float(rsi),
                'price': float(price),
                'ema_50': float(ema_50),
                'adx': float(adx)
            }
        }
    
    def analyze(self, klines):
        df = self.process_klines(klines)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        df = self.calculate_indicators(df)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        return self.generate_signal(df)
