#!/bin/bash

# ML Strategy Optimization - Background Runner
# Tests multiple ML configurations to find the best strategy

echo "🚀 Starting ML Strategy Optimization in background..."
echo ""
echo "This will:"
echo "  • Test 63 different strategy combinations"
echo "  • Compare XGBoost vs LightGBM"
echo "  • Test different label horizons (5min to 30min)"
echo "  • Test different thresholds (0.2% to 1.5%)"
echo "  • Test different hyperparameters"
echo "  • Run for approximately 30-60 minutes"
echo ""
echo "📊 Progress will be logged to: optimization_run.log"
echo "📁 Results will be saved to: optimization_results/"
echo ""

# Create results directory
mkdir -p optimization_results

# Run in background with nohup
nohup python3 strategy_optimizer.py --symbol BTC/USDT > optimization_run.log 2>&1 &

# Get PID
PID=$!

echo "✅ Optimization started!"
echo "   Process ID: $PID"
echo ""
echo "📋 Monitor progress:"
echo "   tail -f optimization_run.log"
echo ""
echo "🔍 Check if running:"
echo "   ps aux | grep strategy_optimizer"
echo ""
echo "⏹️  Stop optimization:"
echo "   kill $PID"
echo ""
echo "📊 View results when done:"
echo "   cat optimization_results/strategy_optimization_*.json | jq"
echo ""

# Save PID to file
echo $PID > optimization_run.pid
echo "💾 PID saved to: optimization_run.pid"

