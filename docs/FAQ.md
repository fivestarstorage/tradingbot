# ❓ Frequently Asked Questions (FAQ)

Quick answers to common questions about the trading bot.

---

## 🚀 Getting Started

### Q: Do I need coding knowledge?
**A:** No! Use the web dashboard - it's point-and-click. You only need to:
1. Edit `.env` file (just copy/paste API keys)
2. Run `./start.sh` in terminal
3. Use the web interface for everything else

### Q: How much money do I need to start?
**A:** 
- **Testnet (fake money):** Any amount
- **Real trading:** Minimum $50 per bot (Binance minimums)
- **Recommended:** Start with $100-200 total, split across 2-3 bots

### Q: Is this safe?
**A:** The bot is safe, but trading crypto is risky:
- ✅ Bot has stop losses and risk management
- ✅ Start with testnet (fake money)
- ✅ Only trade what you can afford to lose
- ⚠️ Crypto markets are volatile - you can lose money

### Q: What is testnet?
**A:** Binance's practice environment with fake money:
- Looks and works exactly like real trading
- Perfect for learning without risk
- Use it for 1-2 weeks before going live
- Set `USE_TESTNET=true` in `.env` file

---

## 💻 Technical Setup

### Q: What operating system works?
**A:**
- ✅ macOS (tested)
- ✅ Linux (tested)
- ✅ Windows (with WSL or Git Bash)
- ✅ Raspberry Pi (tested)

### Q: Do I need to keep my computer on?
**A:** Yes, for bots to keep trading. Options:
1. Leave computer/laptop on 24/7
2. Run on VPS/cloud server (DigitalOcean, AWS, etc.)
3. Use Raspberry Pi (cheap, low power)
4. Run during specific hours only

### Q: Can I run this on my phone?
**A:** Not directly, but:
- ✅ Access dashboard from phone browser
- ✅ Monitor and control bots
- ❌ Can't run the Python bot on phone
- Consider: VPS + access from phone

### Q: What's the difference between dashboard and bot?
**A:**
- **Dashboard (`simple_dash.py`)**: Web interface, shows stats, starts/stops bots
- **Bot (`integrated_trader.py`)**: Does the actual trading, runs in background

---

## 🤖 Bot Management

### Q: How many bots can I run?
**A:** Unlimited! But practically:
- 1-3 bots: Perfect for beginners
- 5-10 bots: Good for diversification
- 10+ bots: Advanced, monitor closely

Each bot:
- Trades one coin
- Uses one strategy
- Logs separately
- Independent from others

### Q: Can I run same coin with different strategies?
**A:** Yes! Example:
- Bot 1: BTCUSDT with Volatile Coins strategy
- Bot 2: BTCUSDT with Ticker News strategy
- Bot 3: BTCUSDT with Conservative strategy

They all trade independently.

### Q: How do I stop a bot?
**A:** Three ways:
1. Click "Stop" button in dashboard (easiest)
2. Run `./stop-all-bots.sh` (stops all bots)
3. Manual: `screen -S bot_1 -X quit`

**Important:** Stopping a bot doesn't close positions! The position stays open.

### Q: What happens if I restart a bot?
**A:** Bot remembers everything:
- ✅ Loads saved position from file
- ✅ Continues managing the position
- ✅ Continues where it left off

Position data saved in: `bot_X_position.json`

### Q: Bot won't start - what's wrong?
**A:** Check these:
1. **API Keys**: Make sure they're correct in `.env`
2. **Screen**: Install with `brew install screen` (Mac)
3. **Balance**: Need enough USDT in account
4. **Logs**: Check `cat bot_1.log` for errors

Common errors:
- `API key not found` → Add keys to `.env`
- `Insufficient balance` → Add USDT to account
- `Symbol not found` → Coin doesn't exist on Binance

---

## 💰 Trading & Money

### Q: Why isn't my bot trading?
**A:** This is usually normal! Bots wait for good setups:
- Checks every 15 minutes
- May wait hours or days for signal
- Strategies are selective (fewer, better trades)
- Check logs: `tail -f bot_1.log`

