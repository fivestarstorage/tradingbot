# 🚀 **Auto-Deploy Setup Guide**

Automatically deploy code when you push to GitHub!

---

## **Option 1: GitHub Webhook (Instant Updates) ⚡**

### **How It Works:**
```
You push to GitHub → GitHub sends webhook → Server deploys automatically
```

**Pros:**
- ✅ Instant deployment (< 5 seconds)
- ✅ Only deploys when you push
- ✅ Secure (signature verification)

**Cons:**
- ⚠️ Requires GitHub webhook setup
- ⚠️ Need to expose port 5002

---

### **Setup Steps:**

#### **1. Server Setup:**

```bash
ssh root@134.199.159.103
cd /root/tradingbot

# Pull the new code
git pull

# Add webhook secret to .env
nano .env

# Add these lines:
GITHUB_WEBHOOK_SECRET=your-super-secret-key-here
DEPLOY_KEY=another-secret-for-manual-deploys

# Save: Ctrl+X, Y, Enter

# Make script executable
chmod +x start_webhook.sh

# Start webhook server
./start_webhook.sh

# Verify it's running
screen -ls
# Should show: webhook

# Check logs
screen -r webhook
# Press Ctrl+A, then D to detach

# Test health endpoint
curl http://localhost:5002/health
```

#### **2. GitHub Setup:**

1. Go to your GitHub repo: `https://github.com/fivestarstorage/tradingbot`
2. Click **Settings** → **Webhooks** → **Add webhook**
3. Fill in:
   ```
   Payload URL: http://134.199.159.103:5002/webhook
   Content type: application/json
   Secret: your-super-secret-key-here (same as in .env)
   ```
4. Select **Just the push event**
5. Click **Add webhook**

#### **3. Test It:**

```bash
# From your local machine
cd /Users/rileymartin/tradingbot

# Make a small change
echo "# Test auto-deploy" >> README.md

# Commit and push
git add README.md
git commit -m "Test auto-deploy"
git push origin main

# Check server logs
ssh root@134.199.159.103
screen -r webhook

# You should see:
# 📨 Received push to main branch
# 📝 1 commit(s) pushed
# 🚀 STARTING AUTO-DEPLOYMENT
# ✅ DEPLOYMENT COMPLETE
```

---

### **What Gets Deployed:**

**Automatically:**
- ✅ `git pull` latest code
- ✅ Dashboard restarts (no downtime)

**NOT Automatically:**
- ❌ Bots keep running (preserves positions)
- ❌ No packages installed (you do this manually)

**To restart bots automatically**, include `[restart-bots]` in commit message:
```bash
git commit -m "Fix critical bug [restart-bots]"
```

---

## **Option 2: Cron Auto-Update (Simple) 🔄**

### **How It Works:**
```
Every 5 minutes → Check git → If new commits → Deploy
```

**Pros:**
- ✅ Super simple setup
- ✅ No webhook needed
- ✅ Works without internet-facing server

**Cons:**
- ⚠️ Up to 5-minute delay
- ⚠️ Polls GitHub constantly

---

### **Setup Steps:**

```bash
ssh root@134.199.159.103
cd /root/tradingbot

# Pull the new code
git pull

# Make script executable
chmod +x auto_update.sh

# Test it manually
./auto_update.sh

# Check log
tail -20 auto_update.log

# Should show:
# [2025-10-07 12:30:00] 🔍 Checking for updates...
# [2025-10-07 12:30:01] ✅ Already up to date

# Add to crontab (runs every 5 minutes)
crontab -e

# Add this line at the bottom:
*/5 * * * * /root/tradingbot/auto_update.sh

# Save and exit (Ctrl+X, Y, Enter)

# Verify cron is set
crontab -l
```

---

### **Test It:**

```bash
# From your local machine
cd /Users/rileymartin/tradingbot

# Make a change
echo "# Test cron deploy" >> README.md

git add README.md
git commit -m "Test cron auto-deploy"
git push origin main

# Wait up to 5 minutes, then check server
ssh root@134.199.159.103
tail -30 /root/tradingbot/auto_update.log

# Should show:
# [2025-10-07 12:35:00] 🚀 New commits detected! Deploying...
# [2025-10-07 12:35:02] ✅ DEPLOYMENT COMPLETE
```

---

## **Option 3: Manual Deploy Button 🖱️**

Want to manually trigger deployment without SSH?

### **Use the Manual Deploy Endpoint:**

```bash
# From your local machine or anywhere
curl -X POST http://134.199.159.103:5002/deploy \
  -H "Authorization: Bearer your-deploy-key-from-env"

# Response:
# {"status": "success", "message": "Deployment successful"}
```

---

## **Comparison Table:**

| Feature | GitHub Webhook | Cron Script | Manual |
|---------|----------------|-------------|--------|
| **Speed** | Instant (< 5s) | Up to 5 min | Instant |
| **Setup Complexity** | Medium | Easy | Easy |
| **GitHub Setup** | Required | Not needed | Not needed |
| **Server Port** | 5002 exposed | No ports | 5002 exposed |
| **Reliability** | High | High | Manual only |
| **Best For** | Production | Simple setups | Testing |

