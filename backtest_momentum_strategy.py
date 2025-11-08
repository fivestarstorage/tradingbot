#!/usr/bin/env python3
"""
Momentum Trading Strategy Backtest

Strategy:
1. Detect early momentum swings (positive sentiment > 70/100)
2. Invest $1000 USDT when bullish signal detected
3. Hold position with stop-loss rules:
   a. Sell if price drops 10% below entry (hard stop-loss)
   b. After 7 days, sell if price drops below 10% profit (trailing stop)
4. Track all trades and calculate performance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import requests
from typing import List, Dict, Tuple
import json

# Test coins - a diverse set for backtesting
TEST_COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'ADA', 'DOGE', 
    'MATIC', 'DOT', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC',
    'FTM', 'NEAR', 'ALGO', 'VET', 'SAND', 'MANA'
]

class Trade:
    def __init__(self, coin: str, entry_price: float, entry_time: datetime, 
                 entry_sentiment: float, investment: float = 1000):
        self.coin = coin
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_sentiment = entry_sentiment
        self.investment = investment
        self.quantity = investment / entry_price
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0
        self.pnl_percent = 0
        self.hold_days = 0
        
    def close(self, exit_price: float, exit_time: datetime, reason: str):
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        
        exit_value = self.quantity * exit_price
        self.pnl = exit_value - self.investment
        self.pnl_percent = (self.pnl / self.investment) * 100
        self.hold_days = (exit_time - self.entry_time).days
        
    def should_exit(self, current_price: float, current_time: datetime) -> Tuple[bool, str]:
        """Check if position should be exited based on stop-loss rules"""
        
        # Rule A: Hard stop-loss at -10%
        stop_loss_price = self.entry_price * 0.90
        if current_price <= stop_loss_price:
            return True, "Hard Stop-Loss (-10%)"
        
        # Rule B: After 7 days, trailing stop at +10% profit
        days_held = (current_time - self.entry_time).days
        if days_held >= 7:
            trailing_stop_price = self.entry_price * 1.10
            if current_price < trailing_stop_price:
                return True, f"Trailing Stop (7+ days, <10% profit)"
        
        return False, ""
    
    def to_dict(self) -> dict:
        return {
            'coin': self.coin,
            'entry_price': f"${self.entry_price:.8f}",
            'entry_time': self.entry_time.strftime('%Y-%m-%d %H:%M'),
            'entry_sentiment': self.entry_sentiment,
            'exit_price': f"${self.exit_price:.8f}" if self.exit_price else None,
            'exit_time': self.exit_time.strftime('%Y-%m-%d %H:%M') if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'hold_days': self.hold_days,
            'pnl': f"${self.pnl:.2f}",
            'pnl_percent': f"{self.pnl_percent:.2f}%"
        }


class MomentumBacktester:
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.open_positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        
    def fetch_historical_klines(self, coin: str, days: int = 365) -> List[dict]:
        """Fetch historical OHLCV data from Binance"""
        symbol = f"{coin}USDT"
        
        # Binance API endpoint
        url = "https://api.binance.com/api/v3/klines"
        
        # Calculate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        params = {
            'symbol': symbol,
            'interval': '1h',  # Hourly candles
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1000  # Max per request
        }
        
        all_klines = []
        
        try:
            # Fetch in batches if needed
            current_start = start_time
            while current_start < end_time:
                params['startTime'] = int(current_start.timestamp() * 1000)
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    klines = response.json()
                    if not klines:
                        break
                    
                    for kline in klines:
                        all_klines.append({
                            'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    
                    # Move to next batch
                    if len(klines) < 1000:
                        break
                    current_start = datetime.fromtimestamp(klines[-1][0] / 1000)
                else:
                    print(f"  ⚠️  Error fetching {coin}: {response.status_code}")
                    return []
                    
        except Exception as e:
            print(f"  ❌ Failed to fetch {coin}: {e}")
            return []
        
        return all_klines
    
    def calculate_momentum_score(self, klines: List[dict], index: int) -> float:
        """
        Calculate momentum score based on price action
        Simulates AI sentiment (0-100)
        """
        if index < 24:  # Need at least 24 hours of data
            return 50
        
        # Get recent price action
        recent_klines = klines[max(0, index-24):index+1]
        
        # Calculate short-term momentum indicators
        prices = [k['close'] for k in recent_klines]
        
        # 1-hour change
        change_1h = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) >= 2 else 0
        
        # 24-hour change
        change_24h = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) >= 24 else 0
        
        # Volume spike (comparing to average)
        volumes = [k['volume'] for k in recent_klines]
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Calculate momentum score (0-100)
        # Positive = bullish, Negative = bearish
        score = 50  # Neutral baseline
        
        # Price momentum contribution
        score += change_1h * 2  # 1h change weighted heavily
        score += change_24h * 0.5  # 24h change weighted less
        
        # Volume contribution (volume spike = more conviction)
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 2:
            score += 20
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        return score
    
    def run_backtest(self, coin: str, klines: List[dict]) -> List[Trade]:
        """Run backtest for a single coin"""
        coin_trades = []
        
        print(f"\n  📊 Testing {coin}...")
        print(f"     Data points: {len(klines)}")
        
        for i, kline in enumerate(klines):
            current_time = kline['timestamp']
            current_price = kline['close']
            
            # Check open positions for exits
            if coin in self.open_positions:
                trade = self.open_positions[coin]
                should_exit, reason = trade.should_exit(current_price, current_time)
                
                if should_exit:
                    trade.close(current_price, current_time, reason)
                    self.cash += (trade.quantity * current_price)
                    self.closed_trades.append(trade)
                    coin_trades.append(trade)
                    del self.open_positions[coin]
                    
                    # print(f"     🔴 SELL {coin} @ ${current_price:.6f} | {reason} | P&L: {trade.pnl_percent:.2f}%")
            
            # Check for entry signals (only if no open position and have cash)
            elif self.cash >= 1000:
                momentum = self.calculate_momentum_score(klines, i)
                
                # Entry condition: Strong bullish momentum (>70)
                if momentum >= 70:
                    trade = Trade(coin, current_price, current_time, momentum)
                    self.open_positions[coin] = trade
                    self.cash -= 1000
                    
                    # print(f"     🟢 BUY {coin} @ ${current_price:.6f} | Sentiment: {momentum:.1f}/100")
        
        # Close any remaining open positions at end of backtest
        if coin in self.open_positions:
            trade = self.open_positions[coin]
            final_kline = klines[-1]
            trade.close(final_kline['close'], final_kline['timestamp'], "End of backtest")
            self.cash += (trade.quantity * final_kline['close'])
            self.closed_trades.append(trade)
            coin_trades.append(trade)
            del self.open_positions[coin]
        
        print(f"     ✅ Completed {len(coin_trades)} trades")
        
        return coin_trades
    
    def print_results(self):
        """Print backtest results"""
        print("\n" + "="*100)
        print("📈 BACKTEST RESULTS")
        print("="*100)
        
        if not self.closed_trades:
            print("\n❌ No trades executed")
            return
        
        # Calculate statistics
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in self.closed_trades)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        final_capital = self.cash
        roi = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        avg_hold_days = sum(t.hold_days for t in self.closed_trades) / total_trades if total_trades > 0 else 0
        
        # Print summary
        print(f"\n💰 CAPITAL")
        print(f"   Initial: ${self.initial_capital:,.2f}")
        print(f"   Final:   ${final_capital:,.2f}")
        print(f"   P&L:     ${total_pnl:,.2f} ({roi:+.2f}%)")
        
        print(f"\n📊 TRADE STATISTICS")
        print(f"   Total Trades:   {total_trades}")
        print(f"   Winning:        {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing:         {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"   Avg Hold Time:  {avg_hold_days:.1f} days")
        
        print(f"\n💵 PROFIT/LOSS")
        print(f"   Avg P&L/Trade:  ${avg_pnl_per_trade:,.2f}")
        print(f"   Avg Win:        ${avg_win:,.2f}")
        print(f"   Avg Loss:       ${avg_loss:,.2f}")
        print(f"   Risk/Reward:    {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   Risk/Reward:    N/A")
        
        # Exit reasons breakdown
        print(f"\n🚪 EXIT REASONS")
        exit_reasons = {}
        for trade in self.closed_trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_trades) * 100
            print(f"   {reason:30s} {count:3d} ({percentage:.1f}%)")
        
        # Top 5 winners
        print(f"\n🏆 TOP 5 WINNING TRADES")
        top_winners = sorted(winning_trades, key=lambda t: t.pnl, reverse=True)[:5]
        for i, trade in enumerate(top_winners, 1):
            print(f"   {i}. {trade.coin:6s} ${trade.pnl:8.2f} ({trade.pnl_percent:+6.2f}%) | {trade.hold_days} days | {trade.exit_reason}")
        
        # Top 5 losers
        print(f"\n💔 TOP 5 LOSING TRADES")
        top_losers = sorted(losing_trades, key=lambda t: t.pnl)[:5]
        for i, trade in enumerate(top_losers, 1):
            print(f"   {i}. {trade.coin:6s} ${trade.pnl:8.2f} ({trade.pnl_percent:+6.2f}%) | {trade.hold_days} days | {trade.exit_reason}")
        
        # Save detailed results to JSON
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'total_pnl': total_pnl,
                'roi_percent': roi,
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'avg_hold_days': avg_hold_days,
                'avg_pnl_per_trade': avg_pnl_per_trade,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'risk_reward_ratio': abs(avg_win/avg_loss) if avg_loss != 0 else 0
            },
            'trades': [t.to_dict() for t in self.closed_trades]
        }
        
        with open('momentum_backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: momentum_backtest_results.json")
        print("="*100)


def main():
    print("="*100)
    print("🚀 MOMENTUM TRADING STRATEGY BACKTEST")
    print("="*100)
    print("\n📋 Strategy Rules:")
    print("   1. Enter: When momentum score > 70/100 (bullish signal)")
    print("   2. Position Size: $1000 USDT per trade")
    print("   3. Exit Rules:")
    print("      a. Hard stop-loss: -10% below entry")
    print("      b. Trailing stop (after 7 days): Below +10% profit")
    print("\n⏳ Fetching 1 year of historical data for 20 coins...")
    
    backtester = MomentumBacktester(initial_capital=10000)
    
    for coin in TEST_COINS:
        print(f"\n📥 Fetching {coin}...")
        klines = backtester.fetch_historical_klines(coin, days=365)
        
        if not klines:
            print(f"   ⚠️  Skipping {coin} (no data)")
            continue
        
        backtester.run_backtest(coin, klines)
    
    backtester.print_results()


if __name__ == '__main__':
    main()

