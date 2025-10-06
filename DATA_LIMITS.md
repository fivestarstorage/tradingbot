# 📊 Understanding Data Limits & Solutions

## ⚠️ The 1000 Candle Limit

**Binance API restricts single requests to 1000 candles maximum.**

This is NOT a bug - it's an intentional API limit to prevent server abuse.

## 📏 What This Means

### For Different Intervals:

| Interval | Candles/Day | 1000 Candles = Days | Max w/ Single API Call |
|----------|-------------|---------------------|------------------------|
| **1m**   | 1,440       | 0.7 days (~17 hrs)  | < 1 day               |
| **5m**   | 288         | 3.5 days            | ~3 days               |
| **15m**  | 96          | 10.4 days           | ~10 days              |
| **1h**   | 24          | 41.7 days           | ~41 days              |
| **4h**   | 6           | 166.7 days          | ~166 days             |
| **1d**   | 1           | 1000 days           | ~3 years              |

### Your Example:
- **Requested**: 100 days of 5m data = 28,800 candles
- **Got**: 1000 candles = 3.5 days
- **Missing**: 27,800 candles!

## ✅ Solutions

### 1. Use Batch Downloader (Best for Large Datasets)

```bash
python download_large_dataset.py
```

**What it does:**
- Makes multiple API calls automatically
- Downloads data in 1000-candle batches
- Combines all batches into one CSV file
- No manual work required!

**Example:**
```bash
python download_large_dataset.py
Symbol: BTCUSDT
Interval: 5m
Days: 100

# Downloads:
# Batch 1: 1000 candles
# Batch 2: 1000 candles
# ...
# Batch 29: 800 candles
# Total: 28,800 candles saved to CSV
```

**Then use the CSV:**
```bash
python backtest_runner.py
# Option 2
# Enter: data/BTCUSDT_5m_100days.csv
```

### 2. Download from External Sources

**CryptoDataDownload.com:**
- https://www.cryptodatadownload.com/data/binance/
- Pre-compiled historical data
- Multiple years available
- Free download

**Binance Data Portal:**
- https://data.binance.vision/
- Official Binance historical data
- Very large datasets available
- Requires some processing

### 3. Use Longer Intervals

If you only need the API (no batch downloading):

```bash
python backtest_runner.py
```

**Choose intervals wisely:**
- **1m**: Only ~17 hours max
- **5m**: Only ~3.5 days max ❌ Too short for 100 days!
- **15m**: Up to ~10 days ✅ Better
- **1h**: Up to ~41 days ✅ Good for monthly tests
- **4h**: Up to ~166 days ✅ Perfect for quarterly tests
- **1d**: Up to ~3 years ✅ Great for long-term

### 4. Adjust Your Testing Period

For quick tests with direct API (Option 1):

```bash
python backtest_runner.py
# Option 1

# 5m interval → Max 3 days
Symbol: BTCUSDT
Interval: 5m
Days: 3  ← Not 100!

# 1h interval → Max 40 days
Symbol: BTCUSDT
Interval: 1h
Days: 40

# 4h interval → Max 150 days
Symbol: BTCUSDT
Interval: 4h
Days: 150
```

## 🎯 Recommendations

### For Day Trading (5m, 15m):
```bash
# Use batch downloader for large datasets
python download_large_dataset.py
# Days: 100
```

### For Swing Trading (1h, 4h):
```bash
# Can use direct API
python backtest_runner.py
# Option 1
# 1h → 30-40 days OK
# 4h → 150 days OK
```

### For Position Trading (1d):
```bash
# Can use direct API
python backtest_runner.py
# Option 1
# 1d → 365+ days OK
```

## 🔍 How to Check What You Got

After running backtest, look at the data range:

```python
# Your results showed:
"Fetched 1000 candles"

# Calculate actual days:
# 5m interval: 1000 ÷ 288 candles/day = 3.47 days
# NOT the 100 days you requested!
```

## 📈 Why More Data Matters

### More Data = Better Testing:
- ✅ Tests strategy in different market conditions
- ✅ Bulls markets, bear markets, sideways
- ✅ High volatility, low volatility
- ✅ More statistically significant results

### 3.5 Days vs 100 Days:
- **3.5 days**: Might be all bull or all bear
- **100 days**: Covers multiple market phases
- **Result**: More reliable backtest

## 🚀 Quick Commands

### Download 100 Days of 5m Data:
```bash
python download_large_dataset.py
# BTCUSDT, 5m, 100
# Wait ~15 seconds for all batches
# Use the generated CSV file
```

### Then Backtest:
```bash
python backtest_runner.py
# Option 2
# Enter: data/BTCUSDT_5m_100days.csv
```

### Quick 3-Day Test (Direct API):
```bash
python backtest_runner.py
# Option 1
# BTCUSDT, 5m, 3  ← Note: 3 not 100
```

## 💡 Pro Tips

1. **Download once, test many times**
   - Save the CSV
   - Reuse for multiple strategy tests
   - No repeated downloads

2. **Start with smaller datasets**
   - Test on 10-30 days first
   - Verify strategy works
   - Then test on 100+ days

3. **Use appropriate intervals**
   - Day trading: 5m or 15m
   - Swing trading: 1h or 4h  
   - Position trading: 4h or 1d

4. **Keep downloaded CSVs organized**
   ```
   data/
   ├── BTCUSDT_5m_100days.csv
   ├── ETHUSDT_1h_60days.csv
   ├── DOGEUSDT_15m_30days.csv
   ```

---

## Summary

| Task | Command | Notes |
|------|---------|-------|
| **Quick test (≤3 days)** | `backtest_runner.py` → Option 1 | Direct API, fast |
| **Large dataset (100+ days)** | `download_large_dataset.py` | Multiple batches, then use CSV |
| **Pre-downloaded data** | `backtest_runner.py` → Option 2 | Upload your CSV |

**The 1000 candle limit is normal - now you know how to work around it!** ✅