If truly stuck:
- Verify sufficient USDT balance
- Check symbol is correct
- Try different strategy
- Review logs for errors

### Q: How often do bots trade?
**A:** Depends on strategy and market:
- **Volatile Coins**: 1-5 trades per day
- **Ticker News**: 1-3 trades per day
- **Conservative**: 1 trade per week
- **Ranging markets**: Fewer trades
- **Trending markets**: More trades

### Q: How much profit can I expect?
**A:** Realistic expectations:
- **Good months**: 5-15% returns
- **Average months**: 2-5% returns
- **Bad months**: -5% to -10% losses
- **Long-term average**: 2-7% per month

⚠️ **Not guaranteed!** Markets are unpredictable.

### Q: How does the bot manage money?
**A:**
- **First trade**: Uses configured `trade_amount`
- **Subsequent trades**: Reinvests ALL available USDT
- This compounds profits over time
- Losses limited to initial investment

Example:
```
Start: $100
Trade 1: Buy $100 of BTC
Sell: Get back $105 (5% profit)
Trade 2: Buy $105 of ETH (reinvests profit)
Sell: Get back $110
Trade 3: Buy $110 of BTC
... and so on
```

### Q: What are stop loss and take profit?
**A:**
- **Stop Loss**: Auto-sell if price drops X% (limits losses)
- **Take Profit**: Auto-sell if price rises X% (locks in gains)
- Default: 2% stop loss, 5% take profit
- Set automatically on each buy

Example:
```
Buy Bitcoin @ $50,000
Stop Loss = $49,000 (-2%)
Take Profit = $52,500 (+5%)

If price drops to $49,000 → AUTO SELL
If price rises to $52,500 → AUTO SELL
```

### Q: Can I trade with borrowed money (margin)?
**A:** No, and you shouldn't:
- Bot uses spot trading only (no leverage)
- Margin trading is extremely risky
- Could lose more than you have
- Not recommended for bots

---

## 📊 Strategies

### Q: Which strategy should I use?
**A:** Start with these:
- **Beginners**: Volatile Coins strategy (works for any coin)
- **AI/News**: Ticker News strategy (requires API keys)
- **Conservative**: Simple Profitable strategy
- **Learning**: Try each for a few days

See [STRATEGIES.md](STRATEGIES.md) for detailed guide.

### Q: Can I create my own strategy?
**A:** Yes! If you know Python:
1. Create file in `strategies/` folder
2. Implement `analyze(data)` method
3. Return signal dict
4. Add to `integrated_trader.py`

See [STRATEGIES.md](STRATEGIES.md) for details.

### Q: How do I know if a strategy is working?
**A:** Track these metrics:
- **Win Rate**: >50% is good
- **Profit Factor**: >1.5 is good
- **Max Drawdown**: <15% is good
- **Consistency**: Profitable most weeks

Review weekly, not daily!

### Q: Can I switch strategies?
**A:** Not for existing bots. Instead:
1. Stop the bot
2. Delete it (or leave it stopped)
3. Create new bot with different strategy

Each bot's strategy is set at creation.

---

## 🔐 Security & Safety

### Q: Are my API keys safe?
**A:** Yes, if you:
- ✅ Keep `.env` file private (never share)
- ✅ Don't commit `.env` to Git
- ✅ Use API key restrictions on Binance
- ✅ Disable withdrawals on API keys

**Binance API Key Settings (IMPORTANT):**
- Enable: ✅ Read Info, ✅ Spot Trading
- Disable: ❌ Withdrawals, ❌ Margin, ❌ Futures

### Q: Can the bot withdraw my money?
**A:** Only if you enable withdrawals on Binance API:
- **Default**: Withdrawals DISABLED (safe)
- **You control**: Binance API key permissions
- **Bot only**: Reads balance, places trades

Always disable withdrawals on API keys!

### Q: What if my computer gets hacked?
**A:**
- Hacker gets API keys from `.env` file
- Can trade but not withdraw (if you disabled withdrawals)
- Immediately: Delete API keys on Binance
- Create new API keys

