#!/usr/bin/env python3
"""
Diagnostic script to check why DOGE doesn't have an auto-manager bot
"""
import os
import json
from dotenv import load_dotenv
from binance_client import BinanceClient

load_dotenv()

print("=" * 70)
print("🔍 DOGE Auto-Manager Diagnostic")
print("=" * 70)

# Initialize client
client = BinanceClient(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET'),
    testnet=os.getenv('USE_TESTNET', 'true').lower() == 'true'
)

print(f"\n📡 Connected to: {'Testnet' if client.testnet else 'Mainnet'}")

# Check 1: DOGE Balance
print("\n1️⃣  Checking DOGE balance...")
account = client.client.get_account()
doge_balance = None
for balance in account['balances']:
    if balance['asset'] == 'DOGE':
        free = float(balance['free'])
        locked = float(balance['locked'])
        total = free + locked
        doge_balance = total
        print(f"   DOGE Balance: {total:.8f}")
        if total == 0:
            print("   ❌ Balance is 0 - Auto Manager won't create bot for 0 balance")
        else:
            print(f"   ✅ Balance > 0 - Should trigger auto-manager")
        break

if doge_balance is None:
    print("   ❌ DOGE not found in account balances")

# Check 2: DOGUSDT Tradeable
print("\n2️⃣  Checking if DOGEUSDT is tradeable...")
is_tradeable = client.is_symbol_tradeable('DOGEUSDT')
if is_tradeable:
    print("   ✅ DOGEUSDT is tradeable on Binance")
else:
    print("   ❌ DOGEUSDT is NOT tradeable - Auto Manager can't create bot")

# Check 3: Existing Bots
print("\n3️⃣  Checking existing bots...")
try:
    with open('active_bots.json', 'r') as f:
        data = json.load(f)
        bots = data.get('bots', [])
        
    doge_bot_found = False
    for bot in bots:
        if bot['symbol'] == 'DOGEUSDT':
            print(f"   ✅ DOGE bot found: {bot['name']} (ID: {bot['id']}, Status: {bot['status']})")
            print(f"   ℹ️  Auto Manager skips DOGE because it's already managed")
            doge_bot_found = True
            break
    
    if not doge_bot_found:
        print("   ℹ️  No existing bot managing DOGEUSDT")
        
except FileNotFoundError:
    print("   ⚠️  active_bots.json not found")
except json.JSONDecodeError:
    print("   ⚠️  active_bots.json is corrupted")

# Check 4: Auto-Manager Logic
print("\n4️⃣  Auto-Manager Decision:")
if doge_balance is None:
    print("   ❌ DOGE not in wallet")
elif doge_balance == 0:
    print("   ❌ DOGE balance is 0 (no coins to manage)")
elif not is_tradeable:
    print("   ❌ DOGEUSDT not tradeable on Binance")
elif doge_bot_found:
    print("   ✅ DOGE already managed by existing bot")
else:
    print("   🤔 DOGE should have auto-manager created!")
    print("\n   Possible reasons:")
    print("   • Dashboard hasn't been restarted since you got DOGE")
    print("   • Auto-manager encountered an error (check dashboard logs)")
    print("   • active_bots.json was modified manually")
    print("\n   Solution:")
    print("   • Restart dashboard: screen -X -S dashboard quit && screen -dmS dashboard python3 advanced_dashboard.py")
    print("   • OR create bot manually from dashboard")

# Recommendations
print("\n" + "=" * 70)
print("💡 RECOMMENDATIONS")
print("=" * 70)

if doge_balance and doge_balance > 0 and is_tradeable and not doge_bot_found:
    print("\n✅ Create DOGE bot manually:")
    print("   1. Go to dashboard: http://134.199.159.103:5001")
    print("   2. Click 'Add New Bot'")
    print("   3. Symbol: DOGEUSDT")
    print("   4. Strategy: AI Autonomous")
    print("   5. Capital: $100")
    print("   6. Start the bot")
    print("\n   OR restart dashboard to trigger auto-scan:")
    print("   screen -X -S dashboard quit")
    print("   screen -dmS dashboard python3 advanced_dashboard.py")
elif doge_balance == 0:
    print("\n⚠️  DOGE balance is 0. No bot needed.")
    print("   Buy DOGE first, then restart dashboard.")
elif not is_tradeable:
    print("\n❌ DOGEUSDT cannot be traded on this exchange.")
    print("   Check if you're on testnet (testnet has limited coins).")
    print("   Consider switching to mainnet.")
elif doge_bot_found:
    print("\n✅ DOGE is already being managed!")
    print("   Check dashboard to see the bot's status.")

print("\n" + "=" * 70)

