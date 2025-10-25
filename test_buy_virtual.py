#!/usr/bin/env python3
"""
Test Buy Function - VIRTUALUSDT with $1
"""
import os
from dotenv import load_dotenv
from core.binance_client import BinanceClient
from app.trading_service import TradingService
from app.db import SessionLocal

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print("=" * 80)
print("🧪 Testing Buy Function - VIRTUALUSDT")
print("=" * 80)

# Initialize
binance = BinanceClient(api_key, api_secret, testnet=False)
trading_service = TradingService(binance)
db = SessionLocal()

try:
    # Get current price
    price = binance.get_current_price('VIRTUALUSDT')
    print(f"\n📊 Current VIRTUALUSDT Price: ${price:.6f}")
    
    # Calculate how much we'll get
    approx_quantity = 1.0 / price
    print(f"💰 With $1 USDT, you'll get approximately {approx_quantity:.2f} VIRTUAL")
    
    # Check USDT balance
    usdt_balance = binance.get_account_balance('USDT')
    print(f"\n💵 Your USDT Balance:")
    print(f"   Free: ${usdt_balance['free']:.2f}")
    print(f"   Locked: ${usdt_balance['locked']:.2f}")
    print(f"   Total: ${usdt_balance['total']:.2f}")
    
    if usdt_balance['free'] < 1.0:
        print(f"\n❌ ERROR: Not enough free USDT (need $1, have ${usdt_balance['free']:.2f})")
        exit(1)
    
    # Execute buy
    print(f"\n🎯 Attempting to buy $1 of VIRTUALUSDT...")
    print(f"   Using MARKET ORDER (instant conversion)")
    
    input("\nPress ENTER to continue with the purchase, or Ctrl+C to cancel...")
    
    result = trading_service.buy_market(db, 'VIRTUALUSDT', 1.0)
    
    if result:
        print(f"\n✅ SUCCESS! Buy order executed:")
        print(f"   Symbol: {result.symbol}")
        print(f"   Quantity: {result.quantity:.6f} VIRTUAL")
        print(f"   Price: ${result.price:.6f}")
        print(f"   Total: ${result.notional:.2f}")
        print(f"   Status: {result.status}")
        print(f"   Binance Order ID: {result.binance_order_id}")
        
        # Check new balance
        print(f"\n📊 New Balances:")
        usdt_new = binance.get_account_balance('USDT')
        virtual_new = binance.get_account_balance('VIRTUAL')
        print(f"   USDT: ${usdt_new['free']:.2f}")
        print(f"   VIRTUAL: {virtual_new['free']:.6f} (${virtual_new['free'] * price:.2f})")
    else:
        print(f"\n❌ FAILED: Buy order did not execute")
        print(f"   Check logs above for error details")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 80)

