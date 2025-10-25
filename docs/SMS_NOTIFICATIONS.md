# 📱 SMS Trade Notifications

Your trading bot now sends SMS notifications for **every trade** to `+61431269296` (and +61422335161) via Twilio!

## 📋 What Gets Sent

### 🟢 BUY Alerts
```
🟢 BUY ALERT - API Trading Bot

Coin: XRPUSDT
Price: $1.23
Quantity: 81.30081300
Total: $100.00

💰 Position opened!

💡 Reasoning:
Bought XRPUSDT via API
```

### 🔴 SELL Alerts
```
🔴 SELL ALERT - Portfolio Manager

Coin: SOLUSDT
Price: $168.50
Quantity: 0.59405940
Total: $100.00

📈 Profit: $12.50 (+12.50%)

💡 Reasoning:
Taking profits on strong gain while 
maintaining exposure.
```

## 🎯 When SMS is Sent

SMS notifications are sent for:

1. **Manual trades** via chatbot
   - "buy $100 worth of XRP" → SMS sent ✅
   - "sell all my SOL" → SMS sent ✅

2. **Automated news-based trades** (if `AUTO_TRADE=true`)
   - High confidence BUY signals → SMS sent ✅
   - SELL signals executed → SMS sent ✅

3. **Portfolio management trades** (if `PORTFOLIO_AUTO_MANAGE=true`)
   - SELL for profit/loss → SMS sent ✅
   - BUY MORE on conviction → SMS sent ✅

## 🔧 Setup

### Step 1: Add Twilio Credentials to .env

```bash
# Get these from twilio.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

### Step 2: Restart Backend

```bash
cd /Users/rileymartin/tradingbot
./stop_all.sh
./start.sh
```

### Step 3: Test It!

```bash
# Test SMS functionality
python -c "from app.twilio_notifier import TwilioNotifier; TwilioNotifier().test_sms()"
```

## 📱 Recipients

Currently configured to send to:
- **Riley Martin**: +61431269296 ✅
- **Neal Martin**: +61422335161

To modify recipients, edit `/app/twilio_notifier.py`:

```python
self.recipients = [
    {'name': 'Riley Martin', 'number': '+61431269296'},
    {'name': 'Neal Martin', 'number': '+61422335161'}
]
```

## 🎨 Message Format

### BUY
- 🟢 Emoji + "BUY ALERT"
- Coin symbol
- Price, Quantity, Total
- "Position opened!"
- AI reasoning (if available)

### SELL
- 🔴 Emoji + "SELL ALERT"
- Coin symbol
- Price, Quantity, Total
- 📈 or 📉 Profit/Loss with %
- AI reasoning (if available)

## 🔍 Where SMS is Integrated

### 1. Trading Service (`app/trading_service.py`)
- Sends SMS when API executes BUY/SELL
- Used by chatbot and scheduled jobs

### 2. Portfolio Manager (`app/portfolio_manager.py`)
- Sends SMS for portfolio management trades
- Includes AI reasoning in message

### 3. Scheduled Job (`app/server.py`)
- Automated trades from news signals
- Portfolio management trades

## ⚙️ Technical Details

### Twilio Configuration

**Messaging Service SID**: `MG00a1831705f28abc4958c7986fcad688`  
(Hardcoded in `twilio_notifier.py`)

### SMS Character Limit

- Max reasoning length: 400 characters
- Automatically truncated if longer
- Keeps messages under SMS limits

### Error Handling

If Twilio fails:
- Trade still executes ✅
- Error logged to console
- Bot continues normally

SMS is **optional** - bot works fine without it!

## 🧪 Testing

### Test SMS Only
```bash
cd /Users/rileymartin/tradingbot
python app/twilio_notifier.py
```

### Test Full Trade with SMS
```bash
# Via chatbot
Open http://localhost:3000/chat
Type: "buy $10 worth of BTC"

# Via API
curl -X POST http://localhost:8000/api/trade/buy?symbol=BTCUSDT&usdt=10
```

## 📊 SMS Summary (Future Feature)

The code also supports 6-hour trading summaries:

```
🤖 6 HOURS SUMMARY
Bot: Portfolio Manager

📊 Trading Activity:
  Total Trades: 5
  • Buys: 3
  • Sells: 2

📈 Performance:
  Profit: $12.50 (+2.5%)

💼 Open Positions:
  BTC, ETH

💰 Account Value: $1,250.00
```

*Currently disabled - can be enabled if needed.*

## ⚠️ Important Notes

### SMS Costs
- **Twilio charges** per SMS sent
- ~$0.0075 per SMS in Australia
- With 2 recipients per trade = $0.015/trade
- 100 trades/month = ~$1.50 in SMS costs

### Production Use
- Verify Twilio account
- Add credits to Twilio balance
- Monitor usage in Twilio dashboard

### Privacy
- SMS contain trade details
- Keep phone numbers private
- Don't share message screenshots publicly

## 🔒 Security

### Credentials
- Twilio credentials in `.env` (not committed to git)
- SMS sent over Twilio's secure API
- No sensitive data stored in Twilio logs

### Phone Numbers
- Hardcoded in `twilio_notifier.py`
- Only you and Neal receive notifications
- Can't be changed via API (security feature)

## 🎉 Benefits

✅ **Real-time alerts** - Know instantly when trades execute
✅ **Peace of mind** - Don't need to check dashboard constantly  
✅ **Track profits** - See P&L on every sell
✅ **AI reasoning** - Understand why trades were made
✅ **Multiple recipients** - You and Neal both get alerts

## 🆘 Troubleshooting

### "Twilio not configured"
- Check `.env` has TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
- Restart backend after adding

### "Failed to send SMS"
- Verify Twilio account is active
- Check phone numbers are verified
- Ensure Twilio has credits

### "No SMS received"
- Check phone can receive SMS
- Verify number in `recipients` list
- Check Twilio logs: https://console.twilio.com/us1/monitor/logs/sms

### SMS sent but trade didn't execute
- Check backend logs for trade errors
- SMS sends AFTER successful trade
- If you got SMS, trade DID execute

## 📚 Files Modified

- ✅ `archive/twilio_notifier.py` → Copied to `app/twilio_notifier.py`
- ✅ `app/trading_service.py` - Added SMS on BUY/SELL
- ✅ `app/portfolio_manager.py` - Added SMS for portfolio trades
- ✅ `env_template.txt` - Added Twilio variables

---

**You'll now get an SMS on your phone for every trade!** 📱💰

Test it: `curl -X POST http://localhost:8000/api/trade/buy?symbol=BTCUSDT&usdt=10`

