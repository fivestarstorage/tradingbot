#!/usr/bin/env python3
"""
Momentum Strategy Optimizer

Tests multiple strategy variations to find the most profitable configuration:
- Different momentum entry thresholds
- Different stop-loss percentages
- Different trailing stop timings
- Different trailing stop profit thresholds
- Different position sizes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import requests
from typing import List, Dict, Tuple
import json
from itertools import product

# Expanded coin list for more testing
TEST_COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'ADA', 'DOGE', 
    'MATIC', 'DOT', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC',
    'FTM', 'NEAR', 'ALGO', 'VET', 'SAND', 'MANA',
    'APE', 'CRV', 'LDO', 'OP', 'ARB'  # Added more coins
]

class Trade:
    def __init__(self, coin: str, entry_price: float, entry_time: datetime, 
                 entry_sentiment: float, investment: float = 1000):
        self.coin = coin
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_sentiment = entry_sentiment
        self.investment = investment
        self.quantity = investment / entry_price
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0
        self.pnl_percent = 0
        self.hold_days = 0
        
    def close(self, exit_price: float, exit_time: datetime, reason: str):
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        
        exit_value = self.quantity * exit_price
        self.pnl = exit_value - self.investment
        self.pnl_percent = (self.pnl / self.investment) * 100
        self.hold_days = (exit_time - self.entry_time).days
        
    def should_exit(self, current_price: float, current_time: datetime,
                   stop_loss_pct: float, trailing_days: int, trailing_profit_pct: float) -> Tuple[bool, str]:
        """Check if position should be exited based on configurable stop-loss rules"""
        
        # Rule A: Hard stop-loss
        stop_loss_price = self.entry_price * (1 - stop_loss_pct/100)
        if current_price <= stop_loss_price:
            return True, f"Hard Stop-Loss (-{stop_loss_pct}%)"
        
        # Rule B: Trailing stop after X days
        days_held = (current_time - self.entry_time).days
        if days_held >= trailing_days:
            trailing_stop_price = self.entry_price * (1 + trailing_profit_pct/100)
            if current_price < trailing_stop_price:
                return True, f"Trailing Stop ({trailing_days}+ days, <{trailing_profit_pct}% profit)"
        
        return False, ""


class StrategyConfig:
    def __init__(self, momentum_threshold: float, stop_loss_pct: float,
                 trailing_days: int, trailing_profit_pct: float, position_size: float):
        self.momentum_threshold = momentum_threshold
        self.stop_loss_pct = stop_loss_pct
        self.trailing_days = trailing_days
        self.trailing_profit_pct = trailing_profit_pct
        self.position_size = position_size
    
    def __str__(self):
        return (f"M{self.momentum_threshold:.0f}_SL{self.stop_loss_pct:.0f}_"
                f"T{self.trailing_days}d{self.trailing_profit_pct:.0f}_"
                f"${self.position_size:.0f}")


class MomentumBacktester:
    def __init__(self, config: StrategyConfig, initial_capital: float = 10000):
        self.config = config
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.open_positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.cache = {}  # Cache historical data
        
    def fetch_historical_klines(self, coin: str, days: int = 365) -> List[dict]:
        """Fetch historical OHLCV data from Binance (with caching)"""
        if coin in self.cache:
            return self.cache[coin]
        
        symbol = f"{coin}USDT"
        url = "https://api.binance.com/api/v3/klines"
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        params = {
            'symbol': symbol,
            'interval': '1h',
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1000
        }
        
        all_klines = []
        current_start = start_time
        
        try:
            while current_start < end_time:
                params['startTime'] = int(current_start.timestamp() * 1000)
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    klines = response.json()
                    if not klines:
                        break
                    
                    for kline in klines:
                        all_klines.append({
                            'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    
                    if len(klines) < 1000:
                        break
                    current_start = datetime.fromtimestamp(klines[-1][0] / 1000)
                else:
                    return []
        except Exception:
            return []
        
        self.cache[coin] = all_klines
        return all_klines
    
    def calculate_momentum_score(self, klines: List[dict], index: int) -> float:
        """Calculate momentum score (0-100)"""
        if index < 24:
            return 50
        
        recent_klines = klines[max(0, index-24):index+1]
        prices = [k['close'] for k in recent_klines]
        
        change_1h = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) >= 2 else 0
        change_24h = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) >= 24 else 0
        
        volumes = [k['volume'] for k in recent_klines]
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        score = 50
        score += change_1h * 2
        score += change_24h * 0.5
        
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 2:
            score += 20
        
        score = max(0, min(100, score))
        return score
    
    def run_backtest(self, coin: str, klines: List[dict]) -> int:
        """Run backtest for a single coin, return number of trades"""
        trades_count = 0
        
        for i, kline in enumerate(klines):
            current_time = kline['timestamp']
            current_price = kline['close']
            
            # Check open positions for exits
            if coin in self.open_positions:
                trade = self.open_positions[coin]
                should_exit, reason = trade.should_exit(
                    current_price, current_time,
                    self.config.stop_loss_pct,
                    self.config.trailing_days,
                    self.config.trailing_profit_pct
                )
                
                if should_exit:
                    trade.close(current_price, current_time, reason)
                    self.cash += (trade.quantity * current_price)
                    self.closed_trades.append(trade)
                    del self.open_positions[coin]
                    trades_count += 1
            
            # Check for entry signals
            elif self.cash >= self.config.position_size:
                momentum = self.calculate_momentum_score(klines, i)
                
                if momentum >= self.config.momentum_threshold:
                    trade = Trade(coin, current_price, current_time, momentum, self.config.position_size)
                    self.open_positions[coin] = trade
                    self.cash -= self.config.position_size
        
        # Close any remaining open positions
        if coin in self.open_positions:
            trade = self.open_positions[coin]
            final_kline = klines[-1]
            trade.close(final_kline['close'], final_kline['timestamp'], "End of backtest")
            self.cash += (trade.quantity * final_kline['close'])
            self.closed_trades.append(trade)
            del self.open_positions[coin]
            trades_count += 1
        
        return trades_count
    
    def get_results(self) -> dict:
        """Calculate and return results"""
        if not self.closed_trades:
            return {
                'roi': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'final_capital': self.initial_capital
            }
        
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = sum(t.pnl for t in self.closed_trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        final_capital = self.cash
        roi = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'roi': roi,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'final_capital': final_capital,
            'winning_trades': len(winning_trades),
            'losing_trades': total_trades - len(winning_trades)
        }


def optimize_strategy():
    """Test multiple strategy configurations"""
    print("="*100)
    print("🚀 MOMENTUM STRATEGY OPTIMIZER")
    print("="*100)
    print("\n⏳ Testing multiple strategy variations across 25 coins...")
    print("   This will take several minutes...\n")
    
    # Define parameter ranges to test
    momentum_thresholds = [60, 65, 70, 75, 80]
    stop_loss_pcts = [5, 10, 15, 20]
    trailing_days_options = [3, 7, 14, 21]
    trailing_profit_pcts = [5, 10, 15, 20]
    position_sizes = [500, 1000, 2000]
    
    # Generate all combinations (this will be a lot!)
    all_configs = []
    for m, sl, td, tp, ps in product(momentum_thresholds, stop_loss_pcts, 
                                      trailing_days_options, trailing_profit_pcts, 
                                      position_sizes):
        all_configs.append(StrategyConfig(m, sl, td, tp, ps))
    
    print(f"📊 Total configurations to test: {len(all_configs)}")
    print(f"🪙 Total coins: {len(TEST_COINS)}")
    print(f"🔢 Total backtests: {len(all_configs) * len(TEST_COINS)}\n")
    
    # Fetch all historical data first (with progress)
    print("📥 Fetching historical data for all coins...")
    global_cache = {}
    valid_coins = []
    
    for i, coin in enumerate(TEST_COINS, 1):
        try:
            dummy_backtester = MomentumBacktester(all_configs[0])
            klines = dummy_backtester.fetch_historical_klines(coin, days=365)
            if klines and len(klines) > 1000:  # Need sufficient data
                global_cache[coin] = klines
                valid_coins.append(coin)
                print(f"   [{i:2d}/{len(TEST_COINS)}] ✅ {coin:8s} {len(klines):5d} data points")
            else:
                print(f"   [{i:2d}/{len(TEST_COINS)}] ⚠️  {coin:8s} insufficient data")
        except Exception as e:
            print(f"   [{i:2d}/{len(TEST_COINS)}] ❌ {coin:8s} error: {e}")
    
    print(f"\n✅ Successfully loaded {len(valid_coins)} coins\n")
    
    # Test all configurations
    results = []
    
    for config_idx, config in enumerate(all_configs, 1):
        backtester = MomentumBacktester(config, initial_capital=10000)
        backtester.cache = global_cache  # Use pre-fetched data
        
        total_trades = 0
        for coin in valid_coins:
            klines = global_cache[coin]
            trades = backtester.run_backtest(coin, klines)
            total_trades += trades
        
        result = backtester.get_results()
        result['config'] = config
        result['config_str'] = str(config)
        results.append(result)
        
        # Progress update every 20 configs
        if config_idx % 20 == 0:
            print(f"   Progress: {config_idx}/{len(all_configs)} configurations tested...")
    
    print(f"\n✅ Completed testing {len(all_configs)} configurations!\n")
    
    # Sort by ROI
    results.sort(key=lambda x: x['roi'], reverse=True)
    
    # Print top 20 strategies
    print("="*100)
    print("🏆 TOP 20 MOST PROFITABLE STRATEGIES")
    print("="*100)
    print(f"\n{'Rank':<5} {'ROI':<8} {'Trades':<7} {'Win%':<6} {'AvgP&L':<9} {'Configuration':<60}")
    print("-"*100)
    
    for i, result in enumerate(results[:20], 1):
        print(f"{i:<5} {result['roi']:+7.2f}% {result['total_trades']:<7} "
              f"{result['win_rate']:5.1f}% ${result['avg_pnl']:7.2f}   {result['config_str']}")
    
    # Print worst 10 for comparison
    print("\n" + "="*100)
    print("💔 WORST 10 STRATEGIES (for comparison)")
    print("="*100)
    print(f"\n{'Rank':<5} {'ROI':<8} {'Trades':<7} {'Win%':<6} {'AvgP&L':<9} {'Configuration':<60}")
    print("-"*100)
    
    for i, result in enumerate(results[-10:], 1):
        rank = len(results) - 10 + i
        print(f"{rank:<5} {result['roi']:+7.2f}% {result['total_trades']:<7} "
              f"{result['win_rate']:5.1f}% ${result['avg_pnl']:7.2f}   {result['config_str']}")
    
    # Print best strategy details
    best = results[0]
    print("\n" + "="*100)
    print("🥇 BEST STRATEGY DETAILS")
    print("="*100)
    print(f"\n   Configuration: {best['config_str']}")
    print(f"\n   Momentum Threshold:      {best['config'].momentum_threshold:.0f}/100")
    print(f"   Stop Loss:               {best['config'].stop_loss_pct:.0f}%")
    print(f"   Trailing Stop After:     {best['config'].trailing_days} days")
    print(f"   Trailing Profit Target:  {best['config'].trailing_profit_pct:.0f}%")
    print(f"   Position Size:           ${best['config'].position_size:.0f}")
    print(f"\n   📈 Performance:")
    print(f"      ROI:              {best['roi']:+.2f}%")
    print(f"      Final Capital:    ${best['final_capital']:,.2f}")
    print(f"      Total Trades:     {best['total_trades']}")
    print(f"      Win Rate:         {best['win_rate']:.1f}%")
    print(f"      Avg P&L/Trade:    ${best['avg_pnl']:.2f}")
    
    # Save results
    output = {
        'summary': {
            'total_configs_tested': len(all_configs),
            'coins_tested': valid_coins,
            'best_roi': results[0]['roi'],
            'worst_roi': results[-1]['roi'],
            'median_roi': results[len(results)//2]['roi']
        },
        'top_20_strategies': [
            {
                'rank': i,
                'config': r['config_str'],
                'roi': r['roi'],
                'total_trades': r['total_trades'],
                'win_rate': r['win_rate'],
                'avg_pnl': r['avg_pnl'],
                'final_capital': r['final_capital']
            }
            for i, r in enumerate(results[:20], 1)
        ],
        'best_strategy': {
            'momentum_threshold': best['config'].momentum_threshold,
            'stop_loss_pct': best['config'].stop_loss_pct,
            'trailing_days': best['config'].trailing_days,
            'trailing_profit_pct': best['config'].trailing_profit_pct,
            'position_size': best['config'].position_size,
            'roi': best['roi'],
            'final_capital': best['final_capital'],
            'total_trades': best['total_trades'],
            'win_rate': best['win_rate'],
            'avg_pnl': best['avg_pnl']
        }
    }
    
    with open('strategy_optimization_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: strategy_optimization_results.json")
    print("="*100)


if __name__ == '__main__':
    optimize_strategy()

