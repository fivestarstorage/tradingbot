#!/usr/bin/env python3
"""
Momentum Strategy Optimizer
Automatically tests HUNDREDS of parameter combinations to find what works best.
"""
import os
import itertools
import json
from datetime import datetime
from dotenv import load_dotenv
from test_momentum_swing import backtest_momentum_swing, detect_momentum_swing, should_exit
from core.binance_client import BinanceClient
from app.ml_service import CoinMLService
import numpy as np

load_dotenv()


def optimize_momentum_strategy(symbol='BTCUSDT', starting_capital=1000.0, days=365, top_n=10):
    """
    Test hundreds of parameter combinations to find the best momentum trading config.
    
    Focus: High momentum pickups, ride the wave, sell when it drops, frequent trades
    """
    print("=" * 100)
    print(f"🔬 MOMENTUM STRATEGY OPTIMIZER - {symbol}")
    print("=" * 100)
    print(f"Starting Capital: ${starting_capital:,.2f}")
    print(f"Testing Period: {days} days")
    print(f"Goal: Frequent trades, catch big swings, exit before crashes")
    print("=" * 100)
    
    # Initialize
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    binance = BinanceClient(api_key, api_secret, testnet=False)
    ml_service = CoinMLService(binance)
    
    # Fetch data ONCE (reuse for all tests)
    print(f"\n📈 Fetching {days} days of historical data...")
    candles = ml_service.fetch_historical_data(symbol, days=days)
    print(f"✅ Got {len(candles)} candles ({len(candles)/24:.0f} days)")
    
    # Define parameter ranges to test
    # AGGRESSIVE SETTINGS for frequent trades + big moves
    param_grid = {
        'min_price_1h': [1.5, 2.0, 2.5, 3.0],           # How much % surge needed
        'min_volume_ratio': [1.5, 2.0, 2.5, 3.0],       # Volume spike needed
        'breakout_threshold': [93, 95, 97, 99],         # How close to 24h high
        'min_momentum_score': [40, 50, 60, 70],         # Minimum total score
        'stop_loss_pct': [2, 3, 4, 5],                  # Max loss per trade
        'take_profit_pct': [6, 8, 10, 12, 15],          # Take profit target
        'trailing_stop_pct': [1.5, 2, 2.5, 3, 4]        # Trail distance from peak
    }
    
    # Calculate total combinations
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    
    print(f"\n🧪 Testing {total_combinations} parameter combinations...")
    print(f"   This will take a few minutes...")
    print("-" * 100)
    
    results = []
    tested = 0
    
    # Test all combinations
    for min_price in param_grid['min_price_1h']:
        for min_vol in param_grid['min_volume_ratio']:
            for breakout in param_grid['breakout_threshold']:
                for min_score in param_grid['min_momentum_score']:
                    for stop_loss in param_grid['stop_loss_pct']:
                        for take_profit in param_grid['take_profit_pct']:
                            for trailing in param_grid['trailing_stop_pct']:
                                tested += 1
                                
                                # Skip invalid configs
                                if trailing >= stop_loss:
                                    continue  # Trailing stop should be tighter than stop loss
                                if take_profit <= stop_loss:
                                    continue  # TP should be bigger than SL
                                
                                config = {
                                    'min_price_1h': min_price,
                                    'min_volume_ratio': min_vol,
                                    'breakout_threshold': breakout,
                                    'min_momentum_score': min_score,
                                    'stop_loss_pct': stop_loss,
                                    'take_profit_pct': take_profit,
                                    'trailing_stop_pct': trailing
                                }
                                
                                # Run backtest with this config
                                result = run_single_backtest(candles, config, starting_capital)
                                
                                if result:
                                    results.append({
                                        'config': config,
                                        'pnl': result['pnl'],
                                        'return_pct': result['return_pct'],
                                        'trades': result['trades'],
                                        'win_rate': result['win_rate'],
                                        'avg_win': result['avg_win'],
                                        'avg_loss': result['avg_loss'],
                                        'profit_factor': result['profit_factor'],
                                        'swings_found': result['swings_found']
                                    })
                                
                                # Progress update every 100 tests
                                if tested % 100 == 0:
                                    print(f"   Progress: {tested}/{total_combinations} ({tested/total_combinations*100:.1f}%)")
    
    print(f"\n✅ Tested {len(results)} valid configurations!")
    
    # Sort by profitability
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    
    # Display top results
    print("\n" + "=" * 100)
    print(f"🏆 TOP {top_n} MOST PROFITABLE CONFIGURATIONS")
    print("=" * 100)
    
    for i, r in enumerate(results[:top_n], 1):
        cfg = r['config']
        print(f"\n#{i} - Return: {r['return_pct']:+.2f}% | P&L: ${r['pnl']:,.2f}")
        print(f"   Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}% | Profit Factor: {r['profit_factor']:.2f}")
        print(f"   Avg Win: {r['avg_win']:.2f}% | Avg Loss: {r['avg_loss']:.2f}%")
        print(f"   ⚙️ Config:")
        print(f"      Entry: {cfg['min_price_1h']}% price | {cfg['min_volume_ratio']}x vol | {cfg['breakout_threshold']}% breakout | {cfg['min_momentum_score']} score")
        print(f"      Exit:  -{cfg['stop_loss_pct']}% stop | +{cfg['take_profit_pct']}% target | {cfg['trailing_stop_pct']}% trail")
    
    # Find highest trade frequency
    print("\n" + "=" * 100)
    print(f"🎯 TOP {top_n} MOST ACTIVE TRADING CONFIGS (Frequent Trades)")
    print("=" * 100)
    
    results_by_trades = sorted(results, key=lambda x: x['trades'], reverse=True)
    
    for i, r in enumerate(results_by_trades[:top_n], 1):
        cfg = r['config']
        # Only show profitable ones with high frequency
        if r['return_pct'] > 0:
            print(f"\n#{i} - Trades: {r['trades']} | Return: {r['return_pct']:+.2f}% | Win Rate: {r['win_rate']:.1f}%")
            print(f"   Avg Win: {r['avg_win']:.2f}% | Avg Loss: {r['avg_loss']:.2f}%")
            print(f"   ⚙️ Config:")
            print(f"      Entry: {cfg['min_price_1h']}% price | {cfg['min_volume_ratio']}x vol | {cfg['breakout_threshold']}% breakout | {cfg['min_momentum_score']} score")
            print(f"      Exit:  -{cfg['stop_loss_pct']}% stop | +{cfg['take_profit_pct']}% target | {cfg['trailing_stop_pct']}% trail")
    
    # Find best risk/reward ratio
    print("\n" + "=" * 100)
    print(f"⚖️ BEST RISK/REWARD RATIOS (Avg Win > Avg Loss)")
    print("=" * 100)
    
    # Filter for configs where avg_win > avg_loss and profitable
    good_ratios = [r for r in results if r['avg_win'] > abs(r['avg_loss']) and r['return_pct'] > 0]
    good_ratios.sort(key=lambda x: x['avg_win'] / abs(x['avg_loss']) if x['avg_loss'] != 0 else 0, reverse=True)
    
    for i, r in enumerate(good_ratios[:top_n], 1):
        cfg = r['config']
        ratio = r['avg_win'] / abs(r['avg_loss']) if r['avg_loss'] != 0 else float('inf')
        print(f"\n#{i} - Ratio: {ratio:.2f}:1 | Return: {r['return_pct']:+.2f}% | Trades: {r['trades']}")
        print(f"   Win Rate: {r['win_rate']:.1f}% | Avg Win: {r['avg_win']:.2f}% vs Avg Loss: {r['avg_loss']:.2f}%")
        print(f"   ⚙️ Config:")
        print(f"      Entry: {cfg['min_price_1h']}% price | {cfg['min_volume_ratio']}x vol | {cfg['breakout_threshold']}% breakout | {cfg['min_momentum_score']} score")
        print(f"      Exit:  -{cfg['stop_loss_pct']}% stop | +{cfg['take_profit_pct']}% target | {cfg['trailing_stop_pct']}% trail")
    
    # Summary statistics
    print("\n" + "=" * 100)
    print("📊 OPTIMIZATION SUMMARY")
    print("=" * 100)
    
    profitable_configs = [r for r in results if r['return_pct'] > 0]
    
    print(f"\n✅ Profitable Configs: {len(profitable_configs)}/{len(results)} ({len(profitable_configs)/len(results)*100:.1f}%)")
    print(f"❌ Losing Configs: {len(results) - len(profitable_configs)}")
    
    if profitable_configs:
        best = results[0]
        print(f"\n🏆 BEST OVERALL CONFIG:")
        print(f"   Return: {best['return_pct']:+.2f}%")
        print(f"   P&L: ${best['pnl']:,.2f}")
        print(f"   Trades: {best['trades']} | Win Rate: {best['win_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        
        cfg = best['config']
        print(f"\n   📋 Copy this config to your bot:")
        print(f"   config = {{")
        print(f"       'min_price_1h': {cfg['min_price_1h']},")
        print(f"       'min_volume_ratio': {cfg['min_volume_ratio']},")
        print(f"       'breakout_threshold': {cfg['breakout_threshold']},")
        print(f"       'min_momentum_score': {cfg['min_momentum_score']},")
        print(f"       'stop_loss_pct': {cfg['stop_loss_pct']},")
        print(f"       'take_profit_pct': {cfg['take_profit_pct']},")
        print(f"       'trailing_stop_pct': {cfg['trailing_stop_pct']}")
        print(f"   }}")
        
        # Save to file
        output_file = f'momentum_optimization_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump({
                'symbol': symbol,
                'tested_at': datetime.now().isoformat(),
                'days': days,
                'total_configs': len(results),
                'profitable_configs': len(profitable_configs),
                'best_config': best,
                'top_10': results[:10]
            }, f, indent=2)
        
        print(f"\n💾 Full results saved to: {output_file}")
    
    print("\n" + "=" * 100)
    
    return results


