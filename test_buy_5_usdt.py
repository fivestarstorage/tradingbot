#!/usr/bin/env python3
"""
Buy Test - VIRTUALUSDT with $5 (Binance minimum)
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
print("🧪 Buy Test - VIRTUALUSDT ($5 minimum)")
print("=" * 80)

binance = BinanceClient(api_key, api_secret, testnet=False)
trading_service = TradingService(binance)
db = SessionLocal()

try:
    price = binance.get_current_price('VIRTUALUSDT')
    print(f"\n💰 Current Price: ${price:.6f}")
    print(f"📊 $5 will buy ~{5.0/price:.2f} VIRTUAL")
    
    usdt_balance = binance.get_account_balance('USDT')
    print(f"\n💵 Your Balance: ${usdt_balance['free']:.2f} USDT")
    
    if usdt_balance['free'] < 5.0:
        print(f"❌ Not enough USDT (need $5, have ${usdt_balance['free']:.2f})")
        exit(1)
    
    print(f"\n🎯 Ready to buy $5 of VIRTUALUSDT")
    response = input(f"   Execute REAL trade? (yes/no): ")
    
    if response.lower() != 'yes':
        print(f"❌ Cancelled")
        exit(0)
    
    print(f"\n⏳ Executing market buy order...")
    result = trading_service.buy_market(db, 'VIRTUALUSDT', 5.0)
    
    if result:
        print(f"\n✅ SUCCESS!")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Symbol: {result.symbol}")
        print(f"Quantity: {result.quantity:.2f} VIRTUAL")
        print(f"Price: ${result.price:.6f}")
        print(f"Total: ${result.notional:.2f}")
        print(f"Status: {result.status}")
        print(f"Order ID: {result.binance_order_id}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        virtual_balance = binance.get_account_balance('VIRTUAL')
        print(f"\n📊 New VIRTUAL Balance: {virtual_balance['free']:.2f} (${virtual_balance['free']*price:.2f})")
        print(f"\n🎉 Trade completed and saved to database!")
    else:
        print(f"\n❌ FAILED")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 80)

