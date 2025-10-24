# 📱 SMS Trade Notifications Setup

Get instant text messages when your bots make trades!

---

## 🎯 What You'll Get:

Every time a bot makes a trade, **both Riley and Neal get an SMS**:

### Buy Notification:
```
🟢 BUY ALERT - AI Autonomous Trader

Coin: SOLUSDT
Price: $143.50
Quantity: 0.69686412
Total: $100.00

💰 Position opened!
```

### Sell Notification:
```
🔴 SELL ALERT - AI Autonomous Trader

Coin: SOLUSDT
Price: $151.80
Quantity: 0.69686412
Total: $105.78

📈 Profit: +$5.78 (+5.78%)
```

---

## 🔧 Setup (3 Steps):

### Step 1: Add Twilio Credentials to .env

Your `.env` file needs these two lines:

```bash
# SMS Notifications
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

**Get these from:** Your Twilio console (same as your Next.js app)

---

### Step 2: Install Twilio Package

**Local:**
```bash
pip3 install twilio
```

**Server:**
```bash
pip3 install twilio --break-system-packages
```

---

### Step 3: Test It Works

```bash
python3 twilio_notifier.py
```

**You should receive test SMS on both phones!** 📱

---

## 📞 Recipients

SMS notifications go to:
- **Riley Martin:** +61431269296
- **Neal Martin:** +61422335161

**To change recipients:** Edit `twilio_notifier.py`:
```python
self.recipients = [
    {'name': 'Riley Martin', 'number': '+61431269296'},
    {'name': 'Neal Martin', 'number': '+61422335161'},
    # Add more here...
]
```

---

## 💰 Costs

**Twilio SMS Pricing:**
- ~$0.08 USD per SMS to Australian mobile
- 2 recipients = $0.16 per trade
- 20 trades/day = $3.20/day = ~$96/month

**Cost control:**
- Only sends on actual trades (not signals/holds)
- No spam - just important stuff!

---

## 🚀 Deployment

### On Local Machine:
```bash
cd /Users/rileymartin/tradingbot

# Add credentials to .env
nano .env
# Add:
# TWILIO_ACCOUNT_SID=AC...
# TWILIO_AUTH_TOKEN=...

# Test
python3 twilio_notifier.py
```

### On Server:
```bash
ssh root@134.199.159.103
cd /root/tradingbot

# Install Twilio
pip3 install twilio --break-system-packages

# Add credentials
nano .env
# Add same Twilio credentials

# Test
python3 twilio_notifier.py

# Restart bots (they'll now send SMS)
screen -ls | grep bot_ | cut -d. -f1 | xargs -I {} screen -X -S {} quit
# Start your bots again from dashboard
```

---

## 📊 What Gets Notified:

| Event | SMS Sent? | Example |
|-------|-----------|---------|
| **Bot Opens Position** | ✅ Yes | "🟢 BUY ALERT - BTCUSDT @ $62,450" |
| **Bot Closes Position** | ✅ Yes | "🔴 SELL ALERT - Profit: +$12.50" |
| Bot analyzing signals | ❌ No | (Too spammy) |
| Bot waiting/holding | ❌ No | (Not important) |
| Bot errors | ❌ No* | (*Can enable if wanted) |

---

## 🧪 Testing

### Test 1: SMS Functionality
```bash
python3 twilio_notifier.py
```
Both phones should receive: "🤖 Test SMS from Trading Bot"

### Test 2: Trade Notification
Create a test bot with small amount ($10) and wait for a trade.

### Test 3: Multiple Recipients
All recipients in the list will receive every notification.

---

## ⚙️ Advanced Configuration

### Enable Bot Status Notifications

Want SMS when bots start/stop/error? Edit `integrated_trader.py`:

```python
# At bot startup
self.sms_notifier.send_bot_status(
    bot_name=self.bot_name,
    status='started',
    message=f'Trading {self.symbol} with ${self.trade_amount}'
)
```

### Customize Message Format

Edit `twilio_notifier.py` → `_format_trade_message()`:

```python
def _format_trade_message(self, trade_data):
    # Customize your message here!
    message = f"🚀 TRADE: {trade_data['symbol']}\n"
    message += f"💵 ${trade_data['amount']}"
    return message
```

### Add More Recipients

```python
self.recipients = [
    {'name': 'Riley', 'number': '+61431269296'},
    {'name': 'Neal', 'number': '+61422335161'},
    {'name': 'Mom', 'number': '+61...'},  # Add more!
]
```

---

## 🐛 Troubleshooting

### "Twilio not configured"
→ Add `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to `.env`

### "Failed to send SMS"
→ Check Twilio account has credits
→ Verify phone numbers are correct format (+61...)
→ Check messaging service SID is correct

### "No SMS received"
→ Check spam/junk folder
→ Verify phone number is in correct format
→ Test with: `python3 twilio_notifier.py`

### SMS Working But Not on Trades
→ Make sure bots were restarted AFTER adding Twilio
→ Check bot logs: `screen -r bot_1`
→ Look for: "✅ Twilio SMS notifier initialized"

---

## 🔐 Security Notes

**Never commit `.env` to git!**
- `.env` is in `.gitignore` already
- Keep Twilio credentials private
- Regenerate if accidentally leaked

---

## 💡 Tips

**Silence Notifications at Night:**
```python
from datetime import datetime

# In _format_trade_message, add:
hour = datetime.now().hour
if 22 <= hour or hour <= 7:  # 10 PM to 7 AM
    return None  # Don't send SMS
```

**Only Notify Big Trades:**
```python
# In send_trade_notification, add:
if trade_data['amount'] < 100:  # Less than $100
    return False  # Skip SMS
```

**Only Notify Profitable Sells:**
```python
# For sells, add:
if trade_data['action'] == 'SELL':
    if trade_data.get('profit', 0) < 0:
        return False  # Don't notify losses
```

---

## 📋 Quick Checklist

- [ ] Get Twilio Account SID and Auth Token
- [ ] Add credentials to local `.env`
- [ ] Install twilio: `pip3 install twilio`
- [ ] Test: `python3 twilio_notifier.py`
- [ ] Receive test SMS on both phones
- [ ] Add credentials to server `.env`
- [ ] Install on server: `pip3 install twilio --break-system-packages`
- [ ] Restart all bots
- [ ] Make a test trade
- [ ] Receive trade SMS!

---

## 🎉 You're Set!

Now every trade triggers instant SMS to both phones! 📱💰

**Next trade = Instant notification!** 🚀
