# ⚡ Quick Start Guide - 5 Minutes to First Test

## Step 1: Install (30 seconds)

```bash
pip install -r requirements.txt
```

## Step 2: Configure (1 minute)

```bash
cp env_template.txt .env
```

Edit `.env` and add your Binance API keys:
```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
USE_TESTNET=false  # false = more data, true = safe testnet
```

**Get API keys:** https://www.binance.com/en/my/settings/api-management

## Step 3: Run Your First Test (30 seconds)

```bash
python3 quick_backtest.py
```

**Enter:**
- Strategy: `1` (Simple Profitable ⭐)
- Coin: `1` (Bitcoin)
- Timeframe: `3` (1h, 90 days)

**Wait ~30 seconds for results!**

---

## Understanding Your Results

```
BACKTEST RESULTS: Simple Profitable ⭐ on BTCUSDT
================================================================
Initial Capital:      $1000.00
Final Equity:         $1150.00
Total Return:         +15.00%         ← Profit!

Total Trades:         18               ← Number of trades
Winning Trades:       11 (61.1%)      ← Win rate
Profit Factor:        2.1              ← Risk/reward

✅ GOOD - Profitable strategy
```

**What's good?**
- ✅ Return > +5%
- ✅ Win rate > 50%
- ✅ Profit factor > 1.5

---

## What to Test Next

### Test Different Coins

```bash
python3 quick_backtest.py
```

Try:
- Coin 2: Ethereum
- Coin 4: Solana
- Coin 5: Dogecoin

### Test Different Strategies

```bash
python3 quick_backtest.py
```

Try:
- Strategy 4: Mean Reversion (good for volatile coins)
- Strategy 2: Enhanced Momentum (good for BTC/ETH)

### Find the Best Combination

```bash
python3 test_all_combinations.py
```

Choose mode 3, enter your favorite coin.
**It tests all 6 strategies and shows you which works best!**

---

## 6 Available Strategies

| # | Name | Best For | Trades |
|---|------|----------|--------|
| **1** | **Simple Profitable ⭐** | **All coins** | 10-20 |
| 2 | Enhanced Momentum | BTC, ETH | 20-40 |
| 3 | Volatile Coins | SOL, DOGE | 10-25 |
| 4 | Mean Reversion | Ranging markets | 15-30 |
| 5 | Breakout | Strong trends | 10-20 |
| 6 | Conservative | Risk-averse | 5-15 |

**Start with #1 (Simple Profitable) - it works on everything!**

---

## 10 Available Coins

### Large Cap (Stable)
1. Bitcoin (BTCUSDT)
2. Ethereum (ETHUSDT)
3. Binance Coin (BNBUSDT)
8. Cardano (ADAUSDT)
9. Ripple (XRPUSDT)

### High Volatility
4. Solana (SOLUSDT)
5. Dogecoin (DOGEUSDT)
6. Avalanche (AVAXUSDT)
7. Polygon (MATICUSDT)
10. Polkadot (DOTUSDT)

---

## 4 Timeframes

| Option | Interval | Days | Candles | Best For |
|--------|----------|------|---------|----------|
| 1 | 5m | 30 | ~8,640 | Day trading |
| 2 | 15m | 60 | ~5,760 | Intraday |
| **3** | **1h** | **90** | **~2,160** | **Swing trading ⭐** |
| 4 | 4h | 180 | ~1,080 | Position trading |

**Recommendation: Use option 3 (1h) for best results**

---

## Common Issues

**"0 trades" or "Strategy too selective"**
→ Use 1h timeframe (option 3) instead of 5m or 15m

**"Failed to fetch data"**
→ Set `USE_TESTNET=false` in `.env` (testnet has limited data)

**"Invalid symbol"**
→ Use full pair name: `BTCUSDT` not `BTC`

---

## Pro Tips

✅ **Start with 1h timeframe** - Best balance of data and quality
✅ **Test on multiple coins** - What works for BTC might not work for DOGE
✅ **Look for consistency** - Good if profitable across multiple timeframes
✅ **Use test_all_combinations.py** - Let it find the best strategy for you

---

## Next Steps

1. ✅ Test Simple Profitable on BTC (5 minutes)
2. ✅ Test on 2-3 different coins (10 minutes)
3. ✅ Run `test_all_combinations.py` mode 2 or 3 (5-10 minutes)
4. ✅ Find your best combination!
5. ✅ Test on Binance Testnet before live trading

---

## Quick Commands

```bash
# Test single strategy
python3 quick_backtest.py

# Find best for specific coin
python3 test_all_combinations.py  # Mode 3

# Test everything (10 min)
python3 test_all_combinations.py  # Mode 1
```

---

**That's it! Start testing and find your winning combination! 🚀**

For detailed docs, see `README.md`
