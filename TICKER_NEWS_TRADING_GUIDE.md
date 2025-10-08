# 📰 **Ticker News Trading - Complete Guide**

## **✨ What's New**

Two major features added:

1. **🔄 One-Click Dashboard Restart** - Restart dashboard from the web UI
2. **📰 Ticker News Trading** - News-driven trading per ticker

---

## **Feature 1: One-Click Dashboard Restart 🔄**

### **What It Does:**
Restart your dashboard server with one click - no more SSH commands!

### **How to Use:**
```
1. Go to System tab in dashboard
2. Click "🔄 Restart Dashboard" button
3. Confirm the action
4. Dashboard restarts automatically
5. Page refreshes after 5 seconds
```

### **When to Use:**
- After pulling code updates from git
- When dashboard becomes unresponsive
- After changing .env configuration
- When you need a fresh start

### **What Happens:**
1. Dashboard stops current server
2. Starts new dashboard instance
3. Your browser auto-refreshes
4. All bots keep running (unaffected)

---

## **Feature 2: Ticker News Trading 📰**

### **🎯 The Core Concept:**

**Old Way (Technical Strategies):**
- Bot looks at price charts
- Uses RSI, MACD, etc.
- Makes decisions based on patterns
- No awareness of news events

**NEW Way (News-Driven):**
- Bot tracks ONE specific ticker (BTC, ETH, SOL, etc.)
- Fetches news for that ticker every hour
- AI analyzes news sentiment
- Bot trades based on what's happening in the world!
- Manages its own allocated capital

---

## **📊 How It Works**

### **Step-by-Step Flow:**

```
You create bot → Select ticker (e.g., BTC)
   ↓
Bot fetches BTC-specific news (hourly)
   ↓
AI analyzes sentiment (bullish/bearish/neutral)
   ↓
AI decides: BUY, SELL, or HOLD
   ↓
Bot executes trade (if confidence high enough)
   ↓
Bot manages position (stop-loss, take-profit)
   ↓
Repeat every hour
```

### **Example:**

```
Hour 1: 📰 News: "Bitcoin ETF approval expected!"
        🤖 AI: "Bullish sentiment (85% confidence)"
        ✅ Action: BUY $200 of BTC @ $60,000

Hour 2: 📰 News: "BTC holds strong above $61K"
        🤖 AI: "Positive but already in position"
        ⏸️  Action: HOLD (monitoring)

Hour 3: 📰 News: "Profit-taking begins after rally"
        🤖 AI: "Bearish sentiment (75% confidence)"
        🔴 Action: SELL BTC @ $63,000
        💰 Profit: +$100 (+5%)

Hour 4: 📰 News: "Market consolidation expected"
        🤖 AI: "Neutral sentiment"
        ⏸️  Action: HOLD in cash, wait for signal
```

---

## **🚀 Creating a News Trading Bot**

### **Step 1: Click "Add New Bot"**

### **Step 2: Fill Out Form**

```
┌────────────────────────────────────┐
│ ➕ Add New Trading Bot             │
├────────────────────────────────────┤
│ Bot Name:                          │
│ [BTC News Trader_____________]     │
│                                    │
│ Strategy:                          │
│ [📰 Ticker News Trading ▼]         │
│ (NEWS-DRIVEN) ⭐ NEW!              │
│                                    │
│ Select Ticker: 📰 News for ticker  │
│ [BTC - Bitcoin ▼]                  │
│                                    │
│ Allocated Capital:                 │
│ [200] USDT                         │
│ 💡 Total USDT this bot manages     │
│                                    │
│ [Cancel]  [Create Bot]             │
└────────────────────────────────────┘
```

### **Step 3: Start the Bot**

Click ▶ Start and bot begins:
- Fetching news for your ticker
- Analyzing with AI
- Trading based on sentiment

---

## **📈 Available Tickers**

```
BTC   - Bitcoin
ETH   - Ethereum  
SOL   - Solana
XRP   - Ripple
ADA   - Cardano
DOGE  - Dogecoin
MATIC - Polygon
DOT   - Polkadot
AVAX  - Avalanche
LINK  - Chainlink
```

