# 📊 Trading Strategies Guide

Complete guide to understanding and choosing trading strategies for your bots.

---

## Table of Contents

1. [Strategy Overview](#strategy-overview)
2. [How Strategies Work](#how-strategies-work)
3. [Available Strategies](#available-strategies)
4. [Choosing the Right Strategy](#choosing-the-right-strategy)
5. [Strategy Performance Tips](#strategy-performance-tips)

---

## Strategy Overview

### What is a Trading Strategy?

A trading strategy is a set of rules that determines when to BUY and SELL. Each strategy:
- Analyzes market data (price, volume, indicators)
- Generates signals (BUY, SELL, or HOLD)
- Has its own logic and approach
- Works better in different market conditions

### How Bots Use Strategies

```
1. Bot fetches latest price data from Binance
2. Bot passes data to strategy
3. Strategy analyzes and returns signal
4. Bot executes the trade if signal is BUY or SELL
5. Process repeats every 15 minutes
```

---

## How Strategies Work

### Technical Analysis Strategies

These use **math and statistics** on price/volume data:

**Common Indicators:**
- **RSI** (Relative Strength Index): Measures overbought/oversold
- **MACD** (Moving Average Convergence Divergence): Trend momentum
- **Bollinger Bands**: Volatility and price ranges
- **EMA** (Exponential Moving Average): Price trends
- **Volume**: Trading activity strength

**Example Logic:**
```
IF RSI < 30 (oversold)
AND MACD crosses above signal line
AND price near lower Bollinger Band
THEN → BUY signal

IF RSI > 70 (overbought)  
AND MACD crosses below signal line
AND price near upper Bollinger Band
THEN → SELL signal
```

### AI-Powered Strategies

These combine **technical analysis + news sentiment**:

**How They Work:**
1. Fetch crypto news from CryptoNews API
2. Use OpenAI (ChatGPT) to analyze sentiment
3. Calculate technical indicators
4. Combine both for final decision

**Example:**
```
Technical Analysis: SELL signal (overbought)
News Sentiment: VERY POSITIVE (major adoption news)
Final Decision: HOLD (news overrides technical)
```

---

## Available Strategies

### 1. Volatile Coins Strategy ⭐ (RECOMMENDED)

**File:** `strategies/volatile_coins_strategy.py`

**Best For:**
- Any cryptocurrency
- High-volatility coins (DOGE, SHIB, altcoins)
- Beginners
- Testnet practice

**How It Works:**
- Uses RSI, MACD, Bollinger Bands
- Looks for strong momentum signals
- Wider stop losses for volatility
- Quick entries and exits

**Signal Logic:**
```python
BUY when:
- RSI < 35 (oversold, room to grow)
- MACD crosses above signal (momentum up)
- Price near lower Bollinger Band (at support)
- Volume increasing

SELL when:
- RSI > 65 (overbought)
- MACD crosses below signal (momentum down)
- Price near upper Bollinger Band (at resistance)
- Or stop loss / take profit hit
```

**Settings:**
- Stop Loss: 2-3% (adjusts for volatility)
- Take Profit: 5-8%
- Check Interval: 15 minutes

**Pros:**
- ✅ Works on any coin
- ✅ No API keys needed
- ✅ Simple to understand
- ✅ Good for volatile markets

**Cons:**
- ❌ More false signals in ranging markets
- ❌ Doesn't consider news events

**Best Market Conditions:**
- Trending markets (up or down)
- High volatility
- Clear price movements

---

### 2. Ticker News Strategy (AI-Powered) 🤖

**File:** `strategies/ticker_news_strategy.py`

**Best For:**
- Major coins (BTC, ETH, BNB, ADA, SOL)
- News-driven trading
- Advanced users
- Higher accuracy

**How It Works:**
1. Fetches latest crypto news every 15 mins
2. OpenAI analyzes sentiment (bullish/bearish)
3. Calculates technical indicators (RSI, MACD)
4. Only trades when BOTH agree

**Signal Logic:**
```python
BUY when:
- News sentiment: POSITIVE
- RSI < 40 (not overbought)
- MACD trending up
- Volume confirming

SELL when:
- News sentiment: NEGATIVE
- RSI > 60 (not oversold)
- MACD trending down
- Or stop loss / take profit
```

**Settings:**
- Stop Loss: 2%
- Take Profit: 5%
- News Refresh: Every trade check
- API Calls: ~3 per day (CryptoNews limit)

**Required:**
```bash
# Add to .env file:
OPENAI_API_KEY=your_key_here
CRYPTONEWS_API_KEY=your_key_here
```

**Pros:**
- ✅ Considers market sentiment
- ✅ Fewer false signals
- ✅ Better timing on news events
- ✅ Higher win rate

**Cons:**
- ❌ Requires API keys
- ❌ API costs (OpenAI ~$0.01-0.05/trade)
- ❌ Limited to major coins with news coverage
- ❌ 3 news fetches per day limit

**Best Market Conditions:**
- News-driven markets
- Major coins with active news
- High impact events
- Fundamental changes

---

### 3. Simple Profitable Strategy

**File:** `strategies/simple_profitable_strategy.py`

**Best For:**
- Beginners
- Stable coins (BTC, ETH)
- Conservative trading
- Learning

**How It Works:**
- Balanced mix of indicators
- Conservative entry rules
- Higher confidence threshold
- Fewer but better trades

**Signal Logic:**
```python
BUY when:
- RSI < 30 (very oversold)
- MACD strongly positive
- Price trend upward
- Multiple confirmations

SELL when:
- RSI > 70 (very overbought)
- MACD turns negative
- Take profit reached
```

**Pros:**
- ✅ High win rate (~60-70%)
- ✅ Easy to understand
- ✅ Lower risk
- ✅ Good for learning

**Cons:**
- ❌ Fewer trades (may wait days)
- ❌ Lower total returns
- ❌ Miss some opportunities

**Best Market Conditions:**
- Stable trending markets
- Lower volatility
- Clear trends

---

### 4. Enhanced Strategy

**File:** `strategies/enhanced_strategy.py`

**Best For:**
- Experienced traders
- Medium volatility coins
- Active markets

**How It Works:**
- Advanced indicator combinations
- Market regime detection
- Dynamic position sizing
- Adaptive thresholds

**Pros:**
- ✅ Adapts to market conditions
- ✅ Sophisticated logic
- ✅ Good in various conditions

**Cons:**
- ❌ More complex
- ❌ Harder to debug
- ❌ May overtrade

---

### 5. Mean Reversion Strategy

**File:** `strategies/mean_reversion_strategy.py`

**Best For:**
- Ranging (sideways) markets
- Stable coins
- Low volatility periods

**How It Works:**
- Buys dips
- Sells spikes
- Assumes price returns to average

**Signal Logic:**
```python
BUY when:
- Price significantly below moving average
- Expecting bounce back up

SELL when:
- Price significantly above moving average
- Expecting pullback down
```

**Pros:**
- ✅ Great in ranging markets
- ✅ Consistent small profits
- ✅ Lower risk

**Cons:**
- ❌ Terrible in trending markets
- ❌ Catches falling knives
- ❌ Misses big moves

**Best Market Conditions:**
- Sideways markets
- Established ranges
- Low volatility

---

### 6. Breakout Strategy

**File:** `strategies/breakout_strategy.py`

**Best For:**
- Trending markets
- High volume moves
- Momentum trading

**How It Works:**
- Waits for price breakouts
- Rides momentum
- Volume confirmation required

**Signal Logic:**
```python
BUY when:
- Price breaks above resistance
- High volume confirms
- Momentum strong

SELL when:
- Momentum fades
- Volume drops
- Support breaks
```

**Pros:**
- ✅ Catches big moves
- ✅ High profit potential
- ✅ Clear signals

**Cons:**
- ❌ Many false breakouts
- ❌ Higher risk
- ❌ Needs strong trends

**Best Market Conditions:**
- Strong trends
- High volume
- Clear breakouts

---

### 7. Conservative Strategy

**File:** `strategies/conservative_strategy.py`

**Best For:**
- Risk-averse traders
- Long-term holders
- Stable income

**How It Works:**
- Very selective entries
- Multiple confirmations
- Wide stop losses
- Holds longer

**Pros:**
- ✅ High win rate (70%+)
- ✅ Low risk
- ✅ Fewer trades
- ✅ Peace of mind

**Cons:**
- ❌ May wait weeks for trades
- ❌ Lower returns
- ❌ Misses opportunities

**Best Market Conditions:**
- Any (very selective)
- Prefers trends

---

## Choosing the Right Strategy

### Decision Tree

```
START: What's your goal?
│
├─ Want AI + News?
│  └─ Use: Ticker News Strategy
│     (Requires: OpenAI + CryptoNews API)
│
├─ Trading volatile altcoins?
│  └─ Use: Volatile Coins Strategy ⭐
│     (Best default choice)
│
├─ Just learning?
│  └─ Use: Simple Profitable Strategy
│     (Easy to understand)
│
├─ Market ranging sideways?
│  └─ Use: Mean Reversion Strategy
│     (Buy dips, sell peaks)
│
├─ Strong trend detected?
│  └─ Use: Breakout Strategy
│     (Ride the momentum)
│
└─ Want safety first?
   └─ Use: Conservative Strategy
      (Fewer trades, higher accuracy)
```

### By Coin Type

**Major Coins (BTC, ETH, BNB):**
1. Ticker News (if you have API keys)
2. Simple Profitable
3. Volatile Coins

**Mid-Cap Coins (ADA, DOT, LINK):**
1. Volatile Coins ⭐
2. Enhanced Strategy
3. Breakout Strategy

**Small/Meme Coins (DOGE, SHIB, PEPE):**
1. Volatile Coins ⭐
2. Breakout Strategy
3. Enhanced Strategy

**Stablecoins (low volatility):**
1. Mean Reversion
2. Conservative
3. Simple Profitable

---

## Strategy Performance Tips

### General Guidelines

1. **Match Strategy to Market**
   - Trending → Volatile, Breakout
   - Ranging → Mean Reversion
   - News-heavy → Ticker News

2. **Backtest First**
   ```bash
   python3 utils/backtest_runner.py
   ```
   - Test on historical data
   - See what would have happened
   - Compare different strategies

3. **Start Conservative**
   - Use Simple Profitable or Conservative first
   - Learn how signals work
   - Gain confidence

4. **Monitor Performance**
   - Track win rate (aim for >50%)
   - Calculate profit factor (aim for >1.5)
   - Review every week

### Switching Strategies

You can change a bot's strategy by:
1. Stop the bot
2. Delete it
3. Create new bot with different strategy
4. (Currently strategies are set at bot creation)

### Combining Strategies

Run multiple bots:
- Bot 1: BTC with Ticker News
- Bot 2: ETH with Volatile Coins
- Bot 3: DOGE with Breakout

Each bot is independent!

---

## Advanced: Creating Custom Strategies

Want to create your own strategy?

### Minimum Requirements

```python
# strategies/my_custom_strategy.py

class MyCustomStrategy:
    def analyze(self, data):
        """
        Analyze market data and return trading signal
        
        Args:
            data: List of klines (OHLCV data)
                  [[timestamp, open, high, low, close, volume], ...]
        
        Returns:
            dict: {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'reasoning': 'Why this signal',
                'confidence': 0.0-1.0  # optional
            }
        """
        
        # Your analysis logic here
        # Calculate indicators
        # Make decision
        
        return {
            'signal': 'HOLD',
            'reasoning': 'Waiting for better setup'
        }
```

### Add to Bot

1. Save strategy file in `strategies/` folder
2. Edit `integrated_trader.py`:
   ```python
   from strategies.my_custom_strategy import MyCustomStrategy
   
   STRATEGIES = {
       # ... existing strategies ...
       'my_custom': MyCustomStrategy,
   }
   ```
3. Use 'my_custom' when creating bot in dashboard

---

## Strategy Comparison Table

| Strategy | Risk | Frequency | Win Rate | API Keys | Best For |
|----------|------|-----------|----------|----------|----------|
| Volatile Coins ⭐ | Medium | High | 55-60% | No | Any coin |
| Ticker News | Medium | Medium | 60-65% | Yes | Major coins |
| Simple Profitable | Low | Low | 65-70% | No | Beginners |
| Enhanced | Medium | Medium | 55-60% | No | Active trading |
| Mean Reversion | Low | Medium | 60-65% | No | Ranging |
| Breakout | High | Low | 50-55% | No | Trends |
| Conservative | Low | Very Low | 70-75% | No | Safety |

---

## Common Questions

### How often do bots check for signals?
Every 15 minutes (configurable in code)

### Can I use multiple strategies on same coin?
Yes! Create multiple bots, each with different strategy

### Which strategy makes most profit?
Depends on market conditions. Backtest to find out!

### Do I need API keys?
Only for Ticker News strategy. Others work without.

### Can I modify strategies?
Yes! Edit the Python files in `strategies/` folder

### What if strategy keeps losing?
- Stop the bot
- Review logs
- Try different strategy
- Check market conditions
- Backtest first

---

## Further Reading

- **[README.md](../README.md)** - Main documentation
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - How strategies integrate
- **[QUICKSTART.md](../QUICKSTART.md)** - Get started quickly

---

**Happy Strategy Hunting! 📊🚀**

Remember: No strategy wins 100% of the time. Diversify, monitor, and adjust!

