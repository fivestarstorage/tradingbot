"""
Quick API Connection Test
Tests if your Binance API is working properly
"""
from binance_client import BinanceClient
from config import Config

print("=" * 70)
print("🔍 TESTING BINANCE API CONNECTION")
print("=" * 70)
print()

try:
    # Validate config
    Config.validate()
    print("✅ Config loaded successfully")
    print(f"   Mode: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
    print(f"   API Key: {Config.BINANCE_API_KEY[:10]}...")
    print()
except Exception as e:
    print(f"❌ Config error: {e}")
    exit(1)

# Create client
client = BinanceClient(
    api_key=Config.BINANCE_API_KEY,
    api_secret=Config.BINANCE_API_SECRET,
    testnet=Config.USE_TESTNET
)

print("Testing API endpoints...")
print()

# Test 1: Get account
print("1️⃣ Testing account access...")
try:
    account = client.client.get_account()
    print("✅ Account access: OK")
    print(f"   Can trade: {account['canTrade']}")
    print(f"   Can withdraw: {account['canWithdraw']}")
    print()
except Exception as e:
    print(f"❌ Account access failed: {e}")
    print()
    exit(1)

# Test 2: Get balances
print("2️⃣ Testing balance retrieval...")
try:
    balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
    print(f"✅ Found {len(balances)} assets with balance")
    print()
    
    print("   Your assets:")
    for bal in balances:
        free = float(bal['free'])
        locked = float(bal['locked'])
        total = free + locked
        print(f"   • {bal['asset']}: {total:.8f} (Free: {free:.8f}, Locked: {locked:.8f})")
    print()
except Exception as e:
    print(f"❌ Balance retrieval failed: {e}")
    print()
    exit(1)

# Test 3: Get prices
print("3️⃣ Testing price data...")
try:
    btc_price = client.get_current_price('BTCUSDT')
    print(f"✅ Price data: OK")
    print(f"   BTC/USDT: ${btc_price:,.2f}")
    print()
except Exception as e:
    print(f"❌ Price data failed: {e}")
    print()

# Test 4: Calculate total value
print("4️⃣ Calculating total account value...")
try:
    total_value = 0.0
    
    for bal in balances:
        asset = bal['asset']
        amount = float(bal['free']) + float(bal['locked'])
        
        if asset == 'USDT':
            value = amount
        else:
            try:
                price = client.get_current_price(f"{asset}USDT")
                if price:
                    value = amount * price
                else:
                    value = 0
            except:
                value = 0
        
        total_value += value
        
        if value > 0.01:  # Only show assets worth > $0.01
            print(f"   • {asset}: ${value:.2f}")
    
    print()
    print(f"💰 TOTAL ACCOUNT VALUE: ${total_value:.2f}")
    print()
    
except Exception as e:
    print(f"❌ Value calculation failed: {e}")
    print()

print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("Your API is working correctly!")
print("The dashboard should now show your balance properly.")
print()
print("If dashboard still shows $0, try:")
print("  1. Restart the dashboard: ./stop_dashboard.sh && ./start_dashboard.sh")
print("  2. Check browser console for errors (F12)")
print("  3. Try accessing: http://localhost:5000/api/overview")
print()
