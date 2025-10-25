#!/usr/bin/env python3
"""
Safe Buy Test - Checks everything before executing
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
print("🧪 Safe Buy Test - VIRTUALUSDT")
print("=" * 80)

# Initialize
binance = BinanceClient(api_key, api_secret, testnet=False)
trading_service = TradingService(binance)
db = SessionLocal()

try:
    # Get current price
    print(f"\n1️⃣  Checking VIRTUALUSDT price...")
    price = binance.get_current_price('VIRTUALUSDT')
    if not price:
        print(f"   ❌ Failed to get price")
        exit(1)
    print(f"   ✅ Current Price: ${price:.6f}")
    
    # Calculate quantity
    approx_quantity = 1.0 / price
    print(f"   📊 $1 will buy ~{approx_quantity:.2f} VIRTUAL")
    
    # Check USDT balance
    print(f"\n2️⃣  Checking USDT balance...")
    usdt_balance = binance.get_account_balance('USDT')
    if not usdt_balance:
        print(f"   ❌ Failed to get balance")
        print(f"   ⚠️  This usually means:")
        print(f"      - API keys not set correctly")
        print(f"      - IP not whitelisted on Binance")
        print(f"      - API permissions not enabled")
        print(f"\n   💡 Run this script on your Ubuntu server instead!")
        exit(1)
    
    print(f"   ✅ Free: ${usdt_balance['free']:.2f}")
    print(f"   ✅ Locked: ${usdt_balance['locked']:.2f}")
    
    if usdt_balance['free'] < 1.0:
        print(f"\n   ❌ Not enough free USDT")
        print(f"      Need: $1.00")
        print(f"      Have: ${usdt_balance['free']:.2f}")
        exit(1)
    
    # Check symbol filters
    print(f"\n3️⃣  Checking Binance trading rules...")
    step_size, min_qty, min_notional = trading_service._get_symbol_filters('VIRTUALUSDT')
    print(f"   Step size: {step_size}")
    print(f"   Min quantity: {min_qty}")
    print(f"   Min notional: ${min_notional}")
    
    # Simulate the calculation
    from decimal import Decimal
    raw_qty = Decimal('1.0') / Decimal(str(price))
    quantity = trading_service._floor_to_step(raw_qty, step_size)
    notional = quantity * Decimal(str(price))
    
    print(f"\n   Calculated:")
    print(f"   Raw quantity: {raw_qty:.6f}")
    print(f"   Floored quantity: {quantity:.6f}")
    print(f"   Notional value: ${notional:.6f}")
    
    if quantity < min_qty:
        print(f"   ❌ Quantity {quantity} < minimum {min_qty}")
        exit(1)
    
    if notional < min_notional:
        print(f"   ❌ Notional ${notional} < minimum ${min_notional}")
        print(f"\n   💡 Try buying with at least ${float(min_notional):.2f} USDT")
        exit(1)
    
    print(f"   ✅ All trading rules satisfied!")
    
    # Ready to buy
    print(f"\n4️⃣  Ready to execute buy order:")
    print(f"   Symbol: VIRTUALUSDT")
    print(f"   Type: MARKET ORDER (instant)")
    print(f"   Amount: $1.00 USDT")
    print(f"   Expected quantity: {quantity:.6f} VIRTUAL")
    print(f"   Expected cost: ${notional:.6f}")
    
    response = input(f"\n   ⚠️  Execute REAL trade on Binance? (yes/no): ")
    
    if response.lower() != 'yes':
        print(f"\n   ❌ Cancelled by user")
        exit(0)
    
    # Execute
    print(f"\n5️⃣  Executing buy order...")
    result = trading_service.buy_market(db, 'VIRTUALUSDT', 1.0)
    
    if result:
        print(f"\n   ✅ SUCCESS!")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   Symbol: {result.symbol}")
        print(f"   Quantity: {result.quantity:.6f} VIRTUAL")
        print(f"   Price: ${result.price:.6f}")
        print(f"   Total: ${result.notional:.2f}")
        print(f"   Status: {result.status}")
        print(f"   Order ID: {result.binance_order_id}")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Check new balance
        print(f"\n6️⃣  New balances:")
        usdt_new = binance.get_account_balance('USDT')
        virtual_new = binance.get_account_balance('VIRTUAL')
        print(f"   USDT: ${usdt_new['free']:.2f} (was ${usdt_balance['free']:.2f})")
        print(f"   VIRTUAL: {virtual_new['free']:.6f} (worth ${virtual_new['free'] * price:.2f})")
        
        print(f"\n   🎉 Trade saved to database!")
        print(f"   📱 SMS notification sent (if enabled)")
    else:
        print(f"\n   ❌ FAILED - Buy order did not execute")
        print(f"      Check errors above")
        
except KeyboardInterrupt:
    print(f"\n\n❌ Cancelled by user (Ctrl+C)")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 80)

