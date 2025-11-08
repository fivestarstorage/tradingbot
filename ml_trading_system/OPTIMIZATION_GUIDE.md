# 🎯 ML Strategy Optimization Guide

This tool automatically tests **63 different ML strategies** to find the best performing configuration for your trading bot.

---

## 🚀 Quick Start

### **Start Optimization (Background)**

```bash
cd /Users/rileymartin/tradingbot/ml_trading_system
./run_optimization_background.sh
```

This will:
- ✅ Run in the background
- ✅ Test 63 strategy combinations
- ✅ Take 30-60 minutes
- ✅ Save incremental results

---

## 📊 What It Tests

### **1. Models**
- XGBoost
- LightGBM

### **2. Label Configurations** (7 variations)
| Horizon | Threshold | Description |
|---------|-----------|-------------|
| 5 min | 0.2% | Ultra-short, small moves |
| 10 min | 0.3% | Short-term, conservative |
| 10 min | 0.5% | Short-term, moderate |
| 15 min | 0.5% | Medium-term, conservative |
| 15 min | 1.0% | Medium-term, aggressive |
| 30 min | 1.0% | Long-term, moderate |
| 30 min | 1.5% | Long-term, aggressive |

### **3. Hyperparameters** (3 sets)
- **Conservative**: Depth 4, LR 0.03 (less overfitting)
- **Moderate**: Depth 6, LR 0.05 (balanced)
- **Aggressive**: Depth 8, LR 0.1 (more complex)

### **4. Probability Thresholds**
- 0.5 (50% confidence)
- 0.6 (60% confidence)
- 0.7 (70% confidence)

**Total Combinations**: 2 models × 7 labels × 3 hyperparams × 3 thresholds = **126 strategies**

(Some are skipped if they produce too few signals)

---

## 📋 Monitor Progress

### **Check Status**
```bash
python3 check_optimization_status.py
```

Shows:
- ✅ Is it running?
- 📊 How many strategies completed?
- 🏆 Top 3 strategies so far
- 📈 Average ROI, best ROI, best Sharpe

### **Live Monitoring**
```bash
tail -f optimization_run.log
```

Watch strategies being tested in real-time.

---

## ⏹️ Stop Optimization

```bash
kill $(cat optimization_run.pid)
```

Or find the process:
```bash
ps aux | grep strategy_optimizer
kill <PID>
```

---

## 📊 View Results

### **Latest Results**
```bash
ls -lt optimization_results/
cat optimization_results/strategy_optimization_*.json | jq
```

### **Best Strategy**
The tool prints a comprehensive summary when done, including:
- 🏆 Top 10 by ROI
- 📈 Top 10 by Sharpe Ratio
- 🌟 Best overall (composite score)

---

## 📈 Example Output

```
📊 OPTIMIZATION SUMMARY
================================================================================

✅ Tested 63 strategies successfully

📈 TOP 10 STRATEGIES BY ROI:
--------------------------------------------------------------------------------
 1. Strategy #42 | ROI: +2.15% | Win: 58.3% | Sharpe: 4.82 | PF: 1.65 | Trades: 87
     XGBOOST | 15min/0.5% | prob=0.6 | depth=6

 2. Strategy #28 | ROI: +1.89% | Win: 56.1% | Sharpe: 3.91 | PF: 1.52 | Trades: 104
     LIGHTGBM | 10min/0.5% | prob=0.5 | depth=6

 3. Strategy #51 | ROI: +1.67% | Win: 55.8% | Sharpe: 3.45 | PF: 1.48 | Trades: 92
     XGBOOST | 15min/1.0% | prob=0.7 | depth=4
...

🌟 BEST OVERALL STRATEGY (composite score):
   Strategy #42
   Model: XGBOOST
   Label: 15min ahead, 0.5% threshold
   Probability threshold: 0.6
   ROI: +2.15%
   Win Rate: 58.3%
   Sharpe: 4.82
   Profit Factor: 1.65
   Trades: 87
```

---

## 🎯 After Optimization

### **1. Review Results**
Check the summary output and `optimization_results/` directory.

### **2. Update Config**
Copy the best strategy parameters to `config.yaml`:

```yaml
model:
  type: "xgboost"
  label_horizon: 15
  label_threshold: 0.005
  probability_threshold: 0.6
  hyperparameters:
    max_depth: 6
    learning_rate: 0.05
    n_estimators: 100
    subsample: 0.8
    colsample_bytree: 0.8
```

### **3. Train Final Model**
```bash
python3 quick_demo.py
```

Or full pipeline:
```bash
python3 main_pipeline.py --symbol BTC/USDT
```

### **4. Deploy**
Use the best strategy for live/paper trading!

---

## ⚙️ Advanced Usage

### **Test Different Symbol**
```bash
python3 strategy_optimizer.py --symbol ETH/USDT
```

### **Force Fresh Data**
```bash
python3 strategy_optimizer.py --no-cache
```

### **Custom Strategy Grid**
Edit `strategy_optimizer.py` and modify `define_strategy_grid()` to add:
- More label configurations
- Different hyperparameters
- Additional probability thresholds

---

## 💡 Tips

1. **Let it finish**: Don't interrupt mid-optimization. Results are saved incrementally.

2. **Compare symbols**: Run for BTC, ETH, SOL separately to see which works best.

3. **Rerun periodically**: Market conditions change. Reoptimize monthly.

4. **Consider composite score**: The "best overall" uses a balanced metric (ROI + Sharpe + Win Rate).

5. **Check overfitting**: If test performance is much worse than validation, the model may be overfitting.

---

## 🔍 Troubleshooting

### **"No strategies completed"**
- Check `optimization_run.log` for errors
- Ensure you have enough training data (90+ days)
- Some label configs may produce too few positive samples

### **Optimization stuck**
- Check if process is still running: `ps aux | grep strategy_optimizer`
- Check log: `tail -f optimization_run.log`
- May be on a slow strategy (normal)

### **Out of memory**
- Reduce data size in config (60 days instead of 90)
- Close other applications
- Reduce number of strategies in grid

---

## 📁 File Structure

```
ml_trading_system/
├── strategy_optimizer.py           # Main optimization script
├── run_optimization_background.sh  # Background runner
├── check_optimization_status.py    # Status checker
├── optimization_run.log           # Live log output
├── optimization_run.pid           # Process ID
└── optimization_results/
    └── strategy_optimization_*.json  # Results with timestamps
```

---

## 🎓 Understanding Results

### **ROI (Return on Investment)**
- Total profit/loss as percentage
- **Target**: > 0% (profitable)
- **Good**: > 1%
- **Excellent**: > 2%

### **Win Rate**
- Percentage of profitable trades
- **Target**: > 50%
- **Good**: > 55%
- **Excellent**: > 60%

### **Sharpe Ratio**
- Risk-adjusted returns (higher = better)
- **Target**: > 1.5
- **Good**: > 2.0
- **Excellent**: > 3.0

### **Profit Factor**
- Gross profit / gross loss
- **Target**: > 1.0 (profitable)
- **Good**: > 1.3
- **Excellent**: > 1.5

### **Max Drawdown**
- Largest peak-to-trough decline
- **Target**: < 15%
- **Good**: < 10%
- **Excellent**: < 5%

---

**Built with ❤️ for algorithmic traders who believe in data-driven decisions.**

