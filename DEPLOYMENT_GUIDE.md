# 🚀 Deployment Guide - Run Your Bot 24/7

## Quick Start - Run Locally

### Option 1: Run in Terminal (Simplest)
```bash
# Start the bot
python3 live_trader.py
ssh root@134.199.159.103

# Keep terminal open
# Bot runs until you close it or press Ctrl+C
```

### Option 2: Run in Background (Better)
```bash
# Start bot in background
nohup python3 live_trader.py > bot.log 2>&1 &

# Check if it's running
ps aux | grep live_trader

# View live logs
tail -f bot.log

# Stop it
pkill -f live_trader.py
```

### Option 3: Use Screen (Best for Mac/Linux)
```bash
# Start a screen session
screen -S tradingbot

# Run your bot
python3 live_trader.py

# Detach from screen (bot keeps running)
# Press: Ctrl+A, then D

# Reattach later
screen -r tradingbot

# List all screens
screen -ls

# Kill screen session
screen -X -S tradingbot quit
```

---

## Deploy to Cloud Server (24/7 Operation)

### Why Use a Cloud Server?
- ✅ Runs 24/7 (your laptop can sleep)
- ✅ Reliable internet connection
- ✅ Access from anywhere
- ✅ Professional setup

### Recommended Providers:
1. **DigitalOcean** - $6/month (easiest)
2. **AWS EC2** - Free tier available
3. **Linode** - $5/month
4. **Vultr** - $6/month

---

## Step-by-Step: Deploy to DigitalOcean

### 1. Create Droplet (5 minutes)

1. **Sign up at DigitalOcean.com**
2. **Create new Droplet:**
   - Image: Ubuntu 22.04 LTS
   - Plan: Basic $6/month (1GB RAM is enough)
   - Region: Closest to you
   - Authentication: SSH key (recommended) or password

3. **Note your IP address** (e.g., 123.45.67.89)

### 2. Connect to Server

```bash
# From your Mac
ssh root@YOUR_SERVER_IP

# Example:
# ssh root@123.45.67.89
```

### 3. Setup Server (10 minutes)

```bash
# Update system
apt update && apt upgrade -y

# Install Python
apt install python3 python3-pip git -y

# Install screen (for keeping bot running)
apt install screen -y

# Create trading directory
mkdir /root/tradingbot
cd /root/tradingbot
```

### 4. Upload Your Bot

**Option A: Using Git (if you have a repo)**
```bash
git clone YOUR_REPO_URL
cd YOUR_REPO_NAME
```

**Option B: Using SCP (from your Mac)**
```bash
# From your Mac terminal (in your tradingbot folder)
scp -r * root@YOUR_SERVER_IP:/root/tradingbot/

# This uploads all files
```

### 5. Configure Bot on Server

```bash
# On the server
cd /root/tradingbot

# Install dependencies
pip3 install -r requirements.txt
pip3 install -r requirements.txt --break-system-packages


# Create .env file
nano .env

# Paste your configuration:
# BINANCE_API_KEY=your_key
# BINANCE_API_SECRET=your_secret
# USE_TESTNET=true
# Save: Ctrl+X, Y, Enter

# Test connection
python3 test_connection.py
```

### 6. Run Bot 24/7

```bash
# Start screen session
screen -S tradingbot

# Run the bot
python3 live_trader.py

# Follow the prompts:
# - Strategy: 1
# - Symbol: BTCUSDT
# - Amount: 100
# - Interval: 60

# Detach from screen (bot keeps running)
# Press: Ctrl+A, then D

# Your bot is now running 24/7!
```

### 7. Monitor from Anywhere

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# Reattach to see bot
screen -r tradingbot

# View logs
tail -f live_trading_*.log

# Detach again: Ctrl+A, then D
```

---

## Using Systemd (Professional Setup)

For automatic restarts and system integration:

### 1. Create Service File

```bash
# On your server
sudo nano /etc/systemd/system/tradingbot.service
```

### 2. Paste This Configuration

```ini
[Unit]
Description=Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/tradingbot
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /root/tradingbot/live_trader_auto.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Create Auto-Start Script

```bash
nano /root/tradingbot/live_trader_auto.py
```

Paste:
```python
#!/usr/bin/env python3
"""Auto-start version for systemd"""
from live_trader import LiveTrader
from strategies.simple_profitable_strategy import SimpleProfitableStrategy

# Configure your bot here
trader = LiveTrader(
    strategy_class=SimpleProfitableStrategy,
    symbol='BTCUSDT',
    trade_amount_usdt=100,
    check_interval=60
)

# Run it
trader.run()
```

### 4. Enable and Start Service

```bash
# Make script executable
chmod +x /root/tradingbot/live_trader_auto.py

# Reload systemd
systemctl daemon-reload

# Enable service (starts on boot)
systemctl enable tradingbot

# Start service
systemctl start tradingbot

# Check status
systemctl status tradingbot

# View logs
journalctl -u tradingbot -f

# Stop service
systemctl stop tradingbot

# Restart service
systemctl restart tradingbot
```

---

## Web Dashboard on Server

### Setup Remote Access

```bash
# On your server
cd /root/tradingbot

# Install Flask
pip3 install flask

# Run dashboard on port 80
python3 web_dashboard.py
```

### Access from Browser

```
http://YOUR_SERVER_IP:5000
```

