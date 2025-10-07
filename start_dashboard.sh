#!/bin/bash

echo "🌐 Starting Advanced Trading Dashboard..."

# Check if already running
if screen -list | grep -q "dashboard"; then
    echo "❌ Dashboard already running!"
    echo "   To restart, run: ./stop_dashboard.sh first"
    exit 1
fi

# Start in screen session
screen -dmS dashboard python3 advanced_dashboard.py

echo "✅ Dashboard started!"
echo ""
echo "📊 Access at: http://localhost:5000"
echo ""
echo "✨ Features:"
echo "  • Manage multiple trading bots"
echo "  • Start/stop/edit bots"
echo "  • Adjust trade amounts"
echo "  • View real-time performance"
echo ""
echo "Commands:"
echo "  View logs:  screen -r dashboard"
echo "  Detach:     Ctrl+A then D"
echo "  Stop:       ./stop_dashboard.sh"
