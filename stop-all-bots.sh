#!/bin/bash
#
# Stop All Trading Bots
# ======================
#
# This script stops all running trading bots.
# It does NOT close open positions - just stops the bots from trading.
#
# Usage:
#   ./stop-all-bots.sh
#

echo "=================================================="
echo "🛑 Stopping All Trading Bots"
echo "=================================================="
echo ""

# Check if screen is installed
if ! command -v screen &> /dev/null; then
    echo "❌ Error: 'screen' is not installed"
    echo "   Bots might not be running, or were started differently"
    exit 1
fi

# Get list of bot screen sessions
BOT_SESSIONS=$(screen -ls | grep "bot_" | awk '{print $1}')

if [ -z "$BOT_SESSIONS" ]; then
    echo "ℹ️  No running bots found"
    echo ""
    echo "If you have bots running but this script doesn't see them,"
    echo "they might be running in a different terminal session."
    echo ""
    echo "Try: screen -ls"
    exit 0
fi

# Count bots
BOT_COUNT=$(echo "$BOT_SESSIONS" | wc -l | tr -d ' ')
echo "Found $BOT_COUNT running bot(s)"
echo ""

# Stop each bot
echo "Stopping bots..."
for SESSION in $BOT_SESSIONS; do
    BOT_NAME=$(echo $SESSION | sed 's/\..*//')
    echo "  🛑 Stopping $BOT_NAME..."
    screen -S "$SESSION" -X quit
done

echo ""
echo "✅ All bots stopped!"
echo ""
echo "⚠️  IMPORTANT:"
echo "   • Bots are stopped but positions are saved"
echo "   • You can restart bots from the dashboard"
echo "   • Any open positions will be remembered"
echo "   • Check dashboard for position status"
echo ""
echo "=================================================="