**To use port 80 (no :5000 needed):**
```bash
# Modify web_dashboard.py to use port 80
# Change: app.run(host='0.0.0.0', port=5000)
# To: app.run(host='0.0.0.0', port=80)

# Run with sudo (port 80 requires root)
sudo python3 web_dashboard.py
```

---

## Security Best Practices

### 1. Firewall Setup

```bash
# On server
ufw allow ssh
ufw allow 5000  # For dashboard
ufw enable

# Check status
ufw status
```

### 2. Secure Your .env File

```bash
# Set proper permissions
chmod 600 /root/tradingbot/.env

# Never commit .env to git!
```

### 3. Use SSH Keys (Not Passwords)

```bash
# On your Mac, generate SSH key
ssh-keygen -t rsa -b 4096

# Copy to server
ssh-copy-id root@YOUR_SERVER_IP

# Now you can login without password
```

### 4. Regular Backups

```bash
# Backup your .env and logs
scp root@YOUR_SERVER_IP:/root/tradingbot/.env ./backup/
scp root@YOUR_SERVER_IP:/root/tradingbot/*.log ./backup/
```

---

## Monitoring & Maintenance

### Check Bot Status

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# If using screen:
screen -r tradingbot

# If using systemd:
systemctl status tradingbot

# View logs
tail -f /root/tradingbot/live_trading_*.log
```

### Daily Checks

1. **Morning**: Check if bot is running
2. **Afternoon**: Review trades
3. **Evening**: Check profit/loss

### Weekly Maintenance

```bash
# 1. Update system
apt update && apt upgrade -y

# 2. Backup logs
scp root@YOUR_SERVER_IP:/root/tradingbot/*.log ./backups/

# 3. Clean old logs (optional)
rm /root/tradingbot/live_trading_2024*.log

# 4. Restart bot (fresh start)
systemctl restart tradingbot
```

---

## Common Issues & Solutions

### Bot Stopped Running

**If using screen:**
```bash
screen -ls  # Check if session exists
screen -r tradingbot  # Reattach
# If it crashed, start again:
python3 live_trader.py
```

**If using systemd:**
```bash
systemctl status tradingbot  # Check status
journalctl -u tradingbot -n 50  # View last 50 logs
systemctl restart tradingbot  # Restart
```

### Can't Connect to Server

```bash
# Check if server is running (from DigitalOcean dashboard)
# Try ping:
ping YOUR_SERVER_IP

# Check SSH:
ssh -v root@YOUR_SERVER_IP
```

### Out of Memory

```bash
# Check memory usage
free -h

# If low, upgrade server:
# DigitalOcean: Resize droplet to 2GB ($12/month)
```

---

## Cost Breakdown

### Cloud Hosting Options:

| Provider | Cost | RAM | What You Get |
|----------|------|-----|--------------|
| DigitalOcean | $6/mo | 1GB | Good for 1-2 bots |
| AWS EC2 | Free* | 1GB | 12 months free tier |
| Linode | $5/mo | 1GB | Good performance |
| Vultr | $6/mo | 1GB | Fast network |

*AWS free tier: 750 hours/month for 12 months

### Recommended: DigitalOcean $6/month
- Easy to use
- Good documentation
- Reliable
- 1GB RAM is enough for trading bot

---

## Full Deployment Checklist

### Local Testing:
- [ ] Backtest strategy (positive results)
- [ ] Test on testnet locally (1+ weeks)
- [ ] Verify bot works on your machine
- [ ] Document your settings

### Server Setup:
- [ ] Create cloud server account
- [ ] Deploy Ubuntu droplet
- [ ] Configure SSH access
- [ ] Install Python and dependencies
- [ ] Upload bot files
- [ ] Configure .env with API keys
- [ ] Test connection to Binance

### Bot Deployment:
- [ ] Start with testnet on server
- [ ] Run for 1+ days on testnet
- [ ] Verify logs look correct
- [ ] Test stop/start procedures
- [ ] Set up monitoring (screen or systemd)

### Going Live:
- [ ] Switch to mainnet (USE_TESTNET=false)
- [ ] Start with small amounts
- [ ] Monitor closely first 24 hours
- [ ] Set up daily check routine
- [ ] Document your process

---

## Quick Commands Reference

```bash
# ===== LOCAL =====

# Run in background
nohup python3 live_trader.py > bot.log 2>&1 &

# Stop background bot
pkill -f live_trader.py

# ===== SCREEN =====

# Start screen
screen -S tradingbot

# Detach from screen
Ctrl+A, then D

# Reattach to screen
screen -r tradingbot

# ===== SERVER =====

# Connect to server
ssh root@YOUR_SERVER_IP

# Upload files
scp -r * root@YOUR_SERVER_IP:/root/tradingbot/

# View logs
tail -f live_trading_*.log

# ===== SYSTEMD =====

# Start service
systemctl start tradingbot

# Stop service
systemctl stop tradingbot

# Restart service
systemctl restart tradingbot

# View status
systemctl status tradingbot

# View logs
journalctl -u tradingbot -f
```

---

## Next Steps

1. **Start Local First**
   ```bash
   screen -S tradingbot
   python3 live_trader.py
   Ctrl+A, D
   ```

2. **Test for 1+ Days**
   - Monitor performance
   - Check logs
   - Verify it's stable

3. **Deploy to Server**
   - Follow DigitalOcean guide above
   - Start with testnet
   - Monitor remotely

4. **Go Live**
   - Switch to mainnet
   - Start small
   - Scale gradually

---

**You're ready to deploy! Start local, test thoroughly, then move to cloud. 🚀**
