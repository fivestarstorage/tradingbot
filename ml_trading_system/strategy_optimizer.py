"""
Strategy Optimizer - Background Job

Tests multiple ML strategies to find the best performing one:
- Different models (XGBoost, LightGBM)
- Different hyperparameters
- Different label thresholds
- Different prediction horizons
- Different feature selections

Runs in background and saves results for comparison
"""

import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from itertools import product
from typing import Dict, List, Tuple

from data_ingestion import DataIngestion
from feature_engineering import FeatureEngineering
from model_training import ModelTrainer
from backtest_engine import BacktestEngine


class StrategyOptimizer:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize strategy optimizer"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.results = []
        self.output_dir = Path("optimization_results")
        self.output_dir.mkdir(exist_ok=True)
    
    def define_strategy_grid(self) -> List[Dict]:
        """
        Define grid of strategies to test
        
        Returns list of strategy configurations
        """
        strategies = []
        
        # Model types
        models = ['xgboost', 'lightgbm']
        
        # Label configurations
        label_configs = [
            {'horizon': 5, 'threshold': 0.002},   # 5 min, 0.2%
            {'horizon': 10, 'threshold': 0.003},  # 10 min, 0.3%
            {'horizon': 10, 'threshold': 0.005},  # 10 min, 0.5%
            {'horizon': 15, 'threshold': 0.005},  # 15 min, 0.5%
            {'horizon': 15, 'threshold': 0.010},  # 15 min, 1.0%
            {'horizon': 30, 'threshold': 0.010},  # 30 min, 1.0%
            {'horizon': 30, 'threshold': 0.015},  # 30 min, 1.5%
        ]
        
        # Hyperparameter sets
        hyperparams = [
            # Conservative (less overfitting)
            {
                'max_depth': 4,
                'learning_rate': 0.03,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            },
            # Moderate
            {
                'max_depth': 6,
                'learning_rate': 0.05,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            },
            # Aggressive (more complex)
            {
                'max_depth': 8,
                'learning_rate': 0.1,
                'n_estimators': 150,
                'subsample': 0.9,
                'colsample_bytree': 0.9,
            },
        ]
        
        # Probability thresholds
        prob_thresholds = [0.5, 0.6, 0.7]
        
        # Generate all combinations
        strategy_id = 1
        for model, label_cfg, hyperparam, prob_threshold in product(
            models, label_configs, hyperparams, prob_thresholds
        ):
            strategies.append({
                'id': strategy_id,
                'model': model,
                'label_horizon': label_cfg['horizon'],
                'label_threshold': label_cfg['threshold'],
                'hyperparameters': hyperparam,
                'probability_threshold': prob_threshold,
            })
            strategy_id += 1
        
        return strategies
    
    def test_strategy(
        self, 
        strategy: Dict, 
        df_features: pd.DataFrame, 
        feature_columns: List[str]
    ) -> Dict:
        """
        Test a single strategy configuration
        
        Returns performance metrics
        """
        print(f"\n{'='*80}")
        print(f"Testing Strategy #{strategy['id']}")
        print(f"{'='*80}")
        print(f"Model: {strategy['model']}")
        print(f"Label: {strategy['label_horizon']}min ahead, {strategy['label_threshold']*100:.1f}% threshold")
        print(f"Prob Threshold: {strategy['probability_threshold']}")
        print(f"Hyperparams: depth={strategy['hyperparameters']['max_depth']}, "
              f"lr={strategy['hyperparameters']['learning_rate']}")
        
        try:
            # Update config with strategy parameters
            self.config['model']['type'] = strategy['model']
            self.config['model']['label_horizon'] = strategy['label_horizon']
            self.config['model']['label_threshold'] = strategy['label_threshold']
            self.config['model']['probability_threshold'] = strategy['probability_threshold']
            self.config['model']['hyperparameters'] = strategy['hyperparameters']
            
            # Recreate labels with new config
            fe = FeatureEngineering(self.config)
            df_test = df_features.copy()
            
            # Recalculate labels
            df_test['label'] = (
                df_test['close'].shift(-strategy['label_horizon']) / df_test['close'] - 1 
                >= strategy['label_threshold']
            ).astype(int)
            df_test = df_test.dropna()
            
            positive_pct = df_test['label'].mean() * 100
            print(f"Label distribution: {positive_pct:.1f}% positive")
            
            # Skip if too few positive samples
            if df_test['label'].sum() < 50:
                print(f"⚠️  Skipping: Only {df_test['label'].sum()} positive samples")
                return None
            
            # Train model
            trainer = ModelTrainer(self.config)
            
            # Prepare data
            train_size = int(len(df_test) * 0.8)
            df_train = df_test.iloc[:train_size]
            df_backtest = df_test.iloc[train_size:].reset_index(drop=True)
            
            X_train = df_train[feature_columns].values
            y_train = df_train['label'].values
            
            X_val_split = int(len(X_train) * 0.9)
            X_train_split = X_train[:X_val_split]
            y_train_split = y_train[:X_val_split]
            X_val = X_train[X_val_split:]
            y_val = y_train[X_val_split:]
            
            # Train
            if strategy['model'] == 'xgboost':
                trainer.model = trainer.train_xgboost(X_train_split, y_train_split, X_val, y_val)
            else:
                trainer.model = trainer.train_lightgbm(X_train_split, y_train_split, X_val, y_val)
            
            trainer.feature_columns = feature_columns
            trainer.model_type = strategy['model']
            
            # Backtest
            X_test = df_backtest[feature_columns].values
            probabilities = trainer.predict_proba(X_test)
            predictions = trainer.predict(X_test)
            
            print(f"Generated {predictions.sum()} signals")
            
            backtest = BacktestEngine(self.config)
            metrics = backtest.run_backtest(df_backtest, predictions, probabilities)
            
            # Combine strategy config with results
            result = {
                **strategy,
                'metrics': metrics,
                'train_samples': len(df_train),
                'test_samples': len(df_backtest),
                'positive_rate': positive_pct,
                'signals_generated': int(predictions.sum()),
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error testing strategy: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_optimization(self, symbol: str = 'BTC/USDT', use_cached_data: bool = True):
        """
        Run optimization across all strategies
        
        Args:
            symbol: Trading pair to test
            use_cached_data: Use data from database if available
        """
        print("\n" + "="*80)
        print("🚀 ML STRATEGY OPTIMIZATION")
        print("="*80)
        print(f"Symbol: {symbol}")
        print(f"Testing multiple ML configurations to find the best strategy\n")
        
        # Load or fetch data
        print("📊 Loading data...")
        ingestion = DataIngestion(self.config)
        
        if use_cached_data:
            df = ingestion.load_ohlcv(symbol, '1m')
            if df.empty:
                print("No cached data, fetching from exchange...")
                from datetime import datetime, timedelta
                since = datetime.now() - timedelta(days=90)
                df = ingestion.fetch_ohlcv(symbol, '1m', since=since)
                ingestion.store_ohlcv(df)
        else:
            from datetime import datetime, timedelta
            since = datetime.now() - timedelta(days=90)
            df = ingestion.fetch_ohlcv(symbol, '1m', since=since)
        
        print(f"✅ Loaded {len(df):,} candles")
        
        # Create features
        print("\n📊 Creating features...")
        fe = FeatureEngineering(self.config)
        df_features = fe.create_all_features(df)
        feature_columns = fe.get_feature_columns(df_features)
        print(f"✅ {len(feature_columns)} features created")
        
        # Get strategy grid
        strategies = self.define_strategy_grid()
        print(f"\n🎯 Testing {len(strategies)} strategy combinations...")
        print(f"   This will take 30-60 minutes...\n")
        
        # Test each strategy
        for i, strategy in enumerate(strategies, 1):
            print(f"\n[{i}/{len(strategies)}] Testing strategy #{strategy['id']}...")
            
            result = self.test_strategy(strategy, df_features, feature_columns)
            
            if result:
                self.results.append(result)
                
                # Print quick summary
                metrics = result['metrics']
                print(f"   ROI: {metrics['total_return']*100:+.2f}% | "
                      f"Win Rate: {metrics['win_rate']*100:.1f}% | "
                      f"Sharpe: {metrics['sharpe_ratio']:.2f} | "
                      f"Trades: {metrics['total_trades']}")
                
                # Save incremental results
                self._save_results()
        
        # Final analysis
        self._print_summary()
        self._save_results()
    
    def _print_summary(self):
        """Print summary of optimization results"""
        if not self.results:
            print("\n❌ No successful results")
            return
        
        print("\n" + "="*80)
        print("📊 OPTIMIZATION SUMMARY")
        print("="*80)
        
        # Convert to DataFrame for analysis
        df_results = pd.DataFrame([
            {
                'id': r['id'],
                'model': r['model'],
                'horizon': r['label_horizon'],
                'threshold': r['label_threshold'],
                'prob_thresh': r['probability_threshold'],
                'roi': r['metrics']['total_return'] * 100,
                'win_rate': r['metrics']['win_rate'] * 100,
                'sharpe': r['metrics']['sharpe_ratio'],
                'profit_factor': r['metrics']['profit_factor'],
                'max_dd': r['metrics']['max_drawdown'] * 100,
                'trades': r['metrics']['total_trades'],
            }
            for r in self.results
        ])
        
        print(f"\n✅ Tested {len(df_results)} strategies successfully")
        print(f"\n📈 TOP 10 STRATEGIES BY ROI:")
        print("-" * 80)
        
        top_roi = df_results.nlargest(10, 'roi')
        for i, row in enumerate(top_roi.itertuples(), 1):
            print(f"{i:2d}. Strategy #{row.id:3d} | "
                  f"ROI: {row.roi:+6.2f}% | "
                  f"Win: {row.win_rate:5.1f}% | "
                  f"Sharpe: {row.sharpe:5.2f} | "
                  f"PF: {row.profit_factor:4.2f} | "
                  f"Trades: {row.trades:3d}")
            strategy = self.results[row.id - 1]
            print(f"     {strategy['model'].upper()} | "
                  f"{strategy['label_horizon']}min/{strategy['label_threshold']*100:.1f}% | "
                  f"prob={strategy['probability_threshold']} | "
                  f"depth={strategy['hyperparameters']['max_depth']}")
        
        print(f"\n🏆 TOP 10 STRATEGIES BY SHARPE RATIO:")
        print("-" * 80)
        
        top_sharpe = df_results.nlargest(10, 'sharpe')
        for i, row in enumerate(top_sharpe.itertuples(), 1):
            print(f"{i:2d}. Strategy #{row.id:3d} | "
                  f"Sharpe: {row.sharpe:6.2f} | "
                  f"ROI: {row.roi:+6.2f}% | "
                  f"Win: {row.win_rate:5.1f}% | "
                  f"Trades: {row.trades:3d}")
        
        print(f"\n📊 STATISTICS:")
        print(f"   Profitable strategies: {(df_results['roi'] > 0).sum()} / {len(df_results)} "
              f"({(df_results['roi'] > 0).mean()*100:.1f}%)")
        print(f"   Avg ROI: {df_results['roi'].mean():.2f}%")
        print(f"   Best ROI: {df_results['roi'].max():.2f}%")
        print(f"   Worst ROI: {df_results['roi'].min():.2f}%")
        print(f"   Avg Sharpe: {df_results['sharpe'].mean():.2f}")
        print(f"   Best Sharpe: {df_results['sharpe'].max():.2f}")
        
        # Best overall strategy (composite score)
        df_results['composite_score'] = (
            (df_results['roi'] / df_results['roi'].std()) +
            (df_results['sharpe'] / df_results['sharpe'].std()) +
            (df_results['win_rate'] / df_results['win_rate'].std())
        )
        
        best = df_results.nlargest(1, 'composite_score').iloc[0]
        print(f"\n🌟 BEST OVERALL STRATEGY (composite score):")
        print(f"   Strategy #{int(best['id'])}")
        print(f"   Model: {best['model'].upper()}")
        print(f"   Label: {int(best['horizon'])}min ahead, {best['threshold']*100:.1f}% threshold")
        print(f"   Probability threshold: {best['prob_thresh']}")
        print(f"   ROI: {best['roi']:+.2f}%")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Sharpe: {best['sharpe']:.2f}")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        print(f"   Trades: {int(best['trades'])}")
    
    def _save_results(self):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"strategy_optimization_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")


def main():
    """Run strategy optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ML Strategy Optimizer')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Trading symbol')
    parser.add_argument('--no-cache', action='store_true', help='Fetch fresh data')
    
    args = parser.parse_args()
    
    optimizer = StrategyOptimizer()
    optimizer.run_optimization(
        symbol=args.symbol,
        use_cached_data=not args.no_cache
    )


if __name__ == '__main__':
    main()

