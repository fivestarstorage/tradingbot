"""
Simple menu-driven backtesting with preset strategies
"""
import sys
from backtest import Backtester
from binance_client import BinanceClient
from config import Config

# Preset trading pairs
TRADING_PAIRS = {
    '1': 'BTCUSDT',      # Bitcoin (Large cap, moderate volatility)
    '2': 'ETHUSDT',      # Ethereum (Large cap, moderate volatility)
    '3': 'BNBUSDT',      # Binance Coin (Medium cap, good volatility)
    '4': 'SOLUSDT',      # Solana (High volatility)
    '5': 'AVAXUSDT',     # Avalanche (High volatility)
    '6': 'MATICUSDT',    # Polygon (High volatility)
    '7': 'LINKUSDT',     # Chainlink (Medium volatility)
    '8': 'DOGEUSDT',     # Dogecoin (Very high volatility)
    '9': 'SHIBUSDT',     # Shiba Inu (Very high volatility)
    '10': 'ADAUSDT',     # Cardano (Medium volatility)
}

# Preset strategy configurations
STRATEGIES = {
    '1': {
        'name': 'Conservative',
        'description': 'Lower risk, fewer trades',
        'config': {
            'RSI_PERIOD': 14,
            'RSI_OVERBOUGHT': 75,
            'RSI_OVERSOLD': 25,
            'MOMENTUM_PERIOD': 12,
            'STOP_LOSS_PERCENT': 1.5,
            'TAKE_PROFIT_PERCENT': 3.0
        }
    },
    '2': {
        'name': 'Balanced',
        'description': 'Default settings, moderate risk',
        'config': {
            'RSI_PERIOD': 14,
            'RSI_OVERBOUGHT': 70,
            'RSI_OVERSOLD': 30,
            'MOMENTUM_PERIOD': 10,
            'STOP_LOSS_PERCENT': 2.0,
            'TAKE_PROFIT_PERCENT': 5.0
        }
    },
    '3': {
        'name': 'Aggressive',
        'description': 'More trades, higher risk/reward',
        'config': {
            'RSI_PERIOD': 14,
            'RSI_OVERBOUGHT': 65,
            'RSI_OVERSOLD': 35,
            'MOMENTUM_PERIOD': 8,
            'STOP_LOSS_PERCENT': 3.0,
            'TAKE_PROFIT_PERCENT': 7.0
        }
    },
    '4': {
        'name': 'Scalper',
        'description': 'Quick trades, tight stops',
        'config': {
            'RSI_PERIOD': 9,
            'RSI_OVERBOUGHT': 70,
            'RSI_OVERSOLD': 30,
            'MOMENTUM_PERIOD': 5,
            'STOP_LOSS_PERCENT': 1.0,
            'TAKE_PROFIT_PERCENT': 2.0
        }
    },
    '5': {
        'name': 'Swing Trader',
        'description': 'Hold longer, wider stops',
        'config': {
            'RSI_PERIOD': 21,
            'RSI_OVERBOUGHT': 70,
            'RSI_OVERSOLD': 30,
            'MOMENTUM_PERIOD': 14,
            'STOP_LOSS_PERCENT': 4.0,
            'TAKE_PROFIT_PERCENT': 10.0
        }
    },
    '6': {
        'name': 'Ultra Aggressive',
        'description': 'Maximum trades, for volatile altcoins',
        'config': {
            'RSI_PERIOD': 14,
            'RSI_OVERBOUGHT': 60,
            'RSI_OVERSOLD': 40,
            'MOMENTUM_PERIOD': 6,
            'STOP_LOSS_PERCENT': 2.5,
            'TAKE_PROFIT_PERCENT': 5.0
        }
    },
    '7': {
        'name': 'High Frequency',
        'description': 'Very fast, many small trades',
        'config': {
            'RSI_PERIOD': 7,
            'RSI_OVERBOUGHT': 55,
            'RSI_OVERSOLD': 45,
            'MOMENTUM_PERIOD': 3,
            'STOP_LOSS_PERCENT': 1.5,
            'TAKE_PROFIT_PERCENT': 3.0
        }
    },
    '8': {
        'name': 'Momentum Surfer',
        'description': 'Ride strong trends, ignore RSI extremes',
        'config': {
            'RSI_PERIOD': 14,
            'RSI_OVERBOUGHT': 80,
            'RSI_OVERSOLD': 20,
            'MOMENTUM_PERIOD': 5,
            'STOP_LOSS_PERCENT': 3.0,
            'TAKE_PROFIT_PERCENT': 8.0
        }
    },
    '9': {
        'name': 'Hyper Trader',
        'description': 'Maximum trades! Trades on ANY momentum',
        'config': {
            'RSI_PERIOD': 7,
            'RSI_OVERBOUGHT': 52,
            'RSI_OVERSOLD': 48,
            'MOMENTUM_PERIOD': 2,
            'STOP_LOSS_PERCENT': 1.0,
            'TAKE_PROFIT_PERCENT': 2.0
        }
    }
}