def run_single_backtest(candles, config, starting_capital):
    """
    Run a single backtest with given config (optimized version)
    """
    capital = starting_capital
    position = None
    trades = []
    momentum_swings_detected = 0
    
    for i in range(50, len(candles)):
        candle = candles[i]
        current_price = candle['close']
        
        if position is None:
            # Look for momentum swing
            is_swing, score, reason = detect_momentum_swing(candles, i, config)
            
            if is_swing:
                momentum_swings_detected += 1
                
                # Enter position
                buy_amount = capital * 0.95
                quantity = buy_amount / current_price
                
                position = {
                    'entry_price': current_price,
                    'entry_capital': capital,
                    'quantity': quantity,
                    'highest_price': current_price
                }
                
                capital -= buy_amount
        
        else:
            # Update highest price
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Check exit
            should_exit_now, exit_reason = should_exit(
                position['entry_price'],
                current_price,
                position['highest_price'],
                config
            )
            
            if should_exit_now:
                sell_amount = position['quantity'] * current_price
                capital += sell_amount
                
                pnl = capital - position['entry_capital']
                pnl_pct = (pnl / position['entry_capital']) * 100
                
                trades.append({
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                position = None
    
    # Close remaining position
    if position is not None:
        final_price = candles[-1]['close']
        sell_amount = position['quantity'] * final_price
        capital += sell_amount
        
        pnl = capital - position['entry_capital']
        pnl_pct = (pnl / position['entry_capital']) * 100
        
        trades.append({
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
    
    # Calculate metrics
    if not trades:
        return None
    
    final_capital = capital
    total_pnl = final_capital - starting_capital
    total_return_pct = (total_pnl / starting_capital) * 100
    
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    
    win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
    avg_win = sum(t['pnl_pct'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl_pct'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    profit_factor = (sum(t['pnl'] for t in winning_trades) / abs(sum(t['pnl'] for t in losing_trades))) if losing_trades and winning_trades else 0
    
    return {
        'pnl': total_pnl,
        'return_pct': total_return_pct,
        'trades': len(trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'swings_found': momentum_swings_detected
    }


if __name__ == '__main__':
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
    
    try:
        results = optimize_momentum_strategy(symbol=symbol, starting_capital=1000.0, days=days, top_n=10)
        
        if results and any(r['return_pct'] > 0 for r in results):
            print("\n🎊 OPTIMIZATION COMPLETE! Found profitable configurations!")
        else:
            print("\n❌ No profitable configurations found. Try:")
            print("   1. Test on a different coin (altcoins have better momentum)")
            print("   2. Test a different time period (maybe 2024 was choppy)")
            print("   3. Adjust parameter ranges in the script")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

