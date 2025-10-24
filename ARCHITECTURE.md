# 🏗️ Trading Bot Architecture

This document explains how all the pieces fit together.

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [How Trading Works](#how-trading-works)
5. [File Structure](#file-structure)
6. [Process Management](#process-management)

---

## System Overview

### The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                         YOU (User)                          │
│                    Via Web Browser                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   simple_dash.py                            │
│                   (Web Dashboard)                            │
│                                                             │
│  • Flask web server                                         │
│  • Manages bot lifecycle (start/stop)                      │
│  • Displays stats and charts                               │
│  • Reads log files                                          │
└──────────────┬────────────────────────┬─────────────────────┘
               │                        │
               ↓                        ↓
    ┌──────────────────┐      ┌──────────────────┐
    │  active_bots.json│      │  Binance API     │
    │                  │      │  (Account Info)   │
    │  • Bot configs   │      └──────────────────┘
    │  • Track status  │
    └──────────────────┘
               │
               │ starts/stops
               ↓
┌─────────────────────────────────────────────────────────────┐
│              integrated_trader.py (Bot Instances)           │
│                                                             │
│  Each bot runs independently in a 'screen' session:        │
│                                                             │
│  Bot 1 (BTC) ──► Strategy ──► Binance ──► Logs            │
│  Bot 2 (ETH) ──► Strategy ──► Binance ──► Logs            │
│  Bot 3 (DOGE)──► Strategy ──► Binance ──► Logs            │
│                                                             │
│  Every 15 minutes:                                          │
│  1. Fetch market data                                       │
│  2. Analyze with strategy                                   │
│  3. Execute trades if signal                                │
│  4. Log everything                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
              ┌─────────────────┐
              │  Binance API    │
              │  (Trading)      │
              └─────────────────┘
```

---

## Component Architecture

### 1. Web Dashboard (`simple_dash.py`)

**Purpose:** User interface for managing bots

**Key Responsibilities:**
- Serve HTML/CSS/JavaScript interface
- Handle API requests from browser
- Start/stop bot processes using `screen`
- Read and display bot logs
- Query Binance for account balances
- Manage `active_bots.json` configuration file

**Technology Stack:**
- Flask (Python web framework)
- Vanilla JavaScript (no frameworks)
- Chart.js (for graphs)
- HTML/CSS (embedded in Python file)

**API Endpoints:**
```
GET  /                      → Serve dashboard HTML
GET  /api/overview          → Get all bots + stats
GET  /api/bot/:id/details   → Get specific bot details
POST /api/bot/:id/start     → Start a bot
POST /api/bot/:id/stop      → Stop a bot
POST /api/bot/:id/update    → Update bot settings
POST /api/create-bot        → Create new bot
GET  /api/search-coins      → Search Binance symbols
POST /api/send_alert        → Send SMS notification
```

---

### 2. Trading Bot (`integrated_trader.py`)

**Purpose:** Execute trades automatically

**Key Responsibilities:**
- Load selected trading strategy
- Fetch market data from Binance every 15 minutes
- Analyze data using strategy
- Execute BUY/SELL orders
- Manage positions (track entry, stop loss, take profit)
- Save position state to survive restarts
- Log all activity

**How It Starts:**
```bash
# Dashboard runs this command:
screen -dmS bot_1 python3 integrated_trader.py 1 'BTC Bot' BTCUSDT volatile 100

# Arguments:
# 1 = bot_id
# 'BTC Bot' = bot_name
# BTCUSDT = symbol to trade
# volatile = strategy to use
# 100 = trade amount (USDT)
```

**Main Loop:**
```python
while True:
    # 1. Get market data
    data = fetch_klines(symbol, '5m', 100)
    
    # 2. Analyze with strategy
    signal = strategy.analyze(data)
    
    # 3. Execute if BUY or SELL
    if signal == 'BUY':
        place_buy_order()
    elif signal == 'SELL' and has_position:
        place_sell_order()
    
    # 4. Check stop loss / take profit
    check_risk_management()
    
    # 5. Save position state
    save_position_to_file()
    
    # 6. Wait 15 minutes
    sleep(900)
```

---

### 3. Core Modules (`core/`)

#### `binance_client.py`
**Purpose:** Wrapper around Binance API

**Key Methods:**
```python
get_account_balance(asset)      # Check balance
get_klines(symbol, interval)    # Get price data
place_market_order(symbol, side, qty)  # Execute trade
get_current_price(symbol)       # Get current price
is_symbol_tradeable(symbol)     # Validate symbol
```

**Features:**
- Handles API errors gracefully
- Supports testnet and mainnet
- Formats quantities correctly
- Validates trading symbols

#### `config.py`
**Purpose:** Centralized configuration management

**Key Features:**
- Loads settings from `.env` file
- Validates configuration on startup
- Provides easy access to all settings
- Hides sensitive data in logs

**Configuration Categories:**
1. API Credentials (Binance, OpenAI, etc.)
2. Trading Settings (symbol, amount, interval)
3. Technical Indicators (RSI, MACD periods)
4. Risk Management (stop loss, take profit)
5. Optional Features (SMS, AI news)

---

### 4. Trading Strategies (`strategies/`)

**Purpose:** Contain trading logic

**Base Requirements:**
All strategies must implement:
```python
class MyStrategy:
    def analyze(self, data):
        """
        Analyze market data and return signal
        
        Args:
            data: List of klines from Binance
        
        Returns:
            dict: {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'reasoning': 'Why this signal',
                'recommended_symbol': 'BTCUSDT'  # optional
            }
        """
        pass
```

**Available Strategies:**

1. **volatile_coins_strategy.py**
   - Technical analysis only
   - RSI, MACD, Bollinger Bands
   - Good for any coin

2. **ticker_news_strategy.py**
   - AI-powered with news
   - Combines technical + sentiment
   - Requires OpenAI + CryptoNews API

3. **simple_profitable_strategy.py**
   - Balanced approach
   - Conservative entries
   - Good for beginners

4. **enhanced_strategy.py**
   - Advanced indicators
   - Market regime detection
   - Dynamic position sizing

---

## Data Flow

### Creating a Bot

```
User fills form in browser
        ↓
JavaScript sends POST to /api/create-bot
        ↓
simple_dash.py receives request
        ↓
Validates coin symbol with Binance
        ↓
Creates new bot entry in active_bots.json:
{
    "id": 1,
    "name": "BTC Bot",
    "symbol": "BTCUSDT",
    "strategy": "volatile",
    "trade_amount": 100,
    "status": "stopped",
    "profit": 0,
    "trades": 0
}
        ↓
Returns success to browser
        ↓
Dashboard refreshes and shows new bot
```

---

### Starting a Bot

```
User clicks "Start" button
        ↓
JavaScript sends POST to /api/bot/1/start
        ↓
simple_dash.py executes:
screen -dmS bot_1 python3 integrated_trader.py 1 'BTC Bot' BTCUSDT volatile 100
        ↓
New background process starts
        ↓
integrated_trader.py initializes:
  • Loads strategy
  • Connects to Binance
  • Checks for saved position
  • Starts main loop
        ↓
Dashboard updates status to "running"
```

---

### Trading Flow

```
Bot main loop wakes up (every 15 minutes)
        ↓
Fetches last 100 5-minute candles from Binance
        ↓
Passes data to strategy.analyze()
        ↓
Strategy calculates indicators (RSI, MACD, etc.)
        ↓
Strategy returns signal: BUY, SELL, or HOLD
        ↓
If BUY and no position:
  • Check USDT balance
  • Calculate quantity
  • Place market buy order
  • Save position to file
  • Log trade
        ↓
If SELL and has position:
  • Get current balance
  • Place market sell order
  • Calculate profit
  • Clear position file
  • Log trade
        ↓
If HOLD or already has position:
  • Check stop loss / take profit
  • Log current status
        ↓
Sleep for 15 minutes
        ↓
Loop continues...
```

---

### Displaying Bot Status

```
Browser requests /api/overview (every 30 seconds)
        ↓
simple_dash.py:
  • Reads active_bots.json
  • Checks which bots are running (screen -list)
  • Queries Binance for account balance
  • Reads bot log files for last activity
        ↓
For each bot:
  • Parse log for last timestamp
  • Calculate profit from trades
  • Count number of trades
  • Get current position info
        ↓
Returns JSON with all data
        ↓
JavaScript updates dashboard:
  • Shows balance, profit, trades
  • Updates countdown timers
  • Refreshes bot cards
  • Updates charts
```

---

## How Trading Works

### Position Management

**One Position at a Time:**
Each bot only holds ONE position in ONE coin at any time.

**Position States:**
```
NO POSITION (waiting to buy)
        ↓ BUY signal
LONG POSITION (holding coin, waiting to sell)
        ↓ SELL signal or stop loss triggered
NO POSITION (back to waiting)
```

**Position Persistence:**
Bots save position data to `bot_X_position.json`:
```json
{
    "position": "LONG",
    "entry_price": 50000.00,
    "stop_loss": 49000.00,
    "take_profit": 52500.00,
    "symbol": "BTCUSDT",
    "has_traded": true,
    "initial_investment": 100.00,
    "timestamp": "2025-10-24T10:30:00"
}
```

If bot crashes or restarts, it loads this file and continues managing the position.

---

### Trade Amount Logic

**First Trade:**
- Uses configured `trade_amount` from bot settings
- Example: Bot has trade_amount = $100
- Buys $100 worth of Bitcoin

**Subsequent Trades:**
- Uses ALL available USDT (reinvests everything)
- Example: Sold Bitcoin for $105
- Next buy uses all $105
- This compounds profits over time!

**Why This Works:**
- Profit stays in the account
- Each trade uses more money (if profitable)
- Losses are limited to initial investment

---

### Risk Management

**Automatic Stop Loss:**
- Set when position opens (default: -2%)
- If price drops below: auto-sell
- Limits losses on bad trades

**Automatic Take Profit:**
- Set when position opens (default: +5%)
- If price rises above: auto-sell
- Locks in gains

**Example:**
```
Buy Bitcoin @ $50,000
Stop Loss = $49,000 (2% below)
Take Profit = $52,500 (5% above)

If price drops to $49,000 → AUTO SELL
If price rises to $52,500 → AUTO SELL
```

---

## File Structure

### Configuration Files

```
.env                    # Your settings (API keys, etc.)
active_bots.json       # Bot configurations
bot_1_position.json    # Bot 1's current position
bot_2_position.json    # Bot 2's current position
```

### Log Files

```
bot_1.log              # Bot 1's activity log
bot_2.log              # Bot 2's activity log
```

Log Format:
```
2025-10-24 10:30:00 - INFO - 🤖 STARTING BOT: BTC Bot
2025-10-24 10:30:15 - INFO - 📊 Position: LONG @ $50000.00 | Current: $50500.00 | P&L: +1.00%
2025-10-24 10:45:00 - INFO - ⏳ Waiting for signal... (Current: HOLD, Price: $50600.00)
2025-10-24 11:00:00 - INFO - 🔴 SELL signal generated!
2025-10-24 11:00:05 - INFO - 🔴 CLOSED POSITION: BTC Bot
2025-10-24 11:00:05 - INFO -    Exit: $51000.00
2025-10-24 11:00:05 - INFO -    Profit: $100.00 (+2.00%)
```

---

## Process Management

### Screen Sessions

Bots run in `screen` sessions (virtual terminals that persist after SSH logout).

**Why Screen?**
- Bots continue running even if you close terminal
- Each bot has isolated environment
- Easy to view individual bot output
- Simple to stop specific bots

**Useful Commands:**
```bash
# List all running bots
screen -ls

# Attach to a bot to see live output
screen -r bot_1

# Detach (leave it running)
# Press: Ctrl+A, then D

# Kill a specific bot
screen -S bot_1 -X quit

# Kill all bots
pkill screen
```

### Dashboard Process

Dashboard runs in foreground (needs to stay open):
```bash
python3 simple_dash.py

# Access from browser
open http://localhost:5001
```

To run dashboard in background:
```bash
# Option 1: Screen
screen -dmS dashboard python3 simple_dash.py

# Option 2: nohup
nohup python3 simple_dash.py &

# Option 3: tmux
tmux new -d -s dashboard 'python3 simple_dash.py'
```

---

## Error Handling

### Bot Crashes

If a bot crashes:
1. Position data is saved (bot_X_position.json)
2. All trades logged to bot_X.log
3. Restart bot from dashboard
4. Bot loads saved position and continues

### API Errors

If Binance API fails:
1. Bot logs the error
2. Waits 15 minutes
3. Retries automatically
4. No trades lost

### Insufficient Balance

If not enough USDT to trade:
1. Bot logs warning
2. Waits for balance
3. Does not place order
4. Continues checking every 15 minutes

---

## Security Considerations

### API Keys

- Stored in `.env` (never committed to Git)
- Dashboard only reads them
- Bots use them to trade
- Enable only necessary permissions on Binance

### Recommended Binance API Settings

Enable:
- ✅ Read Info
- ✅ Enable Spot & Margin Trading

Disable:
- ❌ Enable Withdrawals
- ❌ Enable Futures
- ❌ Enable Margin

### Network Security

- Dashboard listens on `0.0.0.0:5001` (all interfaces)
- No authentication (use localhost only or add auth)
- Consider using SSH tunnel for remote access

---

## Performance Optimization

### Bot Check Interval

Default: 15 minutes (900 seconds)

**Trade-offs:**
- Shorter (5 min): More responsive, more API calls, higher costs
- Longer (30 min): Fewer API calls, may miss opportunities

**Recommendation:** 15 minutes is a good balance

### Data Caching

Dashboard caches:
- Account balance (30 seconds)
- Bot status (refreshes on each request)
- Log files (read on demand)

### Concurrent Bots

You can run unlimited bots simultaneously:
- Each bot is independent
- Shared USDT balance (first bot to trade gets it)
- Separate log files
- No performance impact until 10+ bots

---

## Scalability

### Current Limits

- Bots: Unlimited (practical limit ~10)
- Dashboard: Single instance
- Database: JSON files (works for <50 bots)

### If You Need More

For heavy usage (50+ bots):
1. Replace JSON with SQLite/PostgreSQL
2. Use Redis for caching
3. Run multiple dashboard instances (load balancer)
4. Use proper process manager (systemd, supervisord)

---

## Monitoring

### Dashboard Monitoring

- Real-time overview of all bots
- Profit tracking
- Trade counts
- Individual bot details
- Log viewing

### Manual Monitoring

```bash
# Check bot status
screen -ls

# View live logs
tail -f bot_1.log

# Check account balance
python3 utils/test_connection.py

# View all log files
ls -lh bot_*.log
```

### SMS Monitoring

Enable SMS notifications:
- Get 6-hour summaries
- Manual alerts from dashboard
- Trade notifications (optional)

---

## Extending the System

### Adding New Strategies

1. Create new file in `strategies/`
2. Implement `analyze(data)` method
3. Return signal dict with 'signal' and 'reasoning'
4. Add to STRATEGIES dict in `integrated_trader.py`
5. Strategy becomes available in dashboard!

### Adding New Features

**Custom Indicators:**
- Add to strategy's `analyze()` method
- Use `ta` library for technical indicators

**New Dashboard Pages:**
- Add route in `simple_dash.py`
- Add HTML in the HTML string
- Add API endpoint if needed

**New Risk Rules:**
- Modify `execute_trade()` in `integrated_trader.py`
- Add validation before placing orders

---

## Debugging

### Common Issues

**Bot won't start:**
```bash
# Check logs
cat bot_1.log

# Test connection
python3 utils/test_connection.py

# Verify API keys
grep BINANCE_API_KEY .env
```

**No trades happening:**
- Check logs for signal info
- Strategies are selective (may wait hours/days)
- Verify sufficient balance

**Dashboard not updating:**
- Hard refresh browser (Ctrl+Shift+R)
- Check Flask is running
- Verify port 5001 not blocked

---

This architecture allows for:
- ✅ Easy to understand and modify
- ✅ Scales to multiple bots
- ✅ Survives crashes and restarts
- ✅ Simple to deploy and maintain
- ✅ Clear separation of concerns

Happy trading! 🚀

