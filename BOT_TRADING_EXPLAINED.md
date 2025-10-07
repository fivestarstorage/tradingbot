# 🤖 **How Your Trading Bot Works (Buy/Sell Cycle)**

## **📋 Quick Answer to Your Questions**

### **Q1: Can the bot recognize insufficient balance?**
✅ **YES - Now it can!** 

I just added:
- ⚠️ Clear warning messages when balance is low
- 💤 Bot pauses for 5 minutes to avoid spam
- 💡 Shows solutions (add USDT, reduce trade amount, sell coins)

### **Q2: Why is it only buying and not selling?**
🎯 **The bot DOES buy AND sell - here's how the cycle works:**

---

## **🔄 The Complete Buy/Sell Trading Cycle**

### **Phase 1: Scanning Mode (No Position)**
```
Bot Status: 🔍 LOOKING FOR OPPORTUNITIES
Position: NONE
What it does:
  • Fetches crypto news every 60 seconds
  • AI analyzes sentiment
  • Looks for BUY signals with 70%+ confidence
  • When found → Goes to Phase 2
```

### **Phase 2: Buy Execution**
```
Bot Status: 💰 BUYING
What it does:
  1. Checks USDT balance (needs trade_amount + 1% for fees)
  2. If insufficient → Shows warning, waits 5 minutes
  3. If sufficient → Places market BUY order
  4. Saves position to file (symbol, entry price, stop loss, take profit)
  5. Sends SMS: "🤖 BUY BTCUSDT @ $60,000"
  6. Goes to Phase 3
```

### **Phase 3: Position Management (Has Position)**
```
Bot Status: 📊 HOLDING BTCUSDT
Position: LONG @ $60,000
What it does:
  • Monitors price every 60 seconds
  • Checks for SELL triggers:
  
  ✅ WILL SELL IF:
    1. Price hits STOP LOSS (e.g., -5% = $57,000)
    2. Price hits TAKE PROFIT (e.g., +5% = $63,000)
    3. AI analyzes NEW news and says "SELL" (70%+ confidence)
    4. Holding time exceeds max_hold_hours (e.g., 72 hours)
  
  When ANY trigger happens → Goes to Phase 4
```

### **Phase 4: Sell Execution**
```
Bot Status: 💵 SELLING
What it does:
  1. Gets current coin balance
  2. Places market SELL order
  3. Calculates profit/loss
  4. Deletes position file
  5. Sends SMS: "💰 SELL BTCUSDT @ $62,000 | Profit: +$20.00 (+3.33%)"
  6. Goes back to Phase 1 (Scanning Mode)
```

---

## **🚨 Common Issues & Fixes**

### **Issue 1: Bot bought but never sells**
**Causes:**
- Bot crashed/restarted and lost position file
- Stop loss/take profit not triggered yet
- AI keeps saying HOLD (not enough negative news)

**Solution:**
```bash
# NEW FEATURE: Bot now auto-detects orphaned coins!
# When bot starts, it checks:
#   1. Do I have coins in wallet?
#   2. Do I have a position file?
#   3. If YES to #1 and NO to #2 → Auto-track the coin
```

**You'll see this in logs:**
```
⚠️  ORPHANED POSITION DETECTED
Found 0.001 BTC in wallet
But no position file exists for this bot
🤖 Bot will now monitor this position
   Will sell when:
   • AI signals SELL
   • Price drops significantly
```

---

### **Issue 2: Insufficient balance errors**
**Causes:**
- Bot tried to buy but you only have $10 and trade_amount is $100
- All your USDT is tied up in other coins

**Solution:**
```bash
# Bot now shows this warning:
⚠️  INSUFFICIENT USDT BALANCE - CANNOT TRADE
Required: $101.00 (includes 1% for fees)
Available: $10.00
Shortfall: $91.00

💡 Solutions:
   1. Add more USDT to your Binance account
   2. Reduce bot trade amount
   3. Sell existing coins to free up USDT

# Bot then sleeps for 5 minutes to avoid spam
```

**How to fix:**
```bash
# Option A: Add more USDT to Binance
# Option B: Edit bot trade amount via dashboard
# Option C: Manually sell coins to free up USDT
```

---

### **Issue 3: "Error formatting quantity: list index out of range"**
**Causes:**
- Binance symbol info not loading properly
- Network issue connecting to Binance
- Symbol doesn't exist on Binance

