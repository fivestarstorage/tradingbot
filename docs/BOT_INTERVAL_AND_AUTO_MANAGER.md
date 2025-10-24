# ⏰ Bot Check Interval & 🤖 Auto Manager Guide

## **Question 1: How to Make Bot Run Every 15 Minutes**

### **Current Behavior:**
Your bot checks for trading signals **every 60 seconds** (1 minute).

```
00:00 → Check market → Trade if signal
00:01 → Check market → Trade if signal
00:02 → Check market → Trade if signal
...
```

### **Why Change to 15 Minutes?**

**Benefits:**
- ✅ Reduces server load
- ✅ Fewer API calls to Binance
- ✅ More aligned with hourly news cycle
- ✅ Less "noise" trading
- ✅ Better for swing trading approach

**When to Use:**
- ✅ AI strategies (news-driven, hourly updates)
- ✅ Longer timeframe trading (4h, 1d candles)
- ✅ Low-frequency strategies

**When NOT to Use:**
- ❌ High-frequency trading
- ❌ Scalping strategies
- ❌ Quick stop-loss requirements

### **The Change:**

I've updated `integrated_trader.py`:

```python
# OLD:
time.sleep(60)  # Check every 1 minute

# NEW:
time.sleep(900)  # Check every 15 minutes
```

### **Other Interval Options:**

You can easily adjust to any interval:

```python
# Common intervals:
time.sleep(60)     # 1 minute
time.sleep(300)    # 5 minutes ⭐ (good balance)
time.sleep(900)    # 15 minutes ⭐ (current)
time.sleep(1800)   # 30 minutes
time.sleep(3600)   # 1 hour
```

### **How This Works with News:**

```
PERFECT ALIGNMENT with hourly news:

Hour 0:00 → Fetch news → AI analysis → Cache result
Hour 0:15 → Bot checks → Uses cached analysis → No OpenAI call
Hour 0:30 → Bot checks → Uses cached analysis → No OpenAI call
Hour 0:45 → Bot checks → Uses cached analysis → No OpenAI call
Hour 1:00 → Fetch NEW news → AI analysis → Cache result
Hour 1:15 → Bot checks → Uses new cached analysis
...

Result: 
- Fresh news every hour
- Bot checks 4 times/hour
- Only 1 OpenAI call/hour
- Perfect efficiency! ✅
```

### **Impact on Your Bots:**

**Bot 1 (Technical Strategy):**
- Checks price/indicators every 15 min
- More stable signals (less noise)
- Better for swing trading

**Bot 2 & 3 (AI Autonomous):**
- Checks every 15 min
- Uses cached AI analysis (59 min/hour)
- Fresh analysis when news updates (1 min/hour)
- Perfectly aligned with hourly news cycle!

---

## **Question 2: How Auto Manager Works**

### **What is Auto Manager?**

The **Auto Manager** automatically detects coins in your wallet that **aren't being managed by any bot** and creates bots for them.

### **The Problem It Solves:**

```
Scenario:
1. You buy BTC, ETH, and SOL manually
2. You create a bot for BTC ✅
3. ETH and SOL are just sitting there ❌
4. No stop-loss, no take-profit ❌
5. No AI monitoring them ❌

Auto Manager:
1. Scans your wallet
2. Finds ETH and SOL (orphaned coins)
3. Auto-creates management bots for them ✅
4. Now they're monitored with AI! ✅
```

### **When Does It Run?**

**Automatically on Dashboard Startup:**

```python
# advanced_dashboard.py - Line 33
def __init__(self):
    # ...
    # Auto-create bots for orphaned coins on startup
    self._auto_create_bots_for_orphaned_coins()
```

**Every time you:**
- Start the dashboard
- Restart the dashboard

### **How It Works (Step-by-Step):**

#### **Step 1: Scan Your Wallet**
```python
# Get all balances from Binance
balances = get_account()

Example:
BTC: 0.0005
ETH: 0.05
SOL: 2.5
USDT: 500.00
```

#### **Step 2: Check Existing Bots**
```python
# Get list of coins already managed
managed_coins = [bot.symbol for bot in bots]

Example:
Bot 1: BTCUSDT ✅ (managing BTC)
Bot 2: ETHUSDT ✅ (managing ETH)

Result: SOL is orphaned! ❌
```

#### **Step 3: Find Orphaned Coins**
```python
for balance in balances:
    if balance > 0 and not managed:
        orphaned_coins.append(coin)

Example:
Found orphaned coins:
- SOL: 2.5
```

#### **Step 4: Validate Trading Symbol**
```python
# Check if coin can be traded on Binance
if is_symbol_tradeable(SOLUSDT):
    create_bot()

Example:
✅ SOLUSDT is tradeable → Create bot!
```

