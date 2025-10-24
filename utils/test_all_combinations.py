"""
Test All Combinations - Find What Works Best!

Tests every strategy on every coin with every timeframe.
Shows you the top performers so you know exactly what to use.

FAIR COMPARISON: All timeframes test the SAME time period (e.g., 30 days)
- This ensures fair comparison across timeframes
- Different timeframes will have different numbers of candles but same duration

Total tests: 6 strategies × 10 coins × 4 timeframes = 240 combinations
"""
import sys
import time
import pandas as pd
from quick_backtest import QuickBacktester, STRATEGIES, COINS
from binance_client import BinanceClient
from config import Config

# Timeframe configurations
# All timeframes test the SAME time period for fair comparison
TIMEFRAMES = {
    '5m': {'interval': '5m', 'candles_per_day': 288},   # 24*60/5 = 288 candles per day
    '15m': {'interval': '15m', 'candles_per_day': 96},  # 24*60/15 = 96 candles per day
    '1h': {'interval': '1h', 'candles_per_day': 24},    # 24 candles per day
    '4h': {'interval': '4h', 'candles_per_day': 6}      # 24/4 = 6 candles per day
}


def test_combination(strategy_key, coin_key, timeframe_key, data_cache, test_days=30):
    """Test a single strategy-coin-timeframe combination"""
    strategy_info = STRATEGIES[strategy_key]
    coin_info = COINS[coin_key]
    tf_config = TIMEFRAMES[timeframe_key]
    
    # Use cached data if available
    cache_key = f"{coin_info['symbol']}_{tf_config['interval']}_{test_days}"
    
    if cache_key not in data_cache:
        # Fetch data - all timeframes get same number of days
        backtester = QuickBacktester(strategy_info['class'])
        klines = backtester.fetch_data(
            coin_info['symbol'],
            interval=tf_config['interval'],
            days=test_days
        )
        data_cache[cache_key] = klines
    else:
        klines = data_cache[cache_key]
    
    if not klines or len(klines) < 100:
        return None
    
    # Calculate actual time period
    expected_candles = test_days * tf_config['candles_per_day']
    actual_candles = len(klines)
    actual_days = actual_candles / tf_config['candles_per_day']
    
    # Run backtest
    try:
        backtester = QuickBacktester(strategy_info['class'])
        results = backtester.run(klines)
        
        return {
            'strategy': strategy_info['name'],
            'coin': coin_info['name'],
            'symbol': coin_info['symbol'],
            'timeframe': timeframe_key,
            'total_return': results['total_return'],
            'trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'profit_factor': results['profit_factor'],
            'final_equity': results['final_equity'],
            'days_tested': actual_days,
            'candles': actual_candles
        }
    except Exception as e:
        print(f"Error testing {strategy_info['name']} on {coin_info['symbol']} {timeframe_key}: {e}")
        return None


