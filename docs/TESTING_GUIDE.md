# 📊 Testing Guide - Fair Comparisons

## The Problem You Solved

When testing strategies across different timeframes, using the **same number of candles** creates unfair comparisons:

### Example (8000 candles):
- **5m candles**: 8000 × 5min = 27.7 days
- **15m candles**: 8000 × 15min = 83.3 days
- **1h candles**: 8000 × 1hr = 333 days
- **4h candles**: 8000 × 4hr = 1,333 days

❌ **Problem**: You're comparing strategies over completely different time periods!

---

## The Solution

Our `test_all_combinations.py` now uses the **same time period** for all timeframes:

### Example (30 days):
- **5m candles**: 30 days × 288 candles/day = **8,640 candles**
- **15m candles**: 30 days × 96 candles/day = **2,880 candles**
- **1h candles**: 30 days × 24 candles/day = **720 candles**
- **4h candles**: 30 days × 6 candles/day = **180 candles**

✅ **Solution**: All strategies tested over the exact same 30-day period!

---

## How It Works

### 1. You Choose the Time Period

When you run the test, you're asked:

```bash
How many days to test? (7/14/30/60/90) [30]: 
```

**Options:**
- **7 days** - Quick test, good for rapid iteration
- **14 days** - Moderate test, decent sample size
- **30 days** - Recommended, good balance
- **60 days** - Thorough, better statistical significance
- **90 days** - Comprehensive, best for final validation

### 2. All Timeframes Use That Period

The script automatically calculates the right number of candles for each timeframe:

```
✓ Testing 30 days for all timeframes
  5m:  ~8640 candles
  15m: ~2880 candles
  1h:  ~720 candles
  4h:  ~180 candles
```

### 3. Fair Comparison

Now when you see results like:

```
🏆 TOP PERFORMERS
Simple Profitable    Bitcoin    5m  → +15.50%
Enhanced             Bitcoin    1h  → +12.30%
Breakout             Ethereum   4h  → +10.20%
```

You know they were **all tested over the same 30-day period**!

---

## Candles Per Day Reference

| Timeframe | Candles Per Day | Formula |
|-----------|----------------|---------|
| 5m        | 288            | 24×60÷5 |
| 15m       | 96             | 24×60÷15 |
| 1h        | 24             | 24÷1 |
| 4h        | 6              | 24÷4 |

---

## Why This Matters

### 1. **Fair Strategy Comparison**
- Compare apples to apples
- Each strategy tested in same market conditions
- Same number of market cycles

### 2. **Timeframe Selection**
- See which timeframe actually performs better
- Not skewed by different time periods

### 3. **Statistical Validity**
- All tests have same sample period
- More reliable conclusions

---

## Usage Examples

### Quick Test (7 days)
```bash
python3 test_all_combinations.py
# Enter: 7
# Good for: Rapid testing, development
```

### Standard Test (30 days)
```bash
python3 test_all_combinations.py
# Enter: 30
# Good for: Normal validation, default choice
```

### Thorough Test (90 days)
```bash
python3 test_all_combinations.py
# Enter: 90
# Good for: Final validation before live trading
```

---

## Understanding Results

### Example Output:

```
Test period: 30 days (same for all timeframes)
Actual days: 4.8 - 30.0 days (varies by data availability)

🏆 TOP 10 BEST PERFORMERS
Simple Profitable    Bitcoin    5m   → +15.50% | 45 trades | 8640 candles
Enhanced             Bitcoin    1h   → +12.30% | 12 trades | 720 candles
```

**What this means:**
- **Test period**: You requested 30 days
- **Actual days**: Some coins might have less data available (especially on testnet)
- **Candles**: Different timeframes have different candle counts, but same time period

---

## Recommendations by Test Period

### 7 Days:
- ✅ Quick iteration
- ✅ Testing new strategies
- ❌ Limited data for conclusions
- ❌ May miss longer-term patterns

### 14 Days:
- ✅ Good for initial validation
- ✅ Reasonable sample size
- ⚠️ Some strategies need more time

### 30 Days (Recommended):
- ✅ Good balance
- ✅ Captures weekly patterns
- ✅ Enough trades for statistics
- ✅ Most common choice

### 60 Days:
- ✅ More reliable results
- ✅ Better statistical significance
- ✅ Captures monthly patterns
- ⚠️ Takes longer to fetch data

### 90 Days:
- ✅ Very thorough
- ✅ Best for final validation
- ✅ Seasonal patterns visible
- ❌ Slower to run
- ❌ May exceed testnet data limits

---

## Data Availability Note

⚠️ **Testnet has limited historical data** (~5-7 days)

If you're on testnet and request 30 days, you might only get 5 days of actual data.

**Solution:**
1. Switch to mainnet for more data (`USE_TESTNET=false`)
2. Use shorter test periods on testnet
3. Check the "Actual days" in results

---

## Quick Reference

```bash
# Test with default 30 days
python3 test_all_combinations.py

# Test with custom period
python3 test_all_combinations.py
# When prompted: enter 7, 14, 30, 60, or 90

# Mode 1: Full test (all coins)
# Mode 2: Quick test (BTC only) ⭐ Recommended for testing
# Mode 3: Specific coin
```

---

## Pro Tips

1. **Start with 30 days** - Good balance of speed and accuracy

2. **Use Mode 2** (quick test) - Test all strategies on BTC first
   - Fast (~1 minute)
   - BTC is most liquid
   - Good indicator of strategy performance

3. **Increase to 60-90 days** for final validation before live trading

4. **Check "Actual days"** in results to confirm you got enough data

5. **Export to CSV** for deeper analysis in Excel/Python

---

**Now your tests are fair and comparable! 📊✅**
