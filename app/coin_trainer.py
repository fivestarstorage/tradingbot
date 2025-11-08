#!/usr/bin/env python3
"""
ML Training Service for Dynamic Coins
Trains ML models on 3 years of historical data to find best trading strategy
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from .models import TradingCoin


def fetch_historical_data(coin: str, days: int = 1095) -> pd.DataFrame:
    """
    Fetch historical kline data from Binance
    
    Args:
        coin: Coin symbol (e.g., "ZEC")
        days: Number of days of history (default 1095 = 3 years)
    
    Returns:
        DataFrame with OHLCV data
    """
    import requests
    
    symbol = f"{coin}USDT"
    
    # Binance limits to 1000 candles per request
    # For 3 years of daily data, we need 1095 candles
    # Use 1d interval
    
    print(f"📊 Fetching {days} days of historical data for {symbol}...")
    
    try:
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': '1d',
            'limit': min(days + 10, 1000)  # Get a bit more for buffer
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        klines = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Keep only what we need
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.set_index('timestamp')
        
        print(f"✅ Fetched {len(df)} days of data")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        raise


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators for ML features"""
    
    print("📈 Calculating technical indicators...")
    
    # Returns
    df['returns'] = df['close'].pct_change()
    df['returns_5d'] = df['close'].pct_change(5)
    df['returns_10d'] = df['close'].pct_change(10)
    
    # Moving averages
    df['sma_7'] = df['close'].rolling(7).mean()
    df['sma_25'] = df['close'].rolling(25).mean()
    df['sma_99'] = df['close'].rolling(99).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Volume indicators
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # Volatility
    df['volatility'] = df['returns'].rolling(20).std()
    
    # Price momentum
    df['momentum'] = df['close'] / df['close'].shift(10) - 1
    
    # Target: Future returns (next 7 days)
    df['target'] = df['close'].shift(-7) / df['close'] - 1
    
    # Drop NaN values
    df = df.dropna()
    
    print(f"✅ Calculated indicators, {len(df)} rows remaining")
    return df


def train_ml_model(df: pd.DataFrame) -> Dict:
    """
    Train ML model and evaluate different strategies
    
    Returns:
        Dict with best model info and metrics
    """
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    
    print("🤖 Training ML models...")
    
    # Features for prediction
    feature_cols = [
        'returns', 'returns_5d', 'returns_10d',
        'rsi', 'bb_position', 'volume_ratio',
        'volatility', 'momentum'
    ]
    
    X = df[feature_cols]
    
    # Binary classification: Will price go up >2% in next 7 days?
    y = (df['target'] > 0.02).astype(int)
    
    # Split data
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"  Training set: {len(X_train)} samples")
    print(f"  Test set: {len(X_test)} samples")
    
    # Try different models
    models = {
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
        'GradientBoosting': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    }
    
    best_model = None
    best_accuracy = 0
    best_model_name = None
    
    for name, model in models.items():
        print(f"\n  Training {name}...")
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"    Accuracy: {accuracy:.2%}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model = model
            best_model_name = name
    
    print(f"\n✅ Best model: {best_model_name} ({best_accuracy:.2%})")
    
    # Calculate additional metrics
    y_pred = best_model.predict(X_test)
    
    # Win rate: Of all predicted "buy" signals, how many were correct?
    buy_signals = y_pred == 1
    if buy_signals.sum() > 0:
        win_rate = (y_test[buy_signals] == 1).mean()
    else:
        win_rate = 0
    
    # Calculate returns if we followed the model
    test_returns = df['target'][split_idx:]
    strategy_returns = test_returns[buy_signals].values
    
    if len(strategy_returns) > 0:
        avg_return = strategy_returns.mean()
        sharpe = strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0
    else:
        avg_return = 0
        sharpe = 0
    
    print(f"  Win Rate: {win_rate:.2%}")
    print(f"  Avg Return per Trade: {avg_return:.2%}")
    print(f"  Sharpe Ratio: {sharpe:.2f}")
    
    return {
        'model_type': best_model_name,
        'accuracy': best_accuracy,
        'win_rate': win_rate,
        'sharpe_ratio': sharpe,
        'avg_return': avg_return,
        'total_signals': int(buy_signals.sum()),
        'feature_importance': dict(zip(feature_cols, best_model.feature_importances_.tolist())),
        'strategy': {
            'signal_threshold': 0.5,
            'features': feature_cols,
            'lookback_days': 7
        }
    }


def add_trading_coin(db: Session, coin: str, coin_name: str = None, force: bool = False) -> dict:
    """
    Add coin to trading list (no ML training - uses sentiment-based trading)
    
    Args:
        db: Database session
        coin: Coin symbol (e.g., "ZEC")
        coin_name: Full coin name (e.g., "Zcash")
        force: Not used anymore, kept for compatibility
    
    Returns:
        Dict with results
    """
    coin = coin.upper()
    symbol = f"{coin}USDT"
    
    print("\n" + "="*80)
    print(f"🚀 ADDING {coin} TO TRADING LIST")
    print("="*80 + "\n")
    
    # Check if already exists
    existing = db.query(TradingCoin).filter(TradingCoin.coin == coin).first()
    if existing:
        print(f"⚠️  {coin} already exists in trading list!")
        return {
            'success': False,
            'reason': 'already_exists',
            'coin': existing,
            'recommendation': 'This coin is already in your trading list.'
        }
    
    try:
        # Just add the coin - no ML training!
        print(f"📰 Adding {coin} with sentiment-based trading strategy...")
        print(f"   Strategy: Buy when news is positive, sell when negative")
        print(f"   Thresholds: Sell < 30/100, Buy > 50/100")
        
        trading_coin = TradingCoin(
            coin=coin,
            coin_name=coin_name or coin,
            symbol=symbol,
            ml_model_type=None,  # No ML
            ml_strategy=None,
            ml_accuracy=None,
            ml_sharpe_ratio=None,
            ml_win_rate=None,
            training_period_days=0,
            enabled=True,
            ai_decisions_enabled=True,  # Always enabled (uses sentiment, not ML)
            test_mode=True
        )
        
        db.add(trading_coin)
        db.commit()
        
        print("\n" + "="*80)
        print(f"✅ {coin} ADDED SUCCESSFULLY!")
        print("="*80)
        print(f"\n📰 Trading Strategy: SENTIMENT-BASED")
        print(f"   • Trades based on news sentiment only")
        print(f"   • No ML models or technical indicators")
        print(f"   • Sell when sentiment < 30/100")
        print(f"   • Buy when sentiment > 50/100")
        print(f"\n🎯 {coin} is now available in your dashboard")
        print(f"   • AI decisions: ENABLED (sentiment-based)")
        print(f"   • Test mode: ENABLED (safe virtual trading)")
        print()
        
        return {
            'success': True,
            'coin': trading_coin,
            'results': {},
            'ai_enabled': True,
            'recommendation': 'Sentiment-based trading enabled'
        }
        
    except Exception as e:
        print(f"\n❌ Error adding {coin}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise


def get_all_trading_coins(db: Session) -> list:
    """Get all trading coins including base coins and dynamically added ones"""
    
    # Get all enabled coins from database
    all_coins = db.query(TradingCoin).filter(TradingCoin.enabled == True).all()
    
    # Convert to list with proper format
    coins_list = []
    seen_symbols = set()
    
    for coin in all_coins:
        if coin.coin not in seen_symbols:
            coins_list.append({
                **coin.to_dict(),
                'is_base': coin.coin in ['BTC', 'ETH', 'XRP', 'VIRTUAL']  # Mark base coins
            })
            seen_symbols.add(coin.coin)
    
    return coins_list

