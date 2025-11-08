# 🧠 ML Crypto Trading System

A comprehensive machine learning-based cryptocurrency trading system that predicts price movements and executes trades automatically.

## 📋 Features

- **Data Ingestion**: Fetches OHLCV data from Binance via CCXT
- **Feature Engineering**: 50+ technical indicators and rolling statistics
- **ML Models**: XGBoost, LightGBM (with LSTM support planned)
- **Backtesting**: Realistic simulation with fees, slippage, and risk management
- **Performance Metrics**: Sharpe ratio, win rate, profit factor, max drawdown
- **Walk-Forward Validation**: Time-series aware train/test splits
- **Risk Management**: Stop-loss, take-profit, position sizing, drawdown limits

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ml_trading_system
pip install -r requirements.txt
```

### 2. Configure Settings

Edit `config.yaml` to customize:
- Trading symbols
- Timeframe (1m, 5m, 15m, 1h)
- Model hyperparameters
- Backtest parameters
- Risk management rules

### 3. Fetch Data

```bash
python main_pipeline.py --mode update-data
```

This will fetch 90 days of 1-minute data for all configured symbols.

### 4. Run Pipeline

#### Single Symbol
```bash
python main_pipeline.py --symbol BTC/USDT
```

#### All Symbols
```bash
python main_pipeline.py --mode multi
```

## 📊 Pipeline Steps

The pipeline executes these steps automatically:

1. **Data Ingestion** 
   - Load historical OHLCV data
   - Fetch from exchange if needed
   - Store in SQLite database

2. **Feature Engineering**
   - Calculate 50+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
   - Create rolling statistics (mean, std, z-score)
   - Detect price spikes
   - Generate forward-looking labels

3. **Model Training**
   - Train XGBoost/LightGBM classifier
   - Time-series train/test split
   - Early stopping with validation set
   - Feature importance analysis

4. **Backtesting**
   - Simulate trades on test data
   - Apply transaction fees (0.1%) and slippage (0.05%)
   - Implement stop-loss and take-profit
   - Track equity curve and drawdown

5. **Performance Analysis**
   - Calculate Sharpe ratio, win rate, profit factor
   - Generate confusion matrix and feature importance plots
   - Save detailed trade log

## 📈 Success Criteria

The system evaluates performance against these benchmarks:

| Metric | Target | Description |
|--------|--------|-------------|
| **Sharpe Ratio** | > 1.5 | Risk-adjusted returns |
| **Win Rate** | > 55% | Percentage of profitable trades |
| **Profit Factor** | > 1.3 | Gross profit / gross loss |
| **Max Drawdown** | < 15% | Largest peak-to-trough decline |
| **ROI** | > 0% | Overall return on investment |

## 🔧 Module Details

### `data_ingestion.py`
- Fetches OHLCV data from Binance
- Stores in SQLite database
- Supports incremental updates
- Handles multiple timeframes

### `feature_engineering.py`
- 50+ technical indicators using `ta` library
- Rolling window statistics (5, 15, 30, 60 periods)
- Spike detection (price z-score + volume surge)
- Forward return calculation for labeling

### `model_training.py`
- XGBoost and LightGBM classifiers
- Time-series aware splits (no future peeking)
- Hyperparameter configuration via YAML
- Model versioning and metadata tracking
- Feature importance visualization

### `backtest_engine.py`
- Realistic trade simulation
- Transaction costs and slippage
- Stop-loss and take-profit exits
- Position sizing (% of capital)
- Equity curve tracking
- Comprehensive trade logging

### `main_pipeline.py`
- Orchestrates full workflow
- Single or multi-symbol execution
- Detailed performance reporting
- Success criteria evaluation

## 📁 Output Files

After running the pipeline, you'll find:

```
ml_trading_system/
├── ml_trading_data.db           # Historical OHLCV data
├── models/
│   ├── xgboost_20251028_*.json  # Trained model
│   ├── xgboost_20251028_*_metadata.json
│   └── metrics/
│       ├── confusion_matrix.png
│       └── feature_importance.png
└── results_BTC_USDT_*.json      # Backtest results
```

## 🎯 Example Results

```
📊 BACKTEST RESULTS
================================================================================

