"""
ML Trading System - Main Pipeline

Orchestrates the entire ML trading workflow:
1. Data ingestion
2. Feature engineering
3. Model training
4. Backtesting
5. Performance analysis
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime

from data_ingestion import DataIngestion
from feature_engineering import FeatureEngineering
from model_training import ModelTrainer
from backtest_engine import BacktestEngine


class MLTradingPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize ML trading pipeline"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ingestion = DataIngestion(config_path)
        self.feature_eng = FeatureEngineering(config_path)
        self.trainer = ModelTrainer(config_path)
        self.backtest = BacktestEngine(config_path)
    
    def run_full_pipeline(self, symbol: str = None):
        """Run complete ML trading pipeline for a symbol"""
        if symbol is None:
            symbol = self.config['data']['symbols'][0]
        
        print("\n" + "="*80)
        print(f"🚀 ML TRADING SYSTEM - FULL PIPELINE")
        print(f"📊 Symbol: {symbol}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # STEP 1: Data Ingestion
        print("\n" + "="*80)
        print("STEP 1: DATA INGESTION")
        print("="*80)
        
        df = self.ingestion.load_ohlcv(symbol, self.config['data']['timeframe'])
        
        if df.empty:
            print(f"   ⚠️  No data found locally, fetching from exchange...")
            df = self.ingestion.fetch_ohlcv(symbol, self.config['data']['timeframe'])
            if not df.empty:
                self.ingestion.store_ohlcv(df)
            else:
                print(f"   ❌ Failed to fetch data for {symbol}")
                return None
        
        print(f"   ✅ Loaded {len(df)} candles")
        print(f"   📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # STEP 2: Feature Engineering
        print("\n" + "="*80)
        print("STEP 2: FEATURE ENGINEERING")
        print("="*80)
        
        df_features = self.feature_eng.create_all_features(df)
        feature_columns = self.feature_eng.get_feature_columns(df_features)
        
        print(f"   ✅ Created {len(feature_columns)} features")
        print(f"   📊 Dataset size: {len(df_features)} rows")
        
        # STEP 3: Model Training
        print("\n" + "="*80)
        print("STEP 3: MODEL TRAINING")
        print("="*80)
        
        train_metrics = self.trainer.train(df_features, feature_columns)
        
        # STEP 4: Backtesting
        print("\n" + "="*80)
        print("STEP 4: BACKTESTING")
        print("="*80)
        
        # Split data for backtest (use test set)
        train_size = int(len(df_features) * self.config['model']['train_test_split'])
        df_test = df_features.iloc[train_size:].reset_index(drop=True)
        
        # Generate predictions
        X_test = df_test[feature_columns].values
        probabilities = self.trainer.predict_proba(X_test)
        predictions = self.trainer.predict(X_test)
        
        # Run backtest
        backtest_metrics = self.backtest.run_backtest(df_test, predictions, probabilities)
        
        # STEP 5: Save Results
        print("\n" + "="*80)
        print("STEP 5: SAVING RESULTS")
        print("="*80)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"results_{symbol.replace('/', '_')}_{timestamp}.json"
        self.backtest.save_results(backtest_metrics, results_file)
        
        # SUMMARY
        print("\n" + "="*80)
        print("📊 PIPELINE SUMMARY")
        print("="*80)
        
        print(f"\n🎯 MODEL PERFORMANCE:")
        print(f"   Accuracy:  {train_metrics['accuracy']:.3f}")
        print(f"   Precision: {train_metrics['precision']:.3f}")
        print(f"   ROC-AUC:   {train_metrics['roc_auc']:.3f}")
        
        print(f"\n💰 BACKTEST PERFORMANCE:")
        print(f"   ROI:          {backtest_metrics['total_return']*100:+.2f}%")
        print(f"   Win Rate:     {backtest_metrics['win_rate']*100:.1f}%")
        print(f"   Profit Factor: {backtest_metrics['profit_factor']:.2f}")
        print(f"   Sharpe Ratio:  {backtest_metrics['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown:  {backtest_metrics['max_drawdown']*100:.2f}%")
        print(f"   Total Trades:  {backtest_metrics['total_trades']}")
        
        # Success criteria
        print(f"\n✅ SUCCESS CRITERIA:")
        criteria = {
            'Sharpe > 1.5': backtest_metrics['sharpe_ratio'] > 1.5,
            'Win Rate > 55%': backtest_metrics['win_rate'] > 0.55,
            'Profit Factor > 1.3': backtest_metrics['profit_factor'] > 1.3,
            'Max Drawdown < 15%': backtest_metrics['max_drawdown'] < 0.15,
            'ROI > 0%': backtest_metrics['total_return'] > 0
        }
        
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {criterion}")
        
        passed_count = sum(criteria.values())
        print(f"\n   🎯 Passed {passed_count}/{len(criteria)} criteria")
        
        print("\n" + "="*80)
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        return {
            'train_metrics': train_metrics,
            'backtest_metrics': backtest_metrics,
            'criteria': criteria
        }
    
    def run_multi_symbol_pipeline(self):
        """Run pipeline for all configured symbols"""
        symbols = self.config['data']['symbols']
        
        print("\n" + "="*80)
        print(f"🚀 MULTI-SYMBOL PIPELINE")
        print(f"📊 Testing {len(symbols)} symbols")
        print("="*80)
        
        results = {}
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n{'='*80}")
            print(f"Symbol {i}/{len(symbols)}: {symbol}")
            print(f"{'='*80}")
            
            try:
                result = self.run_full_pipeline(symbol)
                results[symbol] = result
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                results[symbol] = None
        
        # Summary of all symbols
        print("\n" + "="*80)
        print("📊 MULTI-SYMBOL SUMMARY")
        print("="*80)
        
        for symbol, result in results.items():
            if result:
                metrics = result['backtest_metrics']
                passed = sum(result['criteria'].values())
                print(f"\n{symbol}:")
                print(f"   ROI: {metrics['total_return']*100:+.2f}% | "
                      f"Win Rate: {metrics['win_rate']*100:.1f}% | "
                      f"Sharpe: {metrics['sharpe_ratio']:.2f} | "
                      f"Criteria: {passed}/5")
            else:
                print(f"\n{symbol}: ❌ Failed")
        
        return results


def main():
    """CLI interface for ML trading system"""
    parser = argparse.ArgumentParser(description='ML Trading System')
    parser.add_argument('--mode', choices=['single', 'multi', 'update-data'], 
                        default='single', help='Pipeline mode')
    parser.add_argument('--symbol', type=str, default=None, 
                        help='Trading symbol (e.g., BTC/USDT)')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Config file path')
    
    args = parser.parse_args()
    
    pipeline = MLTradingPipeline(args.config)
    
    if args.mode == 'update-data':
        print("📥 Updating data for all symbols...")
        pipeline.ingestion.update_all_symbols()
    
    elif args.mode == 'single':
        if args.symbol:
            pipeline.run_full_pipeline(args.symbol)
        else:
            # Use first symbol in config
            symbol = pipeline.config['data']['symbols'][0]
            print(f"ℹ️  No symbol specified, using: {symbol}")
            pipeline.run_full_pipeline(symbol)
    
    elif args.mode == 'multi':
        pipeline.run_multi_symbol_pipeline()


if __name__ == '__main__':
    main()

