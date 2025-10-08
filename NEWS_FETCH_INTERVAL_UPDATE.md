# 📰 News Fetch Interval Changed: Hourly → Every 15 Minutes

## **What Changed:**

✅ **Old behavior:** Bots fetched news every **1 hour** (3600 seconds)  
✅ **New behavior:** Bots fetch news every **15 minutes** (900 seconds)

---

## **Why You Were Seeing Cached Analysis:**

### **Your Logs:**
```
05:24:24 - Bot fetched fresh news + AI analysis
05:39:28 - Bot using "cached analysis (15 minutes old)"
```

### **The Problem:**

Your bots **check every 15 minutes** (set in `integrated_trader.py`), but the strategy was configured to fetch news every **1 hour**:

```
05:24 - Bot checks → 60 min elapsed → ✅ Fetch fresh news
05:39 - Bot checks → 15 min elapsed → ❌ Use cache (not time yet)
05:54 - Bot checks → 30 min elapsed → ❌ Use cache (not time yet)
06:09 - Bot checks → 45 min elapsed → ❌ Use cache (not time yet)
06:24 - Bot checks → 60 min elapsed → ✅ Fetch fresh news
```

So your bots were checking **4 times per hour** but only fetching news **once per hour**.

### **The Fix:**

Changed `news_fetch_interval` from `3600` to `900` seconds:

```python
# OLD:
self.news_fetch_interval = 3600  # 1 hour

# NEW:
self.news_fetch_interval = 900   # 15 minutes
```

Now your bots will fetch fresh news **every time they check**:

```
05:24 - Bot checks → 15 min elapsed → ✅ Fetch fresh news
05:39 - Bot checks → 15 min elapsed → ✅ Fetch fresh news
05:54 - Bot checks → 15 min elapsed → ✅ Fetch fresh news
06:09 - Bot checks → 15 min elapsed → ✅ Fetch fresh news
```

---

## **⚠️ CRITICAL: API Usage Impact**

### **CryptoNews API Limit:**

You mentioned you have **3 calls per day** for CryptoNews API.

### **Current Usage (After This Update):**

With 5 bots (BTC, ETH, BNB, DOGE, SOL) fetching every 15 minutes:

```
Calls per hour per bot: 4
Calls per day per bot: 4 × 24 = 96
Total calls per day (5 bots): 96 × 5 = 480 calls/day

Your limit: 3 calls/day
Your usage: 480 calls/day
OVERAGE: 477 calls/day ❌❌❌
```

**This will INSTANTLY hit your API limit!**

---

## **Solutions:**

### **Option 1: Shared News Cache Across Bots** ⭐ (Recommended)

Instead of each bot fetching independently, create a **shared news service** that fetches once and all bots read from it.

**Implementation:**
```bash
# Create a news caching service
nano /root/tradingbot/shared_news_cache.py
```

```python
# shared_news_cache.py
import json
import os
from datetime import datetime, timedelta
import requests

class SharedNewsCache:
    def __init__(self):
        self.cache_file = 'shared_news_cache.json'
        self.api_key = os.getenv('CRYPTONEWS_API_KEY')
        self.fetch_interval = 28800  # 8 hours (3 calls/day)
        
    def get_news(self, ticker):
        """Get cached news for a ticker or fetch if stale"""
        cache = self._load_cache()
        
        # Check if we have fresh cache for this ticker
        if ticker in cache:
            last_fetch = datetime.fromisoformat(cache[ticker]['timestamp'])
            age = (datetime.now() - last_fetch).total_seconds()
            
            if age < self.fetch_interval:
                print(f"📋 Using cached news for {ticker} ({age/3600:.1f}h old)")
                return cache[ticker]['articles']
        
        # Fetch fresh news
        print(f"📰 Fetching fresh news for {ticker}...")
        articles = self._fetch_from_api(ticker)
        
        # Update cache
        cache[ticker] = {
            'timestamp': datetime.now().isoformat(),
            'articles': articles
        }
        self._save_cache(cache)
        
        return articles
    
    def _fetch_from_api(self, ticker):
        """Fetch from CryptoNews API"""
        try:
            url = "https://cryptonews-api.com/api/v1"
            params = {
                'tickers': ticker,
                'items': 10,
                'page': 1,
                'token': self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return []
    
    def _load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self, cache):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
```

**Then modify `ticker_news_strategy.py`:**
```python
# In __init__:
from shared_news_cache import SharedNewsCache
self.news_cache = SharedNewsCache()

# In fetch_ticker_news():
return self.news_cache.get_news(self.ticker)
```

**Result:**
- Each ticker fetched **3 times per day** (every 8 hours)
- All bots for same ticker share the cache
- Total: **3 calls/day** ✅
- Each bot still checks every 15 min, but uses cached news

---

### **Option 2: Fetch Different Intervals Per Bot**

