# 🚀 Momentum Trading Bot - How It Actually Works

## 📡 Continuous Scanning System

### Background Scheduler
The bot runs **continuously in the background** using a scheduler (APScheduler):

```python
scheduler.add_job(momentum_scanner_job, 'interval', minutes=1, id='momentum_scanner')
```

**This means:**
- ✅ Bot scans **every 60 seconds** when enabled
- ✅ No need for websockets - scheduled scans are more reliable
- ✅ Runs automatically in the background
- ✅ Checks ALL USDT trading pairs on Binance
- ✅ Monitors open positions for exit signals

---

## 🔍 What Happens Every Minute

### 1. **Check if Bot is Enabled**
```
Read /tmp/momentum_config.json
├─ If enabled = false → Skip scan
└─ If enabled = true → Continue to scan
```

### 2. **Scan All USDT Pairs**
```
For each trading pair (BTCUSDT, ETHUSDT, etc.):
├─ Get last 100 candles (5 minute intervals)
├─ Calculate price change % over last hour
├─ Check 24h volume
├─ Calculate volume spike ratio
└─ If meets criteria → Generate signal
```

### 3. **Criteria for Signal Generation**
A coin must pass ALL these checks:

| Check | Default Value | What It Means |
|-------|---------------|---------------|
| Price Change | +20% | Price must have increased 20% in last hour |
| Volume 24h | $1,000,000 | Must have $1M+ trading volume |
| Volume Spike | 2.0x | Current volume must be 2x average |
| AI Confidence | 0.8 (80%) | AI predicts momentum will continue |

### 4. **AI Analysis**
For coins that pass the basic criteria:
```
AI Model analyzes:
├─ Price action patterns
├─ Volume trends
├─ Historical momentum data
├─ Market conditions
└─ Outputs confidence score (0-1)
```

If AI confidence > threshold (default 80%) → **CREATE SIGNAL**

### 5. **Signal Created**
```sql
INSERT INTO momentum_signals (
  symbol, price_change_pct, volume_24h, 
  ai_confidence, technical_score, status
)
```

### 6. **Auto-Trade (If Enabled)**
```
For high-confidence signals:
├─ Calculate position size (max_position_pct of portfolio)
├─ Place market buy order
├─ Set stop loss at -5% (configurable)
├─ Record trade in database
└─ Log to MOMENTUM category
```

### 7. **Monitor Open Positions**
```
For each open trade:
├─ Get current price
├─ Calculate P&L %
├─ If P&L <= -stop_loss_pct → CLOSE POSITION
├─ If P&L >= +target → CONSIDER EXIT (AI decides)
└─ Log all actions
```

---

## ⚙️ Configuration (Editable from Frontend)

### How Config Works
```
1. User updates config in /momentum page
2. Frontend calls POST /api/momentum/config
3. Backend saves to /tmp/momentum_config.json
4. Next scan uses new values immediately
```

### Configuration Options

| Setting | Default | Range | Impact |
|---------|---------|-------|--------|
| **Min Price Change** | 20% | 5-50% | Lower = more signals (less selective) |
| **Min Volume** | $1M | $100k-$10M | Lower = smaller coins included |
| **AI Threshold** | 0.8 | 0.5-0.95 | Lower = more trades (riskier) |
| **Max Position** | 10% | 1-25% | % of portfolio per trade |
| **Stop Loss** | 5% | 2-10% | Auto-exit if loss exceeds % |
| **Scan Frequency** | 60s | 30-300s | How often to scan |

---

## 🎯 Example Scan Cycle

### Minute 0:00
```
[Momentum Scanner Started]
├─ Checking 400+ USDT pairs...
├─ VIRTUALUSDT: +45% in 1h, Volume $2.5M, Spike 3.2x
│   └─ AI analyzing... Confidence: 87% ✅
│   └─ SIGNAL CREATED
├─ ETHUSDT: +2% in 1h, Volume $500M
│   └─ Below threshold (need 20%+) ❌
├─ DOGEUSDT: +25% in 1h, Volume $800k
│   └─ Volume too low (need $1M+) ❌
└─ Found 1 new signal
```

### Minute 0:01
```
[Signal Processing]
└─ VIRTUALUSDT Signal (AI: 87%)
    ├─ Portfolio value: $1,000 USDT
    ├─ Max position: 10% = $100 USDT
    ├─ Current price: $0.50
    ├─ Quantity: 200 VIRTUAL
    ├─ Stop loss: $0.475 (-5%)
    └─ ORDER PLACED ✅
```

### Minute 1:00
```
[Next Scan]
├─ Monitor existing position: VIRTUALUSDT
│   ├─ Entry: $0.50
│   ├─ Current: $0.53
│   ├─ P&L: +6% 🟢
│   └─ Holding...
└─ Scan for new signals...
```

