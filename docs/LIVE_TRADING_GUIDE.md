# 🚀 Live Trading Guide

## ⚠️ IMPORTANT WARNINGS

**Before you start:**
1. ✅ **Backtest First** - Test your strategy thoroughly
2. ✅ **Use Testnet** - Practice with fake money first
3. ✅ **Start Small** - Begin with minimum amounts
4. ✅ **Understand Risks** - You can lose money
5. ✅ **Never Risk More** - Than you can afford to lose

---

## Quick Start - 3 Steps

### Step 1: Deploy Your Bot

```bash
python3 live_trader.py
```

**Configuration:**
- Choose strategy (1-6)
- Enter symbol (e.g., BTCUSDT)
- Set trade amount (e.g., $100)
- Set check interval (e.g., 60 seconds)

### Step 2: Monitor in Real-Time

**Open a second terminal** and run:

```bash
python3 dashboard.py
```

This shows you:
- Current balance
- Open positions
- Recent trades
- Profit/loss

### Step 3: Stop When Needed

In the **live_trader terminal**, press `Ctrl+C`

The bot will:
- ✅ Close any open positions
- ✅ Save all trades
- ✅ Show summary

---

## Configuration

Edit `.env` file:

```bash
# API Keys
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# IMPORTANT: Start with testnet!
USE_TESTNET=true    # true = testnet (fake money)
                     # false = mainnet (REAL money!)

# Trading Parameters (optional)
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0
```

---

## Safety Features

### 1. Stop Loss
Every position automatically has a stop loss:
- **Simple Profitable**: 5% fixed
- **Other strategies**: Based on ATR (2-4x)

### 2. Take Profit
Every position has a take profit target:
- **Simple Profitable**: 10% fixed (2:1 ratio)
- **Other strategies**: Based on ATR (4-8x)

### 3. Emergency Stop
Press `Ctrl+C` in the live_trader terminal to stop immediately.

### 4. Position Limits
The bot only trades with the amount you specify, never more.

---

## Using Testnet (HIGHLY RECOMMENDED)

### What is Testnet?
- Fake Binance account
- Fake money
- Real market data
- Perfect for practice!

### Setup Testnet:

1. **Get Testnet API Keys:**
   - Go to: https://testnet.binance.vision/
   - Create account
   - Generate API keys

2. **Configure:**
   ```bash
   # In .env file
   BINANCE_API_KEY=your_testnet_key
   BINANCE_API_SECRET=your_testnet_secret
   USE_TESTNET=true
   ```

3. **Test Everything:**
   ```bash
   python3 live_trader.py
   # It's all fake money - perfect for learning!
   ```

---

## Live Trading Workflow

### 1. Backtest (30 minutes)

```bash
# Test your strategy
python3 quick_backtest.py

# Find best combination
python3 test_all_combinations.py
```

**Look for:**
- ✅ Return > +5%
- ✅ Win rate > 50%
- ✅ Profit factor > 1.5

### 2. Testnet (1-7 days)

```bash
# Set USE_TESTNET=true in .env
python3 live_trader.py
```

**Monitor for:**
- How many trades per day
- Actual win rate
- Behavior in different market conditions

### 3. Mainnet (Real Money)

**Only after:**
- ✅ Successful backtests
- ✅ 1+ weeks on testnet
- ✅ Consistent profits on testnet
- ✅ You understand the strategy

```bash
# Set USE_TESTNET=false in .env
python3 live_trader.py
# START WITH SMALL AMOUNTS!
```

---

## Monitoring Your Bot

### Dashboard (Real-Time)

```bash
python3 dashboard.py
```

**Shows:**
- 💰 Current balance
- 📊 Open positions
- 📈 Recent trades
- ⏱️ Bot runtime

Refreshes every 5 seconds.

### Log Files

Detailed logs saved to:
```
live_trading_YYYYMMDD.log
```

**Contains:**
- Every trade
- Every signal
- All decisions
- Errors and warnings

**View live:**
```bash
tail -f live_trading_20231015.log
```

---

## Setting Trade Amounts

### Conservative Approach:
- Start with $10-50 per trade
- Use 1-2% of total capital
- Increase slowly

### Moderate Approach:
- $100-500 per trade
- Use 5% of total capital
- Monitor closely

### Aggressive Approach:
- $500+ per trade
- Use 10% of total capital
- **High risk!**

### Example:

**Capital: $1,000**
- Conservative: $20 per trade
- Moderate: $50 per trade
- Aggressive: $100 per trade

