#!/bin/bash
#
# Stop Trading Bot
#

echo "========================================================================"
echo "🛑 STOP TRADING BOT"
echo "========================================================================"
echo ""

# Check if bot is running
if pgrep -f "live_trader.py" > /dev/null; then
    echo "Found running bot process(es):"
    ps aux | grep live_trader.py | grep -v grep
    echo ""
    read -p "Stop bot? (yes/no) [yes]: " confirm
    confirm=${confirm:-yes}
    
    if [ "$confirm" = "yes" ] || [ "$confirm" = "y" ]; then
        echo ""
        echo "Stopping bot..."
        pkill -f live_trader.py
        sleep 2
        
        if pgrep -f "live_trader.py" > /dev/null; then
            echo "⚠️  Bot still running, forcing stop..."
            pkill -9 -f live_trader.py
            sleep 1
        fi
        
        if ! pgrep -f "live_trader.py" > /dev/null; then
            echo "✓ Bot stopped successfully"
        else
            echo "❌ Failed to stop bot"
            exit 1
        fi
    else
        echo "Cancelled"
    fi
else
    echo "No bot running"
fi

# Check for screen sessions
if command -v screen &> /dev/null; then
    if screen -ls | grep -q tradingbot; then
        echo ""
        echo "Found screen session 'tradingbot'"
        read -p "Kill screen session? (yes/no) [no]: " kill_screen
        
        if [ "$kill_screen" = "yes" ] || [ "$kill_screen" = "y" ]; then
            screen -X -S tradingbot quit
            echo "✓ Screen session killed"
        fi
    fi
fi

echo ""