💰 CAPITAL
   Initial: $10,000.00
   Final:   $12,450.00
   P&L:     $2,450.00 (+24.50%)

📊 TRADE STATISTICS
   Total Trades: 156
   Winning:      92 (59.0%)
   Losing:       64 (41.0%)
   Avg Hold:     45.3 periods

💵 PROFIT/LOSS
   Avg Win:       $48.50
   Avg Loss:      $31.20
   Profit Factor: 1.85
   Risk/Reward:   1.55

📉 RISK METRICS
   Max Drawdown: 8.50%
   Sharpe Ratio: 2.15

✅ SUCCESS CRITERIA
   ✅ Sharpe > 1.5
   ✅ Win Rate > 55%
   ✅ Profit Factor > 1.3
   ✅ Max Drawdown < 15%
   ✅ ROI > 0%

   🎯 Passed 5/5 criteria
```

## ⚙️ Configuration

Key settings in `config.yaml`:

### Data
```yaml
data:
  symbols: ["BTC/USDT", "ETH/USDT"]  # Trading pairs
  timeframe: "1m"                    # 1m, 5m, 15m, 1h
  history_days: 90                   # Days of data to fetch
  min_daily_volume_usd: 10000000     # Filter low-volume coins
```

### Model
```yaml
model:
  type: "xgboost"                    # xgboost, lightgbm
  label_horizon: 30                  # Predict N candles ahead
  label_threshold: 0.015             # 1.5% price increase = positive
  probability_threshold: 0.7         # Min confidence to trade
```

### Backtest
```yaml
backtest:
  transaction_fee: 0.001             # 0.1% per trade
  slippage: 0.0005                   # 0.05% slippage
  start_balance: 10000               # Starting capital
  position_size_fraction: 0.02       # 2% per trade
  stop_loss: 0.015                   # 1.5% stop loss
  take_profit: 0.03                  # 3% take profit
```

### Risk Management
```yaml
risk_management:
  daily_max_loss: 0.03               # 3% max daily loss
  max_consecutive_losses: 5
  stop_trading_on_drawdown: 0.10     # Stop at 10% drawdown
```

## 🔍 Testing Individual Modules

Each module can be tested independently:

```bash
# Test data ingestion
python data_ingestion.py

# Test feature engineering
python feature_engineering.py

# Test model training
python model_training.py

# Test backtesting
python backtest_engine.py
```

## 🚧 Future Enhancements

- [ ] LSTM/Transformer models for sequence learning
- [ ] Real-time WebSocket data streaming
- [ ] Live trading execution with exchange API
- [ ] Order book depth features
- [ ] Sentiment analysis from news/social media
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization across multiple coins
- [ ] Telegram/Slack alerts
- [ ] Web dashboard for monitoring
- [ ] Automated hyperparameter tuning
- [ ] Walk-forward optimization

## 📊 Performance Tips

1. **More Data = Better**: Use at least 60-90 days of data
2. **Liquid Pairs Only**: Stick to high-volume coins (BTC, ETH, SOL)
3. **Tune Thresholds**: Adjust `probability_threshold` based on your risk tolerance
4. **Risk Management**: Start with small position sizes (1-2%)
5. **Validate Often**: Retrain models weekly as market conditions change

## ⚠️ Disclaimer

This is an educational project. Cryptocurrency trading involves substantial risk. Never trade with money you can't afford to lose. Past performance does not guarantee future results. Always backtest thoroughly before live trading.

## 📝 License

MIT License - Use at your own risk.

---

Built with ❤️ for crypto traders who believe in data-driven decisions.

