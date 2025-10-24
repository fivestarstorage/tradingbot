# 🧹 Clean Start Guide - Delete All Bots and Auto-Create Fresh

## **Problem:**
You have mixed old and new bots with different strategies.

## **Solution:**
Delete ALL bots → Restart dashboard → Auto-manager creates fresh Ticker News bots for ALL coins!

---

## **Step-by-Step Clean Start:**

### **Step 1: SSH to Server**
```bash
ssh root@134.199.159.103
cd /root/tradingbot
```

### **Step 2: Stop ALL Bots**
```bash
# Kill all running bot processes
pkill -f "integrated_trader.py"

# Kill all bot screen sessions
screen -ls | grep bot_ | awk '{print $1}' | xargs -I {} screen -X -S {} quit

# Verify all stopped
screen -ls
# Should show NO bot_* sessions
```

### **Step 3: Delete Bot Data Files**
```bash
# Delete bot configuration
rm active_bots.json

# Delete bot PIDs
rm bot_pids.json

# Delete bot position files (optional, keeps history if you skip)
rm bot_*_position.json

# Verify deletion
ls -la *.json
```

### **Step 4: Restart Dashboard**
```bash
# Stop dashboard
screen -X -S dashboard quit

# Start dashboard (auto-manager will run!)
screen -dmS dashboard python3 advanced_dashboard.py

# Watch the magic happen
screen -r dashboard
```

### **Step 5: Watch Auto-Manager Work**

You'll see:
```
🔍 Checking for orphaned coins...
⚠️  Found X orphaned coin(s):
   • BTC: 0.00015984
   • ETH: 0.00419580
   • BNB: 0.01481395
   • SOL: 0.90900000
   • DOGE: [amount]

💰 Available USDT: $XXX.XX

🤖 Auto-creating Ticker News Trading bots...

   ✅ Created: 📰 BTC News Trader (Bot #1)
      Symbol: BTCUSDT
      Strategy: Ticker News Trading
      Allocated USDT: $100.00
      🚀 Starting bot...
      ✅ Bot started successfully!

   ✅ Created: 📰 ETH News Trader (Bot #2)
      Symbol: ETHUSDT
      Strategy: Ticker News Trading
      Allocated USDT: $100.00
      🚀 Starting bot...
      ✅ Bot started successfully!

   ✅ Created: 📰 BNB News Trader (Bot #3)
      Symbol: BNBUSDT
      Strategy: Ticker News Trading
      Allocated USDT: $100.00
      🚀 Starting bot...
      ✅ Bot started successfully!

   ✅ Created: 📰 SOL News Trader (Bot #4)
      Symbol: SOLUSDT
      Strategy: Ticker News Trading
      Allocated USDT: $100.00
      🚀 Starting bot...
      ✅ Bot started successfully!

   ✅ Created: 📰 DOGE News Trader (Bot #5)
      Symbol: DOGEUSDT
      Strategy: Ticker News Trading
      Allocated USDT: $100.00
      🚀 Starting bot...
      ✅ Bot started successfully!

💰 Total USDT Allocated: $500.00
💰 Remaining USDT: $XXX.XX

🚀 All auto-created bots have been STARTED automatically!
   They are now monitoring news and managing positions.
```

**Press Ctrl+A then D to detach**

### **Step 6: Verify on Dashboard**

Go to: **http://134.199.159.103:5001**

You should now see:
```
📰 BTC News Trader - RUNNING ✓ - Ticker News
📰 ETH News Trader - RUNNING ✓ - Ticker News
📰 BNB News Trader - RUNNING ✓ - Ticker News
📰 SOL News Trader - RUNNING ✓ - Ticker News
📰 DOGE News Trader - RUNNING ✓ - Ticker News
```

**All the same strategy, all running, all clean!** ✨

---

## **Verify Bots Are Working:**

### **Check Screen Sessions:**
```bash
screen -ls

You should see:
bot_1 (Running)
bot_2 (Running)
bot_3 (Running)
bot_4 (Running)
bot_5 (Running)
```

### **View Live Logs:**
```bash
# View BTC bot
screen -r bot_1

# View ETH bot
screen -r bot_2

# etc...

# Press Ctrl+A then D to detach
```

---

## **What Each Bot Will Do:**

### **Upon Starting:**
1. ✅ Detect existing position (e.g., 0.9 SOL)
2. ✅ Set entry price at current market
3. ✅ Apply stop-loss (-3%)
4. ✅ Apply take-profit (+5%)
5. ✅ Fetch news for ticker
6. ✅ Analyze with AI
7. ✅ Make decision: HOLD/BUY/SELL

### **Ongoing (Every 15 Minutes):**
- Check position
- Check stop-loss/take-profit
- Log status

