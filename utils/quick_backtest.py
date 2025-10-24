"""
Quick Backtest - All-in-One Testing Tool

Features:
- Multiple strategies to choose from
- Prebuilt coin list
- Automatic data fetching
- No CSV files needed!
"""
import sys
import pandas as pd
import numpy as np
from binance_client import BinanceClient
from config import Config
import logging

# Import all strategies
from strategies.enhanced_strategy import EnhancedStrategy
from strategies.volatile_coins_strategy import VolatileCoinsStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.conservative_strategy import ConservativeStrategy
from strategies.simple_profitable_strategy import SimpleProfitableStrategy

logging.basicConfig(level=logging.WARNING)  # Less noise
logger = logging.getLogger(__name__)


# Strategy descriptions
STRATEGIES = {
    '1': {
        'name': 'Simple Profitable ⭐',
        'class': SimpleProfitableStrategy,
        'best_for': 'ALL COINS - What actually works!',
        'trades': 'Low (10-20 per 100 days)',
        'risk': 'Medium',
        'note': 'RECOMMENDED - Tested and proven'
    },
    '2': {
        'name': 'Enhanced Momentum',
        'class': EnhancedStrategy,
        'best_for': 'BTC, ETH - stable coins, trending markets',
        'trades': 'Medium (20-40 per 100 days)',
        'risk': 'Medium'
    },
    '3': {
        'name': 'Volatile Coins',
        'class': VolatileCoinsStrategy,
        'best_for': 'SOL, DOGE, AVAX - high volatility altcoins',
        'trades': 'Low (10-25 per 100 days)',
        'risk': 'Medium-High'
    },
    '4': {
        'name': 'Mean Reversion',
        'class': MeanReversionStrategy,
        'best_for': 'Ranging markets, buy dips/sell rips',
        'trades': 'Low-Medium (15-30 per 100 days)',
        'risk': 'Medium'
    },
    '5': {
        'name': 'Breakout',
        'class': BreakoutStrategy,
        'best_for': 'Strong trends, momentum plays',
        'trades': 'Low (10-20 per 100 days)',
        'risk': 'High'
    },
    '6': {
        'name': 'Conservative',
        'class': ConservativeStrategy,
        'best_for': 'Risk-averse, only perfect setups',
        'trades': 'Very Low (5-15 per 100 days)',
        'risk': 'Low'
    }
}

# Coin presets
COINS = {
    '1': {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'recommended': [1, 2]},
    '2': {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'recommended': [1, 2]},
    '3': {'symbol': 'BNBUSDT', 'name': 'Binance Coin', 'recommended': [1, 2]},
    '4': {'symbol': 'SOLUSDT', 'name': 'Solana', 'recommended': [1, 4]},
    '5': {'symbol': 'DOGEUSDT', 'name': 'Dogecoin', 'recommended': [1, 4]},
    '6': {'symbol': 'AVAXUSDT', 'name': 'Avalanche', 'recommended': [1, 3]},
    '7': {'symbol': 'MATICUSDT', 'name': 'Polygon', 'recommended': [1, 4]},
    '8': {'symbol': 'ADAUSDT', 'name': 'Cardano', 'recommended': [1, 2]},
    '9': {'symbol': 'XRPUSDT', 'name': 'Ripple', 'recommended': [1, 2]},
    '10': {'symbol': 'DOTUSDT', 'name': 'Polkadot', 'recommended': [1, 3]},
}


