"""
Download large historical datasets (more than 1000 candles)

Binance API limits single requests to 1000 candles.
This script makes multiple requests to download larger datasets.
"""
import pandas as pd
from binance_client import BinanceClient
from config import Config
import sys
import time
from datetime import datetime, timedelta

def download_large_dataset(symbol, interval, days, output_filename=None):
    """
    Download large dataset by making multiple API calls
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Timeframe (e.g., '5m', '1h', '4h')
        days: Number of days to download
        output_filename: Optional custom filename
    """
    print(f"Downloading {days} days of {interval} data for {symbol}...")
    print("This will make multiple API calls to fetch all data...\n")
    
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
    
    # Calculate intervals
    interval_minutes = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15,
        '30m': 30, '1h': 60, '4h': 240, '1d': 1440
    }
    
    minutes_per_candle = interval_minutes.get(interval, 5)
    candles_per_batch = 1000  # API limit
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Calculate how many candles we need
    total_minutes = days * 24 * 60
    total_candles_needed = total_minutes // minutes_per_candle
    batches_needed = (total_candles_needed + candles_per_batch - 1) // candles_per_batch
    
    print(f"Total candles needed: {total_candles_needed}")
    print(f"Batches required: {batches_needed}")
    print(f"Each batch: {candles_per_batch} candles\n")
    
    all_klines = []
    current_start = int(start_time.timestamp() * 1000)
    
    for batch_num in range(batches_needed):
        print(f"Fetching batch {batch_num + 1}/{batches_needed}...", end='', flush=True)
        
        try:
            # Fetch this batch
            klines = client.get_klines(
                symbol=symbol, 
                interval=interval, 
                limit=candles_per_batch,
                startTime=current_start
            )
            
            if not klines:
                print(" No data returned")
                break
            
            print(f" Got {len(klines)} candles")
            all_klines.extend(klines)
            
            # Update start time for next batch (use last candle's timestamp + 1)
            current_start = int(klines[-1][0]) + (minutes_per_candle * 60 * 1000)
            
            # Don't hammer the API
            if batch_num < batches_needed - 1:
                time.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            print(f"\nError fetching batch {batch_num + 1}: {e}")
            break
    
    if not all_klines:
        print("No data downloaded")
        return
    
    print(f"\nTotal candles downloaded: {len(all_klines)}")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Keep only required columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # Remove duplicates (in case of overlap)
    df = df.drop_duplicates(subset=['timestamp'])
    
    # Convert types
    df['timestamp'] = df['timestamp'].astype(int)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Generate filename if not provided
    if output_filename is None:
        output_filename = f"data/{symbol}_{interval}_{days}days.csv"
    
    # Save to CSV
    df.to_csv(output_filename, index=False)
    
    print(f"\n✓ Saved {len(df)} candles to {output_filename}")
    
    # Show date range
    start_date = datetime.fromtimestamp(df['timestamp'].iloc[0] / 1000)
    end_date = datetime.fromtimestamp(df['timestamp'].iloc[-1] / 1000)
    actual_days = (end_date - start_date).days
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Actual days: {actual_days}")
    
    print(f"\nYou can now use this file with:")
    print(f"python backtest_runner.py")
    print(f"# Choose option 2")
    print(f"# Enter: {output_filename}")


def main():
    """Interactive mode"""
    print("=" * 70)
    print("DOWNLOAD LARGE HISTORICAL DATASETS")
    print("=" * 70)
    print()
    print("This tool makes multiple API calls to download more than 1000 candles.")
    print("Binance limits single requests to 1000 candles, so we fetch in batches.")
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
    days = int(input("Days of data [100]: ").strip() or '100')
    
    print()
    
    # Warn about large downloads
    interval_minutes = {'1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}
    estimated_candles = (days * 24 * 60) // interval_minutes.get(interval, 5)
    estimated_batches = (estimated_candles + 999) // 1000
    
    print(f"⚠️  This will download approximately {estimated_candles:,} candles")
    print(f"    in {estimated_batches} batches (takes ~{estimated_batches * 0.5:.0f} seconds)")
    print()
    
    confirm = input("Continue? (yes/no) [yes]: ").strip().lower() or 'yes'
    if confirm not in ['yes', 'y']:
        print("Cancelled")
        return
    
    print()
    download_large_dataset(symbol, interval, days)
    
    print("\n✅ Download complete!")


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
