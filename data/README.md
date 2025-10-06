# 📁 Data Folder - CSV Upload Guide

## Quick Start

**You don't need CSV files!** The tools automatically fetch data from Binance.

But if you want to use your own data or test specific periods, you can upload CSVs here.

---

## CSV Format Required

Your CSV must have these 6 columns (in this order):

```csv
timestamp,open,high,low,close,volume
1696550400000,28000.00,28100.00,27900.00,28050.00,1000.50
1696550700000,28050.00,28200.00,28000.00,28150.00,1200.30
1696551000000,28150.00,28300.00,28100.00,28250.00,1500.20
```

### Column Descriptions:
- **timestamp**: Unix timestamp in milliseconds
- **open**: Opening price
- **high**: Highest price in period
- **low**: Lowest price in period
- **close**: Closing price
- **volume**: Trading volume

---

## Where to Get Data

### Option 1: Download from Binance (Easy)

```bash
python3 download_large_dataset.py
```

This automatically:
- Fetches data from Binance
- Makes multiple API calls (bypasses 1000 limit)
- Saves to this folder
- Perfect for getting 100+ days of data

### Option 2: CryptoDataDownload (Free)

**Website:** https://www.cryptodatadownload.com/data/binance/

**Steps:**
1. Go to website
2. Choose "Binance" exchange
3. Download your coin (e.g., `Binance_BTCUSDT_minute.csv`)
4. Save to this folder
5. Format may need adjustment (see below)

### Option 3: TradingView (Manual)

**Steps:**
1. Open TradingView chart
2. Click "..." menu → "Export chart data"
3. Save as CSV
4. Move to this folder
5. May need reformatting

### Option 4: Binance Data Portal (Advanced)

**Website:** https://data.binance.vision/

Official Binance historical data. Very large files, requires processing.

---

## Using CSV Files

### With quick_backtest.py:

Sorry, `quick_backtest.py` only uses API (auto-fetching).

### With backtest_runner.py:

```bash
python3 backtest_runner.py
# Choose: Option 2 (CSV file)
# Enter: data/your_file.csv
```

---

## File Naming (Recommended)

Use this format for easy organization:

```
SYMBOL_INTERVAL_PERIOD.csv
```

Examples:
- `BTCUSDT_5m_30days.csv`
- `ETHUSDT_1h_90days.csv`
- `SOLUSDT_15m_October2023.csv`

---

## Reformatting CSV Files

If your CSV has different columns, you'll need to reformat it.

### Common Formats:

**CryptoDataDownload format:**
```csv
unix,date,symbol,open,high,low,close,Volume BTC,Volume USDT
```

**Needs to become:**
```csv
timestamp,open,high,low,close,volume
```

**Quick Python script to convert:**
```python
import pandas as pd

# Read source file
df = pd.read_csv('downloaded_file.csv')

# Map columns (adjust names as needed)
formatted = pd.DataFrame({
    'timestamp': df['unix'] * 1000,  # Convert to milliseconds
    'open': df['open'],
    'high': df['high'],
    'low': df['low'],
    'close': df['close'],
    'volume': df['Volume USDT']  # Or 'Volume BTC'
})

# Save
formatted.to_csv('data/BTCUSDT_formatted.csv', index=False)
```

---

## Validation

Your CSV should:
- ✅ Have exactly 6 columns
- ✅ Have header row (column names)
- ✅ Timestamps in milliseconds (13 digits)
- ✅ At least 100 rows (candles)
- ✅ No missing values
- ✅ Prices as numbers (not strings with $ or commas)

---

## Example: Complete Workflow

### 1. Download Data
```bash
python3 download_large_dataset.py
# Symbol: BTCUSDT
# Interval: 5m
# Days: 100
# Saves to: data/BTCUSDT_5m_100days.csv
```

### 2. Verify Format
```bash
head -5 data/BTCUSDT_5m_100days.csv
```

Should show:
```
timestamp,open,high,low,close,volume
1696550400000,28000.00,28100.00,27900.00,28050.00,1000.50
...
```

### 3. Use in Backtest
```bash
python3 backtest_runner.py
# Option: 2 (CSV)
# Path: data/BTCUSDT_5m_100days.csv
```

---

## Troubleshooting

**"CSV missing required columns"**
→ Make sure you have all 6 columns with exact names

**"Insufficient data"**
→ Need at least 100 candles (rows)

**"Invalid timestamp"**
→ Timestamps must be in milliseconds (13 digits)
→ If in seconds (10 digits), multiply by 1000

**"Failed to process data"**
→ Check for missing values or non-numeric prices
→ Remove any rows with NaN or blank values

---

## Pro Tips

✅ **Use download_large_dataset.py** - Easiest way to get properly formatted data
✅ **Name files clearly** - Include symbol, interval, period
✅ **Keep multiple periods** - Test on different time ranges
✅ **Verify first 5 rows** - Use `head` command to check format
✅ **Test with small file first** - Make sure format works before big downloads

---

## Do I Really Need CSV Files?

**No!** The tools automatically fetch data from Binance API.

**Use CSV files when:**
- ✅ Testing specific historical periods
- ✅ Binance API is down
- ✅ You have data from another exchange
- ✅ You want to test on curated datasets
- ✅ Running many backtests (avoid API limits)

**Otherwise:** Just use `quick_backtest.py` - it handles everything automatically!

---

**Questions? See main [DOCUMENTATION.md](../DOCUMENTATION.md)**