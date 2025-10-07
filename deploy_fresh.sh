#!/bin/bash

# Fresh Deploy to Server
# Cleans everything and deploys fresh code

SERVER_IP="134.199.159.103"
SERVER_USER="root"
SERVER_PATH="/root/tradingbot"

echo "🧹 FRESH DEPLOYMENT TO SERVER"
echo "================================"
echo "Server: $SERVER_USER@$SERVER_IP"
echo ""
echo "⚠️  WARNING: This will:"
echo "   • Kill all running bots and dashboard"
echo "   • Delete /root/tradingbot folder"
echo "   • Upload fresh code"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🛑 Step 1: Killing all screens and cleaning server..."
ssh $SERVER_USER@$SERVER_IP << 'EOF'
    # Kill all screens
    killall screen 2>/dev/null
    
    # Remove old folder
    rm -rf /root/tradingbot
    
    # Create fresh directory
    mkdir -p /root/tradingbot
    
    echo "✅ Server cleaned"
EOF

echo ""
echo "📤 Step 2: Uploading fresh code..."
rsync -avz --progress \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.log' \
  --exclude 'data/' \
  --exclude '.env' \
  --exclude 'active_bots.json' \
  --exclude 'bot_pids.json' \
  /Users/rileymartin/tradingbot/ \
  $SERVER_USER@$SERVER_IP:$SERVER_PATH/

echo ""
echo "✅ Upload complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. SSH to server:"
echo "   ssh $SERVER_USER@$SERVER_IP"
echo ""
echo "2. Create .env file:"
echo "   cd $SERVER_PATH"
echo "   nano .env"
echo "   (Paste your API keys)"
echo ""
echo "3. Start dashboard:"
echo "   chmod +x *.sh"
echo "   ./start_dashboard.sh"
echo ""
echo "4. Access dashboard:"
echo "   http://$SERVER_IP:5000"
echo ""
echo "🎉 Deployment ready!"
