# 🤖 Trading Bot - Complete System

A professional-grade cryptocurrency trading bot with backtesting, live trading, and monitoring dashboards.

---

## 🚀 Quick Start

### 1. Backtest Strategies
```bash
python3 quick_backtest.py
```
Test different strategies on historical data to find what works.

### 2. Deploy Live Bot
```bash
python3 live_trader.py
```
Run your chosen strategy on Binance (testnet or mainnet).

### 3. Monitor in Real-Time
```bash
# Terminal dashboard
python3 dashboard.py

# OR web dashboard
python3 web_dashboard.py
# Open: http://localhost:5000
```

---

## 📁 File Structure

### Core Files
- **`quick_backtest.py`** - Interactive backtesting tool
- **`live_trader.py`** - Live trading bot with safety features
- **`dashboard.py`** - Terminal-based monitoring
- **`web_dashboard.py`** - Web-based dashboard
- **`test_all_combinations.py`** - Test all strategy/coin combinations

### Trading Components
- **`binance_client.py`** - Binance API interface
- **`config.py`** - Configuration management
- **`position_manager.py`** - Position tracking
- **`trading_bot.py`** - Core bot logic (alternative runner)

### Strategies (`strategies/` folder)
1. **`simple_profitable_strategy.py`** ⭐ **RECOMMENDED**
   - Best for beginners
   - Works on all coins
   - Balanced risk/reward

2. **`enhanced_strategy.py`**
   - Advanced indicators
   - Market regime detection
   - Dynamic position sizing

3. **`volatile_coins_strategy.py`**
   - For high-volatility altcoins
   - Wider stops
   - Stricter entry criteria

4. **`mean_reversion_strategy.py`**
   - For ranging markets
   - Buy dips, sell rips
   - Mean reversion based

5. **`breakout_strategy.py`**
   - For trending markets
   - Catches momentum moves
   - Volume confirmation

6. **`conservative_strategy.py`**
   - Ultra-selective
   - High win rate
   - Lower frequency

### Documentation
- **`QUICK_DEPLOY.md`** - 5-minute deployment guide
- **`LIVE_TRADING_GUIDE.md`** - Complete live trading manual
- **`STRATEGY_GUIDE.md`** - Strategy selection guide
- **`DATA_LIMITS.md`** - Binance API data limits
- **`QUICKSTART.md`** - General quick start

---

## 🎯 Use Cases

### I want to backtest strategies
```bash
python3 quick_backtest.py
```

### I want to find the best strategy
```bash
python3 test_all_combinations.py
```

### I want to trade live
```bash
python3 live_trader.py
```

### I want to monitor my bot
```bash
python3 dashboard.py
# OR
python3 web_dashboard.py
```

---

## ⚙️ Configuration

Edit `.env` file:

```bash
# Binance API Keys
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# Trading Mode
USE_TESTNET=true    # true = fake money (SAFE)
                     # false = real money (LIVE)

# Risk Management (optional)
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0
```

---

## 📊 Features

### Backtesting
- ✅ Test any strategy on historical data
- ✅ Multiple timeframes (5m, 15m, 1h, 4h)
- ✅ All major trading pairs
- ✅ Detailed performance metrics
- ✅ Export to CSV

### Live Trading
- ✅ Automatic trade execution
- ✅ Stop loss & take profit
- ✅ Position management
- ✅ Risk controls
- ✅ Emergency stop (Ctrl+C)
- ✅ Detailed logging

### Monitoring
- ✅ Real-time balance tracking
- ✅ Open position monitoring
- ✅ Trade history
- ✅ Profit/loss calculation
- ✅ Auto-refresh dashboards
- ✅ Web and terminal interfaces

### Safety Features
- ✅ Testnet support (fake money)
- ✅ Automatic stop losses
- ✅ Position limits
- ✅ Clean shutdown
- ✅ Detailed logs
- ✅ Error handling

---

## 💡 Recommended Workflow

### 1. Backtest (Day 1)
```bash
# Test different strategies
python3 quick_backtest.py

# Find best performers
python3 test_all_combinations.py
```

**Look for:**
- Return: >+5%
- Win rate: >50%
- Profit factor: >1.5

### 2. Testnet (Days 2-8)
```bash
# Set USE_TESTNET=true in .env
python3 live_trader.py
```

**Monitor for:**
- Actual trade frequency
- Real-world performance
- Bot behavior

### 3. Live Trading (Day 9+)
```bash
# Set USE_TESTNET=false in .env
# START WITH SMALL AMOUNTS!
python3 live_trader.py
```

**Best practices:**
- Start with $10-50 per trade
- Monitor daily
- Withdraw profits weekly
- Stop if losing >10%

---

## 🎓 Learning Path

### Beginner
1. Read `QUICK_DEPLOY.md`
2. Run `quick_backtest.py`
3. Test on testnet for 1 week
4. Start live with $10-20 trades

