# Community Tips Feature 🎯

## Overview

The **Community Tips** feature scrapes Binance Square hashtag pages to identify trending cryptocurrencies based on community sentiment. It uses AI to analyze posts, extract coin mentions, and track sentiment over time with a decay mechanism.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. SCRAPING (Every 10 minutes)                             │
│     • Scrapes 3 Binance Square hashtags                     │
│     • Scrolls to load posts from last 10 minutes            │
│     • Extracts post content, timestamps, authors            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  2. AI ANALYSIS (OpenAI GPT-4)                              │
│     • Analyzes posts for coin mentions                      │
│     • Extracts sentiment (0-100) and enthusiasm (0-100)     │
│     • Identifies why coins are trending                     │
│     • Captures relevant post snippets                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  3. DATABASE STORAGE                                         │
│     • Stores/updates tips in `community_tips` table         │
│     • Tracks mention count over time                        │
│     • Applies weighted averaging for sentiment              │
│     • Fetches real-time price data from Binance             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  4. SENTIMENT DECAY                                          │
│     • Tips decay 5% every 10 minutes without reinforcement  │
│     • Ensures only actively discussed coins stay trending   │
│     • Decay factor: 0.1-1.0 (10% to 100%)                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  5. FRONTEND DISPLAY                                         │
│     • "Tips" button in dashboard header                     │
│     • Sidebar shows trending coins                          │
│     • Sortedby: sentiment × enthusiasm × decay              │
│     • Click for detailed view with price, opinions, etc.    │
└─────────────────────────────────────────────────────────────┘
```

## Components Created

### Backend

1. **Database Model** (`app/models.py`)
   - `CommunityTip` model with sentiment tracking
   - Stores coin data, sentiment scores, mentions, sources, price data
   - Includes decay mechanism

2. **Tips Service** (`app/tips_service.py`)
   - `TipsScraper` - Scrapes Binance Square hashtags with scroll
   - `extract_coins_with_ai()` - Uses OpenAI to analyze posts
   - `update_or_create_tip()` - Updates database with weighted averaging
   - `apply_sentiment_decay()` - Decays old tips
   - `fetch_and_analyze_tips()` - Main pipeline function
   - `get_top_tips()` - Retrieves sorted tips

3. **API Endpoints** (`app/server.py`)
   - `GET /api/tips` - Get all trending tips
   - `POST /api/tips/refresh` - Manually trigger refresh
   - `GET /api/tips/{coin}` - Get specific coin tip

### Frontend

1. **Tips Sidebar Component** (`app/components/TipsSidebar.tsx`)
   - Beautiful sidebar with tip cards
   - Shows sentiment scores, enthusiasm, prices
   - Detailed view with community opinions and post snippets
   - Refresh button to manually trigger scraping

2. **Main Dashboard Integration** (`app/page.tsx`)
   - "Tips" button added to header (with lightning bolt icon)
   - Opens sidebar when clicked

## Scraped URLs

The feature scrapes these 3 Binance Square hashtag pages:

1. **#WriteToEarnUpgrade**
   ```
   https://www.binance.com/en/square/hashtag/writetoearnupgrade?displayName=WriteToEarnUpgrade
   ```

2. **#MarketRebound**
   ```
   https://www.binance.com/en/square/hashtag/marketrebound?displayName=MarketRebound
   ```

3. **#CPIWatch**
   ```
   https://www.binance.com/en/square/hashtag/cpiwatch?displayName=CPIWatch
   ```

## Database Schema

```sql
CREATE TABLE community_tips (
    id INTEGER PRIMARY KEY,
    coin VARCHAR NOT NULL,
    coin_name VARCHAR,
    
    -- Sentiment tracking
    sentiment_score FLOAT DEFAULT 50.0,  -- 0-100
    sentiment_label VARCHAR,              -- BULLISH, BEARISH, NEUTRAL
    mention_count INTEGER DEFAULT 1,
    enthusiasm_score FLOAT DEFAULT 50.0,  -- 0-100
    
    -- Community opinion
    community_summary TEXT,
    trending_reason TEXT,
    
    -- Source tracking
    sources TEXT,          -- JSON array
    post_snippets TEXT,    -- JSON array
    
    -- Market data
    current_price FLOAT,
    price_change_24h FLOAT,
    volume_24h FLOAT,
    market_cap VARCHAR,
    
    -- Timestamps
    first_seen DATETIME,
    last_updated DATETIME,
    
    -- Decay mechanism
    decay_factor FLOAT DEFAULT 1.0
);
```

## Sentiment Calculation

### Initial Sentiment
When a coin is first mentioned:
```
sentiment_score = AI_extracted_sentiment (0-100)
enthusiasm_score = AI_extracted_enthusiasm (0-100)
mention_count = 1
decay_factor = 1.0
```

### Update (when seen again)
Weighted average: 70% new, 30% old
```
new_sentiment = (AI_sentiment × 0.7) + (old_sentiment × 0.3)
new_enthusiasm = (AI_enthusiasm × 0.7) + (old_enthusiasm × 0.3)
mention_count += 1
decay_factor = 1.0  // Reset decay
```

### Decay Over Time
Every 10 minutes without new mentions:
```
decay_factor = decay_factor × 0.95  // 5% decay
decay_factor = max(0.1, decay_factor)  // Minimum 10%
```

### Effective Sentiment (for sorting)
```
effective_sentiment = sentiment_score × decay_factor × (enthusiasm_score / 100)
```

Tips are sorted by `effective_sentiment` in descending order.

## Testing

Run the comprehensive test suite:

```bash
cd /Users/rileymartin/tradingbot
python3 test_tips_feature.py
```

This tests:
1. ✅ Binance Square scraper with scrolling
2. ✅ AI coin extraction
3. ✅ Database operations (create, update, retrieve)
4. ✅ Price data fetching from Binance API
5. ✅ Full pipeline (scrape → analyze → store)
6. ✅ API endpoints

## Running the Tips Service

### Automatic Scheduling (Built-in) ✨

The tips service **automatically runs every 10 minutes** when the backend server is running!

When you start the server:
```bash
cd /Users/rileymartin/tradingbot
python3 app/server.py
```

You'll see:
```
🤖 AI Auto-fetch scheduler started (runs every 15 minutes)
🎯 Tips Auto-fetch scheduler started (runs every 10 minutes)
[TipsScheduler] Running initial tips fetch on startup...
```

The scheduler will:
- ✅ Run immediately on startup (after 5 seconds)
- ✅ Run every 10 minutes automatically
- ✅ Log all activity to console
- ✅ Handle errors gracefully
- ✅ Apply sentiment decay automatically

**No cron jobs needed!** The scheduler is built into the backend server using APScheduler.

### Manual Refresh

You can also manually trigger a refresh:

**From the frontend:**
1. Click "Tips" button in dashboard header
2. Click "Refresh" button in sidebar
3. Wait 30-60 seconds for scraping and AI analysis
4. Tips will appear sorted by effective sentiment

**From API:**
```bash
curl -X POST http://localhost:8000/api/tips/refresh
```

**From terminal:**
```bash
cd /Users/rileymartin/tradingbot
python3 -c "
from app.db import get_db
from app.tips_service import fetch_and_analyze_tips
import os

