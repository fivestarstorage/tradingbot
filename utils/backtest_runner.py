"""
Simple Backtest Runner
Supports both Binance API and CSV file uploads
"""
import sys
import os
import pandas as pd
from strategies.enhanced_strategy import EnhancedStrategy
from strategies.volatile_coins_strategy import VolatileCoinsStrategy
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class BacktestRunner:
    """Simple backtester that works with any data source"""
    
    def __init__(self, initial_capital=1000, commission=0.001, strategy_type='enhanced'):
        self.initial_capital = initial_capital
        self.commission = commission
        
        # Choose strategy based on type
        if strategy_type == 'volatile':
            self.strategy = VolatileCoinsStrategy()
            logger.info("Using: Volatile Coins Strategy (High confidence, conservative)")
        else:
            self.strategy = EnhancedStrategy()
            logger.info("Using: Enhanced Strategy (Standard momentum)")
        
        self.reset()
    
    def reset(self):
        """Reset state for new backtest"""
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
    
    def load_csv(self, filepath):
        """
        Load data from CSV file
        
        Required columns: timestamp, open, high, low, close, volume
        Optional columns: Any additional data will be ignored
        
        CSV Format Example:
        timestamp,open,high,low,close,volume
        1696550400000,28000.0,28100.0,27900.0,28050.0,1000.5
        1696550700000,28050.0,28200.0,28000.0,28150.0,1200.3
        ...
        """
        logger.info(f"Loading data from {filepath}...")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV file not found: {filepath}")
        
        df = pd.read_csv(filepath)
        
        # Check required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
        
        # Convert to klines format (list of lists)
        klines = []
        for _, row in df.iterrows():
            klines.append([
                int(row['timestamp']),
                str(row['open']),
                str(row['high']),
                str(row['low']),
                str(row['close']),
                str(row['volume']),
                0, 0, 0, 0, 0, 0  # Placeholder for extra Binance fields
            ])
        
        logger.info(f"Loaded {len(klines)} candles from CSV")
        return klines
    
    def fetch_from_binance(self, symbol, interval='5m', days=30):
        """Fetch data from Binance API"""
        logger.info(f"Fetching {days} days of {interval} data for {symbol}...")
        
        try:
            from binance_client import BinanceClient
            
            client = BinanceClient(
                api_key=Config.BINANCE_API_KEY,
                api_secret=Config.BINANCE_API_SECRET,
                testnet=Config.USE_TESTNET
            )
            
            klines_per_day = {
                '1m': 1440, '3m': 480, '5m': 288, '15m': 96,
                '30m': 48, '1h': 24, '4h': 6, '1d': 1
            }
            
            limit = min(klines_per_day.get(interval, 288) * days, 1000)
            klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            if not klines:
                raise Exception("No data returned from Binance")
            
            logger.info(f"Fetched {len(klines)} candles")
            return klines
            
        except Exception as e:
            logger.error(f"Failed to fetch from Binance: {e}")
            return None
    
    def run(self, klines, min_confidence=50):
        """Run backtest on provided klines data"""
        if not klines or len(klines) < 100:
            raise ValueError("Insufficient data (need at least 100 candles)")
        
        logger.info("Starting backtest...")
        self.reset()
        
        # Process data
        df = self.strategy.process_klines(klines)
        df = self.strategy.calculate_indicators(df)
        
        if df is None:
            raise ValueError("Failed to process data")
        
        # Run through each candle
        for i in range(len(df)):
            if i < 60:  # Need enough data for indicators
                continue
            
            current_data = df.iloc[:i+1]
            current = df.iloc[i]
            price = current['close']
            timestamp = current['timestamp']
            
            # Generate signal
            signal_result = self.strategy.generate_signal(current_data)
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            risk = signal_result.get('risk', {})
            
            # Check if we have a position
            if self.position is not None:
                should_exit = False
                reason = None
                
                entry_price = self.position['entry_price']
                stop_loss = self.position['stop_loss']
                take_profit = self.position['take_profit']
                
                # Check exits
                if price <= stop_loss:
                    should_exit = True
                    reason = "Stop Loss"
                elif price >= take_profit:
                    should_exit = True
                    reason = "Take Profit"
                elif signal == 'SELL' and confidence >= min_confidence:
                    should_exit = True
                    reason = "Sell Signal"
                
                if should_exit:
                    self._close_position(price, timestamp, reason)
            
            # Check for entry
            elif signal == 'BUY' and confidence >= min_confidence:
                position_mult = risk.get('position_multiplier', 0.5)
                position_value = self.capital * 0.95 * position_mult
                quantity = position_value / price
                
                stop_loss = risk.get('stop_loss', price * 0.98)
                take_profit = risk.get('take_profit', price * 1.05)
                
                self._open_position(price, timestamp, quantity, signal_result, 
                                  stop_loss, take_profit)
            
            # Track equity
            equity = self.capital
            if self.position:
                equity += self.position['quantity'] * price
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'price': price
            })
        
        # Close any open position
        if self.position:
            final_price = df.iloc[-1]['close']
            final_time = df.iloc[-1]['timestamp']
            self._close_position(final_price, final_time, "End of Backtest")
        
        # Return results
        return self._calculate_results()
    
    def _open_position(self, price, timestamp, quantity, signal, stop_loss, take_profit):
        """Open a position"""
        cost = quantity * price
        commission = cost * self.commission
        
        self.position = {
            'entry_price': price,
            'entry_time': timestamp,
            'quantity': quantity,
            'cost': cost + commission,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
        self.capital -= (cost + commission)
        logger.info(f"OPEN: BUY {quantity:.6f} @ ${price:.2f} (Conf: {signal['confidence']}%)")
    
    def _close_position(self, price, timestamp, reason):
        """Close a position"""
        quantity = self.position['quantity']
        entry_price = self.position['entry_price']
        
        proceeds = quantity * price
        commission = proceeds * self.commission
        net_proceeds = proceeds - commission
        
        pnl = net_proceeds - self.position['cost']
        pnl_percent = (pnl / self.position['cost']) * 100
        
        self.capital += net_proceeds
        
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': timestamp,
            'entry_price': entry_price,
            'exit_price': price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason
        }
        
        self.trades.append(trade)
        logger.info(f"CLOSE: SELL @ ${price:.2f} | P&L: {pnl_percent:+.2f}% | {reason}")
        
        self.position = None
    
    def _calculate_results(self):
        """Calculate backtest metrics"""
        import numpy as np
        
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return = (total_pnl / self.initial_capital) * 100
        win_rate = len(wins) / len(self.trades) * 100
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # Sharpe ratio
        returns = [t['pnl_percent'] for t in self.trades]
        sharpe = (np.mean(returns) / np.std(returns)) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'avg_win': np.mean([t['pnl_percent'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_percent'] for t in losses]) if losses else 0,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'final_equity': self.capital
        }
    
    def print_results(self, results):
        """Print results in a nice format"""
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)
        print(f"Initial Capital:      ${self.initial_capital:.2f}")
        print(f"Final Equity:         ${results['final_equity']:.2f}")
        print(f"Total Return:         {results['total_return']:+.2f}%")
        print(f"Total P&L:            ${results['total_pnl']:+.2f}")
        print()
        print(f"Total Trades:         {results['total_trades']}")
        print(f"Winning Trades:       {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"Losing Trades:        {results['losing_trades']}")
        print()
        print(f"Average Win:          {results['avg_win']:+.2f}%")
        print(f"Average Loss:         {results['avg_loss']:+.2f}%")
        print(f"Profit Factor:        {results['profit_factor']:.2f}")
        print(f"Max Drawdown:         {results['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio:         {results['sharpe_ratio']:.2f}")
        print("=" * 70)
        
        # Recent trades
        if self.trades:
            print("\nRECENT TRADES (Last 5):")
            print("-" * 70)
            for i, trade in enumerate(self.trades[-5:], 1):
                print(f"{i}. ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} | "
                      f"P&L: {trade['pnl_percent']:+.2f}% | {trade['reason']}")
        print()


def main():
    """Main entry point"""
    print("=" * 70)
    print("TRADING STRATEGY BACKTESTER")
    print("=" * 70)
    print()
    
    # Choose strategy
    print("STRATEGY TYPE:")
    print("1. Enhanced Strategy (for BTC, ETH - stable coins)")
    print("2. Volatile Coins Strategy (for SOL, DOGE, SHIB - altcoins)")
    strategy_choice = input("\nChoose strategy (1 or 2): ").strip()
    strategy_type = 'volatile' if strategy_choice == '2' else 'enhanced'
    print()
    
    # Ask for data source
    print("DATA SOURCE:")
    print("1. Fetch from Binance API")
    print("2. Upload CSV file")
    choice = input("\nChoose option (1 or 2): ").strip()
    
    runner = BacktestRunner(initial_capital=1000, strategy_type=strategy_type)
    
    if choice == '2':
        # CSV upload
        print("\nCSV file should have columns: timestamp, open, high, low, close, volume")
        print("Example: data/BTCUSDT_5m_2023.csv")
        filepath = input("\nEnter CSV file path: ").strip()
        
        try:
            klines = runner.load_csv(filepath)
        except Exception as e:
            print(f"\n❌ Error loading CSV: {e}")
            return
    
    else:
        # Binance API
        try:
            Config.validate()
        except ValueError as e:
            print(f"\n❌ Configuration error: {e}")
            print("Make sure you have a .env file with API credentials")
            return
        
        symbol = input(f"\nTrading symbol [BTCUSDT]: ").strip() or 'BTCUSDT'
        interval = input("Interval (5m/15m/1h/4h) [5m]: ").strip() or '5m'
        days = int(input("Days of data [30]: ").strip() or '30')
        
        klines = runner.fetch_from_binance(symbol, interval, days)
        
        if not klines:
            print("\n❌ Failed to fetch data")
            return
    
    # Run backtest
    print()
    try:
        results = runner.run(klines)
        runner.print_results(results)
    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Export option
    export = input("Export results to CSV? (yes/no) [no]: ").strip().lower()
    if export in ['yes', 'y']:
        df = pd.DataFrame(runner.trades)
        filename = 'backtest_results.csv'
        df.to_csv(filename, index=False)
        print(f"✓ Results exported to {filename}")
    
    print("\n✅ Backtest complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(0)