### Q: Should I use 2FA?
**A:** Absolutely!
- Enable on Binance account
- Use Google Authenticator or similar
- Required for withdrawals
- Protects your account

---

## 📱 Dashboard & Monitoring

### Q: Dashboard won't open - why?
**A:** Check these:
1. **Is it running?** Look for "Starting dashboard..." message
2. **Correct URL?** Go to: `http://localhost:5001`
3. **Port blocked?** Try different port in `simple_dash.py`
4. **Firewall?** Allow Python through firewall

### Q: How do I access dashboard from another device?
**A:** If on same network:
1. Find computer's IP: `ifconfig` (Mac/Linux) or `ipconfig` (Windows)
2. Open dashboard: `http://192.168.1.X:5001` (replace X with your IP)

For remote access:
- Use VPN
- Or SSH tunnel: `ssh -L 5001:localhost:5001 user@server`
- Or expose port (security risk!)

### Q: Dashboard shows old data
**A:**
- Refreshes automatically every 30 seconds
- Force refresh: `Ctrl+Shift+R` or `Cmd+Shift+R` (Mac)
- Clear browser cache if stuck

### Q: What's the countdown timer?
**A:** Shows when bot will check next:
- Based on last log timestamp
- Counts down from 15 minutes
- "calculating..." = bot hasn't logged yet
- "checking now..." = time for next check

---

## 🐛 Troubleshooting

### Q: "Module not found" error
**A:** Install dependencies:
```bash
pip3 install -r requirements.txt

# If still failing:
python3 -m pip install -r requirements.txt

# Or install individually:
pip3 install python-binance pandas flask ta python-dotenv
```

### Q: "Screen not found"
**A:** Install screen:
```bash
# Mac
brew install screen

# Ubuntu/Debian
sudo apt-get install screen

# CentOS
sudo yum install screen
```

### Q: Bot keeps restarting
**A:** Check logs for errors:
```bash
cat bot_1.log
```

Common causes:
- Invalid API keys
- Insufficient balance
- Invalid symbol
- Binance API error

Fix the issue, then restart bot from dashboard.

### Q: "Connection refused" or API errors
**A:**
1. **Check Binance status**: https://www.binance.com/en/support/announcement
2. **Test connection**: `python3 utils/test_connection.py`
3. **Check API keys**: Make sure they're correct
4. **VPN?**: Binance blocks some countries/VPNs
5. **Rate limits**: Wait a few minutes and retry

### Q: Dashboard shows $0 balance but I have money
**A:**
1. **Wrong account?**: Check testnet vs mainnet in `.env`
2. **API permissions?**: Enable "Read Info" on Binance
3. **Different asset?**: Bot shows USDT, check you have USDT not BTC
4. **Refresh**: Hard refresh browser

---

## 📈 Advanced Features

### Q: Can I backtest strategies?
**A:** Yes!
```bash
python3 utils/backtest_runner.py
```
- Test on historical data
- See what would have happened
- Compare strategies
- No risk, all simulated

### Q: How do SMS notifications work?
**A:**
- Requires Twilio account (free trial available)
- Add credentials to `.env` file
- Get 6-hour trading summaries
- Click "Send Alert" in dashboard to test

See setup guide in [README.md](../README.md).

### Q: Can I use this on a VPS/cloud server?
**A:** Yes! Great for 24/7 trading:
- Use DigitalOcean, AWS, Vultr, etc.
- Recommend: $5-10/month VPS
- SSH in and run like normal
- Access dashboard via SSH tunnel

### Q: Can I trade multiple exchanges?
**A:** Currently only Binance. To add more:
- Would need to create client for that exchange
- Add to code (requires programming)
- Community contributions welcome!

### Q: Is there a mobile app?
**A:** No dedicated app, but:
- ✅ Dashboard works in mobile browser
- ✅ Responsive design
- ✅ Start/stop bots from phone
- ✅ View stats and logs

Just access: `http://your-server-ip:5001`

---

## 💡 Best Practices

### Q: How often should I check the dashboard?
**A:**
- **Minimum**: Once per day
- **Recommended**: 2-3 times per day
- **Review logs**: Once per week
- **Don't**: Check every 5 minutes (anxiety!)

