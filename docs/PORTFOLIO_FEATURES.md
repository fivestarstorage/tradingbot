# 🎯 New Features: AI Insights & Portfolio Management

## Overview

Your trading bot now has TWO powerful strategies working together:

### 1. **News-Based Trading** (Existing)
- Monitors crypto news every 5 minutes
- Generates AI signals for coins on your watchlist
- Recommends BUY/SELL for **new opportunities**

### 2. **Portfolio Management** (NEW!)
- Monitors coins you **already own**
- Analyzes news + technical indicators (price candles)
- Makes HOLD/SELL/BUY_MORE decisions
- Manages your existing positions

### 3. **AI Market Insights** (NEW!)
- Generates a summary after each run
- Provides actionable recommendations
- Displayed on your dashboard

---

## 📊 How Portfolio Management Works

Every 5 minutes, for each coin you hold (SOL, XRP, etc.):

### Step 1: Gather Data
- **Current holdings**: How much you own
- **Price data**: Last 50 candles (5-minute intervals)
- **Technical indicators**: SMA-20, SMA-50, volume, price changes
- **News**: Recent articles mentioning the coin

### Step 2: AI Analysis
OpenAI analyzes:
- Is there positive/negative news?
- Is the price trending up or down?
- Is volume increasing (momentum)?
- Should we take profits or cut losses?

### Step 3: Generate Recommendation
- **SELL**: Take profits (10%+ gain) or cut losses (5%+ drop with bad news)
- **HOLD**: Maintain position (neutral sentiment)
- **BUY_MORE**: Add to position (strong conviction, 85%+ confidence)

### Step 4: Optional Auto-Execute
If `PORTFOLIO_AUTO_MANAGE=true`, trades execute automatically at 75%+ confidence.

---

## 🔧 Configuration

Add to `/Users/rileymartin/tradingbot/.env`:

```bash
# Enable automatic portfolio management
PORTFOLIO_AUTO_MANAGE=false  # Set to 'true' to auto-execute

# Amount to add when buying more of an existing position
PORTFOLIO_ADD_USDT=25  # Default: $25

# Existing settings still work
AUTO_TRADE=false  # For news-based signals
AUTO_TRADE_USDT=25  # For new coins from watchlist
WATCHLIST=BTC,ETH,SOL,XRP,DOGE
```

### Safety Settings

**Recommended for testing:**
```bash
PORTFOLIO_AUTO_MANAGE=false  # Manual mode - recommendations only
AUTO_TRADE=false              # Manual mode for new signals
```

**For automated trading:**
```bash
PORTFOLIO_AUTO_MANAGE=true  # Auto-execute portfolio trades
AUTO_TRADE=true              # Auto-execute new opportunities
```

---

## 📈 Example Scenario

### You Own SOL

**5-Minute Cycle Runs:**

1. **Fetch News**: Finds 3 positive articles about Solana
2. **Get Price Data**: SOL up 2% in last hour, strong volume
3. **AI Analysis**:
   - News sentiment: Positive
   - Technical momentum: Bullish
   - Current value: $150 (you hold 1 SOL)
   - **Recommendation**: HOLD (85% confidence)
   - **Reasoning**: "Positive momentum with supportive news. Hold position."

4. **Result**: No action taken (HOLD)

### Later: SOL Jumps 12%

1. **Price Data**: SOL now $168 (+12% from your entry)
2. **AI Analysis**:
   - Profit achieved: 12%
   - News: Still positive
   - **Recommendation**: SELL 50% (80% confidence)
   - **Reasoning**: "Take profits on strong gain while maintaining exposure."

3. **Result** (if auto-enabled): Sells 0.5 SOL, keeps 0.5 SOL

---

## 🤖 AI Market Insights

### What It Does

After each 5-minute cycle, AI generates:

```json
{
  "insight": "Market showing bullish sentiment with 8 positive signals. XRP leading momentum.",
  "recommendation": "Consider adding to XRP position or initiating new entry.",
  "confidence": 75
}
```

### Where to See It

- **Dashboard**: Displayed in "AI Insights" section
- **API**: `GET /api/ai/insight`
- **Logs**: Stored in `bot_logs` table (category: 'INSIGHT')

### How It Works

AI considers:
- Total news processed
- Number of bullish vs bearish signals
- Top trending coins
- Your portfolio recommendations
- Recent price action

Then provides a **concise 2-3 sentence insight** and **specific action**.

---

## 📊 New API Endpoints

### 1. Get AI Market Insight
```bash
GET http://localhost:8000/api/ai/insight
```

Response:
```json
{
  "insight": "Market analysis text",
  "recommendation": "Specific action",
  "confidence": 75,
  "generated_at": "2025-10-25T10:30:00"
}
```

