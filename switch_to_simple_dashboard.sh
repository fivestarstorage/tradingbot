#!/bin/bash
# Switch to the new simplified dashboard

echo "🔄 Switching to simple dashboard..."

# Stop old dashboard
screen -X -S dashboard quit
sleep 2

# Start new simple dashboard
screen -dmS dashboard python3 simple_dash.py

echo "✅ Simple dashboard started!"
echo "   Access it at: http://localhost:5001"
echo ""
echo "📊 Features:"
echo "   • Clean, modern interface"
echo "   • Live profit chart"
echo "   • Simplified bot cards"
echo "   • Manual SMS alerts"
echo "   • Auto-refresh every 30s"

