#!/bin/bash
# Start the auto-deploy webhook server

cd /root/tradingbot

# Stop existing webhook if running
screen -S webhook -X quit 2>/dev/null

# Start webhook server in background
screen -dmS webhook python3 deploy_webhook.py

echo "✅ Auto-deploy webhook started"
echo "📡 Listening on port 5002"
echo ""
echo "To view logs:"
echo "  screen -r webhook"
echo ""
echo "To stop:"
echo "  screen -S webhook -X quit"
