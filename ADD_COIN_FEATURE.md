# Add Coin to Trading Feature 🚀

## Overview

The **"Add Coin"** feature allows you to dynamically add any cryptocurrency from the Community Tips sidebar to your trading dashboard. When you add a coin, it:

1. ✅ Trains an ML model on 3 years of historical data
2. ✅ Evaluates best trading strategy  
3. ✅ Adds coin to your coin selector
4. ✅ Enables 15-minute AI trading decisions
5. ✅ Starts in safe test mode

---

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│  1. USER CLICKS "+ Add" ON COIN IN TIPS SIDEBAR             │
│     Example: User sees ZEC trending, clicks "Add ZEC"       │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  2. FETCH 3 YEARS OF HISTORICAL DATA                         │
│     • Fetches 1095 days of OHLCV data from Binance          │
│     • Daily candlesticks for comprehensive analysis          │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  3. CALCULATE TECHNICAL INDICATORS                            │
│     • Returns (1d, 5d, 10d)                                  │
│     • Moving Averages (SMA 7, 25, 99)                        │
│     • RSI (14-period)                                        │
│     • Bollinger Bands                                        │
│     • Volume indicators                                       │
│     • Volatility & Momentum                                  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  4. TRAIN ML MODELS                                           │
│     • Random Forest Classifier                               │
│     • Gradient Boosting Classifier                           │
│     • Predicts: Will price rise >2% in next 7 days?        │
│     • Selects best performing model                         │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  5. EVALUATE PERFORMANCE                                      │
│     • Accuracy on test data (80/20 split)                    │
│     • Win Rate (% of correct buy signals)                    │
│     • Sharpe Ratio (risk-adjusted returns)                  │
│     • Average return per trade                               │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  6. SAVE TO DATABASE                                          │
│     • Store in `trading_coins` table                         │
│     • Save ML model results & strategy                       │
│     • Enable for AI trading decisions                        │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  7. COIN NOW APPEARS IN DASHBOARD                             │
│     • Added to coin selector dropdown                        │
│     • AI decisions run every 15 minutes                      │
│     • Starts in test mode (virtual trading)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Using the Feature

### Step 1: Open Tips Sidebar

1. Click the yellow **"Tips"** button in dashboard header
2. Browse trending coins from Binance Square

### Step 2: Add a Coin

1. Find a coin you want to trade (e.g., ZEC, SOL, DOGE)
2. At the bottom of each tip card, click:
   
   ```
   + Add [COIN] to Trading
   ```

3. Confirm the action in the dialog:
   ```
   Add ZEC to your trading dashboard?
   
   This will:
   • Train ML model on 3 years of data
   • Add ZEC to coin selector
   • Enable AI trading decisions every 15 minutes
   • Start in test mode (safe virtual trading)
   
   This may take 30-60 seconds.
   ```

### Step 3: Wait for ML Training

You'll see a loading state:
```
Training ML Model...
```

This takes 30-60 seconds while:
- Fetching 3 years of data from Binance
- Calculating technical indicators
- Training Random Forest & Gradient Boosting models
- Evaluating performance metrics

### Step 4: View Results

After training, you'll see a success dialog:
```
✅ Success!

ZEC has been added to your trading dashboard!

ML Model Trained:
- Model: RandomForest
- Accuracy: 68.5%
- Win Rate: 72.3%

ZEC will now appear in your coin selector and 
receive AI trading decisions every 15 minutes.
```

### Step 5: Trade the Coin

1. **Page reloads** automatically to update coin selector
2. **ZEC now appears** in the coin dropdown (alongside BTC, ETH, XRP, VIRTUAL)
3. **Select ZEC** from dropdown to view:
   - Live price chart
   - Portfolio metrics
   - AI trading decisions
   - News sentiment analysis

---

## ML Model Details

### Data Collection

- **Source**: Binance API
- **Period**: 3 years (1095 days)
- **Interval**: Daily candlesticks
- **Data**: Open, High, Low, Close, Volume

### Features Calculated

| Feature | Description |
|---------|-------------|
| `returns` | Daily price change % |
| `returns_5d` | 5-day price change % |
| `returns_10d` | 10-day price change % |
| `sma_7` | 7-day moving average |
| `sma_25` | 25-day moving average |
| `sma_99` | 99-day moving average |
| `rsi` | 14-period RSI |
| `bb_position` | Position within Bollinger Bands |
| `volume_ratio` | Volume vs 20-day average |
| `volatility` | 20-day standard deviation |
| `momentum` | 10-day momentum |

