#!/usr/bin/env python3
"""
ML Model Backtesting Script - Optimized Version
- Trains ML model on 1 year of BTCUSDT data
- Uses trained model directly for fast backtesting
- Reports P&L, win rate, and performance metrics
"""
import os
import pickle
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from core.binance_client import BinanceClient
from app.ml_service import CoinMLService

load_dotenv()

def calculate_indicators(candles, index):
    """Calculate technical indicators for a specific candle index"""
    # Need at least 50 candles before the current one
    if index < 50:
        return None
    
    # Get window of candles
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
    
    # Return features in same order as training
    return [
        price_change_1h,
        price_change_4h,
        price_change_24h,
        vol_ratio,
        rsi,
        macd_hist,
        bb_position,
        hl_ratio,
        ema_trend
    ]


def backtest_ml_strategy(symbol='BTCUSDT', starting_capital=1000.0, training_days=365):
    """
    Backtest ML trading strategy using the trained model directly
    """
    print("=" * 80)
    print(f"🧪 ML BACKTESTING - {symbol}")
    print("=" * 80)
    print(f"Starting Capital: ${starting_capital:,.2f}")
    print(f"Training Period: {training_days} days")
    print("=" * 80)
    
    # Initialize
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    binance = BinanceClient(api_key, api_secret, testnet=False)
    ml_service = CoinMLService(binance)
    
    # Step 1: Train the model
    print(f"\n📚 Step 1: Training ML Model...")
    print(f"Fetching {training_days} days of historical data...")
    
    result = ml_service.train_model(symbol, days=training_days)
    
    if result.get('error'):
        print(f"❌ Training failed: {result['error']}")
        return None
    
    print(f"✅ Model trained successfully!")
    print(f"   Test Accuracy: {result['test_accuracy']:.2%}")
    print(f"   Train Accuracy: {result['train_accuracy']:.2%}")
    print(f"   Total Samples: {result.get('samples', 'N/A')}")
    
    # Step 2: Load trained model
    print(f"\n📊 Step 2: Loading Trained Model...")
    model_path = f'/tmp/ml_models/{symbol}_model.pkl'
    scaler_path = f'/tmp/ml_models/{symbol}_scaler.pkl'
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    
    print(f"✅ Model loaded")
    
    # Step 3: Prepare backtest data
    print(f"\n📈 Step 3: Fetching Backtest Data (365 days)...")
    backtest_candles = ml_service.fetch_historical_data(symbol, days=365)
    
    if len(backtest_candles) < 50:
        print(f"❌ Not enough data for backtesting")
        return None
    
    print(f"✅ Got {len(backtest_candles)} candles for backtesting")
    
    # Step 4: Run backtest
    print(f"\n🎯 Step 4: Running Backtest Simulation...")
    print("-" * 80)
    
    capital = starting_capital
    position = None
    trades = []
    
    # Track predictions for debugging
    buy_signals = 0
    sell_signals = 0
    low_confidence = 0
    
    for i in range(50, len(backtest_candles)):
        candle = backtest_candles[i]
        current_price = candle['close']
        current_time = datetime.fromtimestamp(candle['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M')
        
        # Calculate indicators for current candle
        features = calculate_indicators(backtest_candles, i)
        
        if features is None:
            continue
        
        # Scale features and predict
        features_scaled = scaler.transform([features])
        prediction_proba = model.predict_proba(features_scaled)[0]
        prediction = model.predict(features_scaled)[0]
        
        # Map prediction: 0 = HOLD, 1 = BUY/SELL based on probability
        confidence = max(prediction_proba)
        
        # Determine action
        if prediction == 1:  # Price will go up
            action = 'BUY'
        else:  # Price will go down or stay flat
            action = 'SELL'
        
        # Track signals
        if action == 'BUY':
            buy_signals += 1
        else:
            sell_signals += 1
        
        if confidence < 0.70:
            low_confidence += 1
        
        # Trading logic (lowered threshold to 0.65 for more trades)
        if position is None:
            # No position - check for BUY signal
            if action == 'BUY' and confidence >= 0.65:
                # BUY with 95% of capital
                buy_amount = capital * 0.95
                quantity = buy_amount / current_price
                
                position = {
                    'entry_price': current_price,
                    'quantity': quantity,
                    'entry_time': current_time,
                    'entry_capital': capital
                }
                
                capital -= buy_amount
                
                print(f"🟢 BUY  @ ${current_price:,.2f} | {current_time} | Confidence: {confidence:.1%}")
        
        else:
            # Have position - check for SELL signal or stop loss
            current_value = position['quantity'] * current_price
            pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
            
            # Exit conditions
            should_sell = False
            sell_reason = ""
            
            if action == 'SELL' and confidence >= 0.65:
                should_sell = True
                sell_reason = f"ML SELL signal ({confidence:.1%})"
            elif pnl_pct <= -5:  # Stop loss at -5%
                should_sell = True
                sell_reason = "Stop Loss (-5%)"
            elif pnl_pct >= 10:  # Take profit at +10%
                should_sell = True
                sell_reason = "Take Profit (+10%)"
            
            if should_sell:
                # SELL position
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
                    'reason': sell_reason
                })
                
                emoji = "🟢" if pnl > 0 else "🔴"
                print(f"{emoji} SELL @ ${current_price:,.2f} | {current_time} | P&L: ${pnl:,.2f} ({pnl_pct_actual:+.2f}%) | {sell_reason}")
                
                position = None
    
    # Close any remaining position at end
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
            'reason': 'End of backtest'
        })
        
        emoji = "🟢" if pnl > 0 else "🔴"
        print(f"{emoji} SELL @ ${final_price:,.2f} | {final_time} | P&L: ${pnl:,.2f} ({pnl_pct_actual:+.2f}%) | End of backtest")
    
    # Step 5: Calculate results
    print("\n" + "=" * 80)
    print("📈 BACKTEST RESULTS")
    print("=" * 80)
    
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
    
    print(f"\n📊 TRADE STATISTICS:")
    print(f"   Total Candles:   {len(backtest_candles) - 50}")
    print(f"   BUY Signals:     {buy_signals}")
    print(f"   SELL Signals:    {sell_signals}")
    print(f"   Low Confidence:  {low_confidence}")
    print(f"   Total Trades:    {len(trades)}")
    print(f"   Winning Trades:  {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"   Losing Trades:   {len(losing_trades)}")
    print(f"   Average Win:     ${avg_win:,.2f}")
    print(f"   Average Loss:    ${avg_loss:,.2f}")
    
    if winning_trades and losing_trades:
        profit_factor = sum(t['pnl'] for t in winning_trades) / abs(sum(t['pnl'] for t in losing_trades))
        print(f"   Profit Factor:   {profit_factor:.2f}")
    
    # Best and worst trades
    if trades:
        best_trade = max(trades, key=lambda t: t['pnl'])
        worst_trade = min(trades, key=lambda t: t['pnl'])
        
        print(f"\n🏆 BEST TRADE:")
        print(f"   Entry:  ${best_trade['entry_price']:,.2f} @ {best_trade['entry_time']}")
        print(f"   Exit:   ${best_trade['exit_price']:,.2f} @ {best_trade['exit_time']}")
        print(f"   P&L:    ${best_trade['pnl']:,.2f} ({best_trade['pnl_pct']:+.2f}%)")
        
        print(f"\n💩 WORST TRADE:")
        print(f"   Entry:  ${worst_trade['entry_price']:,.2f} @ {worst_trade['entry_time']}")
        print(f"   Exit:   ${worst_trade['exit_price']:,.2f} @ {worst_trade['exit_time']}")
        print(f"   P&L:    ${worst_trade['pnl']:,.2f} ({worst_trade['pnl_pct']:+.2f}%)")
    
    # Compare to buy and hold
    first_price = backtest_candles[50]['close']
    last_price = backtest_candles[-1]['close']
    buy_hold_pnl = ((last_price - first_price) / first_price) * starting_capital
    buy_hold_pct = ((last_price - first_price) / first_price) * 100
    
    print(f"\n📌 BUY & HOLD COMPARISON:")
    print(f"   BTC Price Start: ${first_price:,.2f}")
    print(f"   BTC Price End:   ${last_price:,.2f}")
    print(f"   Buy & Hold P&L:  ${buy_hold_pnl:,.2f} ({buy_hold_pct:+.2f}%)")
    print(f"   ML Strategy P&L: ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    
    outperformance = total_return_pct - buy_hold_pct
    if outperformance > 0:
        print(f"   ✅ ML Strategy outperformed by {outperformance:+.2f}%")
    else:
        print(f"   ❌ ML Strategy underperformed by {outperformance:.2f}%")
    
    print("\n" + "=" * 80)
    
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
    
    # Allow specifying coin via command line
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    
    try:
        result = backtest_ml_strategy(
            symbol=symbol,
            starting_capital=1000.0,
            training_days=365
        )
        
        if result:
            print(f"\n🎉 Backtesting complete!")
            print(f"💵 Final Balance: ${result['ending_capital']:,.2f}")
            print(f"📈 Net Profit: ${result['pnl']:,.2f} ({result['return_pct']:+.2f}%)")
        else:
            print(f"\n❌ Backtesting failed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

