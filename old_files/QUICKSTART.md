# Quick Start Guide

Get your trading bot running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Run Setup

```bash
python setup.py
```

This creates a `.env` file with default settings.

## Step 3: Get Binance API Keys

### Option A: Testnet (Recommended for beginners)

1. Go to https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Copy your API Key and Secret Key

### Option B: Real Trading (Use with caution)

1. Go to https://www.binance.com/
2. Account → API Management
3. Create new API key
4. ⚠️ **Enable only "Spot Trading"** - DO NOT enable withdrawals

## Step 4: Configure Your Bot

Edit the `.env` file:

```env
# Add your actual API keys here
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_secret_key

# Use testnet first!
USE_TESTNET=true

# Choose your trading pair
TRADING_SYMBOL=BTCUSDT

# Set trade amount (start small!)
TRADE_AMOUNT=0.001
```

## Step 5: Test Connection

```bash
python test_connection.py
```

You should see:
- ✓ Connection successful
- ✓ Account balance
- ✓ Current price
- All tests passed!

## Step 6: Backtest the Strategy

**IMPORTANT: Always backtest first!**

```bash
python simple_backtest.py
```

Simple menu will ask you to choose:
1. Trading pair (BTC, ETH, BNB, etc.)
2. Strategy (Conservative, Balanced, Aggressive, etc.)
3. Timeframe (1 week to 6 months)
4. Initial capital ($500 - $10,000)

Results will show:
- Win rate
- Total return
- Trade history
- Risk metrics

## Step 7: Run the Bot

```bash
python trading_bot.py
```

## What to Expect

The bot will:
1. Display your configuration
2. Show your account balance
3. Start monitoring the market every 60 seconds
4. Display status updates with signals and indicators
5. Execute trades when conditions are met
6. Log everything to console and `trading_bot.log`

## Stopping the Bot

Press `Ctrl+C` to stop. The bot will:
- Close any open positions
- Show trading summary
- Exit safely

## Monitoring

Watch for:
- **Signal**: BUY/SELL/HOLD
- **Confidence**: Higher = stronger signal (>50% required to trade)
- **Indicators**: RSI, Momentum, Trend
- **P&L**: Profit/Loss percentage

## Common Issues

### "Configuration Error: API keys not set"
→ Edit `.env` and add your actual API keys

### "Connection failed"
→ Check if your API keys are correct and have trading permissions

### "No trades executing"
→ Normal! Bot only trades when conditions are favorable. Be patient.

## Safety Tips

1. **Always start with testnet** (`USE_TESTNET=true`)
2. **Start with small amounts** when going live
3. **Monitor the first few trades** closely
4. **Understand the strategy** before using real money
5. **Check logs regularly** (`trading_bot.log`)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Adjust strategy parameters in `.env` to match your risk tolerance
- Monitor performance and fine-tune settings
- Consider backtesting different parameters

## Support

- Check `trading_bot.log` for detailed information
- Review the code to understand how it works
- Test thoroughly on testnet before going live

Happy trading! 🚀📈
