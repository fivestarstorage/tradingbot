# 🤖 Automated Crypto Trading Bot

A professional, easy-to-use cryptocurrency trading bot with a beautiful web dashboard. Trade automatically on Binance with AI-powered strategies!

---

## ⚡ Quick Start (5 Minutes)

### 1️⃣ Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2️⃣ Configure Your Settings
```bash
# Copy the template
cp env_template.txt .env

# Edit .env and add your Binance API keys
# Get keys from: https://www.binance.com/en/my/settings/api-management
nano .env  # or use any text editor
```

### 3️⃣ Start the Dashboard
```bash
python3 simple_dash.py
```

### 4️⃣ Open Your Browser
Go to: **http://localhost:5001**

That's it! 🎉 You're ready to create your first trading bot!

---

## 📖 What Does This Bot Do?

This trading bot:
- ✅ **Trades automatically** on Binance 24/7
- ✅ **Multiple bots** - Run different strategies on different coins
- ✅ **AI-powered strategies** - Technical analysis + news sentiment
- ✅ **Risk management** - Automatic stop losses and take profits
- ✅ **Beautiful dashboard** - Monitor everything in real-time
- ✅ **Safe testing** - Start with Binance testnet (fake money!)

---

## 🎯 How It Works

### Simple Explanation

1. **You create a bot** through the web dashboard
   - Choose a coin (Bitcoin, Ethereum, Dogecoin, etc.)
   - Pick a strategy (AI news-based or technical analysis)
   - Set your investment amount

2. **Bot analyzes the market** every 15 minutes
   - Fetches latest price data from Binance
   - Uses your chosen strategy to analyze
   - Generates BUY, SELL, or HOLD signal

3. **Bot trades automatically**
   - If BUY signal: Bot buys the coin
   - If SELL signal: Bot sells and takes profit/loss
   - All trades are logged and visible in dashboard

4. **You monitor and profit** 📈
   - Watch real-time profits in the dashboard
   - See detailed logs for each bot
   - Get SMS alerts (optional)

---

## 🏗️ Project Structure

```
tradingbot/
├── simple_dash.py          ← Web dashboard (START HERE!)
├── integrated_trader.py    ← Bot engine (runs in background)
│
├── core/                   ← Core functionality
│   ├── binance_client.py   ← Talks to Binance API
│   └── config.py           ← Manages settings
│
├── strategies/             ← Trading strategies
│   ├── volatile_coins_strategy.py      ← Technical analysis
│   ├── ticker_news_strategy.py         ← AI + news sentiment
│   ├── simple_profitable_strategy.py   ← Balanced approach
│   └── ... (more strategies)
│
├── docs/                   ← Documentation
│   ├── SETUP.md           ← Detailed setup guide
│   ├── STRATEGIES.md      ← Strategy explanations
│   └── FAQ.md             ← Common questions
│
├── utils/                  ← Helper tools
│   ├── test_connection.py  ← Test Binance connection
│   └── backtest_runner.py  ← Test strategies on historical data
│
├── archive/                ← Old/backup files
└── .env                    ← Your settings (API keys, etc.)
```

---

## 🎮 Using the Dashboard

### Creating Your First Bot

1. **Click "Add Coin"** button
2. **Search for a coin**:
   - Click "Load Trending Coins" to see popular options
   - Or enter manually (e.g., `BTCUSDT` for Bitcoin)
3. **Choose a strategy**:
   - **Volatile Coins**: Pure technical analysis, good for any coin
   - **Ticker News**: AI-powered with news sentiment, best for major coins
4. **Set trade amount**: Start with $50-100 minimum
5. **Click "Create Bot"**

### Starting a Bot

1. Find your bot in the dashboard
2. Click the **"Start"** button
3. Bot will begin analyzing every 15 minutes
4. Watch the countdown timer to see when it checks next

### Monitoring Bots

- **Overview cards** show total balance, profit, and running bots
- **Each bot card** displays:
  - Current status (running/stopped)
  - Budget allocated
  - Number of trades made
  - Profit/loss so far
  - Next check countdown
