"""
Simple script to test Binance API connection
"""
import sys
from config import Config
from binance_client import BinanceClient


def main():
    """Test connection to Binance"""
    print("=" * 60)
    print("Testing Binance Connection")
    print("=" * 60)
    print()
    
    try:
        # Validate config
        Config.validate()
        Config.print_config()
        
        # Initialize client
        print("Initializing Binance client...")
        client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        
        # Test connection
        print("\nTesting API connection...")
        if client.test_connection():
            print("✓ Connection successful!")
        else:
            print("✗ Connection failed!")
            sys.exit(1)
        
        # Get account balance
        print("\nFetching account balance...")
        balance = client.get_account_balance('USDT')
        if balance:
            print(f"✓ USDT Balance: {balance['total']:.2f}")
            print(f"   Free: {balance['free']:.2f}")
            print(f"   Locked: {balance['locked']:.2f}")
        
        # Get current price
        print(f"\nFetching {Config.TRADING_SYMBOL} price...")
        price = client.get_current_price(Config.TRADING_SYMBOL)
        if price:
            print(f"✓ Current price: {price:.2f}")
        
        # Get symbol info
        print(f"\nFetching {Config.TRADING_SYMBOL} trading rules...")
        symbol_info = client.get_symbol_info(Config.TRADING_SYMBOL)
        if symbol_info:
            print(f"✓ Symbol: {symbol_info['symbol']}")
            print(f"   Status: {symbol_info['status']}")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nYou're ready to run the trading bot!")
        print("Run: python trading_bot.py")
        print()
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file (run: python setup.py)")
        print("2. Added your Binance API credentials to .env")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