**Capital: $10,000**
- Conservative: $200 per trade
- Moderate: $500 per trade
- Aggressive: $1,000 per trade

---

## Stopping & Withdrawing

### Stopping the Bot:

**Method 1: Clean Stop**
```bash
# In live_trader terminal
Press Ctrl+C

Bot will:
1. Close open position
2. Save all trades
3. Show summary
```

**Method 2: Emergency Stop**
```bash
# Force stop
Press Ctrl+C twice

Then manually close position on Binance if needed
```

### Withdrawing Funds:

1. **Stop the bot first** (Ctrl+C)
2. **Go to Binance.com**
3. **Wallet → Spot → Withdraw**
4. **Send to your wallet**

---

## Strategy Selection

### For Live Trading, Recommended:

**1. Simple Profitable ⭐**
- Best for beginners
- Works on all coins
- Balanced risk/reward
- 10-20 trades per month

**2. Conservative**
- Very selective
- High win rate
- 5-15 trades per month
- Lower risk

### Not Recommended for Beginners:

- Breakout (high risk)
- Volatile Coins (complex)

---

## Common Issues

### "Insufficient balance"
→ Reduce trade amount or add more funds

### "API error"
→ Check API keys and permissions

### "No trades happening"
→ Strategy is waiting for good setup (normal)

### "Position not closing"
→ Check if stop loss/take profit are being hit
→ Check log file for details

---

## Best Practices

### ✅ Do:
- Start with testnet
- Use Simple Profitable strategy
- Start with small amounts
- Monitor regularly
- Keep logs
- Withdraw profits periodically

### ❌ Don't:
- Skip testnet
- Risk money you can't afford to lose
- Use entire balance per trade
- Leave bot unmonitored for days
- Trade without understanding strategy
- Panic during normal drawdowns

---

## Example Session

```bash
# Terminal 1: Run the bot
python3 live_trader.py
# Strategy: 1 (Simple Profitable)
# Symbol: BTCUSDT
# Amount: $100
# Interval: 60s

# Terminal 2: Monitor
python3 dashboard.py
# Symbol: BTCUSDT
# Refresh: 5s

# Watch the dashboard
# Bot is running automatically
# Press Ctrl+C in Terminal 1 to stop
```

---

## Performance Tracking

### Daily:
- Check dashboard
- Review trades in log
- Calculate P&L

### Weekly:
- Total trades
- Win rate
- Total profit/loss
- Compare to backtest

### Monthly:
- Overall performance
- Adjust strategy if needed
- Withdraw profits

---

## When to Stop/Change Strategy

**Stop if:**
- ❌ Losing more than 10% of capital
- ❌ Win rate drops below 30%
- ❌ Many consecutive losses (5+)
- ❌ Strategy not matching backtest

**Change strategy if:**
- Market conditions changed
- Current strategy underperforming
- Different coin needs different approach

---

## Emergency Contacts

**If something goes wrong:**
1. Stop the bot (Ctrl+C)
2. Go to Binance.com
3. Manually close positions if needed
4. Check account balance
5. Review logs to understand what happened

---

## Example `.env` Configuration

```bash
# Binance API
BINANCE_API_KEY=abc123...
BINANCE_API_SECRET=xyz789...

# Start with testnet!
USE_TESTNET=true

# Trading Parameters
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0

# Trading Symbol (optional, can set in launcher)
TRADING_SYMBOL=BTCUSDT
```

---

## Checklist Before Live Trading

- [ ] Backtested strategy (positive results)
- [ ] Tested on testnet for 1+ weeks
- [ ] Understand stop loss and take profit
- [ ] Set up monitoring dashboard
- [ ] Started with small amount
- [ ] Know how to stop the bot
- [ ] Have time to monitor
- [ ] Read all documentation
- [ ] Comfortable with potential losses
- [ ] Have realistic expectations

---

## Realistic Expectations

**Good Performance:**
- 5-10% per month
- 50-60% win rate
- Occasional losing streaks (normal)

**Excellent Performance:**
- 10-20% per month
- 60-70% win rate
- Profit factor > 2.0

**Warning Signs:**
- Consecutive losses
- Win rate < 40%
- Large drawdowns

**Remember:** Even good strategies have losing periods!

---

## Support

**Need help?**
1. Check log files
2. Review DOCUMENTATION.md
3. Test on testnet first
4. Start small on mainnet

---

**Trade safely and responsibly! 📈💰**