**Use:** Simple Profitable Strategy on BTCUSDT

### Intermediate
1. Read `LIVE_TRADING_GUIDE.md`
2. Test multiple strategies
3. Run `test_all_combinations.py`
4. Testnet for 2 weeks
5. Live with $50-100 trades

**Use:** Enhanced or Conservative strategies

### Advanced
1. Read `STRATEGY_GUIDE.md`
2. Understand all strategies
3. Test on volatile coins
4. Customize parameters
5. Monitor performance metrics

**Use:** Different strategies for different coins

---

## 📈 Expected Performance

### Realistic Monthly Returns:
- **Conservative:** 2-5%
- **Moderate:** 5-10%
- **Aggressive:** 10-20%

### Warning Signs:
- ❌ Win rate <40%
- ❌ Multiple consecutive losses (5+)
- ❌ Large drawdowns (>15%)

**Remember:** Even good strategies have losing periods!

---

## 🛠️ Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp env_template.txt .env
# Edit .env with your API keys

# Test connection
python3 test_connection.py
```

---

## 📱 Dashboards

### Terminal Dashboard
```bash
python3 dashboard.py
```

**Features:**
- Real-time balance
- Recent trades
- Auto-refresh
- No extra dependencies

### Web Dashboard
```bash
python3 web_dashboard.py
# Open browser: http://localhost:5000
```

**Features:**
- Beautiful UI
- Charts and graphs
- Access from any device
- Real-time updates

**Requires:** `pip install flask`

---

## 🚨 Emergency Procedures

### Stop the Bot
```bash
# In live_trader terminal
Press Ctrl+C

# Bot will:
1. Close open positions
2. Save all trades
3. Show summary
```

### Force Stop
```bash
# Press Ctrl+C twice
# Then manually close positions on Binance
```

### Withdraw Funds
1. Stop bot (Ctrl+C)
2. Go to Binance.com
3. Wallet → Spot → Withdraw
4. Send to your wallet

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `QUICK_DEPLOY.md` | 5-minute deployment guide |
| `LIVE_TRADING_GUIDE.md` | Complete live trading manual |
| `STRATEGY_GUIDE.md` | When to use each strategy |
| `DATA_LIMITS.md` | API limits and solutions |
| `QUICKSTART.md` | General quick start |

---

## 🎯 Strategy Selection

### For BTC/ETH (stable pairs):
- ✅ Simple Profitable
- ✅ Enhanced
- ✅ Conservative

### For Altcoins (SOL, AVAX, etc):
- ✅ Volatile Coins
- ✅ Breakout
- Maybe: Enhanced

### For Ranging Markets:
- ✅ Mean Reversion
- ✅ Conservative

### For Trending Markets:
- ✅ Breakout
- ✅ Enhanced
- ✅ Simple Profitable

---

## ⚠️ Important Warnings

1. **Start with Testnet**
   - Always test with fake money first
   - Minimum 1 week on testnet

2. **Risk Management**
   - Only risk money you can afford to lose
   - Start with small amounts
   - Never use entire balance per trade

3. **Monitoring**
   - Check bot daily
   - Review trades weekly
   - Stop if performance degrades

4. **Market Conditions**
   - Strategies perform differently in different conditions
   - Be prepared for losing periods
   - Stop if losing >10% of capital

---

## 🤝 Support

**Need help?**

1. Check documentation in this folder
2. Review log files (`live_trading_*.log`)
3. Test on testnet first
4. Start with small amounts

**Common Issues:**
- API errors → Check keys in `.env`
- No trades → Strategy is selective (normal)
- Losses → Check if strategy matches market conditions

---

## 📊 Performance Tracking

### Daily:
- Check dashboard
- Review log file
- Calculate P&L

### Weekly:
- Total trades count
- Win rate calculation
- Compare to backtest results
- Adjust if needed

### Monthly:
- Overall performance review
- Withdraw profits
- Strategy evaluation
- Portfolio rebalancing

---

## 🔧 Troubleshooting

### Bot won't start
→ Check API keys in `.env`
→ Run `python3 test_connection.py`

### No trades happening
→ Normal - strategy is waiting for setup
→ Check log for signals

### Losing money
→ Review strategy performance
→ Check market conditions
→ Consider switching strategies

### Dashboard not working
→ Check bot is running
→ Check log file exists
→ Verify Flask is installed (web only)

---

## 📄 License

MIT License - Use at your own risk. Not financial advice.

---

## ⚡ Quick Reference

```bash
# Backtest
python3 quick_backtest.py

# Test all combinations  
python3 test_all_combinations.py

# Live trade
python3 live_trader.py

# Monitor (terminal)
python3 dashboard.py

# Monitor (web)
python3 web_dashboard.py

# Download data
python3 download_large_dataset.py

# Test connection
python3 test_connection.py
```

---

**Happy Trading! Remember: Start small, test thoroughly, and never risk more than you can afford to lose. 📈💰**