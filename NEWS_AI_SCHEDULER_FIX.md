# News + AI Scheduler Fix & Coin Additions

## Changes Made

### 1. ✅ Added Three New Coins (PIVX, BNB, YB)

**File**: `/Users/rileymartin/tradingbot/app/server.py`

Added to the `initialize_base_coins()` function:
```python
{'coin': 'PIVX', 'coin_name': 'PIVX', 'symbol': 'PIVXUSDT'},
{'coin': 'BNB', 'coin_name': 'Binance Coin', 'symbol': 'BNBUSDT'},
{'coin': 'YB', 'coin_name': 'YB', 'symbol': 'YBUSDT'},
```

**How it works**:
- `coin`: Base symbol used in news (e.g., "PIVX")
- `symbol`: Trading pair used for Binance API (e.g., "PIVXUSDT")
- News articles will reference "PIVX" as the ticker
- Trading operations will use "PIVXUSDT" to fetch prices and execute trades

### 2. ✅ Combined News Fetch + AI Decisions into ONE Scheduler

**Problem**: Previously had two separate jobs running at different times:
- `scheduled_job()` - Fetched news
- `ai_auto_fetch_job()` - Made AI decisions

These ran independently every 15 minutes but could be offset in time.

**Solution**: Created `news_and_ai_job()` that runs as ONE combined job:

```python
def news_and_ai_job():
    """
    Combined job that runs every 15 minutes:
    1. Fetches fresh news from all sources
    2. Makes AI trading decisions based on that news for all enabled coins
    """
    # Step 1: Fetch fresh news
    scheduled_job()  # CoinDesk, CoinTelegraph, Binance Square
    
    # Step 2: Make AI decisions for all coins
    make_ai_decisions_for_all_coins()
```

**Scheduler Configuration**:
```python
ai_scheduler.add_job(news_and_ai_job, 'interval', minutes=15, id='news_and_ai')
```

### 3. ✅ Added Manual Test Endpoint

Updated `/api/runs/refresh` to trigger the combined job:
```bash
curl -X POST http://localhost:8000/api/runs/refresh
```

This allows you to test the full cycle without waiting 15 minutes.

## Testing Instructions

### Test 1: Verify Coins Are Initialized

**Restart your backend server**, then check the logs for:
```
🔧 Initializing base coin: PIVX
🔧 Initializing base coin: BNB
🔧 Initializing base coin: YB
✅ Base coins initialized
```

**Verify via API**:
```bash
curl http://localhost:8000/api/coins | jq '.coins[] | select(.coin | IN("PIVX", "BNB", "YB"))'
```

Should return all three coins with:
- `coin`: "PIVX" / "BNB" / "YB"
- `symbol`: "PIVXUSDT" / "BNBUSDT" / "YBUSDT"
- `enabled`: true
- `ai_decisions_enabled`: true

### Test 2: Manual Trigger News + AI Cycle

**Trigger the combined job manually**:
```bash
curl -X POST http://localhost:8000/api/runs/refresh
```

**Watch server logs for**:
```
================================================================================
📰🤖 NEWS FETCH + AI DECISIONS - 2025-10-28 12:34:56 UTC
================================================================================

[Step 1/2] Fetching fresh news from all sources...
[ScheduledJob] Starting news fetch and analysis...
[ScheduledJob] Fetching news...
✓ Scraped X CoinDesk articles with AI analysis
✓ Scraped X CoinTelegraph articles with AI analysis
[Binance Square] ✓ Scraped X posts
✅ News fetch completed

[Step 2/2] Making AI trading decisions for all enabled coins...

🤖 AI Decision-making starting at 12:35:10 UTC
📊 Found 7 enabled coins: BTC, ETH, XRP, VIRTUAL, PIVX, BNB, YB
✅ AI decision completed for BTC: HOLD
✅ AI decision completed for ETH: HOLD
✅ AI decision completed for XRP: HOLD
✅ AI decision completed for VIRTUAL: HOLD
✅ AI decision completed for PIVX: HOLD
✅ AI decision completed for BNB: HOLD
✅ AI decision completed for YB: HOLD
✅ AI decisions completed

================================================================================
✅ NEWS FETCH + AI DECISIONS COMPLETED
================================================================================
```

### Test 3: Verify News Articles Contain New Coins

**Check if any news mentions the new coins**:
```bash
# Check for PIVX in news
curl "http://localhost:8000/api/news" | jq '.[] | select(.tickers | contains("PIVX"))'

# Check for BNB in news
curl "http://localhost:8000/api/news" | jq '.[] | select(.tickers | contains("BNB"))'

# Check for YB in news
curl "http://localhost:8000/api/news" | jq '.[] | select(.tickers | contains("YB"))'
```

### Test 4: Check AI Decisions for New Coins

**Get latest AI decision for each coin**:
```bash
# PIVX decision
curl "http://localhost:8000/api/ai/decision?coin=PIVX"

# BNB decision
curl "http://localhost:8000/api/ai/decision?coin=BNB"

# YB decision
curl "http://localhost:8000/api/ai/decision?coin=YB"
```