class QuickBacktester:
    """Simplified backtester for quick testing"""
    
    def __init__(self, strategy_class, initial_capital=1000):
        self.initial_capital = initial_capital
        self.strategy = strategy_class()
        self.reset()
    
    def reset(self):
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
    
    def fetch_data(self, symbol, interval='5m', days=30):
        """Fetch data from Binance with automatic batching"""
        import time
        from datetime import datetime, timedelta
        
        try:
            client = BinanceClient(
                api_key=Config.BINANCE_API_KEY,
                api_secret=Config.BINANCE_API_SECRET,
                testnet=Config.USE_TESTNET
            )
            
            # Calculate how many candles we need
            interval_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15,
                '30m': 30, '1h': 60, '4h': 240, '1d': 1440
            }
            
            minutes_per_candle = interval_minutes.get(interval, 5)
            total_candles_needed = (days * 24 * 60) // minutes_per_candle
            batches_needed = (total_candles_needed + 999) // 1000
            
            # Cap at reasonable amount
            if batches_needed > 30:
                batches_needed = 30
                print(f"⚠️  Limiting to 30 batches (~{batches_needed * 1000} candles)")
            
            all_klines = []
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            current_start = int(start_time.timestamp() * 1000)
            
            for batch_num in range(batches_needed):
                klines = client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=1000,
                    startTime=current_start
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # Update start time for next batch
                current_start = int(klines[-1][0]) + (minutes_per_candle * 60 * 1000)
                
                # Rate limiting
                if batch_num < batches_needed - 1:
                    time.sleep(0.3)
            
            return all_klines
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def run(self, klines, min_confidence=50):
        """Run backtest"""
        if not klines or len(klines) < 100:
            raise ValueError("Insufficient data")
        
        df = self.strategy.process_klines(klines)
        df = self.strategy.calculate_indicators(df)
        
        if df is None:
            raise ValueError("Failed to process data")
        
        commission = 0.001
        
        for i in range(len(df)):
            if i < 60:
                continue
            
            current_data = df.iloc[:i+1]
            current = df.iloc[i]
            price = current['close']
            timestamp = current['timestamp']
            
            signal_result = self.strategy.generate_signal(current_data)
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            risk = signal_result.get('risk', {})
            
            # Check exits
            if self.position:
                entry_price = self.position['entry_price']
                stop_loss = self.position['stop_loss']
                take_profit = self.position['take_profit']
                
                should_exit = False
                reason = None
                
                if price <= stop_loss:
                    should_exit, reason = True, "Stop Loss"
                elif price >= take_profit:
                    should_exit, reason = True, "Take Profit"
                elif signal == 'SELL' and confidence >= min_confidence:
                    should_exit, reason = True, "Sell Signal"
                
                if should_exit:
                    quantity = self.position['quantity']
                    proceeds = quantity * price * (1 - commission)
                    pnl = proceeds - self.position['cost']
                    pnl_percent = (pnl / self.position['cost']) * 100
                    
                    self.capital += proceeds
                    self.trades.append({
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl_percent': pnl_percent,
                        'reason': reason
                    })
                    self.position = None
            
            # Check entries
            elif signal == 'BUY' and confidence >= min_confidence:
                position_mult = risk.get('position_multiplier', 0.5)
                position_value = self.capital * 0.95 * position_mult
                quantity = position_value / price
                cost = quantity * price * (1 + commission)
                
                stop_loss = risk.get('stop_loss', price * 0.97)
                take_profit = risk.get('take_profit', price * 1.05)
                
                self.position = {
                    'entry_price': price,
                    'quantity': quantity,
                    'cost': cost,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                self.capital -= cost
        
        # Close final position
        if self.position:
            final_price = df.iloc[-1]['close']
            quantity = self.position['quantity']
            proceeds = quantity * final_price * (1 - commission)
            pnl = proceeds - self.position['cost']
            pnl_percent = (pnl / self.position['cost']) * 100
            self.capital += proceeds
            self.trades.append({
                'entry_price': self.position['entry_price'],
                'exit_price': final_price,
                'pnl_percent': pnl_percent,
                'reason': 'End'
            })
        
        return self._calc_results()
    
    def _calc_results(self):
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'final_equity': self.initial_capital
            }
        
        wins = [t for t in self.trades if t['pnl_percent'] > 0]
        losses = [t for t in self.trades if t['pnl_percent'] <= 0]
        
        total_pnl = sum(t['pnl_percent'] for t in self.trades)
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(wins) / len(self.trades) * 100
        
        gross_profit = sum(t['pnl_percent'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_percent'] for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_win': np.mean([t['pnl_percent'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_percent'] for t in losses]) if losses else 0,
            'profit_factor': profit_factor,
            'final_equity': self.capital
        }


def print_strategy_menu():
    """Print strategy selection menu"""
    print("=" * 80)
    print("SELECT TRADING STRATEGY")
    print("=" * 80)
    for key, strat in STRATEGIES.items():
        note = f" - {strat['note']}" if 'note' in strat else ""
        print(f"\n{key}. {strat['name']}{note}")
        print(f"   Best for: {strat['best_for']}")
        print(f"   Trades: {strat['trades']}")
        print(f"   Risk: {strat['risk']}")
    print("=" * 80)


def print_coin_menu():
    """Print coin selection menu"""
    print("\n" + "=" * 80)
    print("SELECT COIN TO BACKTEST")
    print("=" * 80)
    print("\n📈 LARGE CAP (Stable):")
    for key in ['1', '2', '3', '8', '9']:
        coin = COINS[key]
        rec = ', '.join([STRATEGIES[str(r)]['name'] for r in coin['recommended']])
        print(f"  {key}. {coin['name']} ({coin['symbol']}) - Recommended: {rec}")
    
    print("\n🚀 HIGH VOLATILITY (Altcoins):")
    for key in ['4', '5', '6', '7', '10']:
        coin = COINS[key]
        rec = ', '.join([STRATEGIES[str(r)]['name'] for r in coin['recommended']])
        print(f"  {key}. {coin['name']} ({coin['symbol']}) - Recommended: {rec}")
    print("=" * 80)


def print_results(results, strategy_name, symbol):
    """Print results"""
    print("\n" + "=" * 80)
    print(f"BACKTEST RESULTS: {strategy_name} on {symbol}")
    print("=" * 80)
    print(f"Initial Capital:      ${1000:.2f}")
    print(f"Final Equity:         ${results['final_equity']:.2f}")
    print(f"Total Return:         {results['total_return']:+.2f}%")
    print()
    print(f"Total Trades:         {results['total_trades']}")
    
    if results['total_trades'] == 0:
        print("\n⚠️  NO TRADES - Strategy too selective for this period")
        print("   Try: Different timeframe, different interval, or different strategy")
        print("=" * 80)
        return
    
    print(f"Winning Trades:       {results['winning_trades']} ({results['win_rate']:.1f}%)")
    print(f"Losing Trades:        {results['losing_trades']}")
    print()
    print(f"Average Win:          {results['avg_win']:+.2f}%")
    print(f"Average Loss:         {results['avg_loss']:+.2f}%")
    print(f"Profit Factor:        {results['profit_factor']:.2f}")
    print("=" * 80)
    
    # Rating
    if results['total_return'] > 10 and results['win_rate'] > 50:
        print("✅ EXCELLENT - Strong performance!")
    elif results['total_return'] > 5:
        print("✅ GOOD - Profitable strategy")
    elif results['total_return'] > 0:
        print("⚠️  MARGINAL - Small profit, consider other strategies")
    else:
        print("❌ POOR - Try different strategy for this coin")
    print()


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("🚀 QUICK BACKTEST - All-in-One Testing Tool")
    print("=" * 80)
    print("\nTest multiple strategies on different coins instantly!")
    print("Data fetched automatically from Binance API")
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Make sure you have a .env file with API credentials")
        return
    
    # Select strategy
    print_strategy_menu()
    strategy_choice = input("\nChoose strategy (1-6) [1]: ").strip() or '1'
    
    if strategy_choice not in STRATEGIES:
        print("❌ Invalid choice")
        return
    
    strategy_info = STRATEGIES[strategy_choice]
    
    # Select coin
    print_coin_menu()
    coin_choice = input("\nChoose coin (1-10): ").strip()
    
    if coin_choice not in COINS:
        print("❌ Invalid choice")
        return
    
    coin_info = COINS[coin_choice]
    
    # Show recommendation
    if int(strategy_choice) in coin_info['recommended']:
        print(f"\n✅ {strategy_info['name']} is RECOMMENDED for {coin_info['name']}")
    else:
        print(f"\n⚠️  {strategy_info['name']} may not be optimal for {coin_info['name']}")
        print(f"   Recommended: {', '.join([STRATEGIES[str(r)]['name'] for r in coin_info['recommended']])}")
        confirm = input("   Continue anyway? (yes/no) [yes]: ").strip().lower() or 'yes'
        if confirm not in ['yes', 'y']:
            print("❌ Cancelled")
            return
    
    # Interval and days
    print("\n⏱️  SELECT TIMEFRAME:")
    print("1. 5m, 30 days (~8,640 candles)")
    print("2. 15m, 60 days (~5,760 candles)")
    print("3. 1h, 90 days (~2,160 candles)")
    print("4. 4h, 180 days (~1,080 candles)")
    
    interval_choice = input("\nChoose interval (1-4) [3]: ").strip() or '3'
    interval_configs = {
        '1': {'interval': '5m', 'days': 30},
        '2': {'interval': '15m', 'days': 60},
        '3': {'interval': '1h', 'days': 90},
        '4': {'interval': '4h', 'days': 180}
    }
    config = interval_configs.get(interval_choice, {'interval': '1h', 'days': 90})
    
    print(f"\n🔄 Fetching {config['days']} days of {config['interval']} data for {coin_info['symbol']}...")
    print("    (Making multiple API calls to get full dataset...)")
    
    # Run backtest
    backtester = QuickBacktester(strategy_info['class'])
    klines = backtester.fetch_data(coin_info['symbol'], interval=config['interval'], days=config['days'])
    
    if not klines:
        print("❌ Failed to fetch data")
        return
    
    print(f"✓ Fetched {len(klines)} candles")
    print("🔄 Running backtest...")
    
    try:
        results = backtester.run(klines)
        print_results(results, strategy_info['name'], coin_info['symbol'])
        
        # Ask to try another
        again = input("Test another combination? (yes/no) [no]: ").strip().lower()
        if again in ['yes', 'y']:
            print("\n" * 2)
            main()
    
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(0)
