# 🤖 AI News Trading Bot

## Overview

This AI-powered trading bot monitors cryptocurrency news in real-time and uses GPT-4 to analyze sentiment and generate trading signals automatically.

---

## 🎯 How It Works

```
Live News → AI Analysis → Trading Signal → Automatic Execution
    ↓            ↓              ↓                ↓
NewsAPI      GPT-4 AI      BUY/SELL         Binance Order
CoinGecko    Sentiment     Confidence       Position Sized
             Analysis      75%+ = Trade      Risk Managed
```

---

## 🔑 Required API Keys

### 1. NewsAPI (Free Tier: 100 requests/day)
1. Go to: https://newsapi.org/
2. Sign up for free account
3. Copy your API key
4. Add to `.env`: `NEWSAPI_KEY=your_key_here`

### 2. OpenAI API (Pay-as-you-go)
1. Go to: https://platform.openai.com/
2. Create account / Sign in
3. Go to API Keys section
4. Create new key
5. Add to `.env`: `OPENAI_API_KEY=your_key_here`

**Cost:** ~$0.01-0.05 per news analysis (very cheap!)

---

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install manually:
pip install openai requests

# Update .env file with API keys
nano .env
```

### Add to .env:
```bash
# AI News Trading
OPENAI_API_KEY=sk-proj-your_key_here
NEWSAPI_KEY=your_newsapi_key_here

# News Trading Configuration
NEWS_MIN_CONFIDENCE=75
NEWS_CHECK_INTERVAL=300
NEWS_MAX_ARTICLES=5
NEWS_TRADE_AMOUNT=100
```

---

## 🧪 Test the System

### Test 1: News Monitor
```bash
python3 news_monitor.py
```
**Should show:** Latest crypto news from NewsAPI + trending coins

### Test 2: AI Analyzer
```bash
python3 ai_analyzer.py
```
**Should show:** AI analysis of a test news article

### Test 3: Full Strategy
```bash
python3 strategies/ai_news_strategy.py
```
**Should show:** Complete news analysis + trading signal

---

## 🚀 Using in Dashboard

### 1. Add AI News Bot in Dashboard:
1. Open dashboard: `http://your_server:5000`
2. Click **"➕ Add New Bot"**
3. Settings:
   - **Name:** "AI News Trader"
   - **Symbol:** BTCUSDT (or any coin)
   - **Strategy:** Select **"AI News Trading"**
   - **Trade Amount:** $100 (or your preference)
4. Click **"Create Bot"**
5. Click **"▶ Start"**

### 2. Bot Will:
- ✅ Check news every 5 minutes
- ✅ Analyze with GPT-4
- ✅ Trade on high-confidence signals (>75%)
- ✅ Log all analyses and trades

---

## 📊 Strategy Configuration

Edit `strategies/ai_news_strategy.py`:

```python
# Minimum confidence to trade
self.min_confidence = 75  # 75% = conservative, 60% = aggressive

# Articles to analyze per cycle (cost control)
self.max_articles_per_cycle = 5  # 5 = ~$0.05 per check

# Check interval (seconds)
self.check_interval = 300  # 300 = every 5 minutes
```

---

## 💰 Cost Estimates

### NewsAPI:
- **Free Tier:** 100 requests/day = ~20 checks/day
- **Paid:** $449/month for unlimited

### OpenAI GPT-4o-mini:
- **Per Analysis:** ~$0.01
- **5 articles/check:** ~$0.05
- **Checks per day (20):** ~$1.00/day = $30/month
- **GPT-4 (more powerful):** ~$0.10/analysis = $10/day

**Total Monthly Cost (conservative):**
- NewsAPI: $0 (free tier)
- OpenAI: ~$30/month
- **Total: ~$30/month**

---

## 📈 Example Analysis

**News:** "Bitcoin ETF approved by SEC"

**AI Analysis:**
```json
{
  "signal": "BUY",
  "confidence": 92,
  "sentiment": "bullish",
  "impact": "high",
  "reasoning": "Major regulatory approval likely to drive institutional adoption",
  "symbols": ["BTCUSDT"],
  "urgency": "immediate"
}
```

**Action:** 
- ✅ Confidence > 75% → **EXECUTE BUY**
- 📊 Position size: $100 (configured amount)
- 🛡️ Stop loss: 3%
- 🎯 Take profit: 5%

