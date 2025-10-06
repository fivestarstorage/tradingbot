#!/bin/bash
#
# Quick Start Script - Run Trading Bot
#
# Usage:
#   ./start_bot.sh           # Interactive mode
#   ./start_bot.sh background # Run in background
#

echo "========================================================================"
echo "🚀 TRADING BOT LAUNCHER"
echo "========================================================================"
echo ""

# Check if running in background mode
if [ "$1" = "background" ]; then
    echo "Starting bot in background mode..."
    nohup python3 live_trader.py > bot_$(date +%Y%m%d_%H%M%S).log 2>&1 &
    PID=$!
    echo "✓ Bot started in background (PID: $PID)"
    echo "✓ Log file: bot_$(date +%Y%m%d_%H%M%S).log"
    echo ""
    echo "To monitor:"
    echo "  tail -f bot_*.log"
    echo ""
    echo "To stop:"
    echo "  kill $PID"
    echo "  # or: pkill -f live_trader.py"
    echo ""
    exit 0
fi

# Check if using screen
if command -v screen &> /dev/null; then
    echo "Screen is available!"
    echo ""
    echo "LAUNCH OPTIONS:"
    echo "1. Run in screen (recommended - bot keeps running if you disconnect)"
    echo "2. Run normally (stops if you close terminal)"
    echo "3. Run in background (no interaction)"
    echo ""
    read -p "Choose option (1-3) [1]: " option
    option=${option:-1}
    
    case $option in
        1)
            echo ""
            echo "Starting in screen session 'tradingbot'..."
            echo ""
            echo "IMPORTANT:"
            echo "  - To detach (leave bot running): Press Ctrl+A, then D"
            echo "  - To reattach later: screen -r tradingbot"
            echo "  - To stop bot: Ctrl+C in the screen session"
            echo ""
            read -p "Press Enter to continue..."
            screen -S tradingbot python3 live_trader.py
            ;;
        2)
            echo ""
            echo "Starting bot normally..."
            python3 live_trader.py
            ;;
        3)
            echo ""
            echo "Starting in background..."
            nohup python3 live_trader.py > bot_$(date +%Y%m%d_%H%M%S).log 2>&1 &
            PID=$!
            echo "✓ Bot started (PID: $PID)"
            echo "✓ To stop: kill $PID"
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
else
    echo "⚠️  Screen not installed (recommended for server use)"
    echo ""
    echo "To install screen:"
    echo "  macOS: brew install screen"
    echo "  Ubuntu: sudo apt install screen"
    echo ""
    echo "Running bot normally..."
    python3 live_trader.py
fi