Each ticker gets news independently!

---

## **🤖 AI Decision Making**

### **What the AI Considers:**

1. **Overall Sentiment**
   - Positive, Negative, or Neutral news?
   - How strong is the sentiment?

2. **News Urgency**
   - Is this breaking news?
   - Does it require immediate action?

3. **Multiple Perspectives**
   - What do different sources say?
   - Are there conflicting reports?

4. **Market Implications**
   - How will this affect price?
   - Short-term or long-term impact?

5. **Risk Assessment**
   - How risky is this trade?
   - What could go wrong?

### **Confidence Thresholds:**

```
BUY Signal:  70%+ confidence required
SELL Signal: 60%+ confidence required
HOLD:        Below thresholds
```

Conservative approach - bot only trades when confident!

---

## **🛡️ Risk Management**

### **Automatic Protection:**

**Stop Loss: 3%**
- If position loses 3%, auto-sell
- Protects your capital

**Take Profit: 5%**
- If position gains 5%, auto-sell
- Locks in profit

**Max Hold Time: 48 hours**
- If holding 48+ hours, auto-sell
- Prevents getting stuck

**News-Based Exits:**
- If negative news appears, can sell early
- AI continuously monitors sentiment

---

## **⏰ Hourly News Cycle**

### **How News Fetching Works:**

```
12:00 PM - Fetch news for BTC
           Analyze with AI
           Make trading decision

1:00 PM  - Check price movements
           Apply stop-loss/take-profit
           Wait for next news cycle

2:00 PM  - Fetch fresh news for BTC
           Analyze with AI
           Make trading decision

...and so on
```

### **Why Hourly?**

- **API Limits:** CryptoNews API limited (3 calls/day per ticker)
- **Quality Over Quantity:** Better to analyze thoroughly than rush
- **Cost Effective:** Fewer OpenAI API calls
- **Still Responsive:** 1 hour is fast enough for news-driven trading

---

## **💰 Bot Wallet Display**

### **What You See:**

```
┌───────────────────────────────────┐
│ 🤖 BTC News Trader    🟢 RUNNING │
├───────────────────────────────────┤
│ 📈 BTCUSDT                        │
│ 🎯 TICKER NEWS TRADING            │
├───────────────────────────────────┤
│ 💰 BOT WALLET                     │
│ Allocated:     $200.00            │
│ Current Value: $210.00            │
│ ─────────────────────            │
│ USDT:          $0.00              │
│ BTC:           0.00350 ($210.00)  │
├───────────────────────────────────┤
│ TRADES: 3  │ P&L: +$10  │ ROI: 5%│
└───────────────────────────────────┘
```

Always know:
- How much you gave bot (Allocated)
- What it's worth now (Current Value)
- What it's holding (USDT vs crypto)
- How much profit it made (P&L & ROI)

---

## **🔍 Detailed Bot View (Click Bot Card)**

### **Investment Breakdown:**
- Initial allocated capital
- Any additional funds added
- Total investment

### **News Analysis:**
- Latest news headlines analyzed
- AI sentiment (Bullish/Bearish/Neutral)
- Confidence levels
- Trading signals generated

### **Trade History:**
- All BUY/SELL decisions
- Timestamps
- Profit/loss per trade
- News that triggered each trade

### **Live Logs:**
- News fetch timestamps
- AI analysis results
- Trade executions
- Position updates

---

## **📊 Multiple News Trading Bots Example**

```
Your Portfolio: $1,000 USDT

┌────────────────────────────────┐
│ 🤖 BTC News Trader             │
│ Ticker: BTC                    │
│ Allocated: $400                │
│ Current:   $420 (+5%)          │
│ News: "ETF approval bullish"   │
│ AI: BUY signal (80%)           │
└────────────────────────────────┘

┌────────────────────────────────┐
│ 🤖 ETH News Trader             │
│ Ticker: ETH                    │
│ Allocated: $300                │
│ Current:   $315 (+5%)          │
│ News: "Ethereum scaling update"│
│ AI: HOLD signal (85%)          │
└────────────────────────────────┘

┌────────────────────────────────┐
│ 🤖 SOL News Trader             │
│ Ticker: SOL                    │
│ Allocated: $200                │
│ Current:   $188 (-6%)          │
│ News: "Network issues reported"│
│ AI: SELL signal (90%)          │
└────────────────────────────────┘

Unallocated: $100 USDT (reserve)
```

