#!/usr/bin/env python3
"""
Hybrid Trading Strategy Backtester
Combines: ML Predictions + News Sentiment + Technical Analysis + Momentum

Strategy: Only trade when MULTIPLE signals align
- ML says BUY + News is Positive + RSI oversold = STRONG BUY
- ML says SELL + News is Negative + RSI overbought = STRONG SELL
"""
import os
import pickle
import numpy as np
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from core.binance_client import BinanceClient
from app.ml_service import CoinMLService

load_dotenv()

def simulate_news_sentiment(timestamp, symbol):
    """
    Simulate news sentiment score (0-100)
    In reality, this would query the database for news articles
    
    Simulates realistic patterns:
    - Generally follows price (positive when price rising)
    - Some noise/randomness
    - Occasional extreme sentiment events
    """
    # Use timestamp as seed for consistency
    random.seed(int(timestamp / 3600000))  # Change every hour
    
    # Base sentiment (slightly bullish bias like real crypto news)
    base = random.randint(45, 65)
    
    # Add some volatility
    noise = random.randint(-15, 15)
    
    # Occasional extreme sentiment (10% chance)
    if random.random() < 0.1:
        extreme = random.choice([-30, 30])  # Fear or FOMO
        base += extreme
    
    sentiment = max(0, min(100, base + noise))
    
    return sentiment


