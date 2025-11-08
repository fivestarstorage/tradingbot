#!/usr/bin/env python3
"""
Momentum Strategy Optimizer - ALL COINS

Fetches ALL available USDT pairs from Binance and tests strategy on them
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import requests
from typing import List, Dict, Tuple
import json
from itertools import product
import time

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
        # Hard stop-loss
        stop_loss_price = self.entry_price * (1 - stop_loss_pct/100)
        if current_price <= stop_loss_price:
            return True, f"Hard Stop-Loss (-{stop_loss_pct}%)"
        
        # Trailing stop after X days
        days_held = (current_time - self.entry_time).days
        if days_held >= trailing_days:
            trailing_stop_price = self.entry_price * (1 + trailing_profit_pct/100)
            if current_price < trailing_stop_price:
                return True, f"Trailing Stop ({trailing_days}+ days)"
        
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
        
    def fetch_historical_klines(self, coin: str, days: int = 365) -> List[dict]:
        """Fetch historical OHLCV data from Binance"""
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
                elif response.status_code == 429:  # Rate limit
                    time.sleep(1)
                    continue
                else:
                    return []
        except Exception:
            return []
        
        return all_klines
    
    def calculate_momentum_score(self, klines: List[dict], index: int) -> float:
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
    
    def run_backtest(self, coin: str, klines: List[dict]):
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
            
            # Check for entry signals
            elif self.cash >= self.config.position_size:
                momentum = self.calculate_momentum_score(klines, i)
                
                if momentum >= self.config.momentum_threshold:
                    trade = Trade(coin, current_price, current_time, momentum, self.config.position_size)
                    self.open_positions[coin] = trade
                    self.cash -= self.config.position_size
        
        # Close remaining positions
        if coin in self.open_positions:
            trade = self.open_positions[coin]
            final_kline = klines[-1]
            trade.close(final_kline['close'], final_kline['timestamp'], "End of backtest")
            self.cash += (trade.quantity * final_kline['close'])
            self.closed_trades.append(trade)
            del self.open_positions[coin]
    
    def get_results(self) -> dict:
        if not self.closed_trades:
            return {'roi': 0, 'total_trades': 0, 'win_rate': 0, 'avg_pnl': 0, 'final_capital': self.initial_capital}
        
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


def get_all_binance_usdt_pairs():
    """Fetch all available USDT trading pairs from Binance"""
    print("📡 Fetching all USDT pairs from Binance API...")
    
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            symbols = data['symbols']
            
            # Filter for USDT pairs that are trading
            usdt_pairs = []
            for symbol in symbols:
                if (symbol['symbol'].endswith('USDT') and 
                    symbol['status'] == 'TRADING' and
                    symbol['symbol'] != 'USDT'):
                    coin = symbol['symbol'][:-4]  # Remove 'USDT'
                    usdt_pairs.append(coin)
            
            print(f"✅ Found {len(usdt_pairs)} USDT trading pairs!\n")
            return sorted(usdt_pairs)
        else:
            print(f"❌ Error fetching pairs: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def optimize_strategy():
    print("="*100)
    print("🚀 MOMENTUM STRATEGY OPTIMIZER - ALL BINANCE COINS")
    print("="*100)
    
    # Get all available coins
    all_coins = get_all_binance_usdt_pairs()
    
    if not all_coins:
        print("❌ No coins found, exiting...")
        return
    
    print(f"🪙 Total coins available: {len(all_coins)}")
    print(f"📊 Sampling first 100 coins for speed...\n")
    
    # Use first 100 for reasonable runtime
    test_coins = all_coins[:100]
    
    # Define parameter ranges - WIDER RANGE
    configs_to_test = [
        # Conservative
        StrategyConfig(momentum_threshold=75, stop_loss_pct=10, trailing_days=7, trailing_profit_pct=10, position_size=1000),
        # Aggressive entry
        StrategyConfig(momentum_threshold=65, stop_loss_pct=15, trailing_days=14, trailing_profit_pct=15, position_size=1000),
        # Tight stops
        StrategyConfig(momentum_threshold=70, stop_loss_pct=5, trailing_days=7, trailing_profit_pct=5, position_size=1000),
        # Long hold
        StrategyConfig(momentum_threshold=80, stop_loss_pct=10, trailing_days=21, trailing_profit_pct=20, position_size=1000),
        # Small positions
        StrategyConfig(momentum_threshold=70, stop_loss_pct=10, trailing_days=7, trailing_profit_pct=10, position_size=500),
        # Large positions
        StrategyConfig(momentum_threshold=70, stop_loss_pct=10, trailing_days=7, trailing_profit_pct=10, position_size=2000),
        # Very aggressive
        StrategyConfig(momentum_threshold=60, stop_loss_pct=20, trailing_days=3, trailing_profit_pct=5, position_size=1000),
        # Ultra conservative
        StrategyConfig(momentum_threshold=85, stop_loss_pct=5, trailing_days=14, trailing_profit_pct=15, position_size=500),
        # Medium everything
        StrategyConfig(momentum_threshold=70, stop_loss_pct=12, trailing_days=10, trailing_profit_pct=12, position_size=1500),
        # Original strategy
        StrategyConfig(momentum_threshold=70, stop_loss_pct=10, trailing_days=7, trailing_profit_pct=10, position_size=1000),
    ]
    
    print(f"🔬 Testing {len(configs_to_test)} different strategy configurations")
    print(f"📈 Total backtests: {len(configs_to_test) * len(test_coins)}\n")
    
    # Fetch data for all coins
    print("📥 Fetching historical data...")
    global_cache = {}
    valid_coins = []
    
    for i, coin in enumerate(test_coins, 1):
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(test_coins)} coins fetched...")
        
        try:
            dummy = MomentumBacktester(configs_to_test[0])
            klines = dummy.fetch_historical_klines(coin, days=365)
            if klines and len(klines) > 2000:  # Need good data
                global_cache[coin] = klines
                valid_coins.append(coin)
        except Exception:
            pass
    
    print(f"\n✅ Successfully loaded {len(valid_coins)} coins with sufficient data\n")
    print(f"🪙 Testing coins: {', '.join(valid_coins[:20])}{'...' if len(valid_coins) > 20 else ''}\n")
    
    # Test all configurations
    results = []
    
    for config_idx, config in enumerate(configs_to_test, 1):
        print(f"⏳ Testing config {config_idx}/{len(configs_to_test)}: {config}")
        
        backtester = MomentumBacktester(config, initial_capital=10000)
        
        for coin in valid_coins:
            klines = global_cache[coin]
            backtester.run_backtest(coin, klines)
        
        result = backtester.get_results()
        result['config'] = config
        result['config_str'] = str(config)
        results.append(result)
        
        print(f"   ROI: {result['roi']:+.2f}% | Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%\n")
    
    # Sort by ROI
    results.sort(key=lambda x: x['roi'], reverse=True)
    
    # Print results
    print("\n" + "="*100)
    print("🏆 STRATEGY RANKING (Best to Worst)")
    print("="*100)
    print(f"\n{'#':<3} {'ROI':<9} {'Trades':<8} {'Win%':<7} {'AvgP&L':<10} {'Configuration':<60}")
    print("-"*100)
    
    for i, result in enumerate(results, 1):
        print(f"{i:<3} {result['roi']:+8.2f}% {result['total_trades']:<8} "
              f"{result['win_rate']:6.1f}% ${result['avg_pnl']:8.2f}   {result['config_str']}")
    
    # Best strategy details
    best = results[0]
    print("\n" + "="*100)
    print("🥇 WINNING STRATEGY")
    print("="*100)
    print(f"\n   💰 ROI:                  {best['roi']:+.2f}%")
    print(f"   💵 Final Capital:        ${best['final_capital']:,.2f}")
    print(f"   📊 Total Trades:         {best['total_trades']}")
    print(f"   ✅ Win Rate:             {best['win_rate']:.1f}%")
    print(f"   💸 Avg Profit/Trade:     ${best['avg_pnl']:.2f}")
    print(f"\n   ⚙️  CONFIGURATION:")
    print(f"      Entry Momentum:       {best['config'].momentum_threshold:.0f}/100")
    print(f"      Stop Loss:            {best['config'].stop_loss_pct:.0f}%")
    print(f"      Trailing Days:        {best['config'].trailing_days} days")
    print(f"      Trailing Target:      {best['config'].trailing_profit_pct:.0f}%")
    print(f"      Position Size:        ${best['config'].position_size:.0f}")
    
    # Save results
    output = {
        'metadata': {
            'total_coins_available': len(all_coins),
            'coins_tested': len(valid_coins),
            'coin_list': valid_coins,
            'configurations_tested': len(configs_to_test),
            'backtest_date': datetime.now().isoformat()
        },
        'all_results': [
            {
                'rank': i,
                'config': r['config_str'],
                'roi': r['roi'],
                'total_trades': r['total_trades'],
                'win_rate': r['win_rate'],
                'avg_pnl': r['avg_pnl'],
                'final_capital': r['final_capital']
            }
            for i, r in enumerate(results, 1)
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
    
    with open('all_coins_optimization_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: all_coins_optimization_results.json")
    print("="*100)


if __name__ == '__main__':
    optimize_strategy()

