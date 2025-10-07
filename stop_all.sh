#!/bin/bash
# Stop all trading bots and dashboard

echo "🛑 Stopping all screens..."

# Kill all screen sessions
pkill screen

# Wait a moment
sleep 1

# Check if any remain
REMAINING=$(screen -ls 2>&1 | grep -c "Socket")

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All screens stopped successfully!"
else
    echo "⚠️  Some screens may still be running:"
    screen -ls
    echo ""
    echo "Run: pkill -9 screen (to force kill)"
fi

echo ""
echo "To restart:"
echo "  Dashboard: screen -dmS dashboard python3 advanced_dashboard.py"
echo "  Bot: Create from dashboard or use start_bot.sh"