Each bot:
- Tracks its own ticker independently
- Gets its own news feed
- Makes its own decisions
- Manages its own capital
- No interference with other bots!

---

## **🎯 Strategy Comparison**

### **Technical Strategies (Old):**
```
Strategy: Simple Profitable
Based on: RSI, MACD, price patterns
Trades when: Technical indicators align
Advantage: Fast, quantitative
Limitation: Blind to news events
```

### **News Trading (NEW!):**
```
Strategy: Ticker News Trading
Based on: Real news + AI sentiment
Trades when: Significant news occurs
Advantage: Event-aware, contextual
Limitation: Limited by news frequency
```

### **When to Use Each:**

**Use Technical Strategies For:**
- Stable markets
- Frequent trading
- Short-term scalping
- No major news expected

**Use News Trading For:**
- Volatile markets
- Major events (ETFs, regulations, etc.)
- Longer-term holds
- Fundamental analysis

**Best Approach: Combine Both!**
- Run technical bots for BTC, ETH
- Run news bots for same tickers
- Technical: Fast reactions to price
- News: Strategic reactions to events

---

## **🚀 Getting Started**

### **Quick Start:**

```bash
# 1. SSH to server
ssh root@134.199.159.103

# 2. Pull latest code
cd /root/tradingbot
git pull origin main

# 3. Restart dashboard
# NOW YOU CAN DO THIS FROM THE WEB UI!
# Go to System tab → Click "Restart Dashboard"
# Or manually:
screen -S dashboard -X quit
screen -dmS dashboard python3 advanced_dashboard.py

# 4. Open dashboard
# Go to: http://134.199.159.103:5001
# Hard refresh: Ctrl + Shift + R
```

### **Create Your First News Bot:**

```
1. Dashboard → ➕ Add New Bot
2. Strategy: Select "📰 Ticker News Trading"
3. Ticker: Select "BTC - Bitcoin"
4. Allocated Capital: 200 (USDT)
5. Bot Name: "BTC News Trader"
6. Click "Create Bot"
7. Click ▶ Start
8. Watch it trade!
```

---

## **⚙️ Configuration**

### **Environment Variables Needed:**

```bash
# In your .env file:

# CryptoNews API (for news)
CRYPTONEWS_API_KEY=your_key_here

# OpenAI API (for AI analysis)
OPENAI_API_KEY=your_key_here

# Binance API (for trading)
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
USE_TESTNET=false

# Twilio (optional, for SMS notifications)
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
```

### **API Usage:**

**CryptoNews API:**
- Limit: 3 calls/day per account
- Usage: 1 call per ticker per hour
- Max tickers: 3 (if 1 call/hour each)

**OpenAI API:**
- Each news fetch = 1 OpenAI call
- Hourly = ~24 calls/day per bot
- ~$0.01 per call = ~$0.24/day per bot

**Cost Example:**
- 1 bot = $0.24/day = $7.20/month
- 3 bots = $21.60/month (OpenAI)
- CryptoNews = Free (100 articles/day limit)

---

## **❓ FAQ**

### **Q: How is this different from AI Autonomous strategy?**
**A:**
- **AI Autonomous:** Scans ALL crypto news, picks coins dynamically
- **Ticker News:** Tracks ONE specific ticker you choose
- **Ticker News:** Hourly fetches (not continuous)
- **Ticker News:** You control which coins to trade

### **Q: Can I run multiple news bots for same ticker?**
**A:** Yes! Each bot is independent and trades separately.

### **Q: What if no news is found for my ticker?**
**A:** Bot holds current position and waits for next news cycle.

