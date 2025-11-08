#!/usr/bin/env python3
"""
Hold + Stop-Loss Strategy Trainer
Tests different stop-loss thresholds on historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime
import requests
import sys


def fetch_historical_data(coin: str, days: int = 1095):
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


def backtest_hold_stoploss(df: pd.DataFrame, stop_loss_pct: float):
    """
    Backtest hold + stop-loss strategy
    
    Strategy:
    - Buy at start and hold
    - Sell if price drops by stop_loss_pct from highest price
    - Re-buy when price recovers above previous high
    """
    
    initial_capital = 10000
    capital = initial_capital
    position = 0
    position_value = 0
    entry_price = 0
    highest_price_since_entry = 0
    
    trades = []
    portfolio_values = []
    
    in_position = False
    
    for timestamp, row in df.iterrows():
        price = row['close']
        
        if not in_position:
            # Buy signal: price recovered above previous high, or first buy
            if len(trades) == 0 or price > highest_price_since_entry:
                # Buy
                position = capital / price
                position_value = capital
                entry_price = price
                highest_price_since_entry = price
                in_position = True
                capital = 0
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY',
                    'price': price,
                    'quantity': position,
                    'value': position_value
                })
        
        else:
            # Update highest price
            if price > highest_price_since_entry:
                highest_price_since_entry = price
            
            # Check stop-loss
            current_value = position * price
            drawdown_from_peak = (highest_price_since_entry - price) / highest_price_since_entry
            
            if drawdown_from_peak >= stop_loss_pct:
                # Stop-loss triggered - sell
                capital = position * price
                sell_pnl = capital - position_value
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'SELL (STOP-LOSS)',
                    'price': price,
                    'quantity': position,
                    'value': capital,
                    'pnl': sell_pnl,
                    'drawdown': drawdown_from_peak * 100
                })
                
                position = 0
                position_value = 0
                in_position = False
        
        # Track portfolio value
        if in_position:
            total_value = position * price
        else:
            total_value = capital
        
        portfolio_values.append({
            'timestamp': timestamp,
            'value': total_value,
            'price': price
        })
    
    # Close any open position
    if in_position:
        final_price = df.iloc[-1]['close']
        capital = position * final_price
        sell_pnl = capital - position_value
        
        trades.append({
            'timestamp': df.index[-1],
            'action': 'SELL (END)',
            'price': final_price,
            'quantity': position,
            'value': capital,
            'pnl': sell_pnl
        })
    
    final_value = capital
    total_return = (final_value - initial_capital) / initial_capital
    
    # Calculate metrics
    portfolio_df = pd.DataFrame(portfolio_values)
    returns = portfolio_df['value'].pct_change().dropna()
    
    sharpe = 0
    if len(returns) > 0 and returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365)  # Annualized
    
    max_drawdown = 0
    peak = portfolio_df['value'].iloc[0]
    for value in portfolio_df['value']:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'stop_loss_pct': stop_loss_pct,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown * 100,
        'num_trades': len(trades),
        'trades': trades,
        'portfolio_values': portfolio_df
    }


def test_strategy(coin: str):
    """Test hold + stop-loss strategy with different thresholds"""
    
    print("\n" + "="*80)
    print(f"🎯 HOLD + STOP-LOSS STRATEGY BACKTESTING: {coin}")
    print("="*80)
    
    # Fetch data
    df = fetch_historical_data(coin, days=1095)
    
    # Test different stop-loss thresholds
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25]  # 5%, 10%, 15%, 20%, 25%
    
    results = []
    
    print("\n📊 Testing different stop-loss thresholds...")
    print("-" * 80)
    
    for threshold in thresholds:
        result = backtest_hold_stoploss(df, threshold)
        results.append(result)
        
        print(f"\n🎲 Stop-Loss: {threshold*100:.0f}%")
        print(f"   Final Value:    ${result['final_value']:,.2f}")
        print(f"   Total Return:   {result['total_return_pct']:+.2f}%")
        print(f"   Sharpe Ratio:   {result['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown:   {result['max_drawdown']:.2f}%")
        print(f"   # Trades:       {result['num_trades']}")
    
    # Find best strategy
    best_result = max(results, key=lambda x: x['total_return'])
    
    print("\n" + "="*80)
    print("🏆 BEST STRATEGY")
    print("="*80)
    print(f"\n✅ Stop-Loss Threshold: {best_result['stop_loss_pct']*100:.0f}%")
    print(f"\n💰 PERFORMANCE:")
    print(f"   Initial Capital:  ${best_result['initial_capital']:,.2f}")
    print(f"   Final Value:      ${best_result['final_value']:,.2f}")
    print(f"   Total Return:     {best_result['total_return_pct']:+.2f}%")
    print(f"   Sharpe Ratio:     {best_result['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:     {best_result['max_drawdown']:.2f}%")
    print(f"   # Trades:         {best_result['num_trades']}")
    
    # Show trade history
    print(f"\n📋 TRADE HISTORY (last 10):")
    print("-" * 80)
    for trade in best_result['trades'][-10:]:
        pnl_str = f" | P&L: ${trade['pnl']:+,.2f}" if 'pnl' in trade else ""
        drawdown_str = f" | Drawdown: {trade['drawdown']:.2f}%" if 'drawdown' in trade else ""
        print(f"   {trade['timestamp'].strftime('%Y-%m-%d')} | {trade['action']:20s} | ${trade['price']:,.2f}{pnl_str}{drawdown_str}")
    
    # Compare to simple buy & hold
    buy_hold_return = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    
    print(f"\n📊 COMPARISON:")
    print(f"   Hold + Stop-Loss:  {best_result['total_return_pct']:+.2f}%")
    print(f"   Simple Buy & Hold: {buy_hold_return:+.2f}%")
    print(f"   Difference:        {best_result['total_return_pct'] - buy_hold_return:+.2f}%")
    
    if best_result['total_return_pct'] > buy_hold_return:
        print(f"\n🎉 Stop-loss strategy OUTPERFORMED buy & hold!")
    else:
        print(f"\n⚠️  Stop-loss strategy underperformed buy & hold")
        print(f"   💡 Consider simple hold strategy instead")
    
    print("\n" + "="*80)
    print("✅ BACKTESTING COMPLETE")
    print("="*80)
    
    return best_result


if __name__ == "__main__":
    coin = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    test_strategy(coin.upper())