### Models Tested

1. **Random Forest**
   - 100 trees
   - Max depth: 10
   - Best for: Complex patterns

2. **Gradient Boosting**
   - 100 estimators
   - Max depth: 5
   - Best for: Sequential patterns

**Best model is automatically selected** based on test accuracy.

### Prediction Target

**Binary Classification**: Will the price increase by more than 2% in the next 7 days?

- **Class 0**: No (price won't rise >2%)
- **Class 1**: Yes (price will rise >2%)

### Performance Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Accuracy** | % of correct predictions | >60% |
| **Win Rate** | % of profitable "buy" signals | >65% |
| **Sharpe Ratio** | Risk-adjusted returns | >1.0 |
| **Avg Return** | Average gain per trade | >2% |

---

## Database Schema

### `trading_coins` Table

```sql
CREATE TABLE trading_coins (
    id INTEGER PRIMARY KEY,
    coin VARCHAR NOT NULL UNIQUE,        -- e.g., "ZEC"
    coin_name VARCHAR,                   -- e.g., "Zcash"
    symbol VARCHAR NOT NULL,             -- e.g., "ZECUSDT"
    
    -- ML Results
    ml_model_type VARCHAR,               -- "RandomForest" or "GradientBoosting"
    ml_strategy TEXT,                    -- JSON with strategy parameters
    ml_accuracy FLOAT,                   -- Model accuracy (0-1)
    ml_sharpe_ratio FLOAT,               -- Risk-adjusted returns
    ml_win_rate FLOAT,                   -- % of winning trades
    training_period_days INTEGER,        -- Default: 1095 (3 years)
    
    -- Configuration
    enabled BOOLEAN DEFAULT TRUE,        -- Is coin active?
    ai_decisions_enabled BOOLEAN DEFAULT TRUE,  -- Run AI decisions?
    test_mode BOOLEAN DEFAULT TRUE,      -- Start in test mode
    
    -- Status
    added_at DATETIME,
    last_decision_at DATETIME,
    total_trades INTEGER DEFAULT 0
);
```

---

## API Endpoints

### GET `/api/coins`

Get all trading coins (base + dynamic).

**Response:**
```json
{
  "ok": true,
  "count": 5,
  "coins": [
    {
      "coin": "BTC",
      "coin_name": "Bitcoin",
      "symbol": "BTCUSDT",
      "is_base": true
    },
    {
      "coin": "ZEC",
      "coin_name": "Zcash",
      "symbol": "ZECUSDT",
      "is_base": false,
      "ml_model_type": "RandomForest",
      "ml_accuracy": 0.685,
      "ml_win_rate": 0.723,
      "ml_sharpe_ratio": 1.45,
      "ai_decisions_enabled": true,
      "test_mode": true
    }
  ]
}
```

### POST `/api/coins/add?coin=ZEC&coin_name=Zcash`

Add a new coin and train ML model.

**Request:**
- `coin` (required): Coin symbol (e.g., "ZEC")
- `coin_name` (optional): Full name (e.g., "Zcash")

**Response:**
```json
{
  "ok": true,
  "message": "ZEC added successfully!",
  "coin": {
    "id": 1,
    "coin": "ZEC",
    "coin_name": "Zcash",
    "symbol": "ZECUSDT",
    "ml_model_type": "RandomForest",
    "ml_accuracy": 0.685,
    "ml_win_rate": 0.723,
    "ml_sharpe_ratio": 1.45,
    "training_period_days": 1095,
    "enabled": true,
    "ai_decisions_enabled": true,
    "test_mode": true,
    "added_at": "2025-10-28T12:00:00Z"
  }
}
```

### DELETE `/api/coins/{coin}`

Remove a coin from trading.

**Response:**
```json
{
  "ok": true,
  "message": "ZEC removed from trading list"
}
```

---

## Example: Adding ZEC

### 1. Click "+ Add ZEC to Trading"

Frontend sends:
```
POST /api/coins/add?coin=ZEC&coin_name=Zcash
```

### 2. Backend Processes

```python
# Fetch 3 years of data
df = fetch_historical_data("ZEC", days=1095)
# Returns: DataFrame with 1095 rows of OHLCV data

# Calculate indicators
df = calculate_technical_indicators(df)
# Adds: RSI, Bollinger Bands, Moving Averages, etc.

# Train models
results = train_ml_model(df)
# Output:
# {
#   'model_type': 'RandomForest',
#   'accuracy': 0.685,
#   'win_rate': 0.723,
#   'sharpe_ratio': 1.45,
#   ...
# }

# Save to database
trading_coin = TradingCoin(
    coin='ZEC',
    coin_name='Zcash',
    symbol='ZECUSDT',
    ml_model_type='RandomForest',
    ml_accuracy=0.685,
    ...
)
db.add(trading_coin)
db.commit()
```

### 3. Frontend Updates

```javascript
// Show success message
alert(`✅ Success! ZEC added with 68.5% accuracy!`)

// Reload page to update coin selector
window.location.reload()
```

### 4. ZEC Now Available

- **Coin Selector**: ZEC appears in dropdown
- **AI Decisions**: Run every 15 minutes
- **Test Mode**: Safe virtual trading enabled
- **Dashboard**: Full trading interface available

---

## Testing the ZEC Article Detection

A test script is included to verify if specific articles are being scraped:

```bash
cd /Users/rileymartin/tradingbot
python3 test_zec_article.py
```

This will:
1. ✅ Scrape CPIWatch URL with visible browser
2. ✅ Search for ZEC mentions in posts
3. ✅ Show timestamps and content
4. ✅ Test AI extraction
5. ✅ Verify if ZEC was extracted

**If ZEC isn't found:**
- Post might be older than 10 minutes
- "Latest" tab might not be clicked
- Scraper might need adjustment

---

## Files Created/Modified

### Backend

- ✅ `app/models.py` - Added `TradingCoin` model
- ✅ `app/coin_trainer.py` - ML training service (NEW)
- ✅ `app/server.py` - Added `/api/coins` endpoints
- ✅ `test_zec_article.py` - ZEC detection test (NEW)
- ✅ `migrate_db.py` - Database migration

### Frontend

- ✅ `app/components/TipsSidebar.tsx` - Added "+ Add" button

### Database

- ✅ `trading_coins` table created

---

## Workflow Example

```
User sees ZEC trending in Tips sidebar
   ↓
Clicks "+ Add ZEC to Trading"
   ↓
Backend fetches 3 years of ZEC/USDT data
   ↓
Calculates technical indicators (RSI, MA, BB, etc.)
   ↓
Trains RandomForest & GradientBoosting models
   ↓
Selects best model (e.g., RandomForest 68.5% accuracy)
   ↓
Saves to database with ML metrics
   ↓
Frontend reloads, ZEC appears in coin selector
   ↓
User selects ZEC from dropdown
   ↓
Dashboard shows ZEC price, portfolio, AI decisions
   ↓
AI generates trading decisions every 15 minutes
   ↓
Test mode executes virtual trades safely
```

---

## Benefits

1. **Dynamic Expansion**: Add any coin without code changes
2. **Data-Driven**: ML model trained on 3 years of real data
3. **Risk Management**: Starts in test mode (virtual trading)
4. **Automated**: AI decisions run every 15 minutes
5. **Performance Metrics**: See accuracy, win rate, Sharpe ratio
6. **One Click**: Entire process automated from tips sidebar

---

## Limitations

1. **Training Time**: Takes 30-60 seconds per coin
2. **Binance Only**: Requires coin to be traded on Binance
3. **Data Requirement**: Needs 3 years of historical data
4. **No Removal UI**: Must use API or database to remove coins
5. **Test Mode Default**: Must manually enable live trading

---

## Future Enhancements

- [ ] Add "Remove" button for dynamic coins
- [ ] Show training progress bar
- [ ] Allow custom training periods (1yr, 2yr, 5yr)
- [ ] Add more ML models (LSTM, XGBoost)
- [ ] Backtesting UI with historical performance
- [ ] Auto-disable poorly performing coins
- [ ] Multi-exchange support
- [ ] Real-time strategy adjustment

---

**Status:** ✅ Fully implemented and ready to use!  
**Version:** 1.0.0  
**Date:** October 28, 2025

