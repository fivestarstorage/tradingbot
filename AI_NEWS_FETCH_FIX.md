# AI News Fetch Fix for Community Tips Coins

## Problem

The AI trading news fetch function was running every 15 minutes, but it was only fetching news for hardcoded coins (`BTC`, `ETH`, `XRP`, `VIRTUAL`). When users added new coins via the Community Tips section in the frontend, those coins were not being added to the news fetch service.

## Root Cause

The `ai_auto_fetch_job()` scheduler function in `app/server.py` was using a hardcoded list of coins:

```python
coins = ['BTC', 'ETH', 'XRP', 'VIRTUAL']
```

When coins were added through the Community Tips feature (via `/api/coins/add`), they were correctly added to the `TradingCoin` database table, but the scheduler never checked this table - it only fetched news for the hardcoded coins.

## Solution

### 1. Dynamic Coin Fetching (✅ Fixed)

Updated `ai_auto_fetch_job()` to query the `TradingCoin` database table instead of using a hardcoded list:

**Before:**
```python
coins = ['BTC', 'ETH', 'XRP', 'VIRTUAL']
for coin in coins:
    # fetch news...
```

**After:**
```python
# Get all enabled coins from database
enabled_coins = db.query(TradingCoin).filter(
    TradingCoin.enabled == True,
    TradingCoin.ai_decisions_enabled == True
).all()

for trading_coin in enabled_coins:
    # fetch news...
```

### 2. Dynamic Timestamp Dictionary (✅ Fixed)

Changed `last_ai_fetch` from a fixed dictionary to a dynamic one that grows as coins are added:

**Before:**
```python
last_ai_fetch = {'BTC': None, 'ETH': None, 'XRP': None, 'VIRTUAL': None}
```

**After:**
```python
last_ai_fetch = {}  # Dynamic dictionary that grows with added coins
```

### 3. Base Coins Initialization (✅ Fixed)

Added a startup function `initialize_base_coins()` that ensures the base coins (BTC, ETH, XRP, VIRTUAL) are in the `TradingCoin` database table when the server starts:

```python
def initialize_base_coins():
    """Ensure base coins are in the TradingCoin table for AI auto-fetch"""
    base_coins = [
        {'coin': 'BTC', 'coin_name': 'Bitcoin', 'symbol': 'BTCUSDT'},
        {'coin': 'ETH', 'coin_name': 'Ethereum', 'symbol': 'ETHUSDT'},
        {'coin': 'XRP', 'coin_name': 'Ripple', 'symbol': 'XRPUSDT'},
        {'coin': 'VIRTUAL', 'coin_name': 'Virtuals Protocol', 'symbol': 'VIRTUALUSDT'},
    ]
    
    # Add to database if they don't exist
    # ...
```

## How It Works Now

1. **Server Startup**: Base coins are automatically added to the `TradingCoin` table
2. **Every 15 minutes**: The scheduler queries all enabled coins from the database
3. **When coins are added via Community Tips**: They are added to `TradingCoin` table with `ai_decisions_enabled=True`
4. **Next scheduler run**: The new coin is automatically included in the news fetch

## Testing

To verify the fix is working:

1. **Check base coins are initialized**:
   - Restart your backend server
   - Look for log message: `✅ Base coins initialized`

2. **Add a coin from Community Tips**:
   - Open the frontend dashboard
   - Click the "Community Tips" button
   - Find a trending coin (e.g., SOL, DOGE, etc.)
   - Click "Add [COIN] to Trading"
   - Wait for success message

3. **Verify it's in the database**:
   ```bash
   # Check via API
   curl http://localhost:8000/api/coins
   ```

4. **Wait for next AI fetch cycle (15 minutes max)**:
   - Watch server logs for: `🤖 AI Auto-fetch starting at...`
   - Should see: `📊 Found X enabled coins: BTC, ETH, XRP, VIRTUAL, [YOUR_NEW_COIN]`
   - Should see: `✅ Auto-fetch completed for [YOUR_NEW_COIN]: ...`

5. **Check the coin's AI decision**:
   ```bash
   # Get AI decision for the new coin
   curl "http://localhost:8000/api/ai/decision?coin=SOL"
   ```

## Files Modified

- `/Users/rileymartin/tradingbot/app/server.py`
  - Added `initialize_base_coins()` function
  - Updated `ai_auto_fetch_job()` to query database
  - Made `last_ai_fetch` dictionary dynamic

## Benefits

✅ **Automatic**: Coins added via Community Tips now automatically get news fetched every 15 minutes  
✅ **Scalable**: Can add unlimited coins without modifying code  
✅ **Persistent**: Coin settings are stored in database, survive server restarts  
✅ **Configurable**: Each coin has its own `ai_decisions_enabled` flag

## Next Steps (Optional Enhancements)

- [ ] Add API endpoint to enable/disable AI decisions for specific coins
- [ ] Add frontend UI to toggle `ai_decisions_enabled` per coin
- [ ] Add statistics showing last fetch time per coin in the UI
- [ ] Consider fetching more frequently for high-priority coins

---

**Status**: ✅ **FIXED**  
**Date**: October 28, 2025  
**Verified**: Server starts successfully, no linting errors