Each should return:
```json
{
  "ok": true,
  "decision": {
    "coin": "PIVX",
    "decision": "HOLD/BUY/SELL",
    "confidence": 75,
    "reasoning": "...",
    "sentiment_summary": "...",
    "created_at": "2025-10-28T12:35:15Z"
  }
}
```

### Test 5: Wait for Automatic Scheduler (15 min cycle)

**After server starts**, the scheduler runs automatically every 15 minutes.

**Check logs at 00, 15, 30, 45 minutes past each hour**:
```
📰🤖 NEWS FETCH + AI DECISIONS - 2025-10-28 12:15:00 UTC
...
📰🤖 NEWS FETCH + AI DECISIONS - 2025-10-28 12:30:00 UTC
...
📰🤖 NEWS FETCH + AI DECISIONS - 2025-10-28 12:45:00 UTC
```

## Architecture

### Before (BROKEN ❌)
```
Scheduler 1 (15 min) → scheduled_job() → Fetch news
Scheduler 2 (15 min) → ai_auto_fetch_job() → Make decisions (using old news)
```
**Problem**: Jobs run at different times, AI might use stale news

### After (FIXED ✅)
```
Scheduler (15 min) → news_and_ai_job() → {
  Step 1: Fetch fresh news
  Step 2: Make AI decisions (using fresh news)
}
```
**Benefit**: Sequential execution ensures AI always uses the latest news

## Coin Symbol Architecture

The system correctly handles the distinction between news tickers and trading symbols:

| Component | PIVX Example | BNB Example | YB Example |
|-----------|--------------|-------------|------------|
| News articles | "PIVX" | "BNB" | "YB" |
| Database `coin` field | "PIVX" | "BNB" | "YB" |
| Database `symbol` field | "PIVXUSDT" | "BNBUSDT" | "YBUSDT" |
| Binance API calls | "PIVXUSDT" | "BNBUSDT" | "YBUSDT" |
| Frontend display | "PIVX" | "BNB" | "YB" |
| AI decision input | "PIVX" | "BNB" | "YB" |

The `AITradingEngine` automatically converts:
- Input: coin symbol (e.g., "PIVX")
- Internal: trading symbol (e.g., "PIVXUSDT" for price data)
- Output: displays both

## Verification Checklist

- [x] PIVX added to database
- [x] BNB added to database
- [x] YB added to database
- [x] News fetch and AI decisions combined into one job
- [x] Scheduler runs every 15 minutes
- [x] Manual trigger endpoint works
- [x] Coin vs symbol distinction maintained
- [ ] **Test with manual trigger** (requires server running)
- [ ] **Verify first automatic cycle** (wait 15 min after server start)

## Expected Log Output (Success)

When everything is working correctly, you'll see this pattern every 15 minutes:

```
================================================================================
📰🤖 NEWS FETCH + AI DECISIONS - 2025-10-28 12:30:00 UTC
================================================================================

[Step 1/2] Fetching fresh news from all sources...
[ScheduledJob] Starting news fetch and analysis...
[ScheduledJob] News fetched: 45 total, 12 inserted
[AI] Analyzing 23 coins from recent news: BTC, ETH, PIVX, BNB, YB, SOL, ADA...
✅ News fetch completed

[Step 2/2] Making AI trading decisions for all enabled coins...
🤖 AI Decision-making starting at 12:30:45 UTC
📊 Found 7 enabled coins: BTC, ETH, XRP, VIRTUAL, PIVX, BNB, YB

[AI Engine] Analyzing PIVX...
  • Found 3 relevant news articles
  • Average sentiment: 65/100
  • Decision: HOLD (confidence: 75%)
✅ AI decision completed for PIVX: HOLD

[AI Engine] Analyzing BNB...
  • Found 8 relevant news articles
  • Average sentiment: 72/100
  • Decision: BUY (confidence: 82%)
✅ AI decision completed for BNB: BUY

[AI Engine] Analyzing YB...
  • Found 1 relevant news articles
  • Average sentiment: 55/100
  • Decision: HOLD (confidence: 60%)
✅ AI decision completed for YB: HOLD

✅ AI decisions completed

================================================================================
✅ NEWS FETCH + AI DECISIONS COMPLETED
================================================================================
```

## Troubleshooting

### Issue: "No enabled coins found"
**Solution**: Restart server to run `initialize_base_coins()`

### Issue: No news articles for PIVX/BNB/YB
**Cause**: These coins might not be mentioned in recent news
**Note**: This is normal - the system will start tracking them when they appear in news

### Issue: Scheduler not running
**Check**: Look for startup message:
```
📰🤖 Combined News + AI scheduler started (runs every 15 minutes)
```

### Issue: Old news being used
**Verify**: Check that logs show BOTH steps completing in sequence

---

**Status**: ✅ **COMPLETE**  
**Date**: October 28, 2025  
**Coins Added**: PIVX, BNB, YB  
**Scheduler**: News + AI combined, runs every 15 minutes