#### **Step 5: Auto-Create Management Bot**
```python
create_bot(
    name="Auto-Manager: SOL",
    symbol="SOLUSDT",
    strategy="ai_autonomous",  # Best for unknown coins
    trade_amount=100,
    status="stopped"  # Start in stopped state
)
```

**Bot created but NOT started!**
- You must manually start it from the dashboard
- This prevents unexpected trading

#### **Step 6: Detect Existing Position**
```python
# When you start the bot, it detects:
has_position = True
entry_price = current_market_price
position_size = 2.5 SOL

# Bot now manages this position with:
- Stop-loss
- Take-profit
- AI news monitoring
```

---

## **Auto Manager Example Scenario**

### **Scenario A: You Buy a Coin Manually**

```
1. You buy 1 ETH on Binance app
   Wallet: 1 ETH

2. Dashboard starts up
   🔍 Scanning wallet...
   ⚠️  Found 1 orphaned coin: ETH
   
3. Auto Manager creates bot
   🤖 Created: "Auto-Manager: ETH"
   Status: Stopped (you must start it)
   
4. You start the bot from dashboard
   ✅ Bot detects existing 1 ETH position
   ✅ Sets entry price at current market
   ✅ Applies stop-loss and take-profit
   ✅ Monitors with AI
   
5. Bot now manages your ETH!
   - Sells if price drops 3% (stop-loss)
   - Sells if price rises 5% (take-profit)
   - Sells if AI detects negative news
```

### **Scenario B: AI Bot Switches Coin**

```
1. Bot 2 is trading BTCUSDT
   Holds: 0.0005 BTC
   
2. AI finds better opportunity in ETH
   Bot sells BTC, buys ETH
   Holds: 0.05 ETH
   
3. Bot 2 now manages ETHUSDT
   Old BTC position: Sold ✅
   New ETH position: Managed ✅
   
No orphaned coins! Everything managed.
```

### **Scenario C: Multiple Orphaned Coins**

```
Wallet:
- BTC: 0.001
- ETH: 0.05
- SOL: 2.5
- XRP: 100
- ADA: 500

Existing Bots:
- Bot 1: BTCUSDT ✅

Dashboard starts:
🔍 Found 4 orphaned coins: ETH, SOL, XRP, ADA

Auto Manager creates:
✅ Bot 2: Auto-Manager: ETH (stopped)
✅ Bot 3: Auto-Manager: SOL (stopped)
✅ Bot 4: Auto-Manager: XRP (stopped)
✅ Bot 5: Auto-Manager: ADA (stopped)

You must start them manually!
```

---

## **Auto Manager Configuration**

### **Default Settings:**

```python
# Auto-created bots use:
Strategy: ai_autonomous
Trade Amount: $100
Status: stopped
AI Model: GPT-4o-mini
Stop Loss: 3%
Take Profit: 5%
```

### **Why AI Autonomous Strategy?**

```
✅ Best for unknown coins
✅ Monitors news for that specific coin
✅ Adapts to market conditions
✅ No technical indicator tuning needed
✅ Works for any coin on Binance
```

### **Why $100 Trade Amount?**

```
Trade Amount = Initial investment for NEW positions

For orphaned coins:
- Bot WON'T buy more (already has coins!)
- Bot WILL manage existing position
- $100 is placeholder, ignored for orphans
- Real value = current coin balance
```

### **Why Stopped Status?**

```
Safety first!

✅ You review the auto-created bot
✅ You verify it's correct
✅ You manually start it
✅ Prevents surprise trades
```

---

## **How to Use Auto Manager**

### **Method 1: Let It Run Automatically**

```bash
# Just start the dashboard
python3 advanced_dashboard.py

# Auto Manager runs on startup:
🔍 Checking for orphaned coins...
⚠️  Found 2 orphaned coin(s):
   • ETH: 0.05000000
   • SOL: 2.50000000

🤖 Auto-creating management bots...
✅ Created bot: Auto-Manager: ETH
✅ Created bot: Auto-Manager: SOL

# Go to dashboard and start them manually
```

### **Method 2: Restart Dashboard to Re-Scan**

```bash
# If you buy new coins after dashboard is running:
# Restart dashboard to trigger auto-scan

# Kill dashboard
screen -X -S dashboard quit

# Start dashboard
screen -dmS dashboard python3 advanced_dashboard.py

# Auto Manager re-scans and creates bots
```

### **Method 3: Manual Bot Creation**