### **Every Hour:**
- Fetch fresh news
- AI analysis
- Trading decision

---

## **Expected Dashboard After Clean Start:**

```
┌─────────────────────────────────────────────────────┐
│ 💰 Available Balance:       $XXX.XX                  │
│ 🔒 In Orders:               $0.00                   │
│ 💵 Total Balance:           $XXX.XX                  │
│ 🤖 Allocated to Bots:       $500.00                 │
│ ✨ Available for Allocation: $XXX.XX                │
└─────────────────────────────────────────────────────┘

🤖 Trading Bots (5)

📰 BTC News Trader
RUNNING ✓
📈 BTCUSDT
🎯 TICKER NEWS TRADING
💰 Allocated: $100.00
📊 Managing: 0.00015984 BTC ($0.21)

📰 ETH News Trader
RUNNING ✓
📈 ETHUSDT
🎯 TICKER NEWS TRADING
💰 Allocated: $100.00
📊 Managing: 0.00419580 ETH ($510.87)

📰 BNB News Trader
RUNNING ✓
📈 BNBUSDT
🎯 TICKER NEWS TRADING
💰 Allocated: $100.00
📊 Managing: 0.01481395 BNB ($65.97)

📰 SOL News Trader
RUNNING ✓
📈 SOLUSDT
🎯 TICKER NEWS TRADING
💰 Allocated: $100.00
📊 Managing: 0.90900000 SOL ($199.99)

📰 DOGE News Trader
RUNNING ✓
📈 DOGEUSDT
🎯 TICKER NEWS TRADING
💰 Allocated: $100.00
📊 Managing: [amount] DOGE ($XX.XX)
```

**Clean, consistent, all running!** ✨

---

## **Why Clean Start?**

### **Benefits:**
```
✅ All bots same strategy (Ticker News)
✅ All bots same naming convention
✅ All bots auto-started
✅ No confusion
✅ No mixed strategies
✅ Fresh allocation tracking
✅ Clean logs
✅ Easy to manage
```

### **vs Keeping Old Bots:**
```
❌ Mixed strategies (AI Autonomous vs Ticker News)
❌ Different naming conventions
❌ Some stopped, some running
❌ Confusing
❌ Old allocation data
❌ Messy logs
❌ Hard to manage
```

---

## **Quick Commands (Copy-Paste):**

```bash
# Complete clean start (ONE command block):
ssh root@134.199.159.103 << 'EOF'
cd /root/tradingbot
pkill -f "integrated_trader.py"
screen -ls | grep bot_ | awk '{print $1}' | xargs -I {} screen -X -S {} quit
rm -f active_bots.json bot_pids.json bot_*_position.json
screen -X -S dashboard quit
sleep 2
screen -dmS dashboard python3 advanced_dashboard.py
echo "✅ Clean start complete! Check dashboard in 10 seconds..."
sleep 10
screen -ls
EOF

# Then check dashboard:
# http://134.199.159.103:5001
```

---

## **Troubleshooting:**

### **"Auto-manager created no bots"**

**Cause:** No coins in wallet or all have $0 balance

**Solution:**
```bash
# Check your balances
python3 -c "
from binance_client import BinanceClient
import os
from dotenv import load_dotenv

load_dotenv()
client = BinanceClient(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET'),
    testnet=os.getenv('USE_TESTNET', 'true').lower() == 'true'
)

account = client.client.get_account()
print('Coins with balance:')
for bal in account['balances']:
    total = float(bal['free']) + float(bal['locked'])
    if total > 0 and bal['asset'] != 'USDT':
        print(f\"  {bal['asset']}: {total}\")
"
```

### **"Bots created but not started"**

**Cause:** Auto-start failed

**Solution:**
```bash
# Start bots manually from dashboard
# Or check logs:
screen -r dashboard
# Look for "Failed to start" messages
```

### **"Dashboard shows old bots"**

**Cause:** Didn't delete active_bots.json

**Solution:**
```bash
# Delete and restart
rm active_bots.json
screen -X -S dashboard quit
screen -dmS dashboard python3 advanced_dashboard.py
```

---

## **Summary:**

**What You Need to Do:**
```
1. SSH to server
2. Run the clean start commands
3. Wait 10 seconds
4. Check dashboard
5. All bots running! ✅
```

**What You'll Get:**
```
✅ Fresh Ticker News bots for all coins
✅ All auto-started
✅ All same strategy
✅ Clean dashboard
✅ Ready to trade
```

**Time Required:** ~30 seconds

**Effort Required:** Copy-paste ONE command block ✨

---

**Let's get you a clean, automated trading setup!** 🚀
