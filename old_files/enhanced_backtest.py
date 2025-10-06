"""
Enhanced backtesting module with advanced features
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from binance_client import BinanceClient
from enhanced_momentum_strategy import EnhancedMomentumStrategy
from enhanced_position_manager import EnhancedPositionManager
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedBacktester:
    """
    Enhanced backtester with:
    - Dynamic position sizing
    - Trailing stops
    - Partial profit taking
    - Advanced risk management
    """
    
    def __init__(self, initial_capital=1000, commission=0.001, use_enhanced=True):
        """
        Initialize enhanced backtester
        
        Args:
            initial_capital: Starting capital in USDT
            commission: Trading commission as decimal (0.001 = 0.1%)
            use_enhanced: Use enhanced strategy features
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.use_enhanced = use_enhanced
        
        # Initialize enhanced strategy
        self.strategy = EnhancedMomentumStrategy(
            rsi_period=Config.RSI_PERIOD,
            rsi_overbought=Config.RSI_OVERBOUGHT,
            rsi_oversold=Config.RSI_OVERSOLD
        )
        
        # Initialize enhanced position manager
        self.position_manager = EnhancedPositionManager(
            base_stop_loss_percent=Config.STOP_LOSS_PERCENT,
            base_take_profit_percent=Config.TAKE_PROFIT_PERCENT
        )
        
        # Trading state
        self.capital = initial_capital
        self.trades = []
        self.equity_curve = []
        
        # Performance tracking
        self.max_concurrent_positions = 1  # For now, only 1 position at a time
        self.total_commissions_paid = 0
        
        logger.info(f"Enhanced Backtester initialized with ${initial_capital} capital")
        logger.info(f"Enhanced features: {'ENABLED' if use_enhanced else 'DISABLED'}")
    
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
    
    def run_backtest(self, klines):
        """
        Run enhanced backtest on historical data
        
        Args:
            klines: Historical kline data
            
        Returns:
            Backtest results dict
        """
        if not klines or len(klines) < 100:
            logger.error("Insufficient data for backtesting")
            return None
        
        logger.info("Starting enhanced backtest...")
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
            
            # Generate signal with enhanced strategy
            signal_result = self.strategy.generate_signal(current_data)
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            risk_mgmt = signal_result.get('risk_management', {})
            
            # Minimum confidence threshold
            min_confidence = 50  # Require at least 50% confidence
            
            # Check if we have a position
            if self.position_manager.has_position():
                # First check for partial exits
                should_partial, exit_percent, partial_reason = self.position_manager.check_partial_exits(current_price)
                if should_partial:
                    partial_trade = self.position_manager.partial_close(current_price, exit_percent, partial_reason)
                    if partial_trade:
                        self._record_trade(partial_trade, current_price, timestamp)
                
                # Check exit conditions (including trailing stop)
                should_exit, reason = self.position_manager.check_exit_conditions(current_price)
                
                # Also check for SELL signal
                if signal == 'SELL' and confidence >= min_confidence:
                    should_exit = True
                    reason = f"Sell Signal (Confidence: {confidence}%)"
                
                # Exit position
                if should_exit:
                    self._close_position(current_price, timestamp, reason)
            
            # Check for entry signal
            elif signal == 'BUY' and confidence >= min_confidence:
                # Calculate position size based on risk management
                position_size_mult = risk_mgmt.get('position_size_multiplier', 0.5)
                
                # Use percentage of available capital with dynamic sizing
                base_position_pct = 0.95  # Max 95% of capital
                adjusted_position_pct = base_position_pct * position_size_mult
                
                position_value = self.capital * adjusted_position_pct
                quantity = position_value / current_price
                
                # Get stop loss and take profit from signal
                stop_loss_price = risk_mgmt.get('stop_loss_price', None)
                take_profit_price = risk_mgmt.get('take_profit_price', None)
                trailing_mult = risk_mgmt.get('trailing_stop_multiplier', 2.0)
                atr_value = risk_mgmt.get('atr_value', None)
                
                self._open_position(
                    current_price, timestamp, quantity, signal_result,
                    stop_loss_price, take_profit_price, trailing_mult, atr_value
                )
            
            # Track equity
            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'price': current_price,
                'signal': signal,
                'confidence': confidence
            })
        
        # Close any open position at the end
        if self.position_manager.has_position():
            final_price = df.iloc[-1]['close']
            final_timestamp = df.iloc[-1]['timestamp']
            self._close_position(final_price, final_timestamp, "End of Backtest")
        
        # Calculate results
        results = self._calculate_results()
        self._print_results(results)
        
        return results
    
    def _open_position(self, price, timestamp, quantity, signal, 
                      stop_loss_price, take_profit_price, trailing_mult, atr_value):
        """Open a position with enhanced risk management"""
        cost = quantity * price
        commission_cost = cost * self.commission
        self.total_commissions_paid += commission_cost
        
        # Open position with dynamic stop loss and take profit
        success = self.position_manager.open_position(
            symbol='SYMBOL',
            side='BUY',
            quantity=quantity,
            entry_price=price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop_mult=trailing_mult,
            atr_value=atr_value
        )
        
        if success:
            self.capital -= (cost + commission_cost)
            
            logger.info(f"[{timestamp}] OPEN: BUY {quantity:.8f} @ ${price:.2f} "
                       f"(Confidence: {signal['confidence']}%)")
            logger.info(f"  Position size: {(cost/self.initial_capital)*100:.1f}% of initial capital")
            logger.info(f"  Risk Management: SL=${stop_loss_price:.2f}, TP=${take_profit_price:.2f}")
    
    def _close_position(self, price, timestamp, reason):
        """Close a position"""
        closed_position = self.position_manager.close_position(price, reason)
        
        if closed_position:
            self._record_trade(closed_position, price, timestamp)
    
    def _record_trade(self, position, exit_price, exit_time):
        """Record a completed trade"""
        quantity = position['quantity']
        entry_price = position['entry_price']
        
        # Calculate proceeds
        proceeds = quantity * exit_price
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost
        self.total_commissions_paid += commission_cost
        
        # Calculate P&L
        cost = quantity * entry_price
        pnl = net_proceeds - cost
        pnl_percent = position['pnl_percent']
        
        # Update capital
        self.capital += net_proceeds
        
        # Record trade
        trade = {
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': position.get('close_reason', 'Unknown'),
            'duration': exit_time - position['entry_time'],
            'is_partial': position.get('is_partial', False),
            'trailing_stop_used': position.get('trailing_stop_enabled', False),
            'peak_profit': position.get('peak_profit_percent', 0)
        }
        
        self.trades.append(trade)
        
        logger.info(f"[{exit_time}] CLOSE: SELL {quantity:.8f} @ ${exit_price:.2f} "
                   f"| P&L: {pnl_percent:+.2f}% | Reason: {trade['reason']}")
    
    def _calculate_equity(self, current_price):
        """Calculate current equity"""
        equity = self.capital
        
        if self.position_manager.has_position():
            position = self.position_manager.get_position_info()
            position_value = position['quantity'] * current_price
            equity += position_value
        
        return equity
    
    def _calculate_results(self):
        """Calculate comprehensive backtest results"""
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
                'final_equity': self.initial_capital,
                'total_commissions': 0
            }
        
        # Separate partial and full trades for analysis
        full_trades = [t for t in self.trades if not t.get('is_partial', False)]
        partial_trades = [t for t in self.trades if t.get('is_partial', False)]
        
        # Basic statistics
        total_trades = len(full_trades)
        winning_trades = [t for t in full_trades if t['pnl'] > 0]
        losing_trades = [t for t in full_trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)  # Include partial trades
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
        max_drawdown_duration = timedelta(0)
        drawdown_start = None
        
        for i, equity in enumerate(equity_values):
            if equity > peak:
                peak = equity
                if drawdown_start:
                    duration = self.equity_curve[i]['timestamp'] - drawdown_start
                    if duration > max_drawdown_duration:
                        max_drawdown_duration = duration
                    drawdown_start = None
            else:
                if not drawdown_start:
                    drawdown_start = self.equity_curve[i]['timestamp']
                drawdown = (peak - equity) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # Sharpe ratio (simplified - annualized)
        returns = [t['pnl_percent'] for t in full_trades]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            # Approximate annualization factor
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate average trade duration
        avg_duration = np.mean([t['duration'].total_seconds() / 3600 for t in full_trades]) if full_trades else 0
        
        # Calculate trailing stop effectiveness
        trailing_stop_trades = [t for t in full_trades if t.get('trailing_stop_used', False)]
        trailing_stop_wins = [t for t in trailing_stop_trades if t['pnl'] > 0]
        
        # Best and worst trades
        best_trade = max(full_trades, key=lambda t: t['pnl_percent']) if full_trades else None
        worst_trade = min(full_trades, key=lambda t: t['pnl_percent']) if full_trades else None
        
        # Consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_consecutive = 0
        last_was_win = None
        
        for trade in full_trades:
            is_win = trade['pnl'] > 0
            if last_was_win is None or last_was_win == is_win:
                current_consecutive += 1
            else:
                if last_was_win:
                    max_consecutive_wins = max(max_consecutive_wins, current_consecutive)
                else:
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
                current_consecutive = 1
            last_was_win = is_win
        
        # Final update
        if last_was_win:
            max_consecutive_wins = max(max_consecutive_wins, current_consecutive)
        else:
            max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
        
        final_equity = self.capital
        
        return {
            'total_trades': total_trades,
            'partial_trades': len(partial_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade['pnl_percent'] if best_trade else 0,
            'worst_trade': worst_trade['pnl_percent'] if worst_trade else 0,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration_hours': max_drawdown_duration.total_seconds() / 3600,
            'sharpe_ratio': sharpe_ratio,
            'final_equity': final_equity,
            'total_commissions': self.total_commissions_paid,
            'avg_trade_duration_hours': avg_duration,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'trailing_stop_trades': len(trailing_stop_trades),
            'trailing_stop_win_rate': (len(trailing_stop_wins) / len(trailing_stop_trades) * 100) if trailing_stop_trades else 0
        }
    
    def _print_results(self, results):
        """Print comprehensive backtest results"""
        print("\n" + "=" * 70)
        print("ENHANCED BACKTEST RESULTS")
        print("=" * 70)
        print(f"Initial Capital:          ${self.initial_capital:.2f}")
        print(f"Final Equity:             ${results['final_equity']:.2f}")
        print(f"Total Return:             {results['total_return']:+.2f}%")
        print(f"Total P&L:                ${results['total_pnl']:+.2f}")
        print(f"Total Commissions Paid:   ${results['total_commissions']:.2f}")
        print()
        print("TRADE STATISTICS")
        print("-" * 70)
        print(f"Total Trades:             {results['total_trades']}")
        print(f"Partial Exits:            {results['partial_trades']}")
        print(f"Winning Trades:           {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"Losing Trades:            {results['losing_trades']}")
        print()
        print(f"Average Win:              {results['avg_win']:+.2f}%")
        print(f"Average Loss:             {results['avg_loss']:+.2f}%")
        print(f"Best Trade:               {results['best_trade']:+.2f}%")
        print(f"Worst Trade:              {results['worst_trade']:+.2f}%")
        print(f"Profit Factor:            {results['profit_factor']:.2f}")
        print()
        print("RISK METRICS")
        print("-" * 70)
        print(f"Max Drawdown:             {results['max_drawdown']:.2f}%")
        print(f"Max DD Duration:          {results['max_drawdown_duration_hours']:.1f} hours")
        print(f"Sharpe Ratio:             {results['sharpe_ratio']:.2f}")
        print(f"Avg Trade Duration:       {results['avg_trade_duration_hours']:.1f} hours")
        print()
        print("STREAK ANALYSIS")
        print("-" * 70)
        print(f"Max Consecutive Wins:     {results['max_consecutive_wins']}")
        print(f"Max Consecutive Losses:   {results['max_consecutive_losses']}")
        print()
        print("ENHANCED FEATURES")
        print("-" * 70)
        print(f"Trailing Stop Trades:     {results['trailing_stop_trades']}")
        print(f"Trailing Stop Win Rate:   {results['trailing_stop_win_rate']:.1f}%")
        print("=" * 70)
        
        # Show recent trade details
        if self.trades:
            print("\nRECENT TRADES (Last 10):")
            print("-" * 70)
            recent_trades = self.trades[-10:]
            for i, trade in enumerate(recent_trades, 1):
                partial_flag = " [PARTIAL]" if trade.get('is_partial', False) else ""
                trailing_flag = " [TRAILING]" if trade.get('trailing_stop_used', False) else ""
                print(f"{i}. {trade['entry_time'].strftime('%m-%d %H:%M')} → "
                      f"{trade['exit_time'].strftime('%m-%d %H:%M')}")
                print(f"   ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} | "
                      f"P&L: {trade['pnl_percent']:+.2f}% | {trade['reason']}{partial_flag}{trailing_flag}")
            print("-" * 70)
        
        print()
    
    def export_results(self, filename='enhanced_backtest_results.csv'):
        """Export trade history to CSV"""
        if not self.trades:
            logger.warning("No trades to export")
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filename, index=False)
        logger.info(f"Results exported to {filename}")
        
        # Also export equity curve
        equity_df = pd.DataFrame(self.equity_curve)
        equity_filename = filename.replace('.csv', '_equity.csv')
        equity_df.to_csv(equity_filename, index=False)
        logger.info(f"Equity curve exported to {equity_filename}")


def main():
    """Main entry point for enhanced backtesting"""
    print("=" * 70)
    print("ENHANCED MOMENTUM STRATEGY BACKTESTER")
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
    
    # Initialize enhanced backtester
    backtester = EnhancedBacktester(initial_capital=initial_capital)
    
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
            filename = f"enhanced_backtest_{symbol}_{interval_input}.csv"
            backtester.export_results(filename)
    
    print("\nBacktest complete!")


if __name__ == '__main__':
    main()
