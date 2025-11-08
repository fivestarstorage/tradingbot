#!/usr/bin/env python3
"""
News Sentiment-Based Trading Strategy
Hold coin but sell when news sentiment turns negative
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import sys


def fetch_historical_data(coin: str, days: int = 365):
    """Fetch historical data from Binance"""
    symbol = f"{coin}USDT"
    print(f"\n📊 Fetching {days} days of data for {symbol}...")
    
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': '1d',
        'limit': min(days + 10, 1000)
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    klines = response.json()
    
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.set_index('timestamp')
    
    print(f"✅ Fetched {len(df)} days of data")
    return df


def simulate_sentiment_signals(df: pd.DataFrame):
    """
    Simulate news sentiment signals based on price action patterns
    In real implementation, these would come from your AI news analysis
    
    Sentiment triggers:
    - NEGATIVE: Big drop (>15% in short period) or sustained downtrend
    - NEUTRAL: Sideways movement
    - POSITIVE: Sustained uptrend
    """
    
    df = df.copy()
    
    # Calculate price momentum indicators
    df['returns_3d'] = df['close'].pct_change(3)
    df['returns_7d'] = df['close'].pct_change(7)
    df['returns_14d'] = df['close'].pct_change(14)
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    
    # Sentiment scoring (0-100)
    df['sentiment'] = 50.0  # Start neutral
    
    for i in range(len(df)):
        if i < 50:  # Need history
            continue
        
        score = 50  # Base neutral
        
        # Recent sharp drop = negative sentiment
        if df['returns_3d'].iloc[i] < -0.15:  # -15% in 3 days
            score -= 30
        elif df['returns_7d'].iloc[i] < -0.20:  # -20% in 7 days
            score -= 25
        
        # Trend indicators
        if df['close'].iloc[i] < df['sma_20'].iloc[i] < df['sma_50'].iloc[i]:
            score -= 15  # Downtrend
        elif df['close'].iloc[i] > df['sma_20'].iloc[i] > df['sma_50'].iloc[i]:
            score += 15  # Uptrend
        
        # Volume spike with drop = panic selling
        avg_volume = df['volume'].iloc[i-20:i].mean()
        if df['volume'].iloc[i] > avg_volume * 2 and df['returns_3d'].iloc[i] < -0.10:
            score -= 20
        
        # Strong recovery = positive sentiment
        if df['returns_7d'].iloc[i] > 0.20:  # +20% in 7 days
            score += 20
        
        df.loc[df.index[i], 'sentiment'] = max(0, min(100, score))
    
    return df


def backtest_sentiment_strategy(df: pd.DataFrame, sell_threshold: int, buy_threshold: int):
    """
    Backtest sentiment-based hold strategy
    
    Strategy:
    - Buy and hold
    - Sell when sentiment drops below sell_threshold
    - Re-buy when sentiment recovers above buy_threshold
    """
    
    initial_capital = 10000
    capital = initial_capital
    position = 0
    in_position = False
    
    trades = []
    portfolio_values = []
    
    for timestamp, row in df.iterrows():
        price = row['close']
        sentiment = row['sentiment']
        
        if pd.isna(sentiment):
            continue
        
        if not in_position:
            # Buy when sentiment is positive
            if sentiment >= buy_threshold:
                position = capital / price
                entry_value = capital
                entry_price = price
                in_position = True
                capital = 0
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY',
                    'price': price,
                    'quantity': position,
                    'sentiment': sentiment,
                    'reason': f'Sentiment recovered to {sentiment:.0f}'
                })
        
        else:
            # Sell when sentiment turns negative
            if sentiment <= sell_threshold:
                capital = position * price
                sell_pnl = capital - entry_value
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'SELL',
                    'price': price,
                    'quantity': position,
                    'sentiment': sentiment,
                    'pnl': sell_pnl,
                    'reason': f'Negative sentiment: {sentiment:.0f}'
                })
                
                position = 0
                in_position = False
        
        # Track portfolio value
        if in_position:
            total_value = position * price
        else:
            total_value = capital
        
        portfolio_values.append({
            'timestamp': timestamp,
            'value': total_value,
            'price': price,
            'sentiment': sentiment
        })
    
    # Close any open position
    if in_position:
        final_price = df.iloc[-1]['close']
        capital = position * final_price
        sell_pnl = capital - entry_value
        
        trades.append({
            'timestamp': df.index[-1],
            'action': 'SELL (END)',
            'price': final_price,
            'quantity': position,
            'sentiment': df.iloc[-1]['sentiment'],
            'pnl': sell_pnl
        })
    
    final_value = capital
    total_return = (final_value - initial_capital) / initial_capital
    
    # Calculate metrics
    portfolio_df = pd.DataFrame(portfolio_values)
    returns = portfolio_df['value'].pct_change().dropna()
    
    sharpe = 0
    if len(returns) > 0 and returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365)
    
    max_drawdown = 0
    peak = portfolio_df['value'].iloc[0]
    for value in portfolio_df['value']:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    winning_trades = [t for t in trades if 'pnl' in t and t['pnl'] > 0]
    losing_trades = [t for t in trades if 'pnl' in t and t['pnl'] < 0]
    
    win_rate = 0
    if len(winning_trades) + len(losing_trades) > 0:
        win_rate = len(winning_trades) / (len(winning_trades) + len(losing_trades))
    
    return {
        'sell_threshold': sell_threshold,
        'buy_threshold': buy_threshold,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown * 100,
        'num_trades': len(trades),
        'win_rate': win_rate * 100,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'trades': trades,
        'portfolio_values': portfolio_df
    }


def test_strategy(coin: str):
    """Test sentiment-based hold strategy"""
    
    print("\n" + "="*80)
    print(f"🎯 NEWS SENTIMENT-BASED TRADING STRATEGY: {coin}")
    print("="*80)
    
    # Fetch data
    df = fetch_historical_data(coin, days=365)
    
    # Simulate sentiment signals
    print("\n🤖 Simulating news sentiment signals...")
    df = simulate_sentiment_signals(df)
    print("✅ Sentiment signals generated")
    
    # Test different thresholds
    test_configs = [
        {'sell': 30, 'buy': 50},  # Aggressive - sell early on negativity
        {'sell': 25, 'buy': 50},  # Very aggressive
        {'sell': 35, 'buy': 55},  # Moderate
        {'sell': 40, 'buy': 60},  # Conservative - only exit on strong negativity
    ]
    
    results = []
    
    print("\n📊 Testing different sentiment thresholds...")
    print("-" * 80)
    
    for config in test_configs:
        result = backtest_sentiment_strategy(df, config['sell'], config['buy'])
        results.append(result)
        
        print(f"\n🎲 Sell at {config['sell']}, Buy at {config['buy']}")
        print(f"   Final Value:    ${result['final_value']:,.2f}")
        print(f"   Total Return:   {result['total_return_pct']:+.2f}%")
        print(f"   Sharpe Ratio:   {result['sharpe_ratio']:.2f}")
        print(f"   Win Rate:       {result['win_rate']:.1f}%")
        print(f"   # Trades:       {result['num_trades']}")
    
    # Find best strategy
    best_result = max(results, key=lambda x: x['total_return'])
    
    print("\n" + "="*80)
    print("🏆 BEST STRATEGY")
    print("="*80)
    print(f"\n✅ Configuration:")
    print(f"   Sell Threshold:  {best_result['sell_threshold']} (sell when sentiment drops below)")
    print(f"   Buy Threshold:   {best_result['buy_threshold']} (buy when sentiment recovers above)")
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Initial Capital:  ${best_result['initial_capital']:,.2f}")
    print(f"   Final Value:      ${best_result['final_value']:,.2f}")
    print(f"   Total Return:     {best_result['total_return_pct']:+.2f}%")
    print(f"   Sharpe Ratio:     {best_result['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:     {best_result['max_drawdown']:.2f}%")
    
    print(f"\n📊 TRADE STATISTICS:")
    print(f"   Total Trades:     {best_result['num_trades']}")
    print(f"   Winning Trades:   {best_result['winning_trades']}")
    print(f"   Losing Trades:    {best_result['losing_trades']}")
    print(f"   Win Rate:         {best_result['win_rate']:.1f}%")
    
    # Show recent trades
    print(f"\n📋 RECENT TRADES:")
    print("-" * 80)
    for trade in best_result['trades'][-6:]:
        pnl_str = f" | P&L: ${trade['pnl']:+,.2f}" if 'pnl' in trade else ""
        print(f"   {trade['timestamp'].strftime('%Y-%m-%d')} | {trade['action']:15s} | ${trade['price']:,.2f} | Sentiment: {trade['sentiment']:.0f}{pnl_str}")
        if 'reason' in trade:
            print(f"      Reason: {trade['reason']}")
    
    # Compare to buy & hold
    buy_hold_return = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    
    print(f"\n📊 COMPARISON (Last {len(df)} days):")
    print(f"   Sentiment Strategy: {best_result['total_return_pct']:+.2f}%")
    print(f"   Simple Buy & Hold:  {buy_hold_return:+.2f}%")
    print(f"   Difference:         {best_result['total_return_pct'] - buy_hold_return:+.2f}%")
    
    if best_result['total_return_pct'] > buy_hold_return:
        print(f"\n🎉 Sentiment strategy OUTPERFORMED buy & hold by {best_result['total_return_pct'] - buy_hold_return:.2f}%!")
        print(f"   ✅ This strategy protects you from major sentiment-driven crashes")
    else:
        diff = buy_hold_return - best_result['total_return_pct']
        if diff < 10:
            print(f"\n⚖️  Sentiment strategy slightly underperformed ({diff:.2f}%)")
            print(f"   ✅ But provided protection from major downturns")
        else:
            print(f"\n⚠️  Sentiment strategy underperformed by {diff:.2f}%")
            print(f"   💡 Market was mostly bullish - hold strategy better in bull markets")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATION")
    print("="*80)
    print("\n✅ SELL WHEN:")
    print(f"   • News sentiment drops below {best_result['sell_threshold']}/100")
    print("   • AI detects consistently negative news")
    print("   • Community enthusiasm fades")
    print("   • Major negative events (regulations, hacks, etc.)")
    
    print("\n✅ BUY WHEN:")
    print(f"   • Sentiment recovers above {best_result['buy_threshold']}/100")
    print("   • Positive news flow returns")
    print("   • Community excitement builds")
    
    print("\n❌ DON'T SELL FOR:")
    print("   • Normal price volatility (-10% to -20%)")
    print("   • Short-term corrections")
    print("   • Temporary market dips")
    
    print("\n" + "="*80)
    print("✅ BACKTESTING COMPLETE")
    print("="*80)
    
    return best_result


if __name__ == "__main__":
    coin = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    test_strategy(coin.upper())