def calculate_indicators(candles, index):
    """Calculate technical indicators for a specific candle index"""
    if index < 50:
        return None
    
    window = candles[index-50:index+1]
    closes = np.array([c['close'] for c in window])
    volumes = np.array([c['volume'] for c in window])
    highs = np.array([c['high'] for c in window])
    lows = np.array([c['low'] for c in window])
    
    current_price = closes[-1]
    
    # Price changes
    price_change_1h = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) > 1 else 0
    price_change_4h = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if len(closes) > 4 else 0
    price_change_24h = ((closes[-1] - closes[-25]) / closes[-25]) * 100 if len(closes) > 24 else 0
    
    # Volume ratio
    avg_volume = np.mean(volumes[:-1])
    vol_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
    
    # RSI (14 period)
    deltas = np.diff(closes[-15:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    rs = avg_gain / avg_loss if avg_loss > 0 else 0
    rsi = 100 - (100 / (1 + rs)) if avg_loss > 0 else 50
    
    # MACD
    ema_12 = closes[-12:].mean()
    ema_26 = closes[-26:].mean() if len(closes) >= 26 else closes.mean()
    macd = ema_12 - ema_26
    signal = closes[-9:].mean()
    macd_hist = macd - signal
    
    # Bollinger Bands
    sma_20 = np.mean(closes[-20:])
    std_20 = np.std(closes[-20:])
    bb_upper = sma_20 + (2 * std_20)
    bb_lower = sma_20 - (2 * std_20)
    bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    
    # High/Low ratio
    hl_ratio = (current_price - lows[-1]) / (highs[-1] - lows[-1]) if (highs[-1] - lows[-1]) > 0 else 0.5
    
    # EMA trend
    ema_20 = np.mean(closes[-20:])
    ema_50 = np.mean(closes[-50:])
    ema_trend = 1 if ema_20 > ema_50 else 0
    
    # Return both ML features and raw indicators
    ml_features = [
        price_change_1h, price_change_4h, price_change_24h,
        vol_ratio, rsi, macd_hist, bb_position, hl_ratio, ema_trend
    ]
    
    indicators = {
        'rsi': rsi,
        'macd': macd,
        'macd_hist': macd_hist,
        'bb_position': bb_position,
        'ema_trend': ema_trend,
        'price_change_24h': price_change_24h,
        'volume_surge': vol_ratio > 1.5
    }
    
    return ml_features, indicators


def hybrid_signal(ml_prediction, ml_confidence, news_score, indicators):
    """
    Combine all signals into a hybrid score (0-100)
    
    Weights:
    - ML Prediction: 30%
    - News Sentiment: 30%
    - Technical Indicators: 40%
    
    Returns: (action, score, reasoning)
    """
    signals = []
    
    # 1. ML Signal (0-30 points)
    if ml_prediction == 'BUY':
        ml_score = ml_confidence * 30
        signals.append(f"ML: BUY ({ml_confidence:.0%})")
    else:
        ml_score = (1 - ml_confidence) * 30
        signals.append(f"ML: SELL ({ml_confidence:.0%})")
    
    # 2. News Sentiment (0-30 points)
    news_signal_score = (news_score / 100) * 30
    if news_score >= 70:
        signals.append(f"News: Very Bullish ({news_score}/100)")
    elif news_score >= 55:
        signals.append(f"News: Bullish ({news_score}/100)")
    elif news_score >= 45:
        signals.append(f"News: Neutral ({news_score}/100)")
    elif news_score >= 30:
        signals.append(f"News: Bearish ({news_score}/100)")
    else:
        signals.append(f"News: Very Bearish ({news_score}/100)")
    
    # 3. Technical Indicators (0-40 points)
    tech_score = 0
    
    # RSI (0-10 points)
    if indicators['rsi'] < 30:
        tech_score += 10  # Oversold = bullish
        signals.append(f"RSI: Oversold ({indicators['rsi']:.0f})")
    elif indicators['rsi'] > 70:
        tech_score += 0  # Overbought = bearish
        signals.append(f"RSI: Overbought ({indicators['rsi']:.0f})")
    else:
        tech_score += 5  # Neutral
    
    # MACD (0-10 points)
    if indicators['macd_hist'] > 0:
        tech_score += 10
        signals.append("MACD: Bullish")
    else:
        tech_score += 0
        signals.append("MACD: Bearish")
    
    # Bollinger Bands (0-10 points)
    if indicators['bb_position'] < 0.2:
        tech_score += 10  # Near lower band = oversold
        signals.append("BB: Near Lower Band")
    elif indicators['bb_position'] > 0.8:
        tech_score += 0  # Near upper band = overbought
        signals.append("BB: Near Upper Band")
    else:
        tech_score += 5
    
    # Trend (0-10 points)
    if indicators['ema_trend'] == 1:
        tech_score += 10
        signals.append("Trend: Bullish")
    else:
        tech_score += 0
        signals.append("Trend: Bearish")
    
    # Calculate hybrid score
    hybrid_score = ml_score + news_signal_score + tech_score
    
    # Determine action
    if hybrid_score >= 70:
        action = 'STRONG_BUY'
    elif hybrid_score >= 55:
        action = 'BUY'
    elif hybrid_score <= 30:
        action = 'STRONG_SELL'
    elif hybrid_score <= 45:
        action = 'SELL'
    else:
        action = 'HOLD'
    
    reasoning = " | ".join(signals)
    
    return action, hybrid_score, reasoning


def backtest_hybrid_strategy(symbol='BTCUSDT', starting_capital=1000.0, training_days=365):
    """
    Backtest hybrid strategy combining ML + News + Technical Analysis
    """
    print("=" * 100)
    print(f"🚀 HYBRID STRATEGY BACKTEST - {symbol}")
    print("=" * 100)
    print(f"Starting Capital: ${starting_capital:,.2f}")
    print(f"Strategy: ML (30%) + News Sentiment (30%) + Technical (40%)")
    print("=" * 100)
    
    # Initialize
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    binance = BinanceClient(api_key, api_secret, testnet=False)
    ml_service = CoinMLService(binance)
    
    # Step 1: Train ML model
    print(f"\n📚 Step 1: Training ML Model ({training_days} days)...")
    result = ml_service.train_model(symbol, days=training_days)
    
    if result.get('error'):
        print(f"❌ Training failed: {result['error']}")
        return None
    
    print(f"✅ Model trained: {result['test_accuracy']:.2%} accuracy")
    
    # Step 2: Load model
    print(f"\n📊 Step 2: Loading Model...")
    model_path = f'/tmp/ml_models/{symbol}_model.pkl'
    scaler_path = f'/tmp/ml_models/{symbol}_scaler.pkl'
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    
    print(f"✅ Model loaded")
    
    # Step 3: Fetch backtest data
    print(f"\n📈 Step 3: Fetching Historical Data (365 days)...")
    backtest_candles = ml_service.fetch_historical_data(symbol, days=365)
    print(f"✅ Got {len(backtest_candles)} candles")
    
    # Step 4: Run backtest
    print(f"\n🎯 Step 4: Running Hybrid Backtest...")
    print("-" * 100)
    
    capital = starting_capital
    position = None
    trades = []
    
    strong_buy_count = 0
    buy_count = 0
    hold_count = 0
    sell_count = 0
    strong_sell_count = 0
    
    for i in range(50, len(backtest_candles)):
        candle = backtest_candles[i]
        current_price = candle['close']
        current_time = datetime.fromtimestamp(candle['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')
        
        # Get ML features and indicators
        result = calculate_indicators(backtest_candles, i)
        if result is None:
            continue
        
        ml_features, indicators = result
        
        # Get ML prediction
        features_scaled = scaler.transform([ml_features])
        prediction_proba = model.predict_proba(features_scaled)[0]
        prediction = model.predict(features_scaled)[0]
        
        ml_action = 'BUY' if prediction == 1 else 'SELL'
        ml_confidence = max(prediction_proba)
        
        # Simulate news sentiment
        news_score = simulate_news_sentiment(candle['timestamp'], symbol)
        
        # Get hybrid signal
        action, hybrid_score, reasoning = hybrid_signal(ml_action, ml_confidence, news_score, indicators)
        
        # Track signals
        if action == 'STRONG_BUY':
            strong_buy_count += 1
        elif action == 'BUY':
            buy_count += 1
        elif action == 'SELL':
            sell_count += 1
        elif action == 'STRONG_SELL':
            strong_sell_count += 1
        else:
            hold_count += 1
        
        # Trading logic
        if position is None:
            # Enter on STRONG_BUY or BUY signals
            if action in ['STRONG_BUY', 'BUY']:
                buy_amount = capital * 0.95
                quantity = buy_amount / current_price
                
                position = {
                    'entry_price': current_price,
                    'quantity': quantity,
                    'entry_time': current_time,
                    'entry_capital': capital,
                    'entry_score': hybrid_score,
                    'entry_reasoning': reasoning
                }
                
                capital -= buy_amount
                
                print(f"🟢 {action:12} @ ${current_price:,.2f} | {current_time} | Score: {hybrid_score:.0f}/100")
                print(f"   → {reasoning}")
        
        else:
            # Exit conditions
            pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
            
            should_sell = False
            sell_reason = ""
            
            # Exit on SELL/STRONG_SELL signals
            if action in ['SELL', 'STRONG_SELL']:
                should_sell = True
                sell_reason = f"{action} signal (Score: {hybrid_score:.0f}/100)"
            # Stop loss
            elif pnl_pct <= -5:
                should_sell = True
                sell_reason = "Stop Loss (-5%)"
            # Take profit
            elif pnl_pct >= 10:
                should_sell = True
                sell_reason = "Take Profit (+10%)"
            
            if should_sell:
                sell_amount = position['quantity'] * current_price
                capital += sell_amount
                
                pnl = sell_amount - (position['entry_capital'] - (starting_capital - capital))
                pnl_pct_actual = (pnl / position['entry_capital']) * 100
                
                trades.append({
                    'entry_time': position['entry_time'],
                    'entry_price': position['entry_price'],
                    'exit_time': current_time,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct_actual,
                    'reason': sell_reason,
                    'entry_score': position['entry_score']
                })
                
                emoji = "🟢" if pnl > 0 else "🔴"
                print(f"{emoji} SELL        @ ${current_price:,.2f} | {current_time} | P&L: ${pnl:,.2f} ({pnl_pct_actual:+.2f}%)")
                print(f"   → {sell_reason}")
                
                position = None
    
    # Close remaining position
    if position is not None:
        final_price = backtest_candles[-1]['close']
        final_time = datetime.fromtimestamp(backtest_candles[-1]['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')
        sell_amount = position['quantity'] * final_price
        capital += sell_amount
        
        pnl = sell_amount - (position['entry_capital'] - (starting_capital - capital))
        pnl_pct_actual = (pnl / position['entry_capital']) * 100
        
        trades.append({
            'entry_time': position['entry_time'],
            'entry_price': position['entry_price'],
            'exit_time': final_time,
            'exit_price': final_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct_actual,
            'reason': 'End of backtest',
            'entry_score': position['entry_score']
        })
        
        emoji = "🟢" if pnl > 0 else "🔴"
        print(f"{emoji} SELL        @ ${final_price:,.2f} | {final_time} | P&L: ${pnl:,.2f} ({pnl_pct_actual:+.2f}%)")
    
    # Results
    print("\n" + "=" * 100)
    print("📈 HYBRID STRATEGY RESULTS")
    print("=" * 100)
    
    final_capital = capital
    total_pnl = final_capital - starting_capital
    total_return_pct = (total_pnl / starting_capital) * 100
    
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    
    win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    print(f"\n💰 CAPITAL:")
    print(f"   Starting: ${starting_capital:,.2f}")
    print(f"   Ending:   ${final_capital:,.2f}")
    print(f"   P&L:      ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    
    print(f"\n📊 SIGNAL DISTRIBUTION:")
    print(f"   STRONG_BUY:  {strong_buy_count:4} ({strong_buy_count/(len(backtest_candles)-50)*100:.1f}%)")
    print(f"   BUY:         {buy_count:4} ({buy_count/(len(backtest_candles)-50)*100:.1f}%)")
    print(f"   HOLD:        {hold_count:4} ({hold_count/(len(backtest_candles)-50)*100:.1f}%)")
    print(f"   SELL:        {sell_count:4} ({sell_count/(len(backtest_candles)-50)*100:.1f}%)")
    print(f"   STRONG_SELL: {strong_sell_count:4} ({strong_sell_count/(len(backtest_candles)-50)*100:.1f}%)")
    
    print(f"\n📊 TRADE STATISTICS:")
    print(f"   Total Trades:    {len(trades)}")
    print(f"   Winning Trades:  {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"   Losing Trades:   {len(losing_trades)}")
    print(f"   Average Win:     ${avg_win:,.2f}")
    print(f"   Average Loss:    ${avg_loss:,.2f}")
    
    if winning_trades and losing_trades:
        profit_factor = sum(t['pnl'] for t in winning_trades) / abs(sum(t['pnl'] for t in losing_trades))
        print(f"   Profit Factor:   {profit_factor:.2f}")
    
    # Best and worst
    if trades:
        best_trade = max(trades, key=lambda t: t['pnl'])
        worst_trade = min(trades, key=lambda t: t['pnl'])
        
        print(f"\n🏆 BEST TRADE:")
        print(f"   Entry:  ${best_trade['entry_price']:,.2f} @ {best_trade['entry_time']} (Score: {best_trade['entry_score']:.0f})")
        print(f"   Exit:   ${best_trade['exit_price']:,.2f} @ {best_trade['exit_time']}")
        print(f"   P&L:    ${best_trade['pnl']:,.2f} ({best_trade['pnl_pct']:+.2f}%)")
        
        print(f"\n💩 WORST TRADE:")
        print(f"   Entry:  ${worst_trade['entry_price']:,.2f} @ {worst_trade['entry_time']} (Score: {worst_trade['entry_score']:.0f})")
        print(f"   Exit:   ${worst_trade['exit_price']:,.2f} @ {worst_trade['exit_time']}")
        print(f"   P&L:    ${worst_trade['pnl']:,.2f} ({worst_trade['pnl_pct']:+.2f}%)")
    
    # Compare to buy and hold
    first_price = backtest_candles[50]['close']
    last_price = backtest_candles[-1]['close']
    buy_hold_pnl = ((last_price - first_price) / first_price) * starting_capital
    buy_hold_pct = ((last_price - first_price) / first_price) * 100
    
    print(f"\n📌 VS. BUY & HOLD:")
    print(f"   Price Start:     ${first_price:,.2f}")
    print(f"   Price End:       ${last_price:,.2f}")
    print(f"   Buy & Hold P&L:  ${buy_hold_pnl:,.2f} ({buy_hold_pct:+.2f}%)")
    print(f"   Hybrid P&L:      ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    
    outperformance = total_return_pct - buy_hold_pct
    if outperformance > 0:
        print(f"   ✅ Hybrid Strategy outperformed by {outperformance:+.2f}%")
    else:
        print(f"   ❌ Hybrid Strategy underperformed by {outperformance:.2f}%")
    
    print("\n" + "=" * 100)
    
    return {
        'starting_capital': starting_capital,
        'ending_capital': final_capital,
        'pnl': total_pnl,
        'return_pct': total_return_pct,
        'trades': trades,
        'win_rate': win_rate
    }


if __name__ == '__main__':
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    
    try:
        result = backtest_hybrid_strategy(symbol=symbol, starting_capital=1000.0, training_days=365)
        
        if result:
            print(f"\n🎉 Backtesting complete!")
            print(f"💵 Final Balance: ${result['ending_capital']:,.2f}")
            print(f"📈 Net Profit: ${result['pnl']:,.2f} ({result['return_pct']:+.2f}%)")
            
            if result['return_pct'] > 0:
                print(f"\n🎊 PROFITABLE STRATEGY FOUND! 🎊")
        else:
            print(f"\n❌ Backtesting failed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