**What bot does now:**
- ✅ Better error handling
- ✅ Falls back to safe 6 decimal precision
- ✅ Shows detailed error logs
- ✅ Trade still goes through (might fail, but won't crash bot)

---

## **📊 Example: Full Trading Session**

```
🕐 00:00 - Bot starts, no position
          Status: 🔍 Scanning news...

🕐 00:05 - AI finds bullish BTC news (85% confidence)
          Status: 💰 Executing BUY
          • Checks balance: $100 available ✓
          • Buys 0.001 BTC @ $60,000
          • SMS: "🤖 BUY BTCUSDT @ $60,000"
          • Saves position file

🕐 00:06 - 12:00 (12 hours)
          Status: 📊 Monitoring position
          • Current: $61,500 (+2.5%)
          • Stop Loss: $57,000
          • Take Profit: $63,000
          • AI says: HOLD (no major news)

🕐 12:15 - Price hits $63,100
          Status: 💵 Executing SELL (Take Profit!)
          • Sells 0.001 BTC @ $63,100
          • Profit: +$3.10 (+5.17%)
          • SMS: "💰 SELL BTCUSDT @ $63,100 | Profit: +$3.10 (+5.17%)"
          • Deletes position file

🕐 12:16 - Back to scanning mode
          Status: 🔍 Scanning for next opportunity...
```

---

## **🔧 How to Check Bot Status**

### **On your server:**
```bash
# View bot logs
screen -r bot_2

# See recent log entries
tail -f /root/tradingbot/bot_logs/bot_2.log

# Check what coins you have
python3 test_api_connection.py
```

### **On your dashboard:**
```
Open: http://134.199.159.103:5000

Look for:
  • 📊 ACTIVE POSITION panel
    Shows: Current position, entry price, P&L, AI reasoning
  
  • Bot status: "running" or "stopped"
  
  • 📋 Recent logs
    Filter by bot ID, search for "BUY" or "SELL"
```

---

## **💡 Pro Tips**

### **1. Speed up selling**
If you want bot to sell faster:
- Lower `take_profit_pct` (e.g., 3% instead of 5%)
- Lower `stop_loss_pct` (e.g., 3% instead of 5%)
- Reduce `max_hold_hours` (e.g., 24 instead of 72)

### **2. Be more selective with buys**
If bot buys too often:
- Increase `min_confidence` (e.g., 80% instead of 70%)
- Reduce trade_amount (bot will be more cautious)

### **3. Handle orphaned coins**
If you have coins from old bot runs:
```bash
# Option A: Let bot auto-detect and manage them (NEW!)
#   Just start the bot with same symbol (BTCUSDT)
#   Bot will see the coins and start managing

# Option B: Manually sell via dashboard
#   (Coming soon)

# Option C: Sell via Binance app manually
```

### **4. Free up USDT**
If you're stuck with coins and need USDT:
```bash
# Check what you have
python3 test_api_connection.py

# Sell manually via Binance app, OR
# Start a bot with that symbol and let it manage/sell
```

---

## **🎯 TL;DR**

**Your bot:**
1. ✅ **Scans** news continuously
2. ✅ **Buys** when AI is 70%+ confident
3. ✅ **Holds** and monitors price + news
4. ✅ **Sells** when stop-loss/take-profit hit OR AI says sell
5. ✅ **Repeats** the cycle

**New features added today:**
- ⚠️ Better "insufficient balance" warnings
- 🔍 Auto-detection of orphaned coins in wallet
- 📊 Will manage coins even if position file was lost
- 💤 Pauses for 5 min when out of money (avoids spam)

**To update your server:**
```bash
# SSH to server
ssh root@134.199.159.103

# Pull latest code
cd /root/tradingbot
git pull origin main

# Restart bots (will restart automatically if using auto-deploy)
screen -S bot_2 -X quit
# Then restart from dashboard
```

---

## **❓ Still confused?**

**Check logs for these key events:**
```bash
# Successful buy
grep "✅ BUY order executed" /root/tradingbot/bot_logs/bot_2.log

# Successful sell  
grep "✅ SELL order executed" /root/tradingbot/bot_logs/bot_2.log

# Position tracking
grep "📊 Position:" /root/tradingbot/bot_logs/bot_2.log

# Balance issues
grep "INSUFFICIENT" /root/tradingbot/bot_logs/bot_2.log

# Orphaned coins
grep "ORPHANED" /root/tradingbot/bot_logs/bot_2.log
```

**Dashboard:**
- Look at "📊 ACTIVE POSITION" panel
- Check "Recent Trades" section
- Use log filters to see buy/sell events

**Still stuck?** Share your bot logs and I'll help debug!