---

## **Recommended Setup:**

### **For Most Users: Cron Script**
```bash
chmod +x /root/tradingbot/auto_update.sh
crontab -e
# Add: */5 * * * * /root/tradingbot/auto_update.sh
```

### **For Advanced: GitHub Webhook**
```bash
# Setup webhook server
./start_webhook.sh

# Configure GitHub webhook
# Payload URL: http://YOUR_IP:5002/webhook
```

---

## **Smart Deployment Rules:**

### **Always Auto-Deploy:**
- Dashboard updates
- Configuration changes
- New features
- Bug fixes

### **Never Auto-Restart Bots:**
- Preserves active positions
- Prevents unexpected sells
- You control when bots restart

### **Manual Bot Restart When:**
- Critical bug affecting trading logic
- Strategy changes
- Position management updates

---

## **Deployment Commands:**

### **Check What Will Be Deployed:**
```bash
ssh root@134.199.159.103
cd /root/tradingbot
git fetch origin main
git log HEAD..origin/main --oneline

# Shows commits that will be deployed
```

### **Force Deploy (Skip Auto):**
```bash
cd /root/tradingbot
git pull
./start_webhook.sh  # or restart bots manually
```

### **View Deployment Logs:**
```bash
# Webhook logs
screen -r webhook

# Cron logs
tail -50 /root/tradingbot/auto_update.log

# Dashboard logs
screen -r dashboard
```

---

## **Troubleshooting:**

### **Webhook Not Triggering:**

**Check webhook status on GitHub:**
1. Go to repo → Settings → Webhooks
2. Click on your webhook
3. Scroll to "Recent Deliveries"
4. Should show successful (green checkmark)

**If failing:**
```bash
# Check if webhook server is running
ssh root@134.199.159.103
screen -ls | grep webhook

# Check logs
screen -r webhook

# Restart webhook server
screen -S webhook -X quit
./start_webhook.sh
```

### **Cron Not Running:**

```bash
# Check crontab
crontab -l

# Check if cron service is running
systemctl status cron

# Check logs
tail -100 /root/tradingbot/auto_update.log

# Test manually
cd /root/tradingbot
./auto_update.sh
```

### **Git Pull Conflicts:**

```bash
# If auto-deploy fails due to conflicts
ssh root@134.199.159.103
cd /root/tradingbot

# Check status
git status

# Reset to remote (careful - loses local changes)
git fetch origin main
git reset --hard origin/main

# Or stash local changes
git stash
git pull
```

---

## **Security Notes:**

### **Webhook Security:**
- ✅ Uses HMAC SHA-256 signature verification
- ✅ Only accepts push events from your repo
- ✅ Secret key required in `.env`

### **Best Practices:**
- 🔒 Use strong `GITHUB_WEBHOOK_SECRET`
- 🔒 Don't commit secrets to git
- 🔒 Use firewall to restrict port 5002 to GitHub IPs (optional)

### **GitHub Webhook IPs:**
```bash
# Optional: Restrict port 5002 to GitHub only
# Get GitHub IPs from: https://api.github.com/meta

# Example UFW rules:
ufw allow from 140.82.112.0/20 to any port 5002
ufw allow from 143.55.64.0/20 to any port 5002
```

---

## **Advanced: Deploy Different Branches:**

### **Deploy from dev branch:**

**Webhook method:**
```python
# Edit deploy_webhook.py
# Change line:
subprocess.run(['git', 'pull', 'origin', 'dev'])  # Instead of 'main'
```

**Cron method:**
```bash
# Edit auto_update.sh
# Change lines:
git fetch origin dev
REMOTE=$(git rev-parse origin/dev)
git pull origin dev
```

---

## **Quick Start:**

**Cron Method (Easiest):**
```bash
ssh root@134.199.159.103
cd /root/tradingbot && git pull
chmod +x auto_update.sh
crontab -e
# Add: */5 * * * * /root/tradingbot/auto_update.sh
# Done!
```

**Webhook Method (Best):**
```bash
ssh root@134.199.159.103
cd /root/tradingbot && git pull
nano .env  # Add GITHUB_WEBHOOK_SECRET
chmod +x start_webhook.sh
./start_webhook.sh
# Then setup GitHub webhook
```

---

## **Testing:**

### **Test Deployment:**
```bash
# Local
echo "# Test $(date)" >> README.md
git add README.md && git commit -m "Test auto-deploy" && git push

# Wait (5s webhook / 5min cron)

# Check server
ssh root@134.199.159.103
tail -20 /root/tradingbot/auto_update.log
# or
screen -r webhook
```

### **Test Bot Position Persistence:**
```bash
# Start bot with position
# Push code update
# Bot restarts and loads position
# Position should be maintained!
```

---

## **Summary:**

✅ **Webhook**: Instant, secure, best for production  
✅ **Cron**: Simple, reliable, no GitHub setup  
✅ **Manual**: Full control, test before deploy  

**Recommended:** Start with **Cron**, upgrade to **Webhook** when comfortable.

**Your deployment is now automated! 🎉**