# Preset timeframes
TIMEFRAMES = {
    '1': {'interval': '1m', 'days': 7, 'name': '1 week of 1-minute data'},
    '2': {'interval': '5m', 'days': 30, 'name': '1 month of 5-minute data'},
    '3': {'interval': '15m', 'days': 60, 'name': '2 months of 15-minute data'},
    '4': {'interval': '1h', 'days': 90, 'name': '3 months of 1-hour data'},
    '5': {'interval': '4h', 'days': 180, 'name': '6 months of 4-hour data'},
}


def print_header():
    """Print header"""
    print("\n" + "=" * 70)
    print("🚀 SIMPLE MOMENTUM STRATEGY BACKTESTER")
    print("=" * 70)


def select_trading_pair():
    """Let user select a trading pair"""
    print("\n📊 SELECT TRADING PAIR:")
    print("-" * 70)
    print("  💰 Large Cap (Stable):")
    print(f"    1. {TRADING_PAIRS['1']}")
    print(f"    2. {TRADING_PAIRS['2']}")
    print()
    print("  🚀 Medium Cap (More Volatile):")
    print(f"    3. {TRADING_PAIRS['3']}")
    print(f"    7. {TRADING_PAIRS['7']}")
    print(f"    10. {TRADING_PAIRS['10']}")
    print()
    print("  ⚡ High Volatility (Most Trading Opportunities):")
    print(f"    4. {TRADING_PAIRS['4']}")
    print(f"    5. {TRADING_PAIRS['5']}")
    print(f"    6. {TRADING_PAIRS['6']}")
    print(f"    8. {TRADING_PAIRS['8']}")
    print(f"    9. {TRADING_PAIRS['9']}")
    print("-" * 70)
    
    while True:
        choice = input("Choose trading pair (1-10): ").strip()
        if choice in TRADING_PAIRS:
            symbol = TRADING_PAIRS[choice]
            print(f"✓ Selected: {symbol}")
            return symbol
        print("❌ Invalid choice. Please enter 1-10.")


def select_strategy():
    """Let user select a strategy"""
    print("\n⚙️  SELECT STRATEGY:")
    print("-" * 70)
    print("  📊 Standard Strategies:")
    for key in ['1', '2', '3', '4', '5']:
        strategy = STRATEGIES[key]
        print(f"    {key}. {strategy['name']:18} - {strategy['description']}")
    print()
    print("  🔥 Ultra-Aggressive (More Trades for Volatile Coins):")
    for key in ['6', '7', '8']:
        strategy = STRATEGIES[key]
        print(f"    {key}. {strategy['name']:18} - {strategy['description']}")
    print()
    print("  ⚡⚡ MAXIMUM TRADES (Warning: Very risky!):")
    print(f"    9. {STRATEGIES['9']['name']:18} - {STRATEGIES['9']['description']}")
    print("-" * 70)
    
    while True:
        choice = input("Choose strategy (1-9): ").strip()
        if choice in STRATEGIES:
            strategy = STRATEGIES[choice]
            print(f"✓ Selected: {strategy['name']}")
            return strategy
        print("❌ Invalid choice. Please enter 1-9.")


def select_timeframe():
    """Let user select a timeframe"""
    print("\n📅 SELECT TIMEFRAME:")
    print("-" * 70)
    for key, tf in TIMEFRAMES.items():
        print(f"  {key}. {tf['name']}")
    print("-" * 70)
    
    while True:
        choice = input("Choose timeframe (1-5): ").strip()
        if choice in TIMEFRAMES:
            timeframe = TIMEFRAMES[choice]
            print(f"✓ Selected: {timeframe['name']}")
            return timeframe
        print("❌ Invalid choice. Please enter 1-5.")


