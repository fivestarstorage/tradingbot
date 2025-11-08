#!/usr/bin/env python3
"""
ML Strategy Training and Backtesting System

This script:
1. Downloads 3+ years of historical data from Binance
2. Creates multiple feature sets (technical indicators)
3. Trains various ML models on different strategies
4. Backtests each strategy on 1 year of holdout data
5. Reports the best performing strategy
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Technical analysis
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice

# ML models
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Binance client
from binance.client import Client


class MLStrategyTrainer:
    def __init__(self, symbols=['BTCUSDT', 'ETHUSDT', 'XRPUSDT']):
        """Initialize the ML strategy trainer"""
        self.symbols = symbols
        self.client = Client("", "")  # Public client (no auth needed for historical data)
        self.results = []
        
    def fetch_historical_data(self, symbol: str, days: int = 1095) -> pd.DataFrame:
        """Fetch historical kline data from Binance (3 years by default)"""
        print(f"\n📊 Fetching {days} days of data for {symbol}...")
        
        # Calculate start date
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        start_str = start_date.strftime('%d %b %Y')
        
        # Fetch 1-hour klines
        klines = self.client.get_historical_klines(
            symbol,
            Client.KLINE_INTERVAL_1HOUR,
            start_str
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        print(f"✅ Fetched {len(df)} candles ({df.index[0]} to {df.index[-1]})")
        return df
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataframe"""
        print("📈 Calculating technical indicators...")
        
        # Trend indicators
        df['sma_20'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['sma_50'] = SMAIndicator(df['close'], window=50).sma_indicator()
        df['sma_200'] = SMAIndicator(df['close'], window=200).sma_indicator()
        df['ema_12'] = EMAIndicator(df['close'], window=12).ema_indicator()
        df['ema_26'] = EMAIndicator(df['close'], window=26).ema_indicator()
        
        # MACD
        macd = MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Momentum indicators
        df['rsi'] = RSIIndicator(df['close']).rsi()
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Volatility indicators
        bb = BollingerBands(df['close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_width'] = (df['bb_high'] - df['bb_low']) / df['bb_mid']
        
        atr = AverageTrueRange(df['high'], df['low'], df['close'])
        df['atr'] = atr.average_true_range()
        
        # Volume indicators
        df['obv'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
        
        # Price action features
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_20'] = df['close'].pct_change(20)
        df['volume_change'] = df['volume'].pct_change()
        
        # Drop NaN values
        df.dropna(inplace=True)
        
        print(f"✅ Added {len([c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume']])} indicators")
        return df
    
    def create_labels(self, df: pd.DataFrame, forward_hours: int = 24, profit_threshold: float = 0.02) -> pd.DataFrame:
        """Create trading labels (1=buy, 0=hold/sell)"""
        # Calculate future return
        df['future_return'] = df['close'].pct_change(forward_hours).shift(-forward_hours)
        
        # Label: 1 if future return > threshold, else 0
        df['label'] = (df['future_return'] > profit_threshold).astype(int)
        
        # Remove rows without labels
        df = df[:-forward_hours]
        
        print(f"📊 Label distribution: {df['label'].value_counts().to_dict()}")
        return df
    
    def create_feature_sets(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Create different feature sets for testing"""
        all_features = [c for c in df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'future_return', 'label']]
        
        feature_sets = {
            'trend_only': [c for c in all_features if any(x in c for x in ['sma', 'ema', 'macd'])],
            'momentum_only': [c for c in all_features if any(x in c for x in ['rsi', 'stoch'])],
            'volatility_only': [c for c in all_features if any(x in c for x in ['bb', 'atr'])],
            'price_action': [c for c in all_features if 'price_change' in c or 'volume_change' in c],
            'all_features': all_features,
            'minimal': ['rsi', 'macd', 'sma_20', 'sma_50', 'price_change', 'volume_change'],
        }
        
        return feature_sets
    
    def train_and_backtest(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Train multiple models with different feature sets and backtest them"""
        print(f"\n🤖 Training models for {symbol}...")
        
        # Split data: First 2 years for training, last 1 year for backtesting
        split_idx = int(len(df) * 0.67)  # ~2 years training, ~1 year testing
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        print(f"📅 Training period: {train_df.index[0]} to {train_df.index[-1]}")
        print(f"📅 Testing period: {test_df.index[0]} to {test_df.index[-1]}")
        
        # Create feature sets
        feature_sets = self.create_feature_sets(train_df)
        
        # ML models to test
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            'GradientBoosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000),
        }
        
        results = []
        
        for feature_name, features in feature_sets.items():
            for model_name, model in models.items():
                try:
                    print(f"\n  🔄 Testing {model_name} with {feature_name} ({len(features)} features)...")
                    
                    # Prepare training data
                    X_train = train_df[features]
                    y_train = train_df['label']
                    
                    # Scale features
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    
                    # Train model
                    model.fit(X_train_scaled, y_train)
                    
                    # Backtest on test data
                    X_test = test_df[features]
                    X_test_scaled = scaler.transform(X_test)
                    
                    # Get predictions
                    predictions = model.predict(X_test_scaled)
                    probabilities = model.predict_proba(X_test_scaled)[:, 1]
                    
                    # Simulate trading
                    backtest_results = self.backtest_strategy(
                        test_df.copy(),
                        predictions,
                        probabilities,
                        symbol
                    )
                    
                    # Store results
                    result = {
                        'symbol': symbol,
                        'model': model_name,
                        'features': feature_name,
                        'num_features': len(features),
                        **backtest_results
                    }
                    results.append(result)
                    
                    print(f"    💰 Total Return: {result['total_return']:.2%} | Sharpe: {result['sharpe_ratio']:.2f} | Trades: {result['num_trades']}")
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    continue
        
        return results
    
    def backtest_strategy(self, df: pd.DataFrame, predictions: np.ndarray, probabilities: np.ndarray, symbol: str) -> Dict:
        """Backtest a strategy with buy/sell signals"""
        # Add predictions to dataframe
        df['signal'] = predictions
        df['probability'] = probabilities
        
        # Trading simulation
        initial_capital = 10000
        capital = initial_capital
        position = 0
        position_price = 0
        trades = []
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            signal = df['signal'].iloc[i]
            prob = df['probability'].iloc[i]
            
            # Buy signal (and not already in position)
            if signal == 1 and prob > 0.6 and position == 0:
                # Buy with 100% of capital
                position = capital / current_price
                position_price = current_price
                capital = 0
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'timestamp': df.index[i]
                })
            
            # Sell signal (if in position)
            elif (signal == 0 or prob < 0.4) and position > 0:
                # Sell position
                capital = position * current_price
                pnl = (current_price - position_price) / position_price
                position = 0
                position_price = 0
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'pnl': pnl,
                    'timestamp': df.index[i]
                })
        
        # Close any open position
        if position > 0:
            capital = position * df['close'].iloc[-1]
            position = 0
        
        # Calculate metrics
        final_value = capital
        total_return = (final_value - initial_capital) / initial_capital
        
        # Calculate Sharpe ratio
        df['returns'] = df['close'].pct_change()
        sharpe_ratio = df['returns'].mean() / df['returns'].std() * np.sqrt(24 * 365) if df['returns'].std() > 0 else 0
        
        # Buy and hold comparison
        buy_hold_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        
        return {
            'total_return': total_return,
            'final_value': final_value,
            'num_trades': len(trades),
            'sharpe_ratio': sharpe_ratio,
            'buy_hold_return': buy_hold_return,
            'outperformance': total_return - buy_hold_return,
        }
    
    def run_training(self):
        """Run the full training pipeline"""
        print("="*80)
        print("🚀 ML STRATEGY TRAINING & BACKTESTING")
        print("="*80)
        
        all_results = []
        
        for symbol in self.symbols:
            try:
                # Fetch data
                df = self.fetch_historical_data(symbol, days=1095)  # 3 years
                
                # Add indicators
                df = self.add_technical_indicators(df)
                
                # Create labels
                df = self.create_labels(df, forward_hours=24, profit_threshold=0.02)
                
                # Train and backtest
                results = self.train_and_backtest(df, symbol)
                all_results.extend(results)
                
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Save results
        self.results = all_results
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save results to JSON file"""
        output_file = 'ml_strategy_results.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n💾 Results saved to {output_file}")
    
    def print_summary(self):
        """Print summary of best strategies"""
        print("\n" + "="*80)
        print("📊 BEST STRATEGIES (Top 10)")
        print("="*80)
        
        # Sort by total return
        sorted_results = sorted(self.results, key=lambda x: x['total_return'], reverse=True)
        
        print(f"\n{'Rank':<6}{'Symbol':<10}{'Model':<20}{'Features':<20}{'Return':<12}{'Sharpe':<10}{'Trades':<8}{'vs B&H':<10}")
        print("-"*100)
        
        for i, result in enumerate(sorted_results[:10], 1):
            print(f"{i:<6}{result['symbol']:<10}{result['model']:<20}{result['features']:<20}"
                  f"{result['total_return']:>10.2%}  {result['sharpe_ratio']:>8.2f}  "
                  f"{result['num_trades']:>6}  {result['outperformance']:>8.2%}")
        
        print("\n" + "="*80)
        
        # Best strategy
        best = sorted_results[0]
        print(f"\n🏆 BEST STRATEGY:")
        print(f"   Symbol: {best['symbol']}")
        print(f"   Model: {best['model']}")
        print(f"   Features: {best['features']} ({best['num_features']} features)")
        print(f"   Total Return: {best['total_return']:.2%}")
        print(f"   Final Value: ${best['final_value']:.2f}")
        print(f"   Number of Trades: {best['num_trades']}")
        print(f"   Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        print(f"   Buy & Hold Return: {best['buy_hold_return']:.2%}")
        print(f"   Outperformance: {best['outperformance']:.2%}")
        print("="*80)


if __name__ == '__main__':
    trainer = MLStrategyTrainer(symbols=['BTCUSDT', 'ETHUSDT', 'XRPUSDT'])
    trainer.run_training()

