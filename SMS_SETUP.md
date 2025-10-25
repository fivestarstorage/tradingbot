# 🚀 Quick SMS Setup Guide

## ✅ What's Done

SMS notifications have been **fully integrated** into your trading bot! Every trade will now send an SMS to **+61431269296** (and +61422335161).

## 📋 Setup Steps

### 1. Add Twilio Credentials to .env

Open `/Users/rileymartin/tradingbot/.env` and add:

```bash
# Twilio SMS Notifications
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

Get these from: https://console.twilio.com/

### 2. Restart Backend

```bash
cd /Users/rileymartin/tradingbot
./stop_all.sh
./start.sh
```

### 3. Test SMS

```bash
cd /Users/rileymartin/tradingbot
python test_sms.py
```

You should receive 2 SMS messages:
1. Test message
2. Sample BUY alert

### 4. Make a Real Trade

Test with a small amount:

```bash
# Via API
curl -X POST "http://localhost:8000/api/trade/buy?symbol=BTCUSDT&usdt=10"

# Or via chatbot
# Open http://localhost:3001/chat
# Type: "buy $10 worth of BTC"
```

You'll receive an SMS like:

```
🟢 BUY ALERT - API Trading Bot

Coin: BTCUSDT
Price: $62,450.00
Quantity: 0.00016000
Total: $10.00

💰 Position opened!

💡 Reasoning:
Bought BTCUSDT via API
```

## 🎯 What Gets SMS Notifications

✅ **Manual trades** via chatbot  
✅ **API trades** via /api/trade/buy or /api/trade/sell  
✅ **Automated trades** from scheduled news analysis  
✅ **Portfolio management** trades (if enabled)

## 📱 SMS Format

### BUY Alerts
- 🟢 Green emoji
- Coin, Price, Quantity
- Total amount
- AI reasoning

### SELL Alerts
- 🔴 Red emoji
- Coin, Price, Quantity
- Total amount
- 📈/📉 Profit/Loss with %
- AI reasoning

## 🔍 Where It's Integrated

### Files Modified:
1. **app/twilio_notifier.py** - SMS sending logic (copied from archive)
2. **app/trading_service.py** - SMS on BUY/SELL orders
3. **app/portfolio_manager.py** - SMS for portfolio trades
4. **env_template.txt** - Added Twilio variables
5. **test_sms.py** - Quick test script (NEW)

### Integration Points:

#### TradingService (`app/trading_service.py`)
- Line ~88-100: BUY order → SMS
- Line ~142-158: SELL order → SMS (with profit/loss)

#### PortfolioManager (`app/portfolio_manager.py`)
- Line ~260-279: SELL signal → SMS
- Line ~301-317: BUY MORE signal → SMS

## 💰 Costs

- **Twilio**: ~$0.0075 per SMS to Australia
- **2 recipients** = $0.015 per trade
- **100 trades/month** = ~$1.50

## ⚠️ Troubleshooting

### "Twilio not configured"
→ Add credentials to `.env` and restart backend

### "No SMS received"
→ Check:
- Phone number in `app/twilio_notifier.py`
- Twilio account is active
- Twilio has credits
- Phone can receive SMS

### SMS sent but no trade executed
→ Impossible - SMS only sent AFTER successful trade

### Want to change recipients?
Edit `app/twilio_notifier.py`:
```python
self.recipients = [
    {'name': 'Your Name', 'number': '+61xxxxxxxxx'},
]
```

## 🎉 Benefits

✅ Know instantly when trades execute  
✅ Track profits on every sell  
✅ Understand AI reasoning  
✅ No need to constantly check dashboard  
✅ Peace of mind while bot runs  

## 📚 More Info

See **SMS_NOTIFICATIONS.md** for complete documentation.

---

**Test it now!**
```bash
python test_sms.py
```

