#!/bin/bash

echo "📊 Viewing Dashboard Logs..."
echo "   (Ctrl+A then D to detach)"
echo ""

if screen -list | grep -q "dashboard"; then
    screen -r dashboard
else
    echo "❌ Dashboard not running"
    echo "   Start it with: ./start_dashboard.sh"
fi
