#!/usr/bin/env python3
"""
Momentum Strategy Backtest - ALL COINS

Tests strategy on ALL available USDT pairs from Binance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import requests
from typing import List, Dict, Tuple
import json
import time

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
        url = "https://api.binance.com/api/v3/klines"
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        params = {
            'symbol': symbol,
            'interval': '1h',
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1000
        }
        
        all_klines = []
        current_start = start_time
        
        try:
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
                    
                    if len(klines) < 1000:
                        break
                    current_start = datetime.fromtimestamp(klines[-1][0] / 1000)
                elif response.status_code == 429:  # Rate limit
                    time.sleep(1)
                    continue
                else:
                    return []
                    
        except Exception as e:
            return []
        
        return all_klines
    
    def calculate_momentum_score(self, klines: List[dict], index: int) -> float:
        """Calculate momentum score based on price action"""
        if index < 24:
            return 50
        
        recent_klines = klines[max(0, index-24):index+1]
        prices = [k['close'] for k in recent_klines]
        
        change_1h = ((prices[-1] - prices[-2]) / prices[-2]) * 100 if len(prices) >= 2 else 0
        change_24h = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) >= 24 else 0
        
        volumes = [k['volume'] for k in recent_klines]
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        score = 50
        score += change_1h * 2
        score += change_24h * 0.5
        
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 2:
            score += 20
        
        score = max(0, min(100, score))
        return score
    
    def run_backtest(self, coin: str, klines: List[dict]) -> List[Trade]:
        """Run backtest for a single coin"""
        coin_trades = []
        
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
            
            # Check for entry signals
            elif self.cash >= 1000:
                momentum = self.calculate_momentum_score(klines, i)
                
                if momentum >= 70:  # Entry threshold
                    trade = Trade(coin, current_price, current_time, momentum)
                    self.open_positions[coin] = trade
                    self.cash -= 1000
        
        # Close remaining positions
        if coin in self.open_positions:
            trade = self.open_positions[coin]
            final_kline = klines[-1]
            trade.close(final_kline['close'], final_kline['timestamp'], "End of backtest")
            self.cash += (trade.quantity * final_kline['close'])
            self.closed_trades.append(trade)
            coin_trades.append(trade)
            del self.open_positions[coin]
        
        return coin_trades
    
    def print_results(self):
        """Print backtest results"""
        print("\n" + "="*100)
        print("📈 BACKTEST RESULTS - ALL COINS")
        print("="*100)
        
        if not self.closed_trades:
            print("\n❌ No trades executed")
            return
        
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
        
        # Count trades by coin
        trades_by_coin = {}
        for trade in self.closed_trades:
            trades_by_coin[trade.coin] = trades_by_coin.get(trade.coin, 0) + 1
        
        print(f"\n💰 CAPITAL")
        print(f"   Initial: ${self.initial_capital:,.2f}")
        print(f"   Final:   ${final_capital:,.2f}")
        print(f"   P&L:     ${total_pnl:,.2f} ({roi:+.2f}%)")
        
        print(f"\n📊 TRADE STATISTICS")
        print(f"   Total Trades:   {total_trades}")
        print(f"   Coins Traded:   {len(trades_by_coin)}")
        print(f"   Winning:        {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing:         {len(losing_trades)} ({100-win_rate:.1f}%)")
        print(f"   Avg Hold Time:  {avg_hold_days:.1f} days")
        
        print(f"\n💵 PROFIT/LOSS")
        print(f"   Avg P&L/Trade:  ${avg_pnl_per_trade:,.2f}")
        print(f"   Avg Win:        ${avg_win:,.2f}")
        print(f"   Avg Loss:       ${avg_loss:,.2f}")
        print(f"   Risk/Reward:    {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   Risk/Reward:    N/A")
        
        # Exit reasons
        print(f"\n🚪 EXIT REASONS")
        exit_reasons = {}
        for trade in self.closed_trades:
            reason = trade.exit_reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_trades) * 100
            print(f"   {reason:35s} {count:4d} ({percentage:.1f}%)")
        
        # Top 10 winners
        print(f"\n🏆 TOP 10 WINNING TRADES")
        top_winners = sorted(winning_trades, key=lambda t: t.pnl, reverse=True)[:10]
        for i, trade in enumerate(top_winners, 1):
            print(f"   {i:2d}. {trade.coin:10s} ${trade.pnl:9.2f} ({trade.pnl_percent:+7.2f}%) | {trade.hold_days:3d} days | {trade.exit_reason}")
        
        # Top 10 losers
        print(f"\n💔 TOP 10 LOSING TRADES")
        top_losers = sorted(losing_trades, key=lambda t: t.pnl)[:10]
        for i, trade in enumerate(top_losers, 1):
            print(f"   {i:2d}. {trade.coin:10s} ${trade.pnl:9.2f} ({trade.pnl_percent:+7.2f}%) | {trade.hold_days:3d} days | {trade.exit_reason}")
        
        # Most traded coins
        print(f"\n🔥 MOST TRADED COINS (Top 15)")
        most_traded = sorted(trades_by_coin.items(), key=lambda x: x[1], reverse=True)[:15]
        for i, (coin, count) in enumerate(most_traded, 1):
            coin_pnl = sum(t.pnl for t in self.closed_trades if t.coin == coin)
            print(f"   {i:2d}. {coin:10s} {count:3d} trades | P&L: ${coin_pnl:9.2f}")
        
        # Save results
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'total_pnl': total_pnl,
                'roi_percent': roi,
                'total_trades': total_trades,
                'coins_traded': len(trades_by_coin),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'avg_hold_days': avg_hold_days,
                'avg_pnl_per_trade': avg_pnl_per_trade,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'risk_reward_ratio': abs(avg_win/avg_loss) if avg_loss != 0 else 0
            },
            'trades': [t.to_dict() for t in self.closed_trades],
            'trades_by_coin': trades_by_coin
        }
        
        with open('all_coins_backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: all_coins_backtest_results.json")
        print("="*100)


def get_all_binance_coins():
    """Fetch ALL USDT pairs from Binance"""
    print("📡 Fetching ALL USDT pairs from Binance...")
    
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            symbols = data['symbols']
            
            usdt_pairs = []
            for symbol in symbols:
                if (symbol['symbol'].endswith('USDT') and 
                    symbol['status'] == 'TRADING' and
                    symbol['symbol'] != 'USDT'):
                    coin = symbol['symbol'][:-4]
                    usdt_pairs.append(coin)
            
            print(f"✅ Found {len(usdt_pairs)} tradable USDT pairs\n")
            return sorted(usdt_pairs)
        else:
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def main():
    print("="*100)
    print("🚀 MOMENTUM STRATEGY BACKTEST - ALL COINS")
    print("="*100)
    print("\n📋 Strategy: Momentum Entry (70/100) | -10% Stop Loss | 7-day +10% Trailing Stop\n")
    
    all_coins = get_all_binance_coins()
    
    if not all_coins:
        print("❌ Failed to fetch coins")
        return
    
    print(f"⏳ Testing strategy on ALL {len(all_coins)} coins...")
    print(f"   This will take several minutes...\n")
    
    backtester = MomentumBacktester(initial_capital=10000)
    
    tested_count = 0
    skipped_count = 0
    
    for i, coin in enumerate(all_coins, 1):
        if i % 50 == 0:
            print(f"   Progress: {i}/{len(all_coins)} coins ({tested_count} tested, {skipped_count} skipped)...")
        
        klines = backtester.fetch_historical_klines(coin, days=365)
        
        if not klines or len(klines) < 2000:
            skipped_count += 1
            continue
        
        backtester.run_backtest(coin, klines)
        tested_count += 1
    
    print(f"\n✅ Completed: {tested_count} coins tested, {skipped_count} skipped\n")
    
    backtester.print_results()


if __name__ == '__main__':
    main()

