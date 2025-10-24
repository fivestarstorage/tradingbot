# 🌐 Advanced Trading Dashboard Guide

## Overview

The Advanced Trading Dashboard lets you:
- ✅ **Manage multiple trading bots** from one place
- ✅ **View all bots** and their performance
- ✅ **Start/stop/edit bots** with one click
- ✅ **Adjust trade amounts** for each bot
- ✅ **Monitor account balance** in real-time
- ✅ **View recent trades** across all bots
- ✅ **Add new bots** with different strategies

---

## Quick Start

### Local Testing

```bash
# Start the dashboard
./start_dashboard.sh

# Access at: http://localhost:5000
```

### On Your Server

```bash
# 1. Upload files
scp advanced_dashboard.py start_dashboard.sh root@YOUR_SERVER_IP:/root/tradingbot/

# 2. SSH to server
ssh root@YOUR_SERVER_IP

# 3. Start dashboard
cd /root/tradingbot
./start_dashboard.sh

# 4. Access from anywhere
# Open browser: http://YOUR_SERVER_IP:5000
```

---

## Dashboard Features

### 1. Account Overview
- **Available Balance**: Free USDT to trade with
- **In Orders**: USDT locked in active orders
- **Total Balance**: Your complete balance
- **Allocated to Bots**: Total amount assigned to running bots

### 2. Bot Management

#### Add New Bot
1. Click **"➕ Add New Bot"**
2. Fill in:
   - **Bot Name**: Give it a memorable name (e.g., "BTC Momentum")
   - **Symbol**: Trading pair (e.g., BTCUSDT)
   - **Strategy**: Choose from 6 strategies
   - **Trade Amount**: USDT per trade (e.g., 100)
3. Click **"Create Bot"**

#### Edit Bot
1. Click **"✏️ Edit"** on any bot
2. Change:
   - Bot name
   - Trade amount
3. Click **"Save Changes"**

#### Control Bots
- **▶ Start**: Activate bot trading
- **⏹ Stop**: Pause bot trading
- **🗑️ Delete**: Remove bot permanently

### 3. Bot Strategies

| Strategy | Best For | Risk |
|----------|----------|------|
| Simple Profitable (⭐) | General use, reliable | Medium |
| Momentum | Trending markets | Medium-High |
| Mean Reversion | Ranging markets | Medium |
| Breakout | Strong trends | High |
| Conservative | Low risk | Low |
| Volatile Coins | High volatility coins | Very High |

### 4. Trade History
View all recent trades from all bots in real-time.

---

## How to Adjust Trade Amounts

### For Existing Bots
1. Click **"✏️ Edit"** on the bot card
2. Change **Trade Amount** field
3. Click **"Save Changes"**

### For New Bots
Set the **Trade Amount** when creating the bot.

---

## How to Add/Withdraw Money

### View Balance
Your balance is shown at the top:
- **Available**: Ready to use
- **Total**: Complete balance

### Withdraw (Testnet)
In testnet, funds are free - just reset your account in Binance Testnet.

### Withdraw (Mainnet)
1. Log into Binance.com
2. Go to **Wallet → Fiat and Spot**
3. Click **Withdraw** next to USDT
4. Follow withdrawal process

### Deposit More
1. Log into Binance.com
2. Go to **Wallet → Fiat and Spot**
3. Click **Deposit** next to USDT
4. Follow deposit instructions

---

## Multiple Bots Example

You can run multiple bots simultaneously:

```
Bot 1: BTC Momentum
- Symbol: BTCUSDT
- Strategy: Simple Profitable
- Amount: $200
- Status: Running

Bot 2: ETH Conservative
- Symbol: ETHUSDT
- Strategy: Conservative
- Amount: $150
- Status: Running

Bot 3: SOL Breakout
- Symbol: SOLUSDT
- Strategy: Breakout
- Amount: $100
- Status: Stopped
```

**Total Allocated**: $350 (Bot 1 + Bot 2)

---

## Important Notes

### ✅ LIVE TRADING ENABLED!

🎉 **The dashboard now controls REAL trading bots!**

- **▶ Start Button**: Spawns actual trading process with real orders
- **⏹ Stop Button**: Stops the trading process immediately
- **Bot Status**: Shows if bot is actually running or stopped
- **Real-Time Data**: Shows actual balance and live trades

### How It Works

When you click **▶ Start**:
1. Dashboard spawns a `screen` session: `bot_1`, `bot_2`, etc.
2. Each bot runs independently with its own strategy
3. Bots place REAL orders on Binance
4. You can monitor logs: `screen -r bot_1`

When you click **⏹ Stop**:
1. Dashboard kills the bot's screen session
2. Trading stops immediately
3. Any open positions remain (close manually if needed)

### View Bot Logs

```bash
# List all running bots
screen -ls

# View bot logs
screen -r bot_1     # Bot ID 1
screen -r bot_2     # Bot ID 2

# Detach from logs (leave bot running)
# Press: Ctrl+A then D
```

---

## Troubleshooting

### Dashboard Won't Start
```bash
# Check if Flask is installed
python3 -c "import flask; print('OK')"

# Install if needed
pip3 install flask
# Or on server:
pip3 install flask --break-system-packages
```

### Can't Access Dashboard
```bash
# Make sure it's running
screen -ls

# Check if screen died (no dashboard in list)
# If died, check logs:
screen -dmS dashboard python3 advanced_dashboard.py
screen -r dashboard
# See the error message
```

### Port 5000 Already in Use
```bash
# Kill whatever is using it
lsof -ti:5000 | xargs kill -9

# Then restart dashboard
./start_dashboard.sh
```

### Dashboard Shows "Error"
- Check your `.env` file has valid API keys
- Make sure Binance API keys are activated
- Check if you're using testnet vs mainnet correctly

---

## Commands Reference

```bash
# Start dashboard (runs forever in background)
./start_dashboard.sh

# View dashboard logs
./view_dashboard.sh
# (Press Ctrl+A then D to detach)

# Stop dashboard
./stop_dashboard.sh

# Check what screens are running
screen -ls
```

---

## Access Points

**Local Machine:**
- http://localhost:5000
- http://127.0.0.1:5000

**Server (from any device):**
- http://YOUR_SERVER_IP:5000
- Example: http://134.199.159.103:5000

**Mobile:**
Works great on phones/tablets! Just use the server URL.

---

## Security Notes

⚠️ **Important for Production:**

1. **Firewall**: Consider restricting port 5000 to your IP only
2. **HTTPS**: Add SSL/TLS for encrypted connection
3. **Authentication**: Add password protection
4. **VPN**: Use a VPN to access your server

**For testnet**: Security is less critical (no real money).

---

## Next Features (Coming Soon)

- 🔐 Password authentication
- 📊 Performance charts and graphs
- 📧 Email/SMS alerts for trades
- 🤖 Actual bot execution from dashboard
- 💰 Direct deposit/withdrawal integration
- 📈 Advanced analytics and backtesting
- 🎯 Portfolio allocation optimizer

---

## Questions?

**Dashboard not showing correct data?**
→ Make sure your bot is running with `./start_bot.sh`

**Want more strategies?**
→ Check `STRATEGY_GUIDE.md` for strategy details

**Need deployment help?**
→ See `DEPLOYMENT_GUIDE.md` for full server setup

---

**Happy Trading! 🚀**