### **Q: Does bot trade 24/7?**
**A:** Bot checks hourly but only trades when AI sees strong signals.

### **Q: What happens if bot is wrong?**
**A:** Stop-loss (3%) limits losses. Bot exits quickly if wrong.

### **Q: Can I change the hourly interval?**
**A:** Yes, edit `news_fetch_interval` in `ticker_news_strategy.py` (default: 3600 seconds = 1 hour)

### **Q: Can I adjust confidence thresholds?**
**A:** Yes, edit `min_buy_confidence` and `min_sell_confidence` in strategy file (default: 70% buy, 60% sell)

### **Q: What news sources does it use?**
**A:** CryptoNews API - aggregates from multiple crypto news sources

### **Q: Can bot trade multiple tickers?**
**A:** No - each bot tracks ONE ticker. Create multiple bots for multiple tickers.

### **Q: Does it work with all cryptocurrencies?**
**A:** Works with major coins that have regular news coverage. Best for: BTC, ETH, SOL, XRP, ADA

---

## **🎨 Dashboard Features**

### **System Tab - New Button:**
```
┌─────────────────────────────────┐
│ 🖥️  Server Information          │
│ Python: 3.13.3                  │
│ Uptime: 2h 15m                  │
│ Working Dir: /root/tradingbot   │
│                                 │
│ [🔄 Restart Dashboard]          │ ← NEW!
│                                 │
│ Click to restart server         │
└─────────────────────────────────┘
```

### **Bot Creation - New Strategy:**
```
Strategy Dropdown:
├─ 📰 Ticker News Trading ⭐ NEW!
├─ Simple Profitable
├─ 🤖 AI Autonomous
├─ 🤖 AI News Trading
├─ Momentum
├─ Mean Reversion
├─ Breakout
├─ Conservative
└─ Volatile Coins
```

When "Ticker News Trading" selected:
- Symbol input → Hidden
- Ticker dropdown → Shown
- Pick from 10 major cryptocurrencies

---

## **📈 Best Practices**

### **1. Start Small**
```
First ticker bot: $100
Test for a week
See how it performs
Then scale up
```

### **2. Diversify Tickers**
```
Don't put all money on one ticker
Spread across BTC, ETH, SOL
Different news cycles
Different price movements
```

### **3. Monitor Daily**
```
Check what news bot fetched
Review AI analysis
Understand trading decisions
Learn from bot behavior
```

### **4. Combine Strategies**
```
BTC: 1 technical bot + 1 news bot
ETH: 1 technical bot + 1 news bot
Different approaches = better coverage
```

### **5. Use Stop Losses**
```
Default 3% stop-loss is good
Don't disable it
Protects against bad AI calls
Limits losses per trade
```

---

## **🔧 Troubleshooting**

### **Bot not trading:**
- Check if news is being fetched (view logs)
- Verify CryptoNews API key in .env
- Check if enough news articles found
- Bot might be waiting for stronger signals

### **"No news found" error:**
- Ticker might have limited news coverage
- Try BTC or ETH (more news available)
- Check API limit not exceeded

### **AI analysis failing:**
- Verify OpenAI API key in .env
- Check OpenAI account has credits
- Review logs for specific error

### **Dashboard won't restart:**
- SSH to server manually
- Check if screen session exists: `screen -ls`
- Manually restart: `./start_dashboard.sh`

---

## **🎉 Summary**

### **What You Got:**

1. ✅ One-click dashboard restart button
2. ✅ New ticker-based news trading strategy
3. ✅ Hourly news fetching per ticker
4. ✅ AI sentiment analysis
5. ✅ Automatic position management
6. ✅ Ticker dropdown in bot creation
7. ✅ Independent capital management per bot
8. ✅ Full wallet visibility

### **What This Means:**

- **No more SSH for dashboard restart!**
- **Trade based on real news, not just charts!**
- **Each bot watches one specific ticker!**
- **AI makes smart decisions based on events!**
- **Your money follows real-world developments!**

---

**Update your server now and start your first news trading bot!** 📰🤖💰
