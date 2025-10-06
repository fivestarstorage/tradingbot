"""
Enhanced Momentum Trading Strategy with Advanced Features

Key Improvements:
1. Multi-indicator confirmation (RSI, MACD, ADX, Bollinger Bands, Volume)
2. Dynamic position sizing based on volatility (ATR)
3. Support/resistance detection
4. Market regime detection (trending vs ranging)
5. Volume confirmation
6. Better entry/exit logic
7. Multiple timeframe analysis
8. Volatility-adjusted signals
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
import logging

logger = logging.getLogger(__name__)


class EnhancedMomentumStrategy:
    """
    Advanced momentum trading strategy with multiple confirmations
    
    Strategy Logic:
    - BUY when: Multiple bullish confirmations from RSI, MACD, Volume, Trend, and Price action
    - SELL when: Multiple bearish confirmations or risk management triggers
    - Uses dynamic position sizing based on volatility
    - Implements trailing stops based on ATR
    """
    
    def __init__(self, 
                 rsi_period=14,
                 rsi_overbought=70,
                 rsi_oversold=30,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 bb_period=20,
                 bb_std=2,
                 atr_period=14,
                 adx_period=14,
                 volume_period=20,
                 ema_fast=9,
                 ema_slow=21,
                 ema_trend=50):
        """
        Initialize enhanced momentum strategy
        
        Args:
            rsi_period: Period for RSI calculation
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation
            atr_period: ATR period for volatility
            adx_period: ADX period for trend strength
            volume_period: Volume moving average period
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            ema_trend: Trend EMA period
        """
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.volume_period = volume_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        
        logger.info(f"Initialized EnhancedMomentumStrategy with advanced indicators")
    
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
        Calculate all technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        if df is None or len(df) < max(self.bb_period, self.macd_slow, self.ema_trend):
            logger.error("Insufficient data for indicator calculation")
            return None
        
        # Price and volume data
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # 1. RSI - Momentum oscillator
        rsi_indicator = RSIIndicator(close=close, window=self.rsi_period)
        df['rsi'] = rsi_indicator.rsi()
        
        # 2. Stochastic RSI for additional momentum confirmation
        stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # 3. MACD - Trend following momentum
        macd = MACD(close=close, window_fast=self.macd_fast, 
                    window_slow=self.macd_slow, window_sign=self.macd_signal)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # 4. Bollinger Bands - Volatility and overbought/oversold
        bb = BollingerBands(close=close, window=self.bb_period, window_dev=self.bb_std)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 5. ATR - Average True Range for volatility
        atr = AverageTrueRange(high=high, low=low, close=close, window=self.atr_period)
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / close) * 100
        
        # 6. ADX - Trend Strength
        adx = ADXIndicator(high=high, low=low, close=close, window=self.adx_period)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        
        # 7. EMAs - Multiple timeframe trend
        ema_fast = EMAIndicator(close=close, window=self.ema_fast)
        ema_slow = EMAIndicator(close=close, window=self.ema_slow)
        ema_trend = EMAIndicator(close=close, window=self.ema_trend)
        df['ema_fast'] = ema_fast.ema_indicator()
        df['ema_slow'] = ema_slow.ema_indicator()
        df['ema_trend'] = ema_trend.ema_indicator()
        
        # 8. Volume indicators
        df['volume_ma'] = volume.rolling(window=self.volume_period).mean()
        df['volume_ratio'] = volume / df['volume_ma']
        
        # On-Balance Volume
        obv = OnBalanceVolumeIndicator(close=close, volume=volume)
        df['obv'] = obv.on_balance_volume()
        df['obv_ema'] = df['obv'].ewm(span=20).mean()
        
        # 9. Price momentum and rate of change
        df['momentum'] = close.pct_change(periods=10) * 100
        df['roc'] = close.pct_change(periods=5) * 100
        
        # 10. Support/Resistance levels using pivot points
        df = self._calculate_pivot_points(df)
        
        # 11. Market regime detection
        df = self._detect_market_regime(df)
        
        # 12. Trend direction
        df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        df['strong_trend'] = np.where(
            (df['ema_fast'] > df['ema_slow']) & (df['ema_slow'] > df['ema_trend']), 1,
            np.where((df['ema_fast'] < df['ema_slow']) & (df['ema_slow'] < df['ema_trend']), -1, 0)
        )
        
        return df
    
    def _calculate_pivot_points(self, df):
        """Calculate pivot points for support/resistance"""
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['r1'] = 2 * df['pivot'] - df['low']
        df['s1'] = 2 * df['pivot'] - df['high']
        df['r2'] = df['pivot'] + (df['high'] - df['low'])
        df['s2'] = df['pivot'] - (df['high'] - df['low'])
        return df
    
    def _detect_market_regime(self, df):
        """
        Detect market regime: trending or ranging
        Uses ADX and price action
        """
        # Trending market: ADX > 25
        # Ranging market: ADX < 20
        df['regime'] = np.where(df['adx'] > 25, 'trending',
                               np.where(df['adx'] < 20, 'ranging', 'neutral'))
        return df
    
    def generate_signal(self, df):
        """
        Generate trading signal with multiple confirmations
        
        Args:
            df: DataFrame with OHLCV and indicator data
            
        Returns:
            'BUY', 'SELL', or 'HOLD' signal with confidence, reasons, and risk management data
        """
        if df is None or len(df) < 2:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasons': ['Insufficient data'],
                'position_size': 0,
                'stop_loss': 0,
                'take_profit': 0
            }
        
        # Get latest values
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Extract indicators
        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        macd_diff = latest['macd_diff']
        bb_position = latest['bb_position']
        bb_width = latest['bb_width']
        atr_percent = latest['atr_percent']
        adx = latest['adx']
        volume_ratio = latest['volume_ratio']
        obv = latest['obv']
        obv_ema = latest['obv_ema']
        trend = latest['trend']
        strong_trend = latest['strong_trend']
        regime = latest['regime']
        price = latest['close']
        stoch_k = latest['stoch_k']
        stoch_d = latest['stoch_d']
        
        signal = 'HOLD'
        confidence = 0
        reasons = []
        
        # Check if data is valid
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(adx):
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasons': ['Indicators not ready'],
                'position_size': 0,
                'stop_loss': 0,
                'take_profit': 0
            }
        
        # =======================
        # BUY SIGNAL LOGIC
        # =======================
        buy_score = 0
        buy_reasons = []
        
        # 1. RSI Oversold (Weight: 15)
        if rsi < self.rsi_oversold:
            buy_score += 15
            buy_reasons.append(f'RSI oversold ({rsi:.1f})')
        elif rsi < 40:
            buy_score += 8
            buy_reasons.append(f'RSI low ({rsi:.1f})')
        
        # 2. RSI Divergence - price making new lows but RSI rising
        if len(df) > 5:
            recent_prices = df['close'].tail(5)
            recent_rsi = df['rsi'].tail(5)
            if recent_prices.iloc[-1] < recent_prices.min() and recent_rsi.iloc[-1] > recent_rsi.iloc[0]:
                buy_score += 20
                buy_reasons.append('Bullish RSI divergence')
        
        # 3. MACD Bullish (Weight: 15)
        if macd > macd_signal and previous['macd'] <= previous['macd_signal']:
            buy_score += 20
            buy_reasons.append('MACD bullish crossover')
        elif macd > macd_signal:
            buy_score += 10
            buy_reasons.append('MACD above signal')
        
        # 4. Stochastic Oversold and turning up (Weight: 10)
        if stoch_k < 20 and stoch_k > previous['stoch_k']:
            buy_score += 15
            buy_reasons.append(f'Stochastic oversold & rising ({stoch_k:.1f})')
        
        # 5. Bollinger Bands (Weight: 10)
        if bb_position < 0.2:  # Near lower band
            buy_score += 10
            buy_reasons.append(f'Near BB lower band (pos: {bb_position:.2f})')
        
        # 6. Volume Confirmation (Weight: 10)
        if volume_ratio > 1.5:  # Volume 50% above average
            buy_score += 10
            buy_reasons.append(f'High volume ({volume_ratio:.2f}x avg)')
        elif volume_ratio > 1.0:
            buy_score += 5
            buy_reasons.append(f'Above avg volume ({volume_ratio:.2f}x)')
        
        # 7. OBV Trend (Weight: 10)
        if obv > obv_ema and previous['obv'] <= previous['obv_ema']:
            buy_score += 12
            buy_reasons.append('OBV bullish crossover')
        elif obv > obv_ema:
            buy_score += 6
            buy_reasons.append('OBV trending up')
        
        # 8. Trend Alignment (Weight: 15)
        if strong_trend == 1:
            buy_score += 15
            buy_reasons.append('Strong uptrend (all EMAs aligned)')
        elif trend == 1:
            buy_score += 8
            buy_reasons.append('Uptrend')
        
        # 9. ADX Trend Strength (Weight: 10)
        if adx > 25 and latest['adx_pos'] > latest['adx_neg']:
            buy_score += 10
            buy_reasons.append(f'Strong bullish trend (ADX {adx:.1f})')
        elif adx > 20:
            buy_score += 5
            buy_reasons.append(f'Moderate trend (ADX {adx:.1f})')
        
        # 10. Market Regime Bonus
        if regime == 'trending' and strong_trend == 1:
            buy_score += 10
            buy_reasons.append('Trending market + aligned trend')
        
        # 11. Price near support (Weight: 10)
        if abs(price - latest['s1']) / price < 0.005:  # Within 0.5% of support
            buy_score += 10
            buy_reasons.append('Price near support level')
        
        # =======================
        # SELL SIGNAL LOGIC
        # =======================
        sell_score = 0
        sell_reasons = []
        
        # 1. RSI Overbought (Weight: 15)
        if rsi > self.rsi_overbought:
            sell_score += 15
            sell_reasons.append(f'RSI overbought ({rsi:.1f})')
        elif rsi > 60:
            sell_score += 8
            sell_reasons.append(f'RSI high ({rsi:.1f})')
        
        # 2. RSI Divergence - price making new highs but RSI falling
        if len(df) > 5:
            recent_prices = df['close'].tail(5)
            recent_rsi = df['rsi'].tail(5)
            if recent_prices.iloc[-1] > recent_prices.max() and recent_rsi.iloc[-1] < recent_rsi.iloc[0]:
                sell_score += 20
                sell_reasons.append('Bearish RSI divergence')
        
        # 3. MACD Bearish (Weight: 15)
        if macd < macd_signal and previous['macd'] >= previous['macd_signal']:
            sell_score += 20
            sell_reasons.append('MACD bearish crossover')
        elif macd < macd_signal:
            sell_score += 10
            sell_reasons.append('MACD below signal')
        
        # 4. Stochastic Overbought and turning down (Weight: 10)
        if stoch_k > 80 and stoch_k < previous['stoch_k']:
            sell_score += 15
            sell_reasons.append(f'Stochastic overbought & falling ({stoch_k:.1f})')
        
        # 5. Bollinger Bands (Weight: 10)
        if bb_position > 0.8:  # Near upper band
            sell_score += 10
            sell_reasons.append(f'Near BB upper band (pos: {bb_position:.2f})')
        
        # 6. Volume Confirmation (Weight: 10)
        if volume_ratio > 1.5:
            sell_score += 10
            sell_reasons.append(f'High volume on potential reversal ({volume_ratio:.2f}x)')
        
        # 7. OBV Trend (Weight: 10)
        if obv < obv_ema and previous['obv'] >= previous['obv_ema']:
            sell_score += 12
            sell_reasons.append('OBV bearish crossover')
        elif obv < obv_ema:
            sell_score += 6
            sell_reasons.append('OBV trending down')
        
        # 8. Trend Alignment (Weight: 15)
        if strong_trend == -1:
            sell_score += 15
            sell_reasons.append('Strong downtrend (all EMAs aligned)')
        elif trend == -1:
            sell_score += 8
            sell_reasons.append('Downtrend')
        
        # 9. ADX Trend Strength (Weight: 10)
        if adx > 25 and latest['adx_neg'] > latest['adx_pos']:
            sell_score += 10
            sell_reasons.append(f'Strong bearish trend (ADX {adx:.1f})')
        
        # 10. Price near resistance (Weight: 10)
        if abs(price - latest['r1']) / price < 0.005:  # Within 0.5% of resistance
            sell_score += 10
            sell_reasons.append('Price near resistance level')
        
        # =======================
        # DECISION LOGIC
        # =======================
        
        # Determine signal based on scores
        if buy_score > sell_score and buy_score >= 50:  # Require strong confirmation
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
            reasons = ['No strong signal', f'Buy score: {buy_score}, Sell score: {sell_score}']
        
        # =======================
        # DYNAMIC RISK MANAGEMENT
        # =======================
        
        # Position sizing based on volatility (ATR)
        # Lower volatility = larger position, Higher volatility = smaller position
        if atr_percent < 1.5:
            position_size_mult = 1.0  # 100% of base size
        elif atr_percent < 2.5:
            position_size_mult = 0.75  # 75% of base size
        elif atr_percent < 4.0:
            position_size_mult = 0.5   # 50% of base size
        else:
            position_size_mult = 0.3   # 30% of base size (very volatile)
        
        # Stop loss based on ATR (more dynamic than fixed percentage)
        atr_value = latest['atr']
        stop_loss_distance = atr_value * 2  # 2x ATR for stop loss
        take_profit_distance = atr_value * 4  # 4x ATR for take profit (2:1 reward/risk)
        
        if signal == 'BUY':
            stop_loss_price = price - stop_loss_distance
            take_profit_price = price + take_profit_distance
        elif signal == 'SELL':
            stop_loss_price = price + stop_loss_distance
            take_profit_price = price - take_profit_distance
        else:
            stop_loss_price = 0
            take_profit_price = 0
        
        # Trailing stop multiplier based on trend strength
        trailing_stop_mult = 1.5 if adx > 30 else 2.0  # Tighter trailing in strong trends
        
        result = {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'indicators': {
                'rsi': float(rsi),
                'macd': float(macd),
                'macd_signal': float(macd_signal),
                'macd_diff': float(macd_diff),
                'adx': float(adx),
                'atr_percent': float(atr_percent),
                'bb_position': float(bb_position),
                'bb_width': float(bb_width),
                'volume_ratio': float(volume_ratio),
                'trend': int(trend),
                'strong_trend': int(strong_trend),
                'price': float(price),
                'regime': regime
            },
            'risk_management': {
                'position_size_multiplier': position_size_mult,
                'stop_loss_price': float(stop_loss_price),
                'take_profit_price': float(take_profit_price),
                'atr_value': float(atr_value),
                'trailing_stop_multiplier': trailing_stop_mult,
                'stop_loss_distance_percent': float((stop_loss_distance / price) * 100),
                'take_profit_distance_percent': float((take_profit_distance / price) * 100)
            }
        }
        
        logger.info(f"Signal: {signal} (Confidence: {confidence}%) - {', '.join(reasons[:3])}")
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
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasons': ['Data processing failed'],
                'risk_management': {}
            }
        
        df = self.calculate_indicators(df)
        if df is None:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasons': ['Indicator calculation failed'],
                'risk_management': {}
            }
        
        signal = self.generate_signal(df)
        return signal