### Q: When should I stop a bot?
**A:** Stop if:
- ❌ Losing consistently (5+ losses in a row)
- ❌ Down >10% from starting capital
- ❌ Strategy not matching market conditions
- ❌ Major news event (wait for clarity)
- ❌ Need to withdraw funds

### Q: Should I reinvest profits?
**A:**
- Bot auto-reinvests (uses all available USDT)
- Consider: Withdraw some profits weekly/monthly
- Keep: Some as "risk capital" for trading
- Withdraw: Anything over your comfort level

Example: Started with $500, now have $650
- Keep $500 in account for trading
- Withdraw $150 profit
- Repeat monthly

### Q: How do I improve performance?
**A:**
1. **Diversify**: Run multiple bots on different coins
2. **Match strategy**: Choose strategy for market conditions
3. **Review logs**: Understand why trades happened
4. **Adjust amounts**: Increase successful bots, decrease losing ones
5. **Be patient**: Good strategies take time
6. **Backtest**: Test before going live

---

## 📚 Learning Resources

### Q: Where can I learn about trading?
**A:**
- [Binance Academy](https://academy.binance.com) - Free courses
- [Investopedia](https://www.investopedia.com) - Trading basics
- [TradingView](https://www.tradingview.com) - Charts and ideas
- YouTube: Search "cryptocurrency trading for beginners"

### Q: Where can I learn about indicators?
**A:**
- **RSI**: Search "RSI indicator explained"
- **MACD**: Search "MACD trading strategy"
- **Bollinger Bands**: Search "Bollinger Bands tutorial"
- Read: [docs/STRATEGIES.md](STRATEGIES.md)

### Q: How do I learn Python to customize?
**A:**
- [Python.org](https://www.python.org/about/gettingstarted/) - Official guide
- [Codecademy](https://www.codecademy.com/learn/learn-python-3) - Interactive
- [Real Python](https://realpython.com/) - Tutorials
- Focus on: functions, classes, APIs

---

## 🆘 Getting Help

### Q: I'm stuck - what should I do?
**A:** Follow this order:
1. **Check logs**: `cat bot_1.log` (often has the answer)
2. **Read docs**: [README.md](../README.md), this FAQ
3. **Test connection**: `python3 utils/test_connection.py`
4. **Search online**: Copy error message → Google it
5. **GitHub issues**: Check if others had same problem

### Q: How do I report a bug?
**A:**
1. Check logs: `cat bot_1.log`
2. Document steps to reproduce
3. Note your setup (OS, Python version)
4. Create GitHub issue with details
5. Include error messages (remove API keys!)

### Q: Can I contribute to the project?
**A:** Yes! Contributions welcome:
- 🐛 Report bugs
- 💡 Suggest features
- 📚 Improve documentation
- 🔧 Submit code improvements
- 📊 Share custom strategies

---

## ⚠️ Important Disclaimers

### Q: Is this financial advice?
**A:** NO! This is educational software only:
- Not financial advice
- Not investment advice
- Use at your own risk
- We're not responsible for losses

### Q: Can I get rich with this?
**A:** Probably not:
- Realistic: 2-7% per month average
- Not a "get rich quick" scheme
- Requires monitoring and patience
- You can lose money
- Most traders lose money

Be realistic and responsible!

### Q: Is this legal?
**A:** Yes, in most countries:
- ✅ Automated trading is legal
- ✅ Using bots is allowed on Binance
- ⚠️ Check your local laws regarding crypto
- ⚠️ Report profits for taxes

---

## Still Have Questions?

- 📖 Read: [README.md](../README.md) - Main documentation
- 🏗️ Read: [ARCHITECTURE.md](../ARCHITECTURE.md) - How it all works
- 📊 Read: [STRATEGIES.md](STRATEGIES.md) - Strategy details
- ⚡ Read: [QUICKSTART.md](../QUICKSTART.md) - Get started fast

---

**Happy Trading! 🚀💰**

Remember: Start small, test thoroughly, and never risk more than you can afford to lose!

