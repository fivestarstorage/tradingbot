"""
Compare Original vs Enhanced Strategy Performance
"""
import sys
from backtest import Backtester as OriginalBacktester
from enhanced_backtest import EnhancedBacktester
from binance_client import BinanceClient
from config import Config

def print_header():
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON: Original vs Enhanced")
    print("=" * 80)

def compare_results(original_results, enhanced_results):
    """Print side-by-side comparison of results"""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"{'Metric':<35} {'Original':<20} {'Enhanced':<20} {'Improvement':<15}")
    print("-" * 80)
    
    metrics = [
        ('Total Return (%)', 'total_return', True),
        ('Win Rate (%)', 'win_rate', True),
        ('Total Trades', 'total_trades', False),
        ('Profit Factor', 'profit_factor', True),
        ('Max Drawdown (%)', 'max_drawdown', False),
        ('Sharpe Ratio', 'sharpe_ratio', True),
        ('Average Win (%)', 'avg_win', True),
        ('Average Loss (%)', 'avg_loss', False),
    ]
    
    for display_name, key, higher_is_better in metrics:
        orig_val = original_results.get(key, 0)
        enh_val = enhanced_results.get(key, 0)
        
        if key == 'max_drawdown' or key == 'avg_loss':
            # For these metrics, lower is better
            if orig_val != 0:
                improvement = ((orig_val - enh_val) / abs(orig_val)) * 100
            else:
                improvement = 0
            improvement_str = f"{improvement:+.1f}%" if orig_val != 0 else "N/A"
        else:
            # Higher is better
            if orig_val != 0:
                improvement = ((enh_val - orig_val) / abs(orig_val)) * 100
            else:
                improvement = 0
            improvement_str = f"{improvement:+.1f}%" if orig_val != 0 else "N/A"
        
        # Format values
        if key in ['total_return', 'win_rate', 'max_drawdown', 'avg_win', 'avg_loss']:
            orig_str = f"{orig_val:.2f}%"
            enh_str = f"{enh_val:.2f}%"
        elif key == 'total_trades':
            orig_str = f"{orig_val}"
            enh_str = f"{enh_val}"
        else:
            orig_str = f"{orig_val:.2f}"
            enh_str = f"{enh_val:.2f}"
        
        print(f"{display_name:<35} {orig_str:<20} {enh_str:<20} {improvement_str:<15}")
    
    print("=" * 80)
    
    # Summary
    print("\nKEY IMPROVEMENTS:")
    print("-" * 80)
    
    if enhanced_results['total_return'] > original_results['total_return']:
        diff = enhanced_results['total_return'] - original_results['total_return']
        print(f"✓ Higher returns: +{diff:.2f}% absolute improvement")
    
    if enhanced_results['win_rate'] > original_results['win_rate']:
        diff = enhanced_results['win_rate'] - original_results['win_rate']
        print(f"✓ Better win rate: +{diff:.1f}% absolute improvement")
    
    if enhanced_results['max_drawdown'] < original_results['max_drawdown']:
        diff = original_results['max_drawdown'] - enhanced_results['max_drawdown']
        print(f"✓ Lower drawdown: -{diff:.2f}% absolute improvement")
    
    if enhanced_results['profit_factor'] > original_results['profit_factor']:
        diff = enhanced_results['profit_factor'] - original_results['profit_factor']
        print(f"✓ Better profit factor: +{diff:.2f} absolute improvement")
    
    if enhanced_results['sharpe_ratio'] > original_results['sharpe_ratio']:
        diff = enhanced_results['sharpe_ratio'] - original_results['sharpe_ratio']
        print(f"✓ Higher Sharpe ratio: +{diff:.2f} absolute improvement")
    
    # Enhanced-specific features
    if 'trailing_stop_trades' in enhanced_results:
        print(f"\n✓ Trailing stops used in {enhanced_results['trailing_stop_trades']} trades")
    
    if 'partial_trades' in enhanced_results and enhanced_results['partial_trades'] > 0:
        print(f"✓ Partial profit taking: {enhanced_results['partial_trades']} partial exits")
    
    print("-" * 80)


def main():
    """Main comparison script"""
    print_header()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Make sure you have a .env file with valid API credentials")
        return
    
    # Get user input
    print("\nTEST CONFIGURATION")
    print("-" * 80)
    symbol = input(f"Trading symbol [{Config.TRADING_SYMBOL}]: ").strip() or Config.TRADING_SYMBOL
    interval = input("Candle interval (5m/15m/1h/4h) [5m]: ").strip() or '5m'
    days = int(input("Days of historical data [30]: ").strip() or '30')
    capital = float(input("Initial capital in USDT [1000]: ").strip() or '1000')
    
    print("\n" + "=" * 80)
    print("FETCHING DATA...")
    print("=" * 80)
    
    # Fetch data once
    client = BinanceClient(
        api_key=Config.BINANCE_API_KEY,
        api_secret=Config.BINANCE_API_SECRET,
        testnet=Config.USE_TESTNET
    )
    
    klines_per_day = {
        '1m': 1440, '3m': 480, '5m': 288, '15m': 96,
        '30m': 48, '1h': 24, '4h': 6, '1d': 1
    }
    limit = min(klines_per_day.get(interval, 288) * days, 1000)
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    if not klines:
        print("❌ Failed to fetch data. Exiting.")
        return
    
    print(f"✓ Fetched {len(klines)} candles for {symbol}")
    
    # Run original strategy
    print("\n" + "=" * 80)
    print("TESTING ORIGINAL STRATEGY...")
    print("=" * 80)
    
    original_backtester = OriginalBacktester(initial_capital=capital)
    original_results = original_backtester.run_backtest(klines)
    
    # Run enhanced strategy
    print("\n" + "=" * 80)
    print("TESTING ENHANCED STRATEGY...")
    print("=" * 80)
    
    enhanced_backtester = EnhancedBacktester(initial_capital=capital)
    enhanced_results = enhanced_backtester.run_backtest(klines)
    
    if not original_results or not enhanced_results:
        print("❌ Backtest failed. Exiting.")
        return
    
    # Compare results
    compare_results(original_results, enhanced_results)
    
    # Export option
    print()
    export = input("Export both results to CSV? (yes/no) [no]: ").strip().lower()
    if export in ['yes', 'y']:
        original_backtester.export_results(f'original_{symbol}_{interval}.csv')
        enhanced_backtester.export_results(f'enhanced_{symbol}_{interval}.csv')
        print("✓ Results exported!")
    
    print("\n✅ Comparison complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Comparison interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