db = next(get_db())
api_key = os.getenv('OPENAI_API_KEY')
fetch_and_analyze_tips(db, api_key)
"
```

## API Usage Examples

### Get All Tips
```bash
curl http://localhost:8000/api/tips?limit=20
```

Response:
```json
{
  "ok": true,
  "count": 15,
  "tips": [
    {
      "id": 1,
      "coin": "BTC",
      "coin_name": "Bitcoin",
      "sentiment_score": 85.5,
      "sentiment_label": "BULLISH",
      "mention_count": 12,
      "enthusiasm_score": 90.0,
      "community_summary": "Community is very bullish on BTC...",
      "trending_reason": "Strong support at 95k, breakout expected",
      "sources": ["#MarketRebound", "#CPIWatch"],
      "post_snippets": ["BTC to the moon! 🚀", "Strong buy signal"],
      "current_price": 96500.00,
      "price_change_24h": 2.5,
      "effective_sentiment": 77.0,
      ...
    }
  ]
}
```

### Get Specific Coin
```bash
curl http://localhost:8000/api/tips/BTC
```

### Refresh Tips
```bash
curl -X POST http://localhost:8000/api/tips/refresh
```

## Frontend Usage

1. **Open Dashboard**
   ```bash
   cd /Users/rileymartin/tradingbot-frontend
   npm run dev
   ```

2. **Navigate to http://localhost:3000**

3. **Click "Tips" Button** (yellow button with lightning bolt, left of coin selector)

4. **View Tips in Sidebar**
   - See all trending coins sorted by effective sentiment
   - Green = Bullish, Blue = Neutral, Red = Bearish
   - Shows sentiment score, enthusiasm score, mentions
   - Displays current price and 24h change
   - Shows why coin is trending and community opinion

5. **Click on a Tip** to see detailed view:
   - Full sentiment analysis
   - Community opinion summary
   - Why it's trending
   - User post snippets
   - Price details
   - Sources

6. **Refresh Tips**
   - Click "Refresh" button in sidebar
   - Triggers fresh scraping (takes 30-60 seconds)
   - Shows loading indicator

## Files Created/Modified

### New Files
- `app/tips_service.py` - Complete tips service
- `app/components/TipsSidebar.tsx` - Sidebar component
- `test_tips_feature.py` - Comprehensive test suite
- `migrate_db.py` - Database migration script
- `TIPS_FEATURE.md` - This documentation

### Modified Files
- `app/models.py` - Added `CommunityTip` model
- `app/server.py` - Added 3 tips API endpoints
- `app/page.tsx` - Added Tips button and sidebar integration

## Performance Notes

- **Scraping**: Takes ~30 seconds for all 3 hashtags (with scrolling)
- **AI Analysis**: Takes ~10-20 seconds per batch of posts
- **Total Refresh**: ~60-90 seconds for complete pipeline
- **Database**: Very fast (<1ms for retrievals)
- **Cron Job**: Run every 10 minutes, uses ~2-3 API tokens

## Limitations

1. **Rate Limits**: Binance Square may rate limit if scraped too frequently
2. **AI Costs**: Each refresh costs ~$0.01-0.02 in OpenAI API credits
3. **Selenium**: Requires Chrome/Chromium browser installed
4. **10-Minute Window**: Only scrapes posts from last 10 minutes
5. **Hashtag Dependency**: Only finds coins mentioned in configured hashtags

## Future Enhancements

1. Add more hashtag sources
2. Implement sentiment trend graphs (sentiment over time)
3. Add price alerts when high-sentiment coins dip
4. Integrate with AI trading decisions
5. Add user-customizable hashtags
6. Implement confidence scoring
7. Add social proof metrics (likes, shares)
8. Create mobile app notifications

## Troubleshooting

### Scheduler Not Running
- Check backend server logs for: `🎯 Tips Auto-fetch scheduler started`
- Look for `[TipsScheduler]` messages in console every 10 minutes
- Verify OPENAI_API_KEY environment variable is set
- Restart the backend server: `python3 app/server.py`

### Scraper Not Working
- Check Chrome/Chromium is installed: `which google-chrome` or `which chromium`
- Run with `headless=False` to see browser window
- Check Binance Square isn't rate limiting or blocking
- Verify network connection

### No Tips Appearing
- Check OPENAI_API_KEY is set: `echo $OPENAI_API_KEY`
- Wait 10 minutes for first scheduled run, or click "Refresh" in frontend
- Run test script to diagnose: `python3 test_tips_feature.py`
- Check database has `community_tips` table: `sqlite3 tradingbot.db ".tables"`
- Look at backend server console for `[TipsScheduler]` errors

### Frontend Not Showing Tips
- Check backend is running on port 8000: `curl http://localhost:8000/api/health`
- Open browser console (F12) for JavaScript errors
- Check Network tab for failed API calls
- Verify Tips button calls `/api/tips` endpoint
- Try manual refresh from frontend sidebar

### Scheduler Logs
Watch the console output when running the backend server:
```bash
# You should see these every 10 minutes:
[TipsScheduler] Starting community tips fetch...
📰 Scraping Binance Square hashtags...
✅ Scraped X total posts
🤖 Analyzing posts with AI...
✅ Found X trending coins
💾 Updating tips database...
[TipsScheduler] ✅ Tips updated successfully
```

## Support

For issues or questions:
1. Check backend server console for `[TipsScheduler]` logs
2. Run test suite: `python3 test_tips_feature.py`
3. Check database: `sqlite3 tradingbot.db "SELECT coin, sentiment_score, mention_count FROM community_tips;"`
4. Verify API: `curl http://localhost:8000/api/tips`
5. Check scheduler status: Look for startup messages in server console

---

**Built by**: Riley Martin's AI Trading Bot
**Version**: 1.0.0
**Date**: October 27, 2025