```python
# Bot 1 (BTC): Fetch at 00:00, 08:00, 16:00
# Bot 2 (ETH): Fetch at 01:00, 09:00, 17:00
# Bot 3 (BNB): Fetch at 02:00, 10:00, 18:00
# Bot 4 (DOGE): Fetch at 03:00, 11:00, 19:00
# Bot 5 (SOL): Fetch at 04:00, 12:00, 20:00

# Total: 3 calls/day per bot = 15 calls/day
```

Still over the limit, but more manageable.

---

### **Option 3: Reduce News Fetch Frequency** (Simple)

Change back to longer intervals:

```python
# Every 8 hours (3 calls/day per bot = 15 total)
self.news_fetch_interval = 28800

# Every 12 hours (2 calls/day per bot = 10 total)  
self.news_fetch_interval = 43200

# Every 24 hours (1 call/day per bot = 5 total)
self.news_fetch_interval = 86400
```

**Downside:** Bots will use cached analysis most of the time.

---

### **Option 4: Priority Tickers Only**

Only fetch news for your **top 2-3 coins**:

```python
# In ticker_news_strategy.py:
PRIORITY_TICKERS = ['BTC', 'SOL', 'ETH']

if self.ticker not in PRIORITY_TICKERS:
    # Use very long cache (24 hours) for low-priority coins
    self.news_fetch_interval = 86400
else:
    # Fetch every 8 hours for priority coins
    self.news_fetch_interval = 28800
```

**Result:**
- BTC, SOL, ETH: 3 calls/day each = 9 calls
- BNB, DOGE: 1 call/day each = 2 calls
- Total: 11 calls/day (still over, but better)

---

### **Option 5: Upgrade CryptoNews API Plan** 💰

If you need real-time news trading, consider upgrading:

- **Free:** 3 calls/day
- **Paid plans:** Usually 100-1000+ calls/day

Check: https://cryptonews-api.com/pricing

---

## **Recommended Approach:**

**For Your 3 Calls/Day Limit:**

1. **Implement Option 1 (Shared Cache)** ⭐
   - Fetch each ticker **once every 8 hours** (3 times/day)
   - All bots check every 15 min but use shared cache
   - Total: ~15 API calls/day (5 tickers × 3 calls)

2. **Or use Option 3 (8-hour interval)**
   - Set `self.news_fetch_interval = 28800`
   - Each ticker fetched 3 times/day
   - Total: 15 API calls/day

**Either way, you'll exceed 3 calls/day unless:**
- You only track 1 ticker (3 calls/day)
- Or fetch once per day per ticker (5 calls/day)

---

## **How to Revert to Hourly (If Needed):**

If you want to go back to hourly fetching:

```bash
ssh root@134.199.159.103
cd /root/tradingbot

# Edit the file
nano strategies/ticker_news_strategy.py

# Line 37, change:
self.news_fetch_interval = 900  # Change this

# To:
self.news_fetch_interval = 3600  # 1 hour (was original)
# Or:
self.news_fetch_interval = 28800  # 8 hours (3 calls/day per bot)

# Save: Ctrl+X, Y, Enter

# Restart bots
pkill -f "integrated_trader.py"
screen -X -S dashboard quit
screen -dmS dashboard python3 advanced_dashboard.py
```

---

## **Deploy Current Changes:**

```bash
ssh root@134.199.159.103
cd /root/tradingbot

# Pull the update
git pull origin main

# Restart bots to use new interval
pkill -f "integrated_trader.py"
screen -X -S dashboard quit
screen -dmS dashboard python3 advanced_dashboard.py

# View logs
screen -r dashboard

# You'll now see:
# 📰 Fetching news for SOL...
# (every 15 minutes instead of hourly)
```

---

## **Monitor API Usage:**

### **Check CryptoNews API Dashboard:**

Go to your CryptoNews API account and monitor your usage:
- https://cryptonews-api.com/dashboard

Watch for:
- Calls remaining today
- Rate limit warnings
- 429 errors in logs

### **In Bot Logs:**

You'll see errors if you hit the limit:

```bash
screen -r dashboard

# Look for:
❌ Error fetching news for BTC: 429 Client Error: Too Many Requests
```

If you see this, immediately switch to **Option 3 (longer intervals)** or implement **Option 1 (shared cache)**.

---

## **Summary:**

### **What Happened:**
- Bots checked every 15 min but fetched news every 60 min
- You saw "cached analysis (15 minutes old)" messages
- Fixed by changing fetch interval to 15 minutes

### **New Behavior:**
- Bots now fetch fresh news every 15 minutes
- No more cached analysis messages
- **But this will use 480 API calls/day (way over your 3/day limit!)**

### **What You Need to Do:**

1. **Deploy the change** (done above)
2. **Monitor API usage** (check CryptoNews dashboard)
3. **If you hit limits**, implement **Shared Cache** (Option 1) or **longer intervals** (Option 3)

### **Quick Fix for 3 Calls/Day:**

Change line 37 to:
```python
self.news_fetch_interval = 28800  # 8 hours = 3 calls/day
```

This gives you:
- Fresh news 3 times per day
- Bots still check every 15 min (use cached data between fetches)
- Within your API limit ✅

---

**Your bots will now be much more responsive to news, but watch your API usage!** 📊⚠️