### 2. Get Portfolio Recommendations
```bash
GET http://localhost:8000/api/portfolio/recommendations
```

Response:
```json
[
  {
    "symbol": "SOLUSDT",
    "action": "HOLD",
    "reasoning": "Positive momentum with supportive news",
    "timestamp": "2025-10-25T10:30:00"
  }
]
```

---

## 📋 Dashboard Updates

### "AI Insights" Section Now Shows:

**Before** (old summary):
```
Last run: 10:25 AM
🟢 5 🔴 2 ⚪ 3
```

**After** (with new insights):
```
Last run: 10:25 AM
🟢 5 🔴 2 ⚪ 3

💡 AI Insight:
Market showing bullish sentiment with 8 positive signals. 
XRP leading momentum.

Recommendation: Consider adding to XRP position (75% confidence)
```

---

## 🎮 How to Use

### Testing Mode (Recommended First)

1. **Update .env**:
```bash
PORTFOLIO_AUTO_MANAGE=false
AUTO_TRADE=false
```

2. **Restart backend**:
```bash
cd /Users/rileymartin/tradingbot
./stop_all.sh
./start.sh
```

3. **Wait 5 minutes** or force refresh:
```bash
curl -X POST http://localhost:8000/api/runs/refresh
```

4. **Check dashboard** for:
   - AI Insights (new recommendations)
   - Portfolio analysis in logs
   - Signals for new opportunities

### Automated Mode (After Testing)

1. **Enable auto-trading**:
```bash
PORTFOLIO_AUTO_MANAGE=true  # For existing holdings
AUTO_TRADE=true              # For new opportunities
AUTO_TRADE_CONFIDENCE=75     # Minimum confidence
```

2. **Monitor**: Check dashboard regularly
3. **Adjust**: Tune confidence levels based on results

---

## 📝 Logs & Monitoring

### Log Categories

Now logged with specific categories:

- **NEWS**: News fetch results
- **AI**: Signal generation
- **PORTFOLIO**: Portfolio analysis
- **TRADE**: Executed trades
- **INSIGHT**: Market insights

### View Logs

**API**:
```bash
curl http://localhost:8000/api/logs | jq '.[] | select(.type=="portfolio")'
```

**Database**:
```sql
SELECT * FROM bot_logs WHERE category = 'PORTFOLIO' ORDER BY created_at DESC LIMIT 10;
```

---

## 🎯 Strategy Summary

### For New Coins (Watchlist)
1. Monitor news for BTC, ETH, SOL, XRP (your watchlist)
2. Generate BUY signals when positive news
3. Execute if confidence ≥ 75% (if AUTO_TRADE=true)

### For Owned Coins (Portfolio)
1. Check each coin you hold
2. Analyze news + technical data
3. Recommend HOLD/SELL/BUY_MORE
4. Execute if confidence ≥ 75% (if PORTFOLIO_AUTO_MANAGE=true)

### AI Insights
1. Summarize market after each cycle
2. Provide actionable recommendation
3. Display on dashboard

---

## ⚠️ Important Notes

### Risk Management

- Portfolio manager uses **conservative** stop-losses (5% drop with bad news)
- Takes profits on **10%+ gains**
- Only adds to positions with **85%+ confidence**
- Respects your wallet balance limits

### When No News Available

If there's no recent news for a coin you own:
- Uses **pure technical analysis** (candles, volume, SMAs)
- More conservative recommendations
- Focuses on taking profits or cutting losses

### Upsert Behavior

News refresh **DOES upsert**:
- Updates existing articles with new sentiment
- Adds new articles
- **With timezone fix, dates will be corrected on next refresh**

---

## 🚀 Quick Start

```bash
# 1. Update configuration
nano /Users/rileymartin/tradingbot/.env
# Add: PORTFOLIO_AUTO_MANAGE=false (testing mode)

# 2. Restart backend
cd /Users/rileymartin/tradingbot
./stop_all.sh
./start.sh

# 3. Force a cycle to test
curl -X POST http://localhost:8000/api/runs/refresh

# 4. Check results
curl http://localhost:8000/api/ai/insight | jq
curl http://localhost:8000/api/portfolio/recommendations | jq

# 5. View dashboard
open http://localhost:8000
```

---

## 📚 Files Modified

- ✅ `app/portfolio_manager.py` - New portfolio management logic
- ✅ `app/server.py` - Integrated portfolio + insights
- ✅ `app/news_service.py` - Fixed timezone handling (upserts correctly)

## 🎉 Result

You now have a **complete trading bot** with:
- News-based opportunity discovery
- Portfolio risk management  
- AI-powered market insights
- Automated or manual execution
- Full transparency via logs

Happy trading! 🚀📈

