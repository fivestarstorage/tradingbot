"""
Volatile Coins Strategy - Optimized for High Volatility Altcoins

Designed for: SOL, DOGE, SHIB, AVAX, MATIC, etc.

Key Features:
1. Stricter entry requirements (70+ confidence vs 50)
2. Wider ATR-based stops (3x ATR vs 2x)
3. Volatility filters (won't trade if too volatile)
4. Stronger trend confirmation required
5. Volume spike detection
6. Better handles pump & dumps
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import logging

logger = logging.getLogger(__name__)


class VolatileCoinsStrategy:
    """
    Strategy specifically optimized for volatile altcoins
    Much more conservative than standard momentum strategy
    """
    
    def __init__(self):
        """Initialize with parameters tuned for volatile coins"""
        self.rsi_period = 14
        self.rsi_overbought = 75  # Higher threshold (more extreme)
        self.rsi_oversold = 25     # Lower threshold (more extreme)
        self.min_confidence = 70   # Much higher than 50
        logger.info("Volatile Coins Strategy initialized (High confidence mode)")
    
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
        df['stoch_d'] = stoch.stoch_signal()
        
        # MACD
        macd = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands (wider for volatile coins)
        bb = BollingerBands(close=close, window=20, window_dev=2.5)  # 2.5 std dev
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
        
        # ATR - Critical for volatile coins
        atr = AverageTrueRange(high=high, low=low, close=close, window=14)
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # ADX - Trend strength
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        
        # EMAs - Multiple timeframes
        df['ema_fast'] = EMAIndicator(close=close, window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=close, window=21).ema_indicator()
        df['ema_trend'] = EMAIndicator(close=close, window=50).ema_indicator()
        df['ema_long'] = EMAIndicator(close=close, window=200).ema_indicator()  # Extra confirmation
        
        # Volume analysis (critical for pump detection)
        df['volume_ma'] = volume.rolling(window=20).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        df['volume_spike'] = df['volume_ratio'] > 3.0  # 3x volume = spike
        
        # OBV
        obv = OnBalanceVolumeIndicator(close=close, volume=volume)
        df['obv'] = obv.on_balance_volume()
        df['obv_ema'] = df['obv'].ewm(span=20).mean()
        
        # Volatility regime detection
        df['volatility_regime'] = np.where(
            df['atr_percent'] > 8, 'extreme',
            np.where(df['atr_percent'] > 5, 'high',
                    np.where(df['atr_percent'] > 3, 'medium', 'low'))
        )
        
        # Trend strength
        df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        df['strong_trend'] = np.where(
            (df['ema_fast'] > df['ema_slow']) & 
            (df['ema_slow'] > df['ema_trend']) & 
            (df['ema_trend'] > df['ema_long']), 1,
            np.where(
                (df['ema_fast'] < df['ema_slow']) & 
                (df['ema_slow'] < df['ema_trend']) & 
                (df['ema_trend'] < df['ema_long']), -1, 0)
        )
        
        # Price momentum
        df['momentum'] = close.pct_change(periods=10) * 100
        df['momentum_strong'] = abs(df['momentum']) > 5  # Strong momentum
        
        return df
    
    def generate_signal(self, df):
        """
        Generate trading signal with STRICT requirements for volatile coins
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
        bb_width = latest['bb_width']
        atr_percent = latest['atr_percent']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        volume_spike = latest['volume_spike']
        obv = latest['obv']
        obv_ema = latest['obv_ema']
        trend = latest['trend']
        strong_trend = latest['strong_trend']
        volatility_regime = latest['volatility_regime']
        momentum = latest['momentum']
        momentum_strong = latest['momentum_strong']
        price = latest['close']
        stoch_k = latest['stoch_k']
        stoch_d = latest['stoch_d']
        
        # Check if data is valid
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(adx):
            return {'signal': 'HOLD', 'confidence': 0, 'risk': {}}
        
        # VOLATILITY FILTER - Don't trade if too volatile
        if volatility_regime == 'extreme':
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'risk': {},
                'reasons': [f'Too volatile (ATR {atr_percent:.1f}%) - staying out']
            }
        
        # TREND FILTER - Only trade with strong trends for volatile coins
        if adx < 20:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'risk': {},
                'reasons': [f'Weak trend (ADX {adx:.0f}) - avoiding chop']
            }
        
        # BUY scoring - MUCH stricter requirements
        buy_score = 0
        buy_reasons = []
        
        # 1. RSI - Only extreme oversold (25 vs 30)
        if rsi < self.rsi_oversold:
            buy_score += 20
            buy_reasons.append(f'RSI extremely oversold ({rsi:.1f})')
        elif rsi < 35:
            buy_score += 10
        
        # 2. Bullish divergence detection
        if len(df) > 10:
            recent_prices = df['close'].tail(10)
            recent_rsi = df['rsi'].tail(10)
            price_low = recent_prices.min()
            if recent_prices.iloc[-1] <= price_low * 1.01 and recent_rsi.iloc[-1] > recent_rsi.iloc[0] + 5:
                buy_score += 25
                buy_reasons.append('Strong bullish divergence')
        
        # 3. MACD - Must be bullish
        if macd > macd_signal and previous['macd'] <= previous['macd_signal']:
            buy_score += 25
            buy_reasons.append('MACD bullish crossover')
        elif macd > macd_signal and macd > 0:
            buy_score += 15
        elif macd <= macd_signal:
            buy_score -= 20  # Penalty if MACD is bearish
        
        # 4. Stochastic - Oversold and turning up
        if stoch_k < 20 and stoch_k > stoch_d:
            buy_score += 20
            buy_reasons.append('Stochastic oversold & rising')
        
        # 5. Bollinger Bands - Near lower band
        if bb_position < 0.15:
            buy_score += 15
            buy_reasons.append('Price at BB lower band')
        
        # 6. Volume - MUST have volume confirmation
        if volume_ratio > 1.8:
            buy_score += 20
            buy_reasons.append(f'Strong volume ({volume_ratio:.1f}x)')
        elif volume_ratio < 0.8:
            buy_score -= 15  # Penalty for low volume
        
        # 7. OBV - Must be bullish
        if obv > obv_ema and previous['obv'] <= previous['obv_ema']:
            buy_score += 20
            buy_reasons.append('OBV bullish crossover')
        elif obv > obv_ema:
            buy_score += 10
        elif obv < obv_ema:
            buy_score -= 10  # Penalty if OBV bearish
        
        # 8. Trend - MUST have strong uptrend
        if strong_trend == 1:
            buy_score += 25
            buy_reasons.append('All EMAs aligned bullish')
        elif trend == 1:
            buy_score += 10
        else:
            buy_score -= 25  # Strong penalty if downtrend
        
        # 9. ADX - Strong trend required
        if adx > 30 and latest['adx_pos'] > latest['adx_neg']:
            buy_score += 20
            buy_reasons.append(f'Strong uptrend (ADX {adx:.0f})')
        elif adx > 25:
            buy_score += 10
        
        # 10. Avoid pump conditions
        if volume_spike and momentum > 15:
            buy_score -= 30
            buy_reasons.append('Possible pump - avoiding')
        
        # SELL scoring
        sell_score = 0
        sell_reasons = []
        
        # 1. RSI overbought
        if rsi > self.rsi_overbought:
            sell_score += 20
            sell_reasons.append(f'RSI overbought ({rsi:.1f})')
        elif rsi > 65:
            sell_score += 10
        
        # 2. Bearish divergence
        if len(df) > 10:
            recent_prices = df['close'].tail(10)
            recent_rsi = df['rsi'].tail(10)
            price_high = recent_prices.max()
            if recent_prices.iloc[-1] >= price_high * 0.99 and recent_rsi.iloc[-1] < recent_rsi.iloc[0] - 5:
                sell_score += 25
                sell_reasons.append('Bearish divergence detected')
        
        # 3. MACD bearish
        if macd < macd_signal and previous['macd'] >= previous['macd_signal']:
            sell_score += 25
            sell_reasons.append('MACD bearish crossover')
        elif macd < macd_signal:
            sell_score += 15
        
        # 4. Stochastic overbought
        if stoch_k > 80 and stoch_k < stoch_d:
            sell_score += 20
            sell_reasons.append('Stochastic overbought & falling')
        
        # 5. Near upper BB
        if bb_position > 0.85:
            sell_score += 15
            sell_reasons.append('Price at BB upper band')
        
        # 6. Volume on reversal
        if volume_ratio > 2.0 and momentum < -3:
            sell_score += 20
            sell_reasons.append('High volume on reversal')
        
        # 7. OBV bearish
        if obv < obv_ema and previous['obv'] >= previous['obv_ema']:
            sell_score += 20
            sell_reasons.append('OBV bearish crossover')
        elif obv < obv_ema:
            sell_score += 10
        
        # 8. Downtrend
        if strong_trend == -1:
            sell_score += 25
            sell_reasons.append('All EMAs aligned bearish')
        elif trend == -1:
            sell_score += 10
        
        # 9. ADX bearish
        if adx > 30 and latest['adx_neg'] > latest['adx_pos']:
            sell_score += 20
            sell_reasons.append(f'Strong downtrend (ADX {adx:.0f})')
        
        # 10. Dump detection
        if volume_spike and momentum < -15:
            sell_score += 30
            sell_reasons.append('Possible dump detected')
        
        # Determine signal - STRICT threshold of 70
        if buy_score > sell_score and buy_score >= 70:
            signal = 'BUY'
            confidence = min(buy_score, 100)
            reasons = buy_reasons
        elif sell_score > buy_score and sell_score >= 70:
            signal = 'SELL'
            confidence = min(sell_score, 100)
            reasons = sell_reasons
        else:
            signal = 'HOLD'
            confidence = 0
            reasons = [f'Insufficient confidence (Buy: {buy_score}, Sell: {sell_score})']
        
        # Position sizing - More conservative for volatile coins
        if volatility_regime == 'high':
            position_mult = 0.3  # Only 30% position in high volatility
        elif volatility_regime == 'medium':
            position_mult = 0.5  # 50% position in medium volatility
        else:
            position_mult = 0.7  # 70% position in low volatility
        
        # Risk management - WIDER stops for volatile coins
        atr_value = latest['atr']
        stop_distance = atr_value * 3  # 3x ATR instead of 2x
        take_profit_distance = atr_value * 6  # 6x ATR (2:1 ratio maintained)
        
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
                'atr_value': float(atr_value),
                'volatility_regime': volatility_regime
            },
            'indicators': {
                'rsi': float(rsi),
                'macd': float(macd),
                'adx': float(adx),
                'price': float(price),
                'atr_percent': float(atr_percent)
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
