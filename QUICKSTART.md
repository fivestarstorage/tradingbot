# ⚡ Quick Start Guide

Get your trading bot running in 5 minutes!

---

## Step 1: Install Dependencies (1 minute)

```bash
pip3 install -r requirements.txt
```

If you get errors:
- Make sure Python 3.8+ is installed
- Try: `python3 -m pip install -r requirements.txt`
- On Mac: May need `brew install python3`

---

## Step 2: Configure Settings (2 minutes)

### Create .env file

```bash
cp env_template.txt .env
```

### Get Binance API Keys

1. Go to: https://www.binance.com/en/my/settings/api-management
2. Click "Create API"
3. Give it a name like "TradingBot"
4. Click "Create"
5. Copy the **API Key** and **Secret Key**

### Edit .env file

Open `.env` in any text editor and add your keys:

```bash
# REQUIRED: Your Binance credentials
BINANCE_API_KEY=paste_your_api_key_here
BINANCE_API_SECRET=paste_your_secret_key_here

# IMPORTANT: Start with testnet (fake money!)
USE_TESTNET=true

# Optional: Change these if you want
TRADING_SYMBOL=BTCUSDT
TRADE_AMOUNT=100
```

**Save the file!**

---

## Step 3: Start Dashboard (30 seconds)

### Easy way:

```bash
chmod +x start.sh
./start.sh
```

### Manual way:

```bash
python3 simple_dash.py
```

You should see:
```
🤖 Starting Trading Bot Dashboard
🚀 Starting dashboard on http://localhost:5001
```

---

## Step 4: Open Browser (10 seconds)

Go to: **http://localhost:5001**

You should see your dashboard! 🎉

---

## Step 5: Create Your First Bot (2 minutes)

### In the Dashboard:

1. **Click "➕ Add Coin" button**

2. **Choose a coin:**
   - Click "Load Trending Coins"
   - Pick Bitcoin (BTCUSDT) or Ethereum (ETHUSDT)
   - Or type manually: `BTCUSDT`

3. **Select strategy:**
   - **Volatile Coins** - Good default choice
   - **Ticker News** - Needs OpenAI API key

4. **Set trade amount:**
   - $50 minimum (for testnet, any amount works)
   - Start small: $50-100

5. **Click "Create Bot"**

Your bot appears in the dashboard! ✅

---

## Step 6: Start Trading! (10 seconds)

1. Find your bot in the list
2. Click **"Start"** button
3. Bot begins analyzing every 15 minutes

Watch the countdown timer to see when it checks next!

---

## Step 7: Monitor Your Bot

### In the Dashboard:

- **Overview cards** show total balance, profit, bots running
- **Bot cards** show individual bot stats
- **Click "View"** to see:
  - Live logs
  - Profit chart
  - Position details

### Check Logs Manually:

```bash
# View bot log
cat bot_1.log

# Watch live updates
tail -f bot_1.log
```

---

## Common Questions

### "API key not found"
- Make sure you saved the `.env` file
- Check there are no extra spaces around the `=` sign
- API key should be inside the quotes

### "Bot won't start"
- Check if `screen` is installed: `screen --version`
- View logs: `cat bot_1.log`
- Make sure Binance keys are correct

### "No trades happening"
- **This is normal!** Bots wait for good setups
- Check logs to see signals: `cat bot_1.log`
- May take hours before first trade
- Bot checks every 15 minutes

### "How do I stop?"
- Click "Stop" button in dashboard
- Or run: `./stop-all-bots.sh`
- Or: `screen -S bot_1 -X quit`

---

## Next Steps

### Test on Testnet First!
- Keep `USE_TESTNET=true` in .env
- Test for at least 1 week
- Learn how everything works
- No risk since it's fake money!

### When Ready for Real Trading:
1. Change `.env`: `USE_TESTNET=false`
2. Restart dashboard
3. Create new bots
4. **Start with small amounts!** ($50-100)

### Monitor Daily:
- Check dashboard once per day
- Review bot logs weekly
- Stop bots if losing consistently

---

## Stop Everything

### Stop a Single Bot:
- Use "Stop" button in dashboard

### Stop All Bots:
```bash
./stop-all-bots.sh
```

### Stop Dashboard:
- Press `Ctrl+C` in terminal

---

## Troubleshooting

### "Port already in use"
Someone else is using port 5001. Edit `simple_dash.py`:
```python
# Change last line:
app.run(host='0.0.0.0', port=5002, debug=False)  # Use 5002 instead
```

### "Module not found"
Install dependencies again:
```bash
pip3 install -r requirements.txt
```

### "Screen not found"
Install screen:
```bash
# Mac
brew install screen

# Ubuntu/Debian
sudo apt-get install screen

# CentOS/RHEL
sudo yum install screen
```

---

## Important Safety Reminders

### Always Start with Testnet
- Use fake money first
- Test for 1-2 weeks
- Learn how it works
- NO RISK!

### Start Small
- $50-100 per bot initially
- Increase only after success
- Never risk more than you can lose

### Monitor Regularly
- Check dashboard daily
- Review logs weekly
- Stop if losing consistently

### Keep API Keys Safe
- Never share your keys
- Don't commit .env to Git
- Use Binance API restrictions

---

## What's Next?

### Learn More:
- **[README.md](README.md)** - Complete documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - How it all works
- **[docs/STRATEGIES.md](docs/STRATEGIES.md)** - Strategy details

### Advanced Features:
- Run multiple bots simultaneously
- Try different strategies
- Enable SMS notifications
- Backtest strategies on historical data

---

**You're all set! Happy trading! 🚀💰**

Remember: Start with testnet, start small, stay safe!