def select_capital():
    """Let user select initial capital"""
    print("\n💰 INITIAL CAPITAL:")
    print("-" * 70)
    print("  1. $500")
    print("  2. $1,000 (recommended)")
    print("  3. $5,000")
    print("  4. $10,000")
    print("  5. Custom amount")
    print("-" * 70)
    
    capital_options = {
        '1': 500,
        '2': 1000,
        '3': 5000,
        '4': 10000
    }
    
    while True:
        choice = input("Choose capital (1-5): ").strip()
        if choice in capital_options:
            capital = capital_options[choice]
            print(f"✓ Selected: ${capital:,}")
            return capital
        elif choice == '5':
            try:
                capital = float(input("Enter custom amount in USDT: ").strip())
                if capital > 0:
                    print(f"✓ Selected: ${capital:,.2f}")
                    return capital
                print("❌ Amount must be greater than 0.")
            except ValueError:
                print("❌ Invalid amount. Please enter a number.")
        else:
            print("❌ Invalid choice. Please enter 1-5.")


def apply_strategy_config(strategy):
    """Temporarily apply strategy configuration"""
    # Save original config
    original_config = {
        'RSI_PERIOD': Config.RSI_PERIOD,
        'RSI_OVERBOUGHT': Config.RSI_OVERBOUGHT,
        'RSI_OVERSOLD': Config.RSI_OVERSOLD,
        'MOMENTUM_PERIOD': Config.MOMENTUM_PERIOD,
        'STOP_LOSS_PERCENT': Config.STOP_LOSS_PERCENT,
        'TAKE_PROFIT_PERCENT': Config.TAKE_PROFIT_PERCENT
    }
    
    # Apply strategy config
    for key, value in strategy['config'].items():
        setattr(Config, key, value)
    
    return original_config


def restore_config(original_config):
    """Restore original configuration"""
    for key, value in original_config.items():
        setattr(Config, key, value)


def print_strategy_details(strategy):
    """Print strategy details"""
    print("\n" + "=" * 70)
    print(f"STRATEGY: {strategy['name']}")
    print("=" * 70)
    print(f"RSI Period:           {strategy['config']['RSI_PERIOD']}")
    print(f"RSI Overbought:       {strategy['config']['RSI_OVERBOUGHT']}")
    print(f"RSI Oversold:         {strategy['config']['RSI_OVERSOLD']}")
    print(f"Momentum Period:      {strategy['config']['MOMENTUM_PERIOD']}")
    print(f"Stop Loss:            {strategy['config']['STOP_LOSS_PERCENT']}%")
    print(f"Take Profit:          {strategy['config']['TAKE_PROFIT_PERCENT']}%")
    print("=" * 70)


def main():
    """Main entry point"""
    try:
        # Validate config
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Make sure you have a .env file with valid API credentials")
        return
    
    print_header()
    
    # User selections
    symbol = select_trading_pair()
    strategy = select_strategy()
    timeframe = select_timeframe()
    capital = select_capital()
    
    # Confirm
    print("\n" + "=" * 70)
    print("📋 BACKTEST CONFIGURATION")
    print("=" * 70)
    print(f"Trading Pair:     {symbol}")
    print(f"Strategy:         {strategy['name']} - {strategy['description']}")
    print(f"Timeframe:        {timeframe['name']}")
    print(f"Initial Capital:  ${capital:,.2f}")
    print("=" * 70)
    
    confirm = input("\n▶️  Start backtest? (yes/no) [yes]: ").strip().lower() or 'yes'
    
    if confirm not in ['yes', 'y']:
        print("\n❌ Backtest cancelled.")
        return
    
    # Apply strategy configuration
    original_config = apply_strategy_config(strategy)
    
    try:
        # Print strategy details
        print_strategy_details(strategy)
        
        # Initialize backtester
        backtester = Backtester(initial_capital=capital)
        
        # Fetch data
        klines = backtester.fetch_historical_data(
            symbol=symbol,
            interval=timeframe['interval'],
            days=timeframe['days']
        )
        
        if not klines:
            print("\n❌ Failed to fetch data. Exiting.")
            return
        
        # Run backtest
        results = backtester.run_backtest(klines)
        
        if results:
            # Export option
            print()
            export = input("💾 Export results to CSV? (yes/no) [no]: ").strip().lower()
            if export in ['yes', 'y']:
                filename = f"backtest_{symbol}_{strategy['name'].lower()}_{timeframe['interval']}.csv"
                backtester.export_results(filename)
                print(f"✓ Results saved to {filename}")
            
            # Save strategy option
            print()
            save = input("💡 Save this strategy to your .env file? (yes/no) [no]: ").strip().lower()
            if save in ['yes', 'y']:
                print("\nAdd these lines to your .env file:")
                print("-" * 70)
                for key, value in strategy['config'].items():
                    print(f"{key}={value}")
                print("-" * 70)
        
        print("\n✅ Backtest complete!")
        
    finally:
        # Restore original configuration
        restore_config(original_config)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Backtest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
