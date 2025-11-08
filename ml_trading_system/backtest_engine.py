"""
Backtesting Engine

Simulates trading based on ML model predictions
Includes transaction costs, slippage, and risk management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import yaml
import json
from dataclasses import dataclass, asdict


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    hold_periods: int
    signal_probability: float


class BacktestEngine:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize backtest engine with config"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.balance = self.config['backtest']['start_balance']
        self.initial_balance = self.balance
        self.peak_balance = self.balance
        
        # Config
        self.transaction_fee = self.config['backtest']['transaction_fee'] / 100
        self.slippage = self.config['backtest']['slippage'] / 100
        self.position_size_fraction = self.config['backtest']['position_size_fraction']
        self.stop_loss = self.config['backtest']['stop_loss']
        self.take_profit = self.config['backtest']['take_profit']
        self.max_holding_periods = self.config['backtest']['max_holding_periods']
        self.probability_threshold = self.config['model']['probability_threshold']
    
    def calculate_position_size(self) -> float:
        """Calculate position size based on current balance"""
        return self.balance * self.position_size_fraction
    
    def apply_costs(self, price: float, is_buy: bool) -> float:
        """Apply transaction fees and slippage"""
        if is_buy:
            # Buying: pay higher (slippage up + fees)
            return price * (1 + self.slippage + self.transaction_fee)
        else:
            # Selling: receive lower (slippage down + fees)
            return price * (1 - self.slippage - self.transaction_fee)
    
    def run_backtest(self, df: pd.DataFrame, predictions: np.ndarray, 
                     probabilities: np.ndarray) -> Dict:
        """
        Run backtest simulation
        
        Args:
            df: DataFrame with OHLCV and features
            predictions: Binary predictions (0 or 1)
            probabilities: Prediction probabilities (0-1)
        
        Returns:
            Dictionary with backtest results
        """
        print("\n" + "="*80)
        print("📈 RUNNING BACKTEST")
        print("="*80)
        
        # Reset state
        self.trades = []
        self.equity_curve = []
        self.balance = self.initial_balance
        self.peak_balance = self.balance
        
        # Track open position
        in_position = False
        entry_idx = None
        entry_price = None
        position_size = None
        signal_prob = None
        
        # Simulate trading
        for i in range(len(df)):
            timestamp = df.iloc[i]['timestamp']
            close_price = df.iloc[i]['close']
            high_price = df.iloc[i]['high']
            low_price = df.iloc[i]['low']
            prediction = predictions[i]
            probability = probabilities[i]
            
            # Record equity
            if in_position:
                current_value = self.balance + (position_size * close_price / entry_price)
                self.equity_curve.append({
                    'timestamp': timestamp,
                    'equity': current_value,
                    'in_position': 1
                })
            else:
                self.equity_curve.append({
                    'timestamp': timestamp,
                    'equity': self.balance,
                    'in_position': 0
                })
            
            # ENTRY LOGIC
            if not in_position and prediction == 1 and probability >= self.probability_threshold:
                # Calculate position size
                position_size = self.calculate_position_size()
                
                # Apply buy costs
                entry_price = self.apply_costs(close_price, is_buy=True)
                
                # Deduct from balance
                self.balance -= position_size
                
                # Record entry
                entry_idx = i
                signal_prob = probability
                in_position = True
                
                continue
            
            # EXIT LOGIC
            if in_position:
                hold_periods = i - entry_idx
                current_price = close_price
                
                # Calculate current P&L
                exit_price = self.apply_costs(current_price, is_buy=False)
                pnl = position_size * (exit_price / entry_price - 1)
                pnl_pct = (exit_price / entry_price - 1)
                
                exit_reason = None
                
                # Check stop loss (using low price)
                if low_price <= entry_price * (1 - self.stop_loss):
                    exit_price = self.apply_costs(entry_price * (1 - self.stop_loss), is_buy=False)
                    pnl = position_size * (exit_price / entry_price - 1)
                    pnl_pct = (exit_price / entry_price - 1)
                    exit_reason = "Stop Loss"
                
                # Check take profit (using high price)
                elif high_price >= entry_price * (1 + self.take_profit):
                    exit_price = self.apply_costs(entry_price * (1 + self.take_profit), is_buy=False)
                    pnl = position_size * (exit_price / entry_price - 1)
                    pnl_pct = (exit_price / entry_price - 1)
                    exit_reason = "Take Profit"
                
                # Check max holding period
                elif hold_periods >= self.max_holding_periods:
                    exit_reason = "Max Hold Time"
                
                # Exit on opposite signal
                elif prediction == 0:
                    exit_reason = "Signal Exit"
                
                # Execute exit if triggered
                if exit_reason:
                    # Add P&L to balance
                    self.balance += position_size * (exit_price / entry_price)
                    
                    # Update peak balance
                    if self.balance > self.peak_balance:
                        self.peak_balance = self.balance
                    
                    # Record trade
                    trade = Trade(
                        entry_time=df.iloc[entry_idx]['timestamp'],
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        position_size=position_size,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason,
                        hold_periods=hold_periods,
                        signal_probability=signal_prob
                    )
                    self.trades.append(trade)
                    
                    # Reset position
                    in_position = False
                    entry_idx = None
                    entry_price = None
                    position_size = None
                    signal_prob = None
        
        # Close any remaining position at end
        if in_position:
            timestamp = df.iloc[-1]['timestamp']
            close_price = df.iloc[-1]['close']
            exit_price = self.apply_costs(close_price, is_buy=False)
            pnl = position_size * (exit_price / entry_price - 1)
            pnl_pct = (exit_price / entry_price - 1)
            
            self.balance += position_size * (exit_price / entry_price)
            
            trade = Trade(
                entry_time=df.iloc[entry_idx]['timestamp'],
                exit_time=timestamp,
                entry_price=entry_price,
                exit_price=exit_price,
                position_size=position_size,
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_reason="End of Backtest",
                hold_periods=len(df) - entry_idx,
                signal_probability=signal_prob
            )
            self.trades.append(trade)
        
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        # Print results
        self.print_results(metrics)
        
        return metrics
    
    def calculate_metrics(self) -> Dict:
        """Calculate backtest performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return': 0,
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'risk_reward': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_hold_time': 0,
                'exit_reasons': {}
            }
        
        trades_df = pd.DataFrame([asdict(t) for t in self.trades])
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = trades_df['pnl'].sum()
        total_return = (self.balance - self.initial_balance) / self.initial_balance
        
        avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if loss_count > 0 else 0
        
        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if win_count > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if loss_count > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Risk/reward
        risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = abs(equity_df['drawdown'].min())
        
        # Sharpe ratio (annualized)
        equity_df['returns'] = equity_df['equity'].pct_change()
        sharpe = (equity_df['returns'].mean() / equity_df['returns'].std() * np.sqrt(252 * 24 * 60)
                  if equity_df['returns'].std() > 0 else 0)
        
        # Holding time
        avg_hold_time = trades_df['hold_periods'].mean()
        
        # Exit reasons
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
        
        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'risk_reward': risk_reward,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'avg_hold_time': avg_hold_time,
            'exit_reasons': exit_reasons
        }
    
    def print_results(self, metrics: Dict):
        """Print backtest results"""
        print("\n" + "="*80)
        print("📊 BACKTEST RESULTS")
        print("="*80)
        
        print(f"\n💰 CAPITAL")
        print(f"   Initial: ${metrics['initial_balance']:,.2f}")
        print(f"   Final:   ${metrics['final_balance']:,.2f}")
        print(f"   P&L:     ${metrics['total_pnl']:,.2f} ({metrics['total_return']*100:+.2f}%)")
        
        print(f"\n📊 TRADE STATISTICS")
        print(f"   Total Trades: {metrics['total_trades']}")
        print(f"   Winning:      {metrics['win_count']} ({metrics['win_rate']*100:.1f}%)")
        print(f"   Losing:       {metrics['loss_count']} ({(1-metrics['win_rate'])*100:.1f}%)")
        print(f"   Avg Hold:     {metrics['avg_hold_time']:.1f} periods")
        
        print(f"\n💵 PROFIT/LOSS")
        print(f"   Avg Win:       ${metrics['avg_win']:.2f}")
        print(f"   Avg Loss:      ${metrics['avg_loss']:.2f}")
        print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   Risk/Reward:   {metrics['risk_reward']:.2f}")
        
        print(f"\n📉 RISK METRICS")
        print(f"   Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
        print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        
        print(f"\n🚪 EXIT REASONS")
        for reason, count in metrics['exit_reasons'].items():
            pct = count / metrics['total_trades'] * 100
            print(f"   {reason:20s} {count:4d} ({pct:.1f}%)")
        
        print("\n" + "="*80)
    
    def save_results(self, metrics: Dict, filename: str = "backtest_results.json"):
        """Save backtest results to file"""
        results = {
            'metrics': metrics,
            'trades': [asdict(t) for t in self.trades],
            'equity_curve': self.equity_curve,
            'config': self.config['backtest']
        }
        
        # Convert datetime and numpy types to JSON-serializable formats
        for trade in results['trades']:
            trade['entry_time'] = str(trade['entry_time'])
            trade['exit_time'] = str(trade['exit_time'])
            # Convert numpy types
            for key, value in trade.items():
                if hasattr(value, 'item'):  # numpy type
                    trade[key] = value.item()
        
        for point in results['equity_curve']:
            point['timestamp'] = str(point['timestamp'])
            # Convert numpy types
            for key, value in point.items():
                if hasattr(value, 'item'):  # numpy type
                    point[key] = value.item()
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved to: {filename}")


def main():
    """Test backtest engine"""
    from data_ingestion import DataIngestion
    from feature_engineering import FeatureEngineering
    from model_training import ModelTrainer
    
    print("="*80)
    print("🧪 TESTING BACKTEST ENGINE")
    print("="*80)
    
    # Load data
    print("\n1️⃣  Loading data...")
    ingestion = DataIngestion()
    df = ingestion.load_ohlcv('BTC/USDT', '1m')
    
    if df.empty:
        print("❌ No data found. Run data_ingestion.py first.")
        return
    
    # Create features
    print("\n2️⃣  Creating features...")
    fe = FeatureEngineering()
    df_features = fe.create_all_features(df)
    feature_columns = fe.get_feature_columns(df_features)
    
    # Train model
    print("\n3️⃣  Training model...")
    trainer = ModelTrainer()
    
    # Split data
    train_size = int(len(df_features) * 0.8)
    df_train = df_features.iloc[:train_size]
    df_test = df_features.iloc[train_size:]
    
    X_train = df_train[feature_columns].values
    y_train = df_train['label'].values
    
    # Quick training
    if trainer.config['model']['type'] == 'xgboost':
        import xgboost as xgb
        dtrain = xgb.DMatrix(X_train, label=y_train)
        params = {'objective': 'binary:logistic', 'max_depth': 6, 'learning_rate': 0.1}
        trainer.model = xgb.train(params, dtrain, num_boost_round=50)
        trainer.feature_columns = feature_columns
    
    # Predict on test set
    print("\n4️⃣  Generating predictions...")
    X_test = df_test[feature_columns].values
    probabilities = trainer.predict_proba(X_test)
    predictions = trainer.predict(X_test)
    
    # Run backtest
    print("\n5️⃣  Running backtest...")
    backtest = BacktestEngine()
    metrics = backtest.run_backtest(df_test, predictions, probabilities)
    
    # Save results
    backtest.save_results(metrics)
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