- **Click "View"** to see:
  - Detailed logs
  - Profit chart over time
  - Current position info

### Stopping a Bot

1. Click the **"Stop"** button
2. Bot will stop checking for signals
3. Any open position remains open
   - You can restart the bot to manage the position
   - Or manually sell on Binance

---

## 📊 Available Strategies

### 1. Volatile Coins Strategy
**Best for:** Any cryptocurrency, especially altcoins

**How it works:**
- Pure technical analysis (RSI, MACD, Bollinger Bands)
- Looks for momentum and volatility
- Quick entries and exits
- No news required

**When to use:** Default choice for most coins

---

### 2. Ticker News Strategy (AI-Powered)
**Best for:** Major coins (BTC, ETH, BNB, etc.)

**How it works:**
- Fetches latest crypto news from CryptoNews API
- Uses OpenAI to analyze sentiment
- Combines technical analysis + news sentiment
- Only trades when both agree

**When to use:** When you want smarter, news-aware trading

**Requirements:**
- OpenAI API key (in .env)
- CryptoNews API key (in .env)

---

### 3. Simple Profitable Strategy
**Best for:** Beginners, stable coins

**How it works:**
- Balanced technical indicators
- Conservative entry/exit rules
- Higher win rate, lower frequency

**When to use:** When you want steady, reliable trades

---

## ⚙️ Configuration (.env file)

### Required Settings

```bash
# Binance API Credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# IMPORTANT: Start with testnet!
USE_TESTNET=true  # true = fake money, false = real money
```

### Optional Settings

```bash
# Trading Defaults
TRADING_SYMBOL=BTCUSDT          # Default coin
TRADE_AMOUNT=0.001              # Default trade size
CHECK_INTERVAL=900              # How often to check (seconds)

# Risk Management
STOP_LOSS_PERCENT=2.0           # Auto-sell if drops 2%
TAKE_PROFIT_PERCENT=5.0         # Auto-sell if gains 5%

# SMS Notifications (optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
YOUR_PHONE_NUMBER=+1987654321

# AI News Trading (optional)
OPENAI_API_KEY=your_openai_key
CRYPTONEWS_API_KEY=your_cryptonews_key
```

---

## 🛡️ Safety & Risk Management

### Start Safe!

1. **Always use testnet first**
   - Set `USE_TESTNET=true` in .env
   - Test for at least 1 week
   - Learn how everything works

2. **Start with small amounts**
   - $50-100 per bot initially
   - Increase only after proven success
   - Never risk money you can't afford to lose

3. **Monitor daily**
   - Check the dashboard at least once per day
   - Review bot logs regularly
   - Stop bots if losing consistently

### Automatic Risk Controls

Each bot automatically:
- ✅ Sets stop loss (default 2% loss = auto-sell)
- ✅ Sets take profit (default 5% gain = auto-sell)
- ✅ Only holds ONE position at a time
- ✅ Saves position state (survives restarts)
- ✅ Logs every action for review

---

## 📱 SMS Alerts (Optional)

Get text messages when your bots make trades!

### Setup

