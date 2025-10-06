"""
Momentum trading strategy implementation
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import logging

logger = logging.getLogger(__name__)


class MomentumStrategy:
    """
    Momentum trading strategy using RSI and price momentum
    
    Strategy Logic:
    - BUY when: RSI is oversold (<30) and price momentum is positive
    - SELL when: RSI is overbought (>70) or price momentum turns negative
    """
    
    def __init__(self, rsi_period=14, rsi_overbought=70, rsi_oversold=30, momentum_period=10):
        """
        Initialize momentum strategy
        
        Args:
            rsi_period: Period for RSI calculation
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            momentum_period: Period for momentum calculation
        """
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.momentum_period = momentum_period
        
        logger.info(f"Initialized MomentumStrategy: RSI({rsi_period}), "
                   f"Overbought={rsi_overbought}, Oversold={rsi_oversold}, "
                   f"Momentum Period={momentum_period}")
    
    def process_klines(self, klines):
        """
        Process raw kline data into a pandas DataFrame
        
        Args:
            klines: Raw kline data from Binance API
            
        Returns:
            DataFrame with OHLCV data
        """
        if not klines or len(klines) == 0:
            logger.error("No kline data provided")
            return None
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert to appropriate types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    
    def calculate_indicators(self, df):
        """
        Calculate technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        if df is None or len(df) < self.rsi_period:
            logger.error("Insufficient data for indicator calculation")
            return None
        
        # Calculate RSI
        rsi_indicator = RSIIndicator(close=df['close'], window=self.rsi_period)
        df['rsi'] = rsi_indicator.rsi()
        
        # Calculate price momentum (rate of change)
        df['momentum'] = df['close'].pct_change(periods=self.momentum_period) * 100
        
        # Calculate EMAs for trend confirmation
        ema_fast = EMAIndicator(close=df['close'], window=9)
        ema_slow = EMAIndicator(close=df['close'], window=21)
        df['ema_fast'] = ema_fast.ema_indicator()
        df['ema_slow'] = ema_slow.ema_indicator()
        
        # Trend: 1 if fast EMA > slow EMA (uptrend), -1 otherwise
        df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        
        return df
    
    def generate_signal(self, df):
        """
        Generate trading signal based on momentum strategy
        
        Args:
            df: DataFrame with OHLCV and indicator data
            
        Returns:
            'BUY', 'SELL', or 'HOLD' signal with confidence and reasons
        """
        if df is None or len(df) == 0:
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['Insufficient data']}
        
        # Get latest values
        latest = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else latest
        
        rsi = latest['rsi']
        momentum = latest['momentum']
        trend = latest['trend']
        price = latest['close']
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # Check if data is valid
        if pd.isna(rsi) or pd.isna(momentum):
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['Indicators not ready']}
        
        # BUY Signal Logic
        if rsi < self.rsi_oversold:
            confidence += 40
            reasons.append(f'RSI oversold ({rsi:.2f} < {self.rsi_oversold})')
            
            if momentum > 0:
                confidence += 30
                reasons.append(f'Positive momentum ({momentum:.2f}%)')
            
            if trend == 1:
                confidence += 20
                reasons.append('Uptrend confirmed (EMA)')
            
            # Additional confirmation: RSI bouncing up
            if rsi > previous['rsi']:
                confidence += 10
                reasons.append('RSI trending up')
            
            if confidence >= 40:  # Lowered from 50 to generate more signals
                signal = 'BUY'
        
        # SELL Signal Logic
        elif rsi > self.rsi_overbought:
            confidence += 40
            reasons.append(f'RSI overbought ({rsi:.2f} > {self.rsi_overbought})')
            
            if momentum < 0:
                confidence += 30
                reasons.append(f'Negative momentum ({momentum:.2f}%)')
            
            if trend == -1:
                confidence += 20
                reasons.append('Downtrend confirmed (EMA)')
            
            # Additional confirmation: RSI trending down
            if rsi < previous['rsi']:
                confidence += 10
                reasons.append('RSI trending down')
            
            if confidence >= 40:  # Lowered from 50 to generate more signals
                signal = 'SELL'
        
        # Neutral zone - look for momentum shifts
        else:
            if momentum > 3 and trend == 1 and rsi < 50:  # Lowered from 5 to 3
                confidence = 40
                reasons.append(f'Strong positive momentum ({momentum:.2f}%) in uptrend')
                signal = 'BUY'
            elif momentum < -3 and trend == -1 and rsi > 50:  # Lowered from -5 to -3
                confidence = 40
                reasons.append(f'Strong negative momentum ({momentum:.2f}%) in downtrend')
                signal = 'SELL'
            # Additional signals for very tight RSI ranges (for hyper-aggressive strategies)
            elif momentum > 1 and rsi < 48:
                confidence = 40
                reasons.append(f'Slight momentum with low RSI')
                signal = 'BUY'
            elif momentum < -1 and rsi > 52:
                confidence = 40
                reasons.append(f'Slight negative momentum with high RSI')
                signal = 'SELL'
            else:
                reasons.append(f'Neutral zone (RSI: {rsi:.2f}, Momentum: {momentum:.2f}%)')
        
        result = {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'indicators': {
                'rsi': float(rsi),
                'momentum': float(momentum),
                'trend': int(trend),
                'price': float(price),
                'ema_fast': float(latest['ema_fast']),
                'ema_slow': float(latest['ema_slow'])
            }
        }
        
        logger.info(f"Signal: {signal} (Confidence: {confidence}%) - {', '.join(reasons)}")
        return result
    
    def analyze(self, klines):
        """
        Full analysis pipeline: process data, calculate indicators, generate signal
        
        Args:
            klines: Raw kline data from Binance API
            
        Returns:
            Signal dict with trading recommendation
        """
        df = self.process_klines(klines)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['Data processing failed']}
        
        df = self.calculate_indicators(df)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': ['Indicator calculation failed']}
        
        signal = self.generate_signal(df)
        return signal
