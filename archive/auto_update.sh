#!/bin/bash
# Auto-update script - checks for git changes and deploys
# Run this with cron every 5 minutes

REPO_PATH="/root/tradingbot"
LOG_FILE="/root/tradingbot/auto_update.log"

cd $REPO_PATH

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

log "🔍 Checking for updates..."

# Fetch latest from GitHub
git fetch origin main 2>&1 >> $LOG_FILE

# Check if local is behind remote
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "✅ Already up to date"
    exit 0
fi

log "🚀 New commits detected! Deploying..."
log "   Local:  $LOCAL"
log "   Remote: $REMOTE"

# Pull changes
git pull origin main 2>&1 >> $LOG_FILE

if [ $? -ne 0 ]; then
    log "❌ Git pull failed!"
    exit 1
fi

# Get commit message
COMMIT_MSG=$(git log -1 --pretty=%B)
log "📝 Latest commit: $COMMIT_MSG"

# Restart dashboard (always safe)
log "🔄 Restarting dashboard..."
screen -S dashboard -X quit 2>/dev/null
screen -dmS dashboard python3 $REPO_PATH/advanced_dashboard.py
log "✅ Dashboard restarted"

# Optional: Restart bots if commit message contains [restart-bots]
if [[ "$COMMIT_MSG" == *"[restart-bots]"* ]]; then
    log "🤖 [restart-bots] detected - restarting all bots..."
    
    # Get list of running bots
    for session in $(screen -ls | grep "bot_" | awk '{print $1}'); do
        bot_name=$(echo $session | cut -d. -f2)
        log "   Restarting $bot_name..."
        screen -S $bot_name -X quit 2>/dev/null
    done
    
    log "✅ Bots stopped (will reload positions on restart)"
    log "⚠️  Manually restart bots or they'll stay stopped"
fi

log "=" * 70
log "✅ DEPLOYMENT COMPLETE"
log "=" * 70

exit 0