1. Sign up at [Twilio.com](https://www.twilio.com)
2. Get a phone number (free trial available)
3. Add credentials to .env:
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE_NUMBER=+1234567890
   YOUR_PHONE_NUMBER=+1987654321
   ```
4. Restart dashboard

### What You'll Get

- 6-hour trading summaries
- Total trades, buys, sells
- Current positions
- Profit/loss updates

Click **"Send Alert"** in dashboard to test!

---

## 🔧 Troubleshooting

### "API key not found" Error
**Solution:** Add your Binance API keys to the `.env` file

### Bot won't start
**Solution:** 
1. Check if `screen` is installed: `screen --version`
2. Check bot logs: `cat bot_1.log`
3. Verify Binance connection: `python3 utils/test_connection.py`

### No trades happening
**Solution:** This is normal! Strategies are selective and wait for good setups.
- Check logs to see what signals are generated
- Bot checks every 15 minutes
- May take hours/days for first trade

### Bot keeps restarting
**Solution:** Check logs for errors. Common issues:
- Insufficient USDT balance
- Invalid API keys
- Symbol not available on Binance

### Dashboard shows "calculating..." for countdown
**Solution:** Bot hasn't logged any activity yet. Wait 15 minutes for first check.

---

## 🚀 Advanced Features

### Backtesting Strategies

Test strategies on historical data before live trading:

```bash
python3 utils/backtest_runner.py
```

Follow prompts to:
- Choose a strategy
- Select a coin
- Set timeframe
- See results with profit metrics

### Multiple Bots

You can run unlimited bots simultaneously:
- Different strategies on the same coin
- Same strategy on different coins
- Different amounts per bot
- Each bot logs separately

### Position Persistence

Bots remember their positions across restarts:
- Saves position data to `bot_X_position.json`
- Restarts don't lose your open trades
- Can safely restart crashed bots

---

## 📚 Documentation

Detailed guides in the `docs/` folder:

- **[SETUP.md](docs/SETUP.md)** - Detailed setup instructions
- **[STRATEGIES.md](docs/STRATEGIES.md)** - Strategy deep-dive
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - How everything works
- **[FAQ.md](docs/FAQ.md)** - Frequently asked questions

---

## ⚠️ Important Warnings

### This is Not Financial Advice

- Trading cryptocurrency is risky
- You can lose all your invested money
- Past performance doesn't guarantee future results
- This bot is provided as-is, no warranties

### Security

- **Never share your API keys**
- Keep your `.env` file private
- Don't commit `.env` to Git
- Use API key restrictions on Binance:
  - Enable: Reading, Spot Trading
  - Disable: Withdrawals, Margin, Futures

### Realistic Expectations

- **Good months:** 5-15% returns
- **Bad months:** -5% to -10% losses
- **Average:** 2-7% per month
- Not a "get rich quick" scheme
- Requires monitoring and patience

---

## 🤝 Support & Community

### Need Help?

1. Check the [FAQ](docs/FAQ.md)
2. Review bot logs: `cat bot_1.log`
3. Test connection: `python3 utils/test_connection.py`
4. Start with testnet and small amounts

### Contributing

Found a bug or want to improve the bot?
- Submit issues and pull requests
- Share your custom strategies
- Help improve documentation

---

## 📜 License

MIT License - Use at your own risk

---

## 🎓 Learning Resources

### Cryptocurrency Trading
- [Binance Academy](https://academy.binance.com)
- [Investopedia - Technical Analysis](https://www.investopedia.com/technical-analysis-4689657)

### Python & Development
- [Python for Beginners](https://www.python.org/about/gettingstarted/)
- [Flask Web Framework](https://flask.palletsprojects.com/)

### APIs Used
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [OpenAI API](https://platform.openai.com/docs)
- [CryptoNews API](https://cryptonews-api.com/)

---

## 📈 Success Tips

1. **Start Small**
   - Test with $50-100 first
   - Increase only after consistent profits
   - Never risk more than 5% of your portfolio per bot

2. **Diversify**
   - Run multiple bots on different coins
   - Use different strategies
   - Don't put all money in one bot

3. **Be Patient**
   - Good strategies take time
   - Don't panic on first loss
   - Review performance weekly, not hourly

4. **Keep Learning**
   - Study your bot logs
   - Understand why trades happened
   - Adjust strategies based on market conditions

5. **Stay Informed**
   - Follow crypto news
   - Understand market trends
   - Know when to pause trading (major events)

---

## 🚦 Quick Command Reference

```bash
# Start Dashboard
python3 simple_dash.py

# Test Binance Connection
python3 utils/test_connection.py

# View Bot Logs
cat bot_1.log
tail -f bot_1.log  # Live view

# Stop All Bots
# Use dashboard's Stop button, or:
screen -ls  # List running bots
screen -S bot_1 -X quit  # Stop specific bot

# Backtest Strategy
python3 utils/backtest_runner.py
```

---

**Happy Trading! 🚀💰**

Remember: Start with testnet, start small, stay informed, and never risk more than you can afford to lose!