```bash
# If Auto Manager doesn't create a bot (e.g., coin not tradeable):
# Create manually from dashboard:

Dashboard → Add New Bot
├─ Name: "My ETH Bot"
├─ Symbol: ETHUSDT
├─ Strategy: AI Autonomous
└─ Capital: $100

When started:
✅ Bot detects existing ETH in wallet
✅ Treats it as an orphaned position
✅ Manages it automatically
```

---

## **Auto Manager Logs**

### **When No Orphaned Coins:**
```
🔍 Checking for orphaned coins...
✅ All coins are managed! No action needed.
```

### **When Orphaned Coins Found:**
```
🔍 Checking for orphaned coins...
⚠️  Found 2 orphaned coin(s):
   • ETH: 0.05000000
   • SOL: 2.50000000

🤖 Auto-creating management bots...
✅ Created bot 4: Auto-Manager: ETH (stopped)
✅ Created bot 5: Auto-Manager: SOL (stopped)

💡 These bots are STOPPED by default.
   Start them from the dashboard to begin management!
```

### **When Coin Not Tradeable:**
```
🔍 Checking for orphaned coins...
⚠️  Found 1 orphaned coin: SHIB

❌ SHIB: Not tradeable on Binance
   (This coin might be locked, staked, or not supported)

💡 Manual action required for this coin.
```

---

## **FAQ**

### **Q: Will Auto Manager start trading immediately?**
A: **No!** Bots are created in `stopped` state. You must manually start them.

### **Q: Will it buy more of the orphaned coin?**
A: **No!** When a bot detects an existing position, it manages it but won't buy more (unless you add funds).

### **Q: What if I don't want a bot for a specific coin?**
A: Delete the auto-created bot from the dashboard. It won't recreate unless you restart the dashboard.

### **Q: Can I change the strategy after auto-creation?**
A: Currently no, but you can delete and recreate manually with your preferred strategy.

### **Q: Does Auto Manager run continuously?**
A: No, only on dashboard startup. To re-scan, restart the dashboard.

### **Q: What if I have 20 coins in my wallet?**
A: Auto Manager will create 20 bots (minus any already managed). This could be overwhelming! Consider:
- Manually creating bots for important coins only
- Consolidating small holdings
- Using fewer coins for active trading

### **Q: Does this work with testnet?**
A: Yes! Auto Manager scans testnet or mainnet depending on your `.env` setting.

---

## **Summary**

### **Bot Check Interval (15 Minutes):**
```
✅ Changed from 60s to 900s (15 min)
✅ Aligns with hourly news cycle
✅ Reduces API calls
✅ Better for AI strategies
✅ Still responsive enough for trading
```

### **Auto Manager:**
```
✅ Scans wallet on dashboard startup
✅ Finds coins not managed by any bot
✅ Auto-creates "Auto-Manager" bots
✅ Uses AI Autonomous strategy
✅ Bots start in stopped state (you must start)
✅ Detects and manages existing positions
✅ Prevents orphaned coins
```

---

## **Deploy the Changes**

### **1. Commit and Push:**
```bash
# On your local machine:
cd /Users/rileymartin/tradingbot
git add integrated_trader.py
git commit -m "Set bot check interval to 15 minutes"
git push origin main
```

### **2. Update Server:**
```bash
# SSH to server:
ssh root@134.199.159.103
cd /root/tradingbot

# Fix git divergence:
git reset --hard origin/main

# Pull latest:
git pull origin main

# Restart all bots:
pkill -f "integrated_trader.py"

# Go to dashboard and restart them:
# http://134.199.159.103:5001
```

### **3. Verify New Interval:**
```bash
# Check logs:
screen -r bot_2

# You should see logs every 15 minutes now:
04:00:00 → Check market
04:15:00 → Check market (next check!)
04:30:00 → Check market
```

---

## **Best Practices**

### **1. Interval Selection:**
```
High-frequency (1-5 min):
├─ Technical strategies
├─ Scalping
└─ Quick stop-losses

Medium-frequency (5-15 min): ⭐ RECOMMENDED
├─ AI strategies
├─ Swing trading
└─ News-driven trading

Low-frequency (30-60 min):
├─ Long-term positions
├─ Macro trading
└─ Manual oversight
```

### **2. Auto Manager Usage:**
```
✅ DO: Let it run automatically
✅ DO: Review auto-created bots before starting
✅ DO: Delete unwanted auto-bots
✅ DO: Monitor dashboard logs for orphan detection

❌ DON'T: Ignore auto-created bots
❌ DON'T: Start all bots without review
❌ DON'T: Rely on it for 20+ coins (overwhelming!)
```

---

**Your bots now check every 15 minutes, perfectly aligned with hourly news!** ⏰
**Your coins are auto-protected from being orphaned!** 🤖
