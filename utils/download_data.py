"""
Simple script to download historical data and save as CSV

This downloads data from Binance and saves it in the correct format
for backtesting with backtest_runner.py
"""
import pandas as pd
from binance_client import BinanceClient
from config import Config
import sys

def download_and_save(symbol, interval, days, output_filename=None):
    """
    Download data from Binance and save as CSV
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Timeframe (e.g., '5m', '1h', '4h')
        days: Number of days to download
        output_filename: Optional custom filename
    """
    print(f"Downloading {days} days of {interval} data for {symbol}...")
    
    # Initialize Binance client
    try:
        client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
    except Exception as e:
        print(f"Error initializing Binance client: {e}")
        print("Make sure your .env file has valid API credentials")
        return
    
    # Calculate limit
    klines_per_day = {
        '1m': 1440, '3m': 480, '5m': 288, '15m': 96,
        '30m': 48, '1h': 24, '4h': 6, '1d': 1
    }
    limit = min(klines_per_day.get(interval, 288) * days, 1000)
    
    # Fetch data
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    if not klines:
        print("No data returned from Binance")
        return
    
    print(f"Downloaded {len(klines)} candles")
    
    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Keep only required columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Convert types
    df['timestamp'] = df['timestamp'].astype(int)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Generate filename if not provided
    if output_filename is None:
        output_filename = f"data/{symbol}_{interval}_{days}days.csv"
    
    # Save to CSV
    df.to_csv(output_filename, index=False)
    print(f"✓ Saved to {output_filename}")
    print(f"\nYou can now use this file with:")
    print(f"python backtest_runner.py")
    print(f"# Choose option 2")
    print(f"# Enter: {output_filename}")


def main():
    """Interactive mode"""
    print("=" * 60)
    print("DOWNLOAD HISTORICAL DATA FOR BACKTESTING")
    print("=" * 60)
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure you have a .env file with valid API credentials")
        return
    
    # Get user input
    symbol = input("Symbol [BTCUSDT]: ").strip() or 'BTCUSDT'
    interval = input("Interval (5m/15m/1h/4h) [5m]: ").strip() or '5m'
    days = int(input("Days of data [30]: ").strip() or '30')
    
    # Optional custom filename
    custom = input("\nCustom filename? (press enter to auto-generate): ").strip()
    filename = custom if custom else None
    
    print()
    download_and_save(symbol, interval, days, filename)
    
    print("\n✅ Done!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
