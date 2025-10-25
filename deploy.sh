#!/bin/bash
# Quick deploy script to Ubuntu server
SERVER="ubuntu-s-1vcpu-1gb-syd1-01"
REMOTE_PATH="/home/your-username/tradingbot"

echo "📦 Deploying updated server.py to Ubuntu server..."

# Copy the fixed files
scp app/server.py $SERVER:$REMOTE_PATH/app/
scp app/twilio_notifier.py $SERVER:$REMOTE_PATH/app/
scp app/news_service.py $SERVER:$REMOTE_PATH/app/
scp app/portfolio_manager.py $SERVER:$REMOTE_PATH/app/

echo "✅ Files copied"
echo "🔄 Now SSH in and run:"
echo "   sudo systemctl restart tradingbot"
