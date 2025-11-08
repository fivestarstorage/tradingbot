#!/usr/bin/env python3
"""
Momentum Strategy Backtest - TOP COINS BY VOLUME

Tests strategy on the highest volume, most liquid coins for realistic results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import requests
from typing import List, Dict, Tuple
import json

print("="*100)
print("🚀 MOMENTUM STRATEGY - TOP COINS BY VOLUME")
print("="*100)
print("\n📡 Fetching top coins by 24h volume...")

# Get top coins by volume
url = "https://api.binance.com/api/v3/ticker/24hr"
response = requests.get(url, timeout=10)

if response.status_code != 200:
    print("❌ Failed to fetch coin data")
    sys.exit(1)

tickers = response.json()
usdt_pairs = []
for ticker in tickers:
    if ticker['symbol'].endswith('USDT') and ticker['symbol'] != 'USDT':
        coin = ticker['symbol'][:-4]
        volume_usdt = float(ticker['quoteVolume'])
        # Filter out stablecoins and wrapped tokens
        if coin not in ['USDC', 'FDUSD', 'USDE', 'PAXG', 'USD1', 'BFUSD', 'EUR', 'AEUR']:
            usdt_pairs.append((coin, volume_usdt))

usdt_pairs.sort(key=lambda x: x[1], reverse=True)
TOP_COINS = [coin for coin, _ in usdt_pairs[:50]]  # Top 50 by volume

print(f"✅ Testing top 50 coins by volume")
print(f"🪙 Coins: {', '.join(TOP_COINS[:15])}...\n")

# Use the backtest code from earlier
exec(open('backtest_momentum_strategy.py').read().split('if __name__')[0])

def main():
    print("⏳ Running backtest on top 50 high-volume coins...")
    print("   (This represents real market conditions)\n")
    
    backtester = MomentumBacktester(initial_capital=10000)
    
    tested_count = 0
    for coin in TOP_COINS:
        print(f"📥 {coin}...")
        klines = backtester.fetch_historical_klines(coin, days=365)
        
        if not klines or len(klines) < 2000:
            print(f"   ⚠️  Skipping (insufficient data)")
            continue
        
        backtester.run_backtest(coin, klines)
        tested_count += 1
    
    print(f"\n✅ Tested {tested_count} coins\n")
    backtester.print_results()

if __name__ == '__main__':
    main()

