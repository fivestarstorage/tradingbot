"""
Feature Engineering Module

Calculates technical indicators, detects spikes, creates ML features
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import yaml
import ta  # Technical Analysis library


class FeatureEngineering:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize feature engineering with config"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.rolling_windows = self.config['features']['rolling_windows']
    
    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate price returns"""
        df = df.copy()
        
        # Simple returns
        df['return_1'] = df['close'].pct_change(1)
        df['return_5'] = df['close'].pct_change(5)
        df['return_15'] = df['close'].pct_change(15)
        df['return_30'] = df['close'].pct_change(30)
        
        # Log returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators using ta library"""
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        df['macd_cross_up'] = ((df['macd'] > df['macd_signal']) & 
                               (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_high'] = bollinger.bollinger_hband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        df['bb_low'] = bollinger.bollinger_lband()
        df['bb_width'] = (df['bb_high'] - df['bb_low']) / df['bb_mid']
        df['bb_position'] = (df['close'] - df['bb_low']) / (df['bb_high'] - df['bb_low'])
        
        # EMA (Exponential Moving Average)
        df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
        df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        df['ema_cross'] = (df['ema_9'] > df['ema_21']).astype(int)
        
        # ATR (Average True Range) - Volatility
        df['atr'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=14
        ).average_true_range()
        df['atr_pct'] = df['atr'] / df['close']
        
        # OBV (On Balance Volume)
        df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
        df['obv_ema'] = ta.trend.EMAIndicator(df['obv'], window=20).ema_indicator()
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # ADX (Average Directional Index) - Trend Strength
        adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'])
        df['adx'] = adx.adx()
        
        return df
    
    def calculate_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate rolling statistics for multiple windows"""
        df = df.copy()
        
        for window in self.rolling_windows:
            # Price statistics
            df[f'close_mean_{window}'] = df['close'].rolling(window).mean()
            df[f'close_std_{window}'] = df['close'].rolling(window).std()
            df[f'close_zscore_{window}'] = (df['close'] - df[f'close_mean_{window}']) / df[f'close_std_{window}']
            
            # Volume statistics
            df[f'volume_mean_{window}'] = df['volume'].rolling(window).mean()
            df[f'volume_std_{window}'] = df['volume'].rolling(window).std()
            df[f'volume_ratio_{window}'] = df['volume'] / df[f'volume_mean_{window}']
            
            # High/Low range
            df[f'hl_ratio_{window}'] = (df['high'] - df['low']).rolling(window).mean() / df['close']
            
            # Momentum
            df[f'momentum_{window}'] = df['close'] - df['close'].shift(window)
            df[f'momentum_pct_{window}'] = df['close'].pct_change(window)
        
        return df
    
    def detect_spikes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect price spikes based on z-score and volume
        
        A spike is defined as:
        1. Price z-score > threshold (e.g., 3.0)
        2. Volume > volume_multiplier × avg_volume (e.g., 5×)
        """
        df = df.copy()
        
        zscore_threshold = self.config['spike_detection']['zscore_threshold']
        volume_multiplier = self.config['spike_detection']['volume_multiplier']
        lookback = self.config['spike_detection']['lookback_window']
        
        # Calculate baseline statistics
        df['price_zscore'] = (df['close'] - df['close'].rolling(lookback).mean()) / df['close'].rolling(lookback).std()
        df['volume_avg'] = df['volume'].rolling(lookback).mean()
        df['volume_ratio_spike'] = df['volume'] / df['volume_avg']
        
        # Spike detection
        df['is_spike'] = (
            (df['price_zscore'] > zscore_threshold) & 
            (df['volume_ratio_spike'] > volume_multiplier)
        ).astype(int)
        
        return df
    
    def calculate_forward_returns(self, df: pd.DataFrame, horizons: List[int] = None) -> pd.DataFrame:
        """
        Calculate forward returns for labeling
        
        Args:
            df: DataFrame with OHLCV data
            horizons: List of forward periods to calculate returns for
        """
        df = df.copy()
        
        if horizons is None:
            horizons = [5, 10, 15, 30, 60]
        
        for horizon in horizons:
            # Future return
            df[f'forward_return_{horizon}'] = df['close'].shift(-horizon) / df['close'] - 1
            
            # Future high (max price in next N periods)
            df[f'forward_high_{horizon}'] = df['high'].rolling(horizon).max().shift(-horizon)
            df[f'forward_high_return_{horizon}'] = df[f'forward_high_{horizon}'] / df['close'] - 1
            
            # Future low (min price in next N periods)
            df[f'forward_low_{horizon}'] = df['low'].rolling(horizon).min().shift(-horizon)
            df[f'forward_low_return_{horizon}'] = df[f'forward_low_{horizon}'] / df['close'] - 1
        
        return df
    
    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create binary labels for ML model
        
        Label = 1 if price increases by threshold% within horizon periods
        Label = 0 otherwise
        """
        df = df.copy()
        
        horizon = self.config['model']['label_horizon']
        threshold = self.config['model']['label_threshold']
        
        # Binary label: will price go up by threshold% in next N periods?
        df[f'forward_return_{horizon}'] = df['close'].shift(-horizon) / df['close'] - 1
        df['label'] = (df[f'forward_return_{horizon}'] >= threshold).astype(int)
        
        # Regression label (optional)
        df['label_regression'] = df[f'forward_return_{horizon}']
        
        return df
    
    def create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create complete feature set
        
        This is the main method to generate all features
        """
        print(f"📊 Creating features for {len(df)} candles...")
        
        df = df.copy()
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Basic returns
        df = self.calculate_returns(df)
        print("   ✅ Returns calculated")
        
        # Technical indicators
        df = self.calculate_technical_indicators(df)
        print("   ✅ Technical indicators calculated")
        
        # Rolling features
        df = self.calculate_rolling_features(df)
        print("   ✅ Rolling features calculated")
        
        # Spike detection
        df = self.detect_spikes(df)
        print("   ✅ Spikes detected")
        
        # Forward returns and labels
        df = self.calculate_forward_returns(df)
        df = self.create_labels(df)
        print("   ✅ Labels created")
        
        # Drop rows with NaN (from rolling calculations)
        initial_rows = len(df)
        df = df.dropna()
        print(f"   ✅ Dropped {initial_rows - len(df)} rows with NaN")
        
        # Replace inf values with NaN and drop those rows too
        import numpy as np
        df = df.replace([np.inf, -np.inf], np.nan)
        before_inf = len(df)
        df = df.dropna()
        if before_inf - len(df) > 0:
            print(f"   ✅ Dropped {before_inf - len(df)} rows with inf values")
        
        print(f"✅ Feature engineering complete: {len(df)} rows, {len(df.columns)} features")
        
        return df
    
    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get list of feature columns (excluding metadata and labels)"""
        exclude = ['timestamp', 'symbol', 'timeframe', 'open', 'high', 'low', 'close', 'volume',
                   'label', 'label_regression']
        
        # Also exclude forward-looking columns used for labeling
        exclude.extend([col for col in df.columns if col.startswith('forward_')])
        
        features = [col for col in df.columns if col not in exclude]
        return features
    
    def get_feature_importance_names(self) -> Dict[str, str]:
        """Human-readable names for features"""
        return {
            'rsi': 'RSI (14)',
            'macd': 'MACD',
            'macd_diff': 'MACD Histogram',
            'bb_width': 'Bollinger Band Width',
            'bb_position': 'BB Position',
            'ema_cross': 'EMA 9/21 Cross',
            'atr_pct': 'ATR %',
            'volume_ratio_spike': 'Volume Spike Ratio',
            'is_spike': 'Spike Detected',
            'return_1': '1-Period Return',
            'return_5': '5-Period Return'
        }


def main():
    """Test feature engineering"""
    from data_ingestion import DataIngestion
    
    print("="*80)
    print("🧪 TESTING FEATURE ENGINEERING")
    print("="*80)
    
    # Load data
    ingestion = DataIngestion()
    df = ingestion.load_ohlcv('BTC/USDT', '1m')
    
    if df.empty:
        print("❌ No data found. Run data_ingestion.py first.")
        return
    
    print(f"\n📊 Loaded {len(df)} candles")
    
    # Create features
    fe = FeatureEngineering()
    df_features = fe.create_all_features(df)
    
    # Display results
    print(f"\n✅ Features created:")
    print(f"   Rows: {len(df_features)}")
    print(f"   Columns: {len(df_features.columns)}")
    print(f"\n📋 Feature columns:")
    feature_cols = fe.get_feature_columns(df_features)
    for i, col in enumerate(feature_cols[:20], 1):
        print(f"   {i:2d}. {col}")
    if len(feature_cols) > 20:
        print(f"   ... and {len(feature_cols) - 20} more")
    
    # Show spike statistics
    spike_count = df_features['is_spike'].sum()
    print(f"\n🔥 Spike Detection:")
    print(f"   Total spikes: {spike_count}")
    print(f"   Spike rate: {spike_count / len(df_features) * 100:.2f}%")
    
    # Show label distribution
    print(f"\n🏷️  Label Distribution:")
    print(f"   Positive: {df_features['label'].sum()} ({df_features['label'].mean()*100:.1f}%)")
    print(f"   Negative: {(1-df_features['label']).sum()} ({(1-df_features['label'].mean())*100:.1f}%)")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()

