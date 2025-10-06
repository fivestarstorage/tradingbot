"""
Enhanced Trading Strategy - Best of all improvements combined
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import logging

logger = logging.getLogger(__name__)


class EnhancedStrategy:
    """
    Production-ready enhanced momentum strategy
    Uses multiple indicators with scoring system for high-quality signals
    """
    
    def __init__(self):
        """Initialize with optimized default parameters"""
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        logger.info("Enhanced Strategy initialized")
    
    def process_klines(self, klines):
        """Convert raw klines to DataFrame"""
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
        """Calculate all technical indicators"""
        if df is None or len(df) < 50:
            return None
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # RSI
        rsi = RSIIndicator(close=close, window=self.rsi_period)
        df['rsi'] = rsi.rsi()
        
        # Stochastic
        stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        
        # MACD
        macd = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = BollingerBands(close=close, window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        atr = AverageTrueRange(high=high, low=low, close=close, window=14)
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # ADX
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        
        # EMAs
        df['ema_fast'] = EMAIndicator(close=close, window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=close, window=21).ema_indicator()
        df['ema_trend'] = EMAIndicator(close=close, window=50).ema_indicator()
        
        # Volume
        df['volume_ma'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        
        # OBV
        obv = OnBalanceVolumeIndicator(close=close, volume=volume)
        df['obv'] = obv.on_balance_volume()
        df['obv_ema'] = df['obv'].ewm(span=20).mean()
        
        # Trend direction
        df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        df['strong_trend'] = np.where(
            (df['ema_fast'] > df['ema_slow']) & (df['ema_slow'] > df['ema_trend']), 1,
            np.where((df['ema_fast'] < df['ema_slow']) & (df['ema_slow'] < df['ema_trend']), -1, 0)
        )
        
        return df
    
    def generate_signal(self, df):
        """
        Generate trading signal using scoring system
        Returns: dict with signal, confidence, and risk management params
        """
        if df is None or len(df) < 2:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Extract indicators
        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        bb_position = latest['bb_position']
        atr_percent = latest['atr_percent']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        obv = latest['obv']
        obv_ema = latest['obv_ema']
        trend = latest['trend']
        strong_trend = latest['strong_trend']
        price = latest['close']
        stoch_k = latest['stoch_k']
        
        # Check if data is valid
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(adx):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        # BUY scoring
        buy_score = 0
        buy_reasons = []
        
        if rsi < self.rsi_oversold:
            buy_score += 15
            buy_reasons.append(f'RSI oversold ({rsi:.1f})')
        elif rsi < 40:
            buy_score += 8
        
        if macd > macd_signal and previous['macd'] <= previous['macd_signal']:
            buy_score += 20
            buy_reasons.append('MACD bullish crossover')
        elif macd > macd_signal:
            buy_score += 10
        
        if stoch_k < 20 and stoch_k > previous['stoch_k']:
            buy_score += 15
            buy_reasons.append('Stochastic oversold & rising')
        
        if bb_position < 0.2:
            buy_score += 10
            buy_reasons.append('Near BB lower band')
        
        if volume_ratio > 1.5:
            buy_score += 10
            buy_reasons.append(f'High volume ({volume_ratio:.1f}x)')
        
        if obv > obv_ema:
            buy_score += 8
            buy_reasons.append('OBV bullish')
        
        if strong_trend == 1:
            buy_score += 15
            buy_reasons.append('Strong uptrend')
        elif trend == 1:
            buy_score += 8
        
        if adx > 25 and latest['adx_pos'] > latest['adx_neg']:
            buy_score += 10
            buy_reasons.append(f'Strong trend (ADX {adx:.0f})')
        
        # SELL scoring
        sell_score = 0
        sell_reasons = []
        
        if rsi > self.rsi_overbought:
            sell_score += 15
            sell_reasons.append(f'RSI overbought ({rsi:.1f})')
        
        if macd < macd_signal and previous['macd'] >= previous['macd_signal']:
            sell_score += 20
            sell_reasons.append('MACD bearish crossover')
        elif macd < macd_signal:
            sell_score += 10
        
        if stoch_k > 80 and stoch_k < previous['stoch_k']:
            sell_score += 15
            sell_reasons.append('Stochastic overbought & falling')
        
        if bb_position > 0.8:
            sell_score += 10
            sell_reasons.append('Near BB upper band')
        
        if volume_ratio > 1.5:
            sell_score += 10
        
        if obv < obv_ema:
            sell_score += 8
            sell_reasons.append('OBV bearish')
        
        if strong_trend == -1:
            sell_score += 15
            sell_reasons.append('Strong downtrend')
        elif trend == -1:
            sell_score += 8
        
        if adx > 25 and latest['adx_neg'] > latest['adx_pos']:
            sell_score += 10
            sell_reasons.append(f'Strong downtrend (ADX {adx:.0f})')
        
        # Determine signal
        if buy_score > sell_score and buy_score >= 50:
            signal = 'BUY'
            confidence = min(buy_score, 100)
            reasons = buy_reasons
        elif sell_score > buy_score and sell_score >= 50:
            signal = 'SELL'
            confidence = min(sell_score, 100)
            reasons = sell_reasons
        else:
            signal = 'HOLD'
            confidence = 0
            reasons = ['No strong signal']
        
        # Dynamic position sizing based on volatility
        if atr_percent < 1.5:
            position_mult = 1.0
        elif atr_percent < 2.5:
            position_mult = 0.75
        elif atr_percent < 4.0:
            position_mult = 0.5
        else:
            position_mult = 0.3
        
        # Risk management
        atr_value = latest['atr']
        stop_distance = atr_value * 2
        take_profit_distance = atr_value * 4
        
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
            'indicators': {
                'rsi': float(rsi),
                'macd': float(macd),
                'adx': float(adx),
                'price': float(price)
            }
        }
    
    def analyze(self, klines):
        """Full analysis pipeline"""
        df = self.process_klines(klines)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        df = self.calculate_indicators(df)
        if df is None:
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        return self.generate_signal(df)
