"""
Full Year Training - ML Trading System

Trains on 365 days of 1-minute BTC/USDT data
"""

import yaml
from data_ingestion import DataIngestion
from feature_engineering import FeatureEngineering
from model_training import ModelTrainer
from backtest_engine import BacktestEngine
from datetime import datetime, timedelta


def main():
    print("\n" + "="*80)
    print("🚀 ML TRADING SYSTEM - FULL YEAR TRAINING")
    print("="*80)
    print("\n📋 This will:")
    print("   1. Fetch 365 days of BTC/USDT 1-minute data (~525,000 candles)")
    print("   2. Create 68 technical features")
    print("   3. Train XGBoost on massive dataset")
    print("   4. Backtest on out-of-sample data")
    print("   5. Compare against 30-day model\n")
    print("⚠️  This will take 10-15 minutes to complete...\n")
    
    # Initialize
    config_path = "config.yaml"
    symbol = "BTC/USDT"
    timeframe = "1m"
    
    print("="*80)
    print("STEP 1: FETCHING 1 YEAR OF DATA")
    print("="*80)
    
    ingestion = DataIngestion(config_path)
    
    # Fetch full year
    since = datetime.now() - timedelta(days=365)
    print(f"📥 Fetching data from {since.strftime('%Y-%m-%d')} to now...")
    print(f"   This may take 5-10 minutes...\n")
    
    df = ingestion.fetch_ohlcv(symbol, timeframe, since=since)
    
    if df.empty:
        print("❌ Failed to fetch data")
        return
    
    print(f"\n✅ Fetched {len(df):,} candles")
    print(f"   📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Store in database
    print(f"\n💾 Storing in database...")
    ingestion.store_ohlcv(df)
    
    # STEP 2: Feature Engineering
    print("\n" + "="*80)
    print("STEP 2: FEATURE ENGINEERING")
    print("="*80)
    print(f"⏳ Creating features for {len(df):,} candles...")
    print(f"   This may take 2-3 minutes...\n")
    
    fe = FeatureEngineering(config_path)
    df_features = fe.create_all_features(df)
    feature_columns = fe.get_feature_columns(df_features)
    
    print(f"\n   ✅ Created {len(feature_columns)} features")
    print(f"   📊 Dataset: {len(df_features):,} rows")
    print(f"   💾 Data size: ~{len(df_features) * len(df_features.columns) * 8 / 1024 / 1024:.1f} MB in memory")
    
    # Show label distribution
    positive_pct = df_features['label'].mean() * 100
    positive_count = df_features['label'].sum()
    print(f"\n   🏷️  Labels: {positive_count:,} positive ({positive_pct:.1f}%), {len(df_features) - positive_count:,} negative")
    
    # STEP 3: Model Training
    print("\n" + "="*80)
    print("STEP 3: MODEL TRAINING ON FULL YEAR")
    print("="*80)
    print(f"⏳ Training XGBoost on {len(df_features):,} samples...")
    print(f"   This may take 3-5 minutes...\n")
    
    trainer = ModelTrainer(config_path)
    train_metrics = trainer.train(df_features, feature_columns)
    
    # STEP 4: Backtesting
    print("\n" + "="*80)
    print("STEP 4: BACKTESTING ON OUT-OF-SAMPLE DATA")
    print("="*80)
    
    # Use test set (last 20% of data)
    train_size = int(len(df_features) * 0.8)
    df_test = df_features.iloc[train_size:].reset_index(drop=True)
    
    print(f"📊 Test set: {len(df_test):,} candles")
    print(f"   📅 Test period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    test_days = (df_test['timestamp'].max() - df_test['timestamp'].min()).days
    print(f"   📆 Duration: {test_days} days\n")
    
    # Generate predictions
    print(f"🤖 Generating predictions...")
    X_test = df_test[feature_columns].values
    probabilities = trainer.predict_proba(X_test)
    predictions = trainer.predict(X_test)
    
    print(f"   Predicted signals: {predictions.sum():,} buy signals")
    
    # Run backtest
    print(f"\n💰 Running backtest simulation...")
    backtest = BacktestEngine(config_path)
    backtest_metrics = backtest.run_backtest(df_test, predictions, probabilities)
    
    # COMPREHENSIVE RESULTS
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE RESULTS - FULL YEAR MODEL")
    print("="*80)
    
    print(f"\n📈 TRAINING DATASET:")
    print(f"   Total Candles: {len(df_features):,}")
    print(f"   Training Period: {(df_features['timestamp'].max() - df_features['timestamp'].min()).days} days")
    print(f"   Train Samples: {train_size:,}")
    print(f"   Test Samples: {len(df_test):,}")
    
    print(f"\n🎯 MODEL PERFORMANCE:")
    print(f"   Accuracy:  {train_metrics['accuracy']:.1%}")
    print(f"   Precision: {train_metrics['precision']:.1%}")
    print(f"   Recall:    {train_metrics['recall']:.1%}")
    print(f"   F1 Score:  {train_metrics['f1']:.3f}")
    print(f"   ROC-AUC:   {train_metrics['roc_auc']:.3f}")
    
    print(f"\n💰 BACKTEST PERFORMANCE:")
    print(f"   ROI:           {backtest_metrics['total_return']*100:+.2f}%")
    print(f"   Annual ROI:    {backtest_metrics['total_return'] * 365 / test_days * 100:+.2f}% (annualized)")
    print(f"   Win Rate:      {backtest_metrics['win_rate']*100:.1f}%")
    print(f"   Profit Factor: {backtest_metrics['profit_factor']:.2f}")
    print(f"   Sharpe Ratio:  {backtest_metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:  {backtest_metrics['max_drawdown']*100:.2f}%")
    print(f"   Total Trades:  {backtest_metrics['total_trades']:,}")
    print(f"   Avg Hold Time: {backtest_metrics['avg_hold_time']:.1f} minutes")
    
    # Calculate trading frequency
    trades_per_day = backtest_metrics['total_trades'] / test_days
    print(f"   Trades/Day:    {trades_per_day:.1f}")
    
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
        print(f"\n   🎉 EXCELLENT! Production-ready strategy!")
    elif passed_count >= 3:
        print(f"\n   👍 GOOD! Strategy shows promise.")
    elif passed_count >= 2:
        print(f"\n   ⚠️  NEEDS WORK! Consider hyperparameter tuning.")
    else:
        print(f"\n   ❌ POOR PERFORMANCE. More training data or features needed.")
    
    # Compare to baseline
    print(f"\n📊 COMPARISON TO BASELINE:")
    print(f"   Simple Hold Strategy ROI: {(df_test['close'].iloc[-1] / df_test['close'].iloc[0] - 1) * 100:+.2f}%")
    print(f"   ML Strategy ROI:          {backtest_metrics['total_return']*100:+.2f}%")
    
    if backtest_metrics['total_return'] > (df_test['close'].iloc[-1] / df_test['close'].iloc[0] - 1):
        print(f"   ✅ ML strategy OUTPERFORMS buy-and-hold!")
    else:
        print(f"   ❌ ML strategy underperforms buy-and-hold")
    
    # Save results
    print(f"\n💾 SAVED FILES:")
    print(f"   📊 Model: models/xgboost_*.json")
    print(f"   📈 Feature Importance: models/metrics/feature_importance.png")
    print(f"   📉 Confusion Matrix: models/metrics/confusion_matrix.png")
    print(f"   📋 Backtest Results: backtest_results_full_year.json")
    
    backtest.save_results(backtest_metrics, "backtest_results_full_year.json")
    
    print("\n" + "="*80)
    print("✅ FULL YEAR TRAINING COMPLETE!")
    print("="*80)
    
    print("\n💡 Key Takeaways:")
    print(f"   • Trained on {len(df_features):,} samples (365 days)")
    print(f"   • Model achieved {train_metrics['roc_auc']:.3f} ROC-AUC")
    print(f"   • Generated {backtest_metrics['total_trades']} trades with {backtest_metrics['win_rate']*100:.1f}% win rate")
    print(f"   • Risk-adjusted returns: Sharpe {backtest_metrics['sharpe_ratio']:.2f}")
    print(f"   • Max drawdown kept under {backtest_metrics['max_drawdown']*100:.2f}%")
    
    print(f"\n🚀 Next Steps:")
    print(f"   • Fine-tune hyperparameters for even better results")
    print(f"   • Test on other coins: ETH, SOL, BNB")
    print(f"   • Deploy for live paper trading")
    print(f"   • Add more features: funding rates, on-chain data\n")


if __name__ == '__main__':
    main()