def main():
    """Run comprehensive test of all combinations"""
    print("\n" + "=" * 80)
    print("🔬 COMPREHENSIVE STRATEGY TEST")
    print("=" * 80)
    print("\nThis will test ALL strategies on ALL coins with ALL timeframes")
    print(f"Total combinations: {len(STRATEGIES)} strategies × {len(COINS)} coins × {len(TIMEFRAMES)} timeframes = {len(STRATEGIES) * len(COINS) * len(TIMEFRAMES)}")
    print("\n⚠️  This will take 5-10 minutes and make many API calls.")
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Ask for test period
    print("TEST PERIOD:")
    print("All timeframes will be tested over the SAME time period for fair comparison.")
    print()
    days_input = input("How many days to test? (7/14/30/60/90) [30]: ").strip()
    try:
        test_days = int(days_input) if days_input else 30
        if test_days < 7:
            print("⚠️  Minimum 7 days recommended")
            test_days = 7
        elif test_days > 365:
            print("⚠️  Limited to 365 days (API constraints)")
            test_days = 365
    except:
        test_days = 30
    
    print(f"✓ Testing {test_days} days for all timeframes")
    print(f"  5m:  ~{test_days * 288} candles")
    print(f"  15m: ~{test_days * 96} candles")
    print(f"  1h:  ~{test_days * 24} candles")
    print(f"  4h:  ~{test_days * 6} candles")
    print()
    
    # Ask for mode
    print("TEST MODE:")
    print("1. Full test (all 240 combinations) - ~10 minutes")
    print("2. Quick test (all strategies on 1 coin, all timeframes) - ~1 minute")
    print("3. Specific coin test (all strategies, all timeframes for one coin)")
    
    mode = input("\nChoose mode (1-3) [2]: ").strip() or '2'
    
    if mode == '2':
        # Quick test on BTC only
        coin_keys = ['1']  # BTC
        print("\n🚀 Quick test: All strategies on Bitcoin")
    elif mode == '3':
        # Specific coin
        print("\nAvailable coins:")
        for key, coin in COINS.items():
            print(f"  {key}. {coin['name']} ({coin['symbol']})")
        coin_choice = input("\nChoose coin (1-10): ").strip()
        if coin_choice not in COINS:
            print("❌ Invalid choice")
            return
        coin_keys = [coin_choice]
        print(f"\n🚀 Testing all strategies on {COINS[coin_choice]['name']}")
    else:
        # Full test
        coin_keys = list(COINS.keys())
        print("\n🚀 Full test: All combinations")
    
    print("\n" + "=" * 80)
    print("RUNNING TESTS...")
    print("=" * 80)
    
    results = []
    data_cache = {}
    
    total_tests = len(STRATEGIES) * len(coin_keys) * len(TIMEFRAMES)
    current_test = 0
    
    # Test all combinations
    for strategy_key in STRATEGIES.keys():
        for coin_key in coin_keys:
            for tf_key in TIMEFRAMES.keys():
                current_test += 1
                
                strategy_name = STRATEGIES[strategy_key]['name']
                coin_name = COINS[coin_key]['name']
                
                print(f"\r[{current_test}/{total_tests}] Testing {strategy_name} on {coin_name} {tf_key}...", end='', flush=True)
                
                result = test_combination(strategy_key, coin_key, tf_key, data_cache, test_days)
                if result:
                    results.append(result)
                
                # Rate limiting
                time.sleep(0.1)
    
    print("\n\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)
    
    if not results:
        print("❌ No successful tests")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(results)
    
    # ===== TOP PERFORMERS =====
    print("\n🏆 TOP 10 BEST PERFORMERS (by Total Return)")
    print("-" * 80)
    print(f"Note: All tests cover ~{test_days} days ({df['days_tested'].mean():.1f} days avg actual)")
    print("-" * 80)
    top_10 = df.nlargest(10, 'total_return')
    for idx, row in top_10.iterrows():
        print(f"{row['strategy']:25} {row['coin']:12} {row['timeframe']:4} → "
              f"{row['total_return']:+7.2f}% | {row['trades']:3} trades | "
              f"WR: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f} | "
              f"{row['candles']:.0f} candles")
    
    # ===== WORST PERFORMERS =====
    print("\n💩 WORST 10 PERFORMERS (by Total Return)")
    print("-" * 80)
    worst_10 = df.nsmallest(10, 'total_return')
    for idx, row in worst_10.iterrows():
        print(f"{row['strategy']:25} {row['coin']:12} {row['timeframe']:4} → "
              f"{row['total_return']:+7.2f}% | {row['trades']:3} trades")
    
    # ===== BEST STRATEGY PER COIN =====
    print("\n📊 BEST STRATEGY FOR EACH COIN")
    print("-" * 80)
    for coin_name in df['coin'].unique():
        coin_data = df[df['coin'] == coin_name]
        best = coin_data.loc[coin_data['total_return'].idxmax()]
        print(f"{best['coin']:12} → {best['strategy']:25} {best['timeframe']:4} "
              f"({best['total_return']:+.2f}%, {best['trades']} trades)")
    
    # ===== BEST COIN PER STRATEGY =====
    print("\n🎯 BEST COIN FOR EACH STRATEGY")
    print("-" * 80)
    for strategy_name in df['strategy'].unique():
        strategy_data = df[df['strategy'] == strategy_name]
        best = strategy_data.loc[strategy_data['total_return'].idxmax()]
        print(f"{best['strategy']:25} → {best['coin']:12} {best['timeframe']:4} "
              f"({best['total_return']:+.2f}%, {best['trades']} trades)")
    
    # ===== BEST TIMEFRAME =====
    print("\n⏱️  BEST TIMEFRAME (Average Performance)")
    print("-" * 80)
    tf_avg = df.groupby('timeframe')['total_return'].agg(['mean', 'count'])
    tf_avg = tf_avg.sort_values('mean', ascending=False)
    for tf, row in tf_avg.iterrows():
        print(f"{tf:4} → Avg: {row['mean']:+.2f}% ({int(row['count'])} tests)")
    
    # ===== STATISTICS =====
    print("\n📈 OVERALL STATISTICS")
    print("-" * 80)
    profitable = df[df['total_return'] > 0]
    print(f"Test period: {test_days} days (same for all timeframes)")
    print(f"Actual days: {df['days_tested'].min():.1f} - {df['days_tested'].max():.1f} days (varies by data availability)")
    print(f"Profitable combinations: {len(profitable)}/{len(df)} ({len(profitable)/len(df)*100:.1f}%)")
    print(f"Average return: {df['total_return'].mean():+.2f}%")
    print(f"Best return: {df['total_return'].max():+.2f}%")
    print(f"Worst return: {df['total_return'].min():+.2f}%")
    print(f"Median return: {df['total_return'].median():+.2f}%")
    
    # ===== RECOMMENDATIONS =====
    print("\n💡 RECOMMENDATIONS")
    print("=" * 80)
    
    # Find the absolute best
    best_overall = df.loc[df['total_return'].idxmax()]
    print(f"\n🏆 BEST OVERALL COMBINATION:")
    print(f"   Strategy: {best_overall['strategy']}")
    print(f"   Coin: {best_overall['coin']} ({best_overall['symbol']})")
    print(f"   Timeframe: {best_overall['timeframe']}")
    print(f"   Return: {best_overall['total_return']:+.2f}%")
    print(f"   Win Rate: {best_overall['win_rate']:.1f}%")
    print(f"   Trades: {best_overall['trades']}")
    
    # Find most consistent (positive in multiple timeframes)
    print(f"\n🎯 MOST CONSISTENT COMBINATIONS (Positive across timeframes):")
    consistency = df[df['total_return'] > 0].groupby(['strategy', 'coin']).size().reset_index(name='count')
    consistency = consistency.sort_values('count', ascending=False).head(5)
    for _, row in consistency.iterrows():
        combo_data = df[(df['strategy'] == row['strategy']) & (df['coin'] == row['coin'])]
        avg_return = combo_data['total_return'].mean()
        print(f"   {row['strategy']:25} on {row['coin']:12} → "
              f"Positive in {row['count']}/4 timeframes, Avg: {avg_return:+.2f}%")
    
    # Export option
    print("\n" + "=" * 80)
    export = input("Export full results to CSV? (yes/no) [no]: ").strip().lower()
    if export in ['yes', 'y']:
        filename = 'test_all_combinations_results.csv'
        df.to_csv(filename, index=False)
        print(f"✓ Results exported to {filename}")
    
    print("\n✅ Testing complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Testing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
