#!/usr/bin/env python3
"""
Automatic Wallet Manager
========================

This script automatically:
1. Scans your Binance wallet for all coins
2. Creates trading bots for each coin you hold
3. Manages them with $25 USDT budget each
4. Starts them automatically

Run once to set up bots for all your holdings.
Run again anytime to add bots for new coins you buy.

Usage:
    python3 auto_manager.py
"""

import sys
import os
import json
import time

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
from binance_client import BinanceClient
from config import Config

def get_wallet_coins(client):
    """Get all non-zero coin balances from wallet"""
    try:
        account = client.client.get_account()
        coins = []
        
        for balance in account['balances']:
            asset = balance['asset']
            total = float(balance['free']) + float(balance['locked'])
            
            # Skip USDT and coins with zero balance
            if asset != 'USDT' and total > 0:
                # Check if tradeable as USDT pair
                symbol = f"{asset}USDT"
                if client.is_symbol_tradeable(symbol):
                    coins.append({
                        'asset': asset,
                        'symbol': symbol,
                        'balance': total
                    })
                    print(f"✅ Found: {asset} ({total:.6f}) - {symbol}")
                else:
                    print(f"⚠️  Skipping: {asset} - not tradeable on USDT pair")
        
        return coins
    except Exception as e:
        print(f"❌ Error getting wallet coins: {e}")
        return []

def load_active_bots():
    """Load existing bots from active_bots.json"""
    bots_file = 'active_bots.json'
    if not os.path.exists(bots_file):
        return []
    
    with open(bots_file, 'r') as f:
        return json.load(f)

def save_active_bots(bots):
    """Save bots to active_bots.json"""
    with open('active_bots.json', 'w') as f:
        json.dump(bots, f, indent=2)

def create_bot_for_coin(coin, bots, trade_amount=25):
    """Create a bot for a coin if it doesn't exist"""
    symbol = coin['symbol']
    
    # Check if bot already exists for this symbol
    existing = [b for b in bots if b['symbol'] == symbol]
    if existing:
        print(f"⏭️  Bot already exists for {symbol} (ID: {existing[0]['id']})")
        return None
    
    # Generate new bot ID
    if not bots:
        new_id = 1
    else:
        new_id = max(bot['id'] for bot in bots) + 1
    
    # Create new bot
    new_bot = {
        'id': new_id,
        'name': f"{coin['asset']} Auto-Trader",
        'symbol': symbol,
        'strategy': 'volatile',  # Default strategy
        'trade_amount': trade_amount,
        'status': 'stopped',
        'profit': 0.0,
        'trades': 0
    }
    
    print(f"✅ Created bot for {symbol} (ID: {new_id}, Budget: ${trade_amount})")
    return new_bot

def start_bot(bot_id, bot_name, symbol, strategy, trade_amount):
    """Start a bot using screen"""
    import subprocess
    
    # Escape single quotes in bot name
    bot_name = bot_name.replace("'", "'\\''")
    
    cmd = f"screen -dmS bot_{bot_id} python3 integrated_trader.py {bot_id} '{bot_name}' {symbol} {strategy} {trade_amount}"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            print(f"❌ Failed to start bot {bot_id}: {result.stderr}")
            return False
        
        time.sleep(1)
        
        # Verify it started
        check = subprocess.run(['screen', '-list'], capture_output=True, text=True)
        if f'bot_{bot_id}' in check.stdout:
            print(f"✅ Started bot {bot_id} for {symbol}")
            return True
        else:
            print(f"❌ Bot {bot_id} failed to start")
            return False
    except Exception as e:
        print(f"❌ Error starting bot {bot_id}: {e}")
        return False

def main():
    print("=" * 70)
    print("🤖 AUTOMATIC WALLET MANAGER")
    print("=" * 70)
    print()
    
    # Check config
    try:
        Config.validate()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease fix your .env file and try again.")
        return
    
    # Connect to Binance
    print("📡 Connecting to Binance...")
    client = BinanceClient(
        api_key=Config.BINANCE_API_KEY,
        api_secret=Config.BINANCE_API_SECRET,
        testnet=Config.USE_TESTNET
    )
    print()
    
    # Get coins from wallet
    print("💰 Scanning wallet for coins...")
    coins = get_wallet_coins(client)
    print()
    
    if not coins:
        print("ℹ️  No coins found in wallet (only USDT)")
        print("   Buy some crypto first, then run this again!")
        return
    
    print(f"Found {len(coins)} coin(s) in wallet\n")
    
    # Load existing bots
    bots = load_active_bots()
    print(f"📋 Currently have {len(bots)} bot(s) configured\n")
    
    # Create bots for each coin
    print("🔧 Creating bots for wallet coins...\n")
    new_bots = []
    for coin in coins:
        new_bot = create_bot_for_coin(coin, bots, trade_amount=25)
        if new_bot:
            bots.append(new_bot)
            new_bots.append(new_bot)
    
    # Save updated bots
    if new_bots:
        save_active_bots(bots)
        print(f"\n✅ Created {len(new_bots)} new bot(s)\n")
    else:
        print("\n✅ All coins already have bots\n")
    
    # Ask to start bots
    if new_bots:
        print("=" * 70)
        response = input("Start all new bots now? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            print("\n🚀 Starting bots...\n")
            for bot in new_bots:
                start_bot(
                    bot['id'],
                    bot['name'],
                    bot['symbol'],
                    bot['strategy'],
                    bot['trade_amount']
                )
                time.sleep(1)
            
            # Update status in config
            for bot in bots:
                if bot['id'] in [b['id'] for b in new_bots]:
                    bot['status'] = 'running'
            save_active_bots(bots)
            
            print("\n✅ All bots started!")
        else:
            print("\nℹ️  Bots created but not started. Start them from the dashboard.")
    
    print("\n" + "=" * 70)
    print("✅ DONE!")
    print("=" * 70)
    print("\nView dashboard: http://localhost:5001")
    print("Or on server: http://134.199.159.103:5001")
    print()

if __name__ == '__main__':
    main()

