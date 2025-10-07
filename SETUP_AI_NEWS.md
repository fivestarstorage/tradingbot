# 🚀 Quick Setup: AI News Trading Bot

## ✅ You're Almost Ready!

I've built you a complete AI news trading system. Here's how to set it up:

---

## 📋 Step 1: Add API Keys to .env

Edit your `.env` file and add these lines at the bottom:

```bash
# AI News Trading
OPENAI_API_KEY=your_openai_api_key_here
NEWSAPI_KEY=your_newsapi_key_here

# Optional Configuration
NEWS_MIN_CONFIDENCE=75
NEWS_CHECK_INTERVAL=300
NEWS_MAX_ARTICLES=5
```

### Get Your NewsAPI Key (FREE):
1. Go to: **https://newsapi.org/**
2. Click "Get API Key"
3. Sign up (free)
4. Copy your API key
5. Replace `get_your_free_key_from_newsapi.org` in `.env`

---

## 📦 Step 2: Install Dependencies

```bash
pip install openai requests

# Or install everything:
pip install -r requirements.txt
```

**On Server:**
```bash
pip3 install openai requests --break-system-packages
```

---

## 🧪 Step 3: Test It Works

```bash
# Test 1: News fetching
python3 news_monitor.py

# Test 2: AI analysis
python3 ai_analyzer.py

# Test 3: Full strategy
python3 strategies/ai_news_strategy.py
```

**Expected output:** Latest crypto news + AI analysis + trading signals!

---

## 🎯 Step 4: Deploy to Server

```bash
# From your local machine:
./sync_to_server.sh

# Then on server:
ssh root@134.199.159.103
cd /root/tradingbot

# Add API keys to .env on server:
nano .env
# (Add the same OpenAI and NewsAPI keys)

# Restart dashboard:
screen -X -S dashboard quit
screen -dmS dashboard python3 advanced_dashboard.py
```

---

## 🤖 Step 5: Create AI News Bot in Dashboard

1. Open: `http://134.199.159.103:5000`
2. Click **"➕ Add New Bot"**
3. Fill in:
   - **Name:** "AI News Trader"
   - **Symbol:** BTCUSDT
   - **Strategy:** **🤖 AI News Trading (GPT-4)**
   - **Amount:** $100
4. Click **"Create Bot"**
5. Click **"▶ Start"**

---

## 📊 How It Works

```
Every 5 minutes:
  1. Fetch latest crypto news (NewsAPI)
  2. Analyze each article with GPT-4
  3. Generate trading signal (BUY/SELL/HOLD)
  4. If confidence > 75% → Execute trade!
```

---

## 💰 Costs

- **NewsAPI:** FREE (100 requests/day)
- **OpenAI GPT-4o-mini:** ~$1/day (~$30/month)
- **Total:** ~$30/month

*Much cheaper than most trading signals subscriptions!*

---

## 🔍 Monitor Your Bot

```bash
# View bot logs
screen -r bot_1  # (or your bot ID)

# Detach: Ctrl+A then D

# Check log file
tail -f bot_1_20251007.log
```

**Look for:**
- `Checking news for BTCUSDT...`
- `Found X articles, analyzing...`
- `AI detected bullish news: ...`
- `🟢 OPENED POSITION...`

---

## ⚙️ Configuration

Edit `strategies/ai_news_strategy.py`:

```python
# How confident AI must be to trade
self.min_confidence = 75  # 60-90 recommended

# Articles to analyze (cost control)
self.max_articles_per_cycle = 5  # 3-10 recommended

# Check interval
self.check_interval = 300  # 300 = 5 minutes
```

---

## 🎯 What News Triggers Trades?

**BUY Signals:**
- ETF approvals
- Major partnerships
- Positive regulations
- Technical breakthroughs
- Institutional adoption

**SELL Signals:**
- Exchange hacks
- Regulatory crackdowns
- Security vulnerabilities
- Market manipulation news
- Negative adoption news

**HOLD:**
- Mixed signals
- Low-impact news
- Old/repeated news
- Low AI confidence

---

## 🐛 Troubleshooting

### "No news found"
→ Check NewsAPI key in `.env`
→ Verify free tier limit (100/day)

### "AI analysis failed"
→ Check OpenAI key in `.env`
→ Check credits: https://platform.openai.com/usage

### "Bot not trading"
→ News might not meet 75% confidence threshold
→ Check bot logs to see analyses
→ Lower `min_confidence` to be more aggressive

### Test APIs individually:
```bash
python3 news_monitor.py  # Test NewsAPI
python3 ai_analyzer.py   # Test OpenAI
```

---

## 📈 Example Trade Flow

**11:05 AM** - Bot checks news
```
Found 3 articles about Bitcoin
Analyzing with GPT-4...
```

**11:05:15 AM** - AI Analysis Complete
```
Article: "Bitcoin ETF Approved by SEC"
Signal: BUY
Confidence: 92%
Sentiment: Extremely Bullish
Impact: High
```

**11:05:20 AM** - Trade Executed
```
🟢 OPENED POSITION: BTCUSDT
Entry: $62,450
Quantity: 0.0016 BTC
Amount: $100
Stop Loss: $60,777 (-2.67%)
Take Profit: $65,573 (+5%)
```

**11:47 AM** - Take Profit Hit
```
🔴 CLOSED POSITION: BTCUSDT
Exit: $65,600
Profit: $5.05 (+5.05%)
```

---

## 🎉 You're All Set!

Your AI news trading bot is ready to go!

**Next Steps:**
1. ✅ Add NewsAPI key to `.env`
2. ✅ Test with `python3 news_monitor.py`
3. ✅ Test with `python3 ai_analyzer.py`
4. ✅ Deploy to server
5. ✅ Create bot in dashboard
6. ✅ Start trading!

---

## 🔐 Security Reminder

⚠️ **IMPORTANT:** Your OpenAI API key is visible in this file!

**After setup, regenerate your key:**
1. Go to: https://platform.openai.com/api-keys
2. Click "Revoke" on the old key
3. Create new key
4. Update `.env` with new key

This prevents unauthorized usage if this file is ever shared/leaked!

---

**Questions? Check `AI_NEWS_TRADING.md` for full documentation!**

Happy AI Trading! 🤖📈🚀
