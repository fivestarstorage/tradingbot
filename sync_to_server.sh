#!/bin/bash

# Sync Trading Bot to Server
# Updates only changed files, preserves .env

SERVER_IP="134.199.159.103"
SERVER_USER="root"
SERVER_PATH="/root/tradingbot/"
LOCAL_PATH="/Users/rileymartin/tradingbot/"

echo "🔄 Syncing trading bot to server..."
echo "   Server: $SERVER_USER@$SERVER_IP"
echo ""

# Ask for confirmation
read -p "Continue? (y/n) [y]: " confirm
confirm=${confirm:-y}

if [ "$confirm" != "y" ]; then
    echo "❌ Cancelled"
    exit 0
fi

# Sync files
rsync -avz --progress \
  --exclude '.env' \
  --exclude '*.log' \
  --exclude '__pycache__' \
  --exclude 'data/' \
  --exclude '.git/' \
  --exclude 'active_bots.json' \
  --exclude 'bot_pids.json' \
  $LOCAL_PATH \
  $SERVER_USER@$SERVER_IP:$SERVER_PATH

echo ""
echo "✅ Sync complete!"
echo ""
echo "Next steps on server:"
echo "  ssh $SERVER_USER@$SERVER_IP"
echo "  cd $SERVER_PATH"
echo "  chmod +x *.sh"
echo "  ./start_dashboard.sh"
