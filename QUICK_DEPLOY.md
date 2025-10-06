# 🚀 Quick Deploy Guide

**Deploy your trading bot in 5 minutes!**

---

## Step 1: Test Your Strategy (2 minutes)

```bash
python3 quick_backtest.py
```

Choose a strategy that shows:
- ✅ Positive returns (>+5%)
- ✅ Win rate >50%
- ✅ Profit factor >1.5

**Recommended:** Strategy 1 (Simple Profitable)

---

## Step 2: Start with Testnet (1 minute)

Make sure `.env` has:
```bash
USE_TESTNET=true
```

This uses **fake money** - perfect for testing!

---

## Step 3: Deploy Bot (1 minute)

```bash
python3 live_trader.py
```

**Configuration:**
- Strategy: `1` (Simple Profitable)
- Symbol: `BTCUSDT`
- Amount: `$100`
- Interval: `60` seconds

Type `yes` to start!

---

## Step 4: Monitor (30 seconds)

**Option A: Terminal Dashboard**
```bash
# Open new terminal
python3 dashboard.py
```

**Option B: Web Dashboard**
```bash
# Open new terminal
python3 web_dashboard.py

# Then open browser:
# http://localhost:5000
```

---

## Step 5: Stop When Done (10 seconds)

In the `live_trader` terminal:
- Press `Ctrl+C`
- Bot closes positions
- Shows summary

---

## That's It! 🎉

You now have:
- ✅ Bot running on testnet
- ✅ Real-time monitoring
- ✅ Automatic trading
- ✅ Safe testing environment

---

## Going Live (After Testing)

**After 1+ weeks of successful testnet trading:**

1. Set `.env`:
   ```bash
   USE_TESTNET=false
   ```

2. **Start small** ($10-50 per trade)

3. Run:
   ```bash
   python3 live_trader.py
   ```

4. Monitor closely!

---

## Trade Amounts by Capital

| Your Capital | Conservative | Moderate | Aggressive |
|--------------|--------------|----------|------------|
| $1,000       | $20/trade    | $50      | $100       |
| $5,000       | $100/trade   | $250     | $500       |
| $10,000      | $200/trade   | $500     | $1,000     |

---

## Emergency Stop

**If things go wrong:**

1. Press `Ctrl+C` in live_trader
2. Bot closes positions automatically
3. Go to Binance.com if needed
4. Review logs

---

## Files You'll Use

- `live_trader.py` - Main trading bot
- `dashboard.py` - Terminal monitor
- `web_dashboard.py` - Browser monitor
- `live_trading_YYYYMMDD.log` - Detailed logs

---

## Quick Troubleshooting

**"Insufficient balance"**
→ Reduce trade amount

**"API error"**
→ Check API keys in `.env`

**"No trades"**
→ Normal - strategy is waiting

**Need help?**
→ Read `LIVE_TRADING_GUIDE.md`

---

**Happy Trading! 📈💰**