### Minute 5:00
```
[Position Check]
└─ VIRTUALUSDT
    ├─ Entry: $0.50
    ├─ Current: $0.47
    ├─ P&L: -6% 🔴
    ├─ Stop loss triggered! (-5% threshold)
    └─ CLOSING POSITION...
```

---

## 📊 Why Every Minute (Not Websockets)?

### Websockets Approach
```
❌ Connection can drop
❌ Complex to maintain
❌ Miss data during reconnection
❌ Hard to debug
```

### Scheduled Scans
```
✅ Reliable and predictable
✅ Easy to debug (check logs)
✅ Can adjust frequency easily
✅ No connection issues
✅ Processes data in batches
✅ Lower API rate limit usage
```

### 1 Minute is Ideal Because:
- Fast enough to catch momentum early
- Slow enough to filter out noise
- Respects Binance API rate limits
- Gives AI time to analyze properly

---

## 📈 Trading Lifecycle

### 1. **Detection Phase** (0-1 minute)
```
Coin pumps → Scanner detects → AI analyzes → Signal created
```

### 2. **Entry Phase** (1-2 minutes)
```
Signal validated → Position sized → Order placed → Stop loss set
```

### 3. **Monitoring Phase** (Continuous)
```
Every minute:
├─ Check current price
├─ Calculate P&L
├─ Monitor for exit conditions
└─ Update dashboard
```

### 4. **Exit Phase** (Varies)
```
Exit triggers:
├─ Stop loss hit (-5%)
├─ AI recommends exit (momentum lost)
├─ Manual close (user clicks)
└─ Position closed, P&L recorded
```

---

## 🔐 Safety Features

### 1. **Position Limits**
- Max 10% of portfolio per trade (configurable)
- Prevents over-exposure to single asset

### 2. **Automatic Stop Loss**
- Set at -5% by default
- Checked every minute
- Auto-closes losing positions

### 3. **AI Validation**
- Every signal validated by AI
- Minimum 80% confidence required
- Filters out false signals

### 4. **Volume Filtering**
- Only trades liquid coins ($1M+ volume)
- Prevents manipulation/pump-and-dumps

### 5. **Logging Everything**
- Every scan logged to database
- Every trade recorded
- View in /logs page (MOMENTUM category)

---

## 📱 Frontend Integration

### Real-Time Updates
```
User opens /momentum page
├─ Fetches current status
├─ Shows active signals
├─ Displays open trades
└─ Updates on refresh
```

### Control Panel
```
Header Buttons:
├─ 🔍 Test → Run manual scan
├─ ⚙️ Config → Edit settings
├─ Start/Pause → Toggle bot
└─ Status Badge → Shows if scanning
```

### Test Mode
```
1. Click "Test" button
2. Bot scans all pairs once
3. Shows results in modal
4. No trades executed
5. See exactly what bot detects
```

### Config Mode
```
1. Click "Config" button
2. Edit any setting
3. Click "Save"
4. Changes apply to next scan
5. No server restart needed
```

---

## 🐛 Troubleshooting

### Bot Not Finding Signals
```
Check:
├─ Is bot enabled? (Status badge)
├─ Are criteria too strict? (Lower min_price_change)
├─ Check /logs for scanner activity
└─ Run Test scan to see results
```

### Bot Not Trading
```
Check:
├─ Do signals meet AI threshold? (Lower ai_threshold)
├─ Is portfolio value sufficient? (Need $11+ USDT)
├─ Check /logs for errors
└─ Verify Binance API keys
```

### Stop Loss Not Working
```
Check:
├─ Is bot enabled? (Must be running)
├─ Check stop_loss_pct setting
├─ View trade details in dashboard
└─ Check /logs for MOMENTUM category
```

---

## 📝 Summary

### How It Works:
1. ✅ **Continuous Scanning**: Every 60 seconds, all USDT pairs
2. ✅ **Smart Filtering**: Price change + volume + AI confidence
3. ✅ **Automatic Trading**: High-confidence signals → Instant trades
4. ✅ **Risk Management**: Stop loss + position limits
5. ✅ **Real-Time Monitoring**: Open positions checked every minute
6. ✅ **Full Logging**: Everything recorded to database

### Why It's Better Than Websockets:
- More reliable (no connection drops)
- Easier to debug (clear logs)
- Lower API usage (batch processing)
- Adjustable frequency (user control)
- Simpler architecture (less complexity)

### User Control:
- ⚙️ Fully configurable from frontend
- 🔍 Test mode to preview results
- ⏸️ Start/pause anytime
- 📊 Real-time dashboard
- 📋 Complete logs

**Bottom Line:** The bot is always working in the background, scanning the market every minute, ready to catch the next big momentum move! 🚀

---

*Last Updated: $(date)*