---

## 🎛️ Advanced Configuration

### Customize News Sources

Edit `news_monitor.py`:
```python
def fetch_crypto_news(self, symbols=['BTC', 'ETH', 'SOL', 'AVAX']):
    # Add your preferred coins
    ...
```

### Customize AI Prompt

Edit `ai_analyzer.py`:
```python
prompt = f"""
Your custom prompt here...
Consider your specific trading style...
"""
```

### Risk Management

Edit trading amounts based on confidence:
```python
# In ai_news_strategy.py
if confidence > 90:
    trade_amount *= 1.5  # Increase size for high confidence
elif confidence < 80:
    trade_amount *= 0.5  # Reduce size for lower confidence
```

---

## 🔍 Monitoring

### View Live Logs:
```bash
# Bot logs
screen -r bot_X  # Replace X with bot ID
tail -f bot_1_20251007.log

# See recent analyses
python3 -c "
from strategies.ai_news_strategy import AINewsStrategy
import os
strategy = AINewsStrategy(
    newsapi_key=os.getenv('NEWSAPI_KEY'),
    openai_key=os.getenv('OPENAI_API_KEY')
)
for a in strategy.get_recent_analyses():
    print(f'{a[\"article\"]} -> {a[\"analysis\"][\"signal\"]}')
"
```

### Dashboard Metrics:
- **Articles Analyzed:** Count of news analyzed
- **Buy Signals:** Number of buy recommendations
- **Sell Signals:** Number of sell recommendations
- **Avg Confidence:** Average AI confidence level

---

## ⚠️ Important Notes

### 1. API Key Security
- **NEVER** share your API keys
- **NEVER** commit `.env` to git
- Regenerate keys if accidentally exposed

### 2. Cost Control
- Free NewsAPI = 100 requests/day
- Limit `max_articles_per_cycle` to control OpenAI costs
- Monitor usage at: https://platform.openai.com/usage

### 3. Trading Risks
- AI can be wrong!
- News may be outdated/fake
- Always use stop losses
- Start with small amounts
- Test on testnet first

### 4. Latency
- News analysis takes ~2-5 seconds
- Not suitable for scalping
- Best for short-term swing trades

---

## 🐛 Troubleshooting

### "No news found"
- Check NewsAPI key is valid
- Verify you're within free tier limit (100/day)
- Try broader search terms

### "AI analysis failed"
- Check OpenAI API key
- Verify account has credits: https://platform.openai.com/usage
- Check for rate limits (60 requests/minute)

### "Bot not trading"
- News may not meet confidence threshold (75%)
- Check recent analyses: are signals HOLD?
- Lower `min_confidence` to be more aggressive
- Increase news check frequency

### API Errors
```bash
# Test APIs individually
python3 news_monitor.py  # Test NewsAPI
python3 ai_analyzer.py   # Test OpenAI
```

---

## 📚 Example .env File

```bash
# Binance
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
USE_TESTNET=false

# AI News Trading
OPENAI_API_KEY=sk-proj-your_openai_key
NEWSAPI_KEY=your_newsapi_key

# News Strategy Settings
NEWS_MIN_CONFIDENCE=75
NEWS_CHECK_INTERVAL=300
NEWS_MAX_ARTICLES=5

# Trading
TRADE_AMOUNT=0.001
STOP_LOSS_PERCENT=3.0
TAKE_PROFIT_PERCENT=5.0
```

---

## 🎯 Quick Start Checklist

- [ ] Get NewsAPI key (https://newsapi.org/)
- [ ] Get OpenAI API key (https://platform.openai.com/)
- [ ] Add keys to `.env` file
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Test: `python3 news_monitor.py`
- [ ] Test: `python3 ai_analyzer.py`
- [ ] Test: `python3 strategies/ai_news_strategy.py`
- [ ] Add bot in dashboard
- [ ] Start bot and monitor!

---

## 🚀 What's Next?

Want to enhance your AI trading bot? Consider:

1. **Add Twitter/X Integration** - Real-time tweets
2. **Add Reddit Sentiment** - Community analysis
3. **Technical + News Combo** - Combine with TA indicators
4. **Multi-timeframe** - Short-term news + long-term trends
5. **Backtesting** - Test strategy on historical news

---

**Happy AI Trading! 🤖📈**

Questions? Issues? Check the logs or test individual components!
