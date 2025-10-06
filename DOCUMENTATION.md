# 📚 Documentation Index

## Start Here

### 🚀 [QUICKSTART.md](QUICKSTART.md)
**Read this first!** 5-minute guide to your first backtest.
- Installation
- Configuration
- Running your first test
- Understanding results

### 📖 [README.md](README.md)
Complete project overview and reference guide.
- All features
- All strategies and coins
- Usage examples
- Troubleshooting
- Pro tips

---

## Detailed Guides

### 📊 [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)
Complete strategy reference guide.
- Detailed explanation of all 6 strategies
- When to use each one
- Coin recommendations
- Risk profiles
- Decision tree for choosing

### 📉 [DATA_LIMITS.md](DATA_LIMITS.md)
Understanding Binance API limits and solutions.
- 1000 candle limit explained
- How to fetch more data
- Batch downloading
- Timeframe calculations

---

## Quick Reference

### Main Tools

| File | Purpose | Use When |
|------|---------|----------|
| `quick_backtest.py` | Test single strategy on one coin | Testing a specific combination |
| `test_all_combinations.py` | Test all strategies on all coins | Finding the best strategy |
| `download_large_dataset.py` | Download 100+ days of data | Need more than default data |
| `trading_bot.py` | Live trading | Ready for real trading (careful!) |

### Strategies Quick Reference

| # | Strategy | Best For |
|---|----------|----------|
| **1** | **Simple Profitable ⭐** | **All coins (RECOMMENDED)** |
| 2 | Enhanced Momentum | BTC, ETH, trending markets |
| 3 | Volatile Coins | SOL, DOGE, high volatility |
| 4 | Mean Reversion | Ranging/sideways markets |
| 5 | Breakout | Strong trends, momentum |
| 6 | Conservative | Risk-averse, perfect setups |

### Recommended Starting Points

**Beginner:**
```bash
python3 quick_backtest.py
# Strategy: 1 (Simple Profitable)
# Coin: 1 (Bitcoin)
# Timeframe: 3 (1h)
```

**Finding Best Strategy:**
```bash
python3 test_all_combinations.py
# Mode: 3 (Specific coin)
# Test all strategies on your target coin
```

**Full Analysis:**
```bash
python3 test_all_combinations.py
# Mode: 1 (Full test)
# Tests all 240 combinations
```

---

## File Structure

```
tradingbot/
├── DOCUMENTATION.md           ← You are here
├── README.md                  ← Complete overview
├── QUICKSTART.md              ← 5-minute start
├── STRATEGY_GUIDE.md          ← Strategy details
├── DATA_LIMITS.md             ← API limits explained
│
├── quick_backtest.py          ← Main testing tool
├── test_all_combinations.py   ← Comprehensive tester
├── download_large_dataset.py  ← Data downloader
├── trading_bot.py             ← Live trading
│
├── strategies/                ← All 6 strategies
│   ├── simple_profitable_strategy.py  ⭐
│   ├── enhanced_strategy.py
│   ├── volatile_coins_strategy.py
│   ├── mean_reversion_strategy.py
│   ├── breakout_strategy.py
│   └── conservative_strategy.py
│
├── data/                      ← Put CSV files here
│   └── README.md              ← CSV format guide
│
├── old_files/                 ← Archived versions
│
├── binance_client.py          ← API wrapper
├── config.py                  ← Configuration
└── requirements.txt           ← Dependencies
```

---

## Common Tasks

### I want to...

**Test Bitcoin with default strategy**
→ Run `quick_backtest.py`, choose 1, 1, 3

**Find best strategy for Solana**
→ Run `test_all_combinations.py`, mode 3, coin 4

**Test all combinations**
→ Run `test_all_combinations.py`, mode 1

**Download 100 days of data**
→ Run `download_large_dataset.py`

**Understand why I only got 1000 candles**
→ Read `DATA_LIMITS.md`

**Learn about strategies**
→ Read `STRATEGY_GUIDE.md`

**Start from scratch**
→ Read `QUICKSTART.md`

**Use for live trading**
→ Read `README.md` → Live Trading section

---

## Getting Help

### Errors and Issues

Check the Troubleshooting section in `README.md`

Common issues:
- API limits → See `DATA_LIMITS.md`
- Strategy selection → See `STRATEGY_GUIDE.md`
- 0 trades → Use 1h timeframe, try different strategy
- Failed to fetch → Set `USE_TESTNET=false` in `.env`

### Understanding Concepts

- **What's a good return?** → 5%+ is good, 10%+ is excellent
- **What's a good win rate?** → 50%+ is good, 60%+ is excellent
- **What's a good profit factor?** → 1.5+ is good, 2.0+ is excellent
- **How many trades should I see?** → 10-40 per 100 days depending on strategy

---

## Documentation Flow

```
New User → QUICKSTART.md (5 min)
           ↓
         Run quick_backtest.py
           ↓
    Want more details? → README.md
           ↓
    Choosing strategy? → STRATEGY_GUIDE.md
           ↓
    Data issues? → DATA_LIMITS.md
           ↓
    Ready for comprehensive testing
           ↓
    Run test_all_combinations.py
```

---

## Last Updated

Documentation structure updated with:
- ✅ 6 strategies (Simple Profitable ⭐ added)
- ✅ Automatic multi-batch data fetching
- ✅ Comprehensive testing tool
- ✅ Simplified file structure
- ✅ Consolidated documentation

---

**Start with [QUICKSTART.md](QUICKSTART.md) and you'll be testing in 5 minutes!** 🚀
