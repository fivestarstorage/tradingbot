"""
Quick Demo - ML Trading System

Runs a fast demo with 30 days of BTC data to showcase the system
"""

import yaml
from data_ingestion import DataIngestion
from feature_engineering import FeatureEngineering
from model_training import ModelTrainer
from backtest_engine import BacktestEngine
from datetime import datetime, timedelta


def main():
    print("\n" + "="*80)
    print("🚀 ML TRADING SYSTEM - QUICK DEMO")
    print("="*80)
    print("\n📋 This demo will:")
    print("   1. Fetch 30 days of BTC/USDT 1-minute data")
    print("   2. Create 50+ technical indicators")
    print("   3. Train XGBoost model")
    print("   4. Backtest the strategy")
    print("   5. Show performance metrics\n")
    
    # Initialize
    config_path = "config.yaml"
    symbol = "BTC/USDT"
    timeframe = "1m"
    days = 30  # Just 30 days for quick demo
    
    print("="*80)
    print("STEP 1: FETCHING DATA")
    print("="*80)
    
    ingestion = DataIngestion(config_path)
    
    # Check if we already have data
    df = ingestion.load_ohlcv(symbol, timeframe)
    
    if len(df) < 10000:  # If less than ~7 days of data
        print(f"📥 Fetching {days} days of {symbol} data...")
        since = datetime.now() - timedelta(days=days)
        df = ingestion.fetch_ohlcv(symbol, timeframe, since=since)
        
        if not df.empty:
            ingestion.store_ohlcv(df)
            print(f"✅ Fetched and stored {len(df)} candles")
    else:
        # Use last 30 days of data
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff]
        print(f"✅ Using existing data: {len(df)} candles")
    
    print(f"   📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # STEP 2: Feature Engineering
    print("\n" + "="*80)
    print("STEP 2: FEATURE ENGINEERING")
    print("="*80)
    
    fe = FeatureEngineering(config_path)
    df_features = fe.create_all_features(df)
    feature_columns = fe.get_feature_columns(df_features)
    
    print(f"\n   ✅ Created {len(feature_columns)} features")
    print(f"   📊 Dataset: {len(df_features)} rows")
    
    # Show top features
    print(f"\n   📋 Sample Features:")
    for i, col in enumerate(feature_columns[:10], 1):
        print(f"      {i:2d}. {col}")
    print(f"      ... and {len(feature_columns) - 10} more")
    
    # STEP 3: Model Training
    print("\n" + "="*80)
    print("STEP 3: MODEL TRAINING")
    print("="*80)
    
    trainer = ModelTrainer(config_path)
    train_metrics = trainer.train(df_features, feature_columns)
    
    # STEP 4: Backtesting
    print("\n" + "="*80)
    print("STEP 4: BACKTESTING")
    print("="*80)
    
    # Use test set for backtest
    train_size = int(len(df_features) * 0.8)
    df_test = df_features.iloc[train_size:].reset_index(drop=True)
    
    # Generate predictions
    X_test = df_test[feature_columns].values
    probabilities = trainer.predict_proba(X_test)
    predictions = trainer.predict(X_test)
    
    # Run backtest
    backtest = BacktestEngine(config_path)
    backtest_metrics = backtest.run_backtest(df_test, predictions, probabilities)
    
    # SUMMARY
    print("\n" + "="*80)
    print("📊 DEMO RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n🎯 MODEL PERFORMANCE:")
    print(f"   Accuracy:  {train_metrics['accuracy']:.1%}")
    print(f"   Precision: {train_metrics['precision']:.1%}")
    print(f"   Recall:    {train_metrics['recall']:.1%}")
    print(f"   ROC-AUC:   {train_metrics['roc_auc']:.3f}")
    
    print(f"\n💰 BACKTEST PERFORMANCE:")
    print(f"   ROI:          {backtest_metrics['total_return']*100:+.2f}%")
    print(f"   Win Rate:     {backtest_metrics['win_rate']*100:.1f}%")
    print(f"   Profit Factor: {backtest_metrics['profit_factor']:.2f}")
    print(f"   Sharpe Ratio:  {backtest_metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:  {backtest_metrics['max_drawdown']*100:.2f}%")
    print(f"   Total Trades:  {backtest_metrics['total_trades']}")
    
    # Success criteria
    print(f"\n✅ SUCCESS CRITERIA CHECK:")
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
    total_criteria = len(criteria)
    
    print(f"\n   🎯 Passed {passed_count}/{total_criteria} criteria")
    
    if passed_count >= 4:
        print(f"\n   🎉 EXCELLENT! This strategy shows strong potential!")
    elif passed_count >= 3:
        print(f"\n   👍 GOOD! Strategy is promising with some improvements needed.")
    elif passed_count >= 2:
        print(f"\n   ⚠️  NEEDS WORK! Consider tuning hyperparameters.")
    else:
        print(f"\n   ❌ POOR PERFORMANCE. Try different features or model.")
    
    # Save results
    print(f"\n💾 SAVED FILES:")
    print(f"   📊 Model: models/xgboost_*.json")
    print(f"   📈 Metrics: models/metrics/")
    print(f"   📋 Backtest: backtest_results.json")
    
    backtest.save_results(backtest_metrics)
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   • Review feature importance plots in models/metrics/")
    print("   • Tune hyperparameters in config.yaml")
    print("   • Test on more symbols: python main_pipeline.py --mode multi")
    print("   • Run full 90-day backtest for production\n")


if __name__ == '__main__':
    main()

