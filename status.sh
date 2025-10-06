#!/bin/bash
#
# Check Trading Bot Status
#

echo "========================================================================"
echo "📊 TRADING BOT STATUS"
echo "========================================================================"
echo ""

# Check if bot is running
echo "🔍 Process Status:"
if pgrep -f "live_trader.py" > /dev/null; then
    echo "✓ Bot is RUNNING"
    echo ""
    ps aux | grep live_trader.py | grep -v grep | awk '{printf "  PID: %s | CPU: %s%% | MEM: %s%% | Running: %s\n", $2, $3, $4, $10}'
else
    echo "✗ Bot is NOT running"
fi

echo ""

# Check screen sessions
if command -v screen &> /dev/null; then
    echo "📺 Screen Sessions:"
    if screen -ls 2>/dev/null | grep -q tradingbot; then
        echo "✓ Screen session 'tradingbot' exists"
        echo "  To attach: screen -r tradingbot"
    else
        echo "✗ No screen session found"
    fi
else
    echo "📺 Screen: Not installed"
fi

echo ""

# Check logs
echo "📝 Recent Logs:"
if ls live_trading_*.log 1> /dev/null 2>&1; then
    latest_log=$(ls -t live_trading_*.log | head -1)
    echo "  Latest: $latest_log"
    
    # Show last 5 lines
    echo ""
    echo "  Last 5 entries:"
    tail -5 "$latest_log" | sed 's/^/    /'
else
    echo "  No log files found"
fi

echo ""

# Check systemd service (if applicable)
if command -v systemctl &> /dev/null; then
    if systemctl list-units --full --all | grep -q tradingbot.service; then
        echo "🔧 Systemd Service:"
        systemctl is-active tradingbot.service &> /dev/null
        if [ $? -eq 0 ]; then
            echo "✓ Service is active"
        else
            echo "✗ Service is inactive"
        fi
        echo "  Status: $(systemctl is-active tradingbot.service)"
        echo "  To view logs: journalctl -u tradingbot -f"
    fi
fi

echo ""
echo "========================================================================"
echo "Quick Commands:"
echo "  Start:   ./start_bot.sh"
echo "  Stop:    ./stop_bot.sh"
echo "  Logs:    tail -f live_trading_*.log"
echo "  Monitor: python3 dashboard.py"
echo "========================================================================"
echo ""
