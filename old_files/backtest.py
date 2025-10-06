"""
Backtesting module for the momentum trading strategy
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from binance_client import BinanceClient
from momentum_strategy import MomentumStrategy
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Backtester:
    """Backtest the momentum trading strategy on historical data"""
    
    def __init__(self, initial_capital=1000, commission=0.001):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital in USDT
            commission: Trading commission as decimal (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        
        # Initialize strategy
        self.strategy = MomentumStrategy(
            rsi_period=Config.RSI_PERIOD,
            rsi_overbought=Config.RSI_OVERBOUGHT,
            rsi_oversold=Config.RSI_OVERSOLD,
            momentum_period=Config.MOMENTUM_PERIOD
        )
        
        # Trading state
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        logger.info(f"Backtester initialized with ${initial_capital} capital")
    
    def fetch_historical_data(self, symbol, interval='5m', days=30):
        """
        Fetch historical data from Binance
        
        Args:
            symbol: Trading pair symbol
            interval: Candle interval
            days: Number of days of historical data
            
        Returns:
            List of klines
        """
        logger.info(f"Fetching {days} days of {interval} data for {symbol}...")
        
        client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        
        # Calculate how many klines we need
        klines_per_day = {
            '1m': 1440,
            '3m': 480,
            '5m': 288,
            '15m': 96,
            '30m': 48,
            '1h': 24,
            '4h': 6,
            '1d': 1
        }
        
        limit = min(klines_per_day.get(interval, 288) * days, 1000)
        
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        
        if not klines:
            logger.error("Failed to fetch historical data")
            return None
        
        logger.info(f"Fetched {len(klines)} candles")
        return klines
    
    def run_backtest(self, klines, trade_amount=None, use_percentage=True):
        """
        Run backtest on historical data
        
        Args:
            klines: Historical kline data
            trade_amount: Amount to trade per position (if None, uses config)
            use_percentage: If True, use percentage of capital (default: True)
            
        Returns:
            Backtest results dict
        """
        if not klines or len(klines) < 100:
            logger.error("Insufficient data for backtesting")
            return None
        
        # For backtesting, use a percentage of capital instead of fixed crypto amount
        self.use_percentage = use_percentage
        self.position_size_pct = 0.95  # Use 95% of capital per trade
        trade_amount = trade_amount or Config.TRADE_AMOUNT
        
        logger.info("Starting backtest...")
        logger.info("=" * 60)
        
        # Process data
        df = self.strategy.process_klines(klines)
        df = self.strategy.calculate_indicators(df)
        
        if df is None:
            logger.error("Failed to process data")
            return None
        
        # Run through each candle
        for i in range(len(df)):
            if i < 50:  # Need enough data for indicators
                continue
            
            # Get data up to current point
            current_data = df.iloc[:i+1].copy()
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            timestamp = current_candle['timestamp']
            
            # Generate signal
            signal = self.strategy.generate_signal(current_data)
            
            # Lower confidence threshold for backtesting to see more trades
            min_confidence = 40  # Lowered from 50
            
            # Check if we have a position
            if self.position is not None:
                # Check exit conditions
                should_exit = False
                exit_reason = None
                
                entry_price = self.position['entry_price']
                
                # Check stop loss
                stop_loss = entry_price * (1 - Config.STOP_LOSS_PERCENT / 100)
                if current_price <= stop_loss:
                    should_exit = True
                    exit_reason = "Stop Loss"
                
                # Check take profit
                take_profit = entry_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
                if current_price >= take_profit:
                    should_exit = True
                    exit_reason = "Take Profit"
                
                # Check for SELL signal
                if signal['signal'] == 'SELL' and signal['confidence'] >= min_confidence:
                    should_exit = True
                    exit_reason = "Sell Signal"
                
                # Exit position
                if should_exit:
                    self._close_position(current_price, timestamp, exit_reason)
            
            # Check for entry signal
            elif signal['signal'] == 'BUY' and signal['confidence'] >= min_confidence:
                # Calculate position size based on available capital
                if self.use_percentage:
                    # Use percentage of available capital
                    position_value = self.capital * self.position_size_pct
                    quantity = position_value / current_price
                else:
                    quantity = trade_amount
                self._open_position(current_price, timestamp, quantity, signal)
            
            # Track equity
            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'price': current_price
            })
        
        # Close any open position at the end
        if self.position is not None:
            final_price = df.iloc[-1]['close']
            final_timestamp = df.iloc[-1]['timestamp']
            self._close_position(final_price, final_timestamp, "End of Backtest")
        
        # Calculate results
        results = self._calculate_results()
        self._print_results(results)
        
        return results
    
    def _open_position(self, price, timestamp, quantity, signal):
        """Open a position"""
        cost = quantity * price
        commission_cost = cost * self.commission
        
        self.position = {
            'entry_price': price,
            'entry_time': timestamp,
            'quantity': quantity,
            'cost': cost + commission_cost,
            'signal': signal
        }
        
        self.capital -= (cost + commission_cost)
        
        logger.info(f"[{timestamp}] OPEN: BUY {quantity} @ ${price:.2f} "
                   f"(Confidence: {signal['confidence']}%)")
    
    def _close_position(self, price, timestamp, reason):
        """Close a position"""
        if self.position is None:
            return
        
        quantity = self.position['quantity']
        entry_price = self.position['entry_price']
        
        # Calculate proceeds
        proceeds = quantity * price
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost
        
        # Calculate P&L
        pnl = net_proceeds - self.position['cost']
        pnl_percent = (pnl / self.position['cost']) * 100
        
        # Update capital
        self.capital += net_proceeds
        
        # Record trade
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': timestamp,
            'entry_price': entry_price,
            'exit_price': price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason,
            'duration': timestamp - self.position['entry_time']
        }
        
        self.trades.append(trade)
        
        logger.info(f"[{timestamp}] CLOSE: SELL {quantity} @ ${price:.2f} "
                   f"| P&L: {pnl_percent:+.2f}% | Reason: {reason}")
        
        self.position = None
    
    def _calculate_equity(self, current_price):
        """Calculate current equity"""
        equity = self.capital
        
        if self.position is not None:
            position_value = self.position['quantity'] * current_price
            equity += position_value
        
        return equity
    
    def _calculate_results(self):
        """Calculate backtest results"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'final_equity': self.initial_capital
            }
        
        # Basic statistics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return = (total_pnl / self.initial_capital) * 100
        
        avg_win = np.mean([t['pnl_percent'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_percent'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Sharpe ratio (simplified)
        returns = [t['pnl_percent'] for t in self.trades]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        final_equity = self.capital
        if self.position is not None:
            final_equity += self.position['quantity'] * self.position['entry_price']
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_equity': final_equity
        }
    
    def _print_results(self, results):
        """Print backtest results"""
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
        
        # Show trade details
        if self.trades:
            print("\nTrade History:")
            print("-" * 70)
            for i, trade in enumerate(self.trades, 1):
                print(f"{i}. {trade['entry_time']} → {trade['exit_time']}")
                print(f"   ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} | "
                      f"P&L: {trade['pnl_percent']:+.2f}% | {trade['reason']}")
            print("-" * 70)
        
        print()
    
    def export_results(self, filename='backtest_results.csv'):
        """Export trade history to CSV"""
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filename, index=False)
        logger.info(f"Results exported to {filename}")


def main():
    """Main entry point for backtesting"""
    print("=" * 70)
    print("MOMENTUM STRATEGY BACKTESTER")
    print("=" * 70)
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure you have a .env file with valid API credentials")
        return
    
    # Get user input
    symbol = input(f"Trading symbol [{Config.TRADING_SYMBOL}]: ").strip() or Config.TRADING_SYMBOL
    
    interval_input = input("Candle interval (1m/5m/15m/1h/4h/1d) [5m]: ").strip() or '5m'
    
    days_input = input("Days of historical data [30]: ").strip()
    days = int(days_input) if days_input else 30
    
    capital_input = input("Initial capital in USDT [1000]: ").strip()
    initial_capital = float(capital_input) if capital_input else 1000
    
    print()
    
    # Initialize backtester
    backtester = Backtester(initial_capital=initial_capital)
    
    # Fetch data
    klines = backtester.fetch_historical_data(symbol, interval=interval_input, days=days)
    
    if not klines:
        print("Failed to fetch data. Exiting.")
        return
    
    # Run backtest
    results = backtester.run_backtest(klines)
    
    if results:
        # Export results
        export = input("\nExport results to CSV? (yes/no) [no]: ").strip().lower()
        if export == 'yes':
            backtester.export_results()
    
    print("\nBacktest complete!")


if __name__ == '__main__':
    main()
