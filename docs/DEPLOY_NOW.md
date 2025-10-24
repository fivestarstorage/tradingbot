# 🚀 Deploy Now - Quick Reference

## Local Deployment (Your Mac)

### Option 1: Quick Start (Easiest)
```bash
./start_bot.sh
```
**What it does:**
- Launches bot with menu
- Runs in screen (keeps running if terminal closes)
- You can disconnect and reconnect anytime

**To check status:**
```bash
./status.sh
```

**To stop:**
```bash
./stop_bot.sh
```

---

### Option 2: Background Mode
```bash
./start_bot.sh background
```
**What it does:**
- Starts bot in background
- Creates log file
- Returns control immediately

---

### Option 3: Screen (Manual)
```bash
# Start screen session
screen -S tradingbot

# Run bot
python3 live_trader.py

# Detach (keep running)
# Press: Ctrl+A, then D

# Reattach later
screen -r tradingbot
```

---

## Cloud Deployment (24/7 Operation)

### Quick Cloud Setup (DigitalOcean)

**1. Create Server (5 minutes)**
- Go to digitalocean.com
- Create Ubuntu 22.04 droplet ($6/month)
- Note your IP address

**2. Connect & Setup (5 minutes)**
```bash
# From your Mac
ssh root@YOUR_SERVER_IP

# Setup server
apt update && apt install python3 python3-pip screen git -y
mkdir /root/tradingbot
```

**3. Upload Files (2 minutes)**
```bash
# From your Mac (in tradingbot folder)
scp -r * root@YOUR_SERVER_IP:/root/tradingbot/
```

**4. Configure & Run (3 minutes)**
```bash
# On server
cd /root/tradingbot
pip3 install -r requirements.txt

# Create .env file
nano .env
# Paste your API keys, save with Ctrl+X, Y, Enter

# Make scripts executable
chmod +x *.sh

# Start bot
./start_bot.sh
# Choose option 1 (screen)
```

**5. Disconnect (Bot Keeps Running!)**
```bash
# In the bot screen, press: Ctrl+A, then D
# Then exit SSH: exit

# Your bot is now running 24/7! ✨
```

---

## Quick Commands

### Start Bot
```bash
./start_bot.sh              # Interactive
./start_bot.sh background   # Background mode
```

### Check Status
```bash
./status.sh                 # Full status
ps aux | grep live_trader   # Quick check
```

### View Logs
```bash
tail -f live_trading_*.log  # Live logs
cat live_trading_*.log      # All logs
```

### Stop Bot
```bash
./stop_bot.sh               # Clean stop
pkill -f live_trader.py     # Force stop
```

### Monitor Dashboard
```bash
# Terminal dashboard
python3 dashboard.py

# Web dashboard
python3 web_dashboard.py
# Then open: http://localhost:5000
```

---

## Screen Commands Reference

```bash
# Create new screen
screen -S tradingbot

# Detach from screen (bot keeps running)
Ctrl+A, then D

# List all screens
screen -ls

# Reattach to screen
screen -r tradingbot

# Kill screen session
screen -X -S tradingbot quit
```

---

## Systemd Service (Advanced)

For automatic restart on crash or server reboot:

**1. Create service file:**
```bash
sudo nano /etc/systemd/system/tradingbot.service
```

**2. Paste:**
```ini
[Unit]
Description=Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/tradingbot
ExecStart=/usr/bin/python3 live_trader.py
Restart=always
RestartSec=10
StandardOutput=append:/root/tradingbot/systemd.log
StandardError=append:/root/tradingbot/systemd_error.log

[Install]
WantedBy=multi-user.target
```

**3. Enable and start:**
```bash
systemctl daemon-reload
systemctl enable tradingbot
systemctl start tradingbot
systemctl status tradingbot
```

---

## Troubleshooting

### Bot Not Starting
```bash
# Check Python
python3 --version

# Check dependencies
pip3 install -r requirements.txt

# Check .env file
cat .env

# Test connection
python3 test_connection.py
```

### Bot Stopped Running
```bash
# Check if running
./status.sh

# View recent logs
tail -50 live_trading_*.log

# Restart
./start_bot.sh
```

### Can't Connect to Server
```bash
# Test connection
ping YOUR_SERVER_IP

# Test SSH
ssh root@YOUR_SERVER_IP

# Check server status on DigitalOcean dashboard
```

---

## Complete Deployment Checklist

### Before Deploying:
- [ ] Tested on testnet locally
- [ ] Profitable backtest results
- [ ] Understand how to stop bot
- [ ] Have .env configured
- [ ] Know your strategy/settings

### Local Deployment:
- [ ] Run `./start_bot.sh`
- [ ] Choose screen option
- [ ] Configure bot settings
- [ ] Verify it's running: `./status.sh`
- [ ] Practice detaching/reattaching
- [ ] Monitor for 1+ hours

### Cloud Deployment:
- [ ] Create server account
- [ ] Deploy Ubuntu droplet
- [ ] Upload files with scp
- [ ] Configure .env on server
- [ ] Run `./start_bot.sh`
- [ ] Test disconnect/reconnect
- [ ] Monitor for 24+ hours on testnet
- [ ] Switch to mainnet (small amounts)

---

## Cost Summary

### Local (Your Mac):
- **Cost:** Free
- **Reliability:** Only when Mac is on
- **Good for:** Testing, short-term trading

### Cloud Server:
- **Cost:** $6/month (DigitalOcean)
- **Reliability:** 99.9% uptime
- **Good for:** 24/7 trading, serious operation

---

## Your First Deployment (Right Now!)

```bash
# 1. Start locally
./start_bot.sh

# 2. Choose option 1 (screen)

# 3. Configure:
#    Strategy: 1 (Simple Profitable)
#    Symbol: BTCUSDT
#    Amount: 100
#    Interval: 60

# 4. Detach: Ctrl+A, then D

# 5. Check it's running
./status.sh

# 6. Monitor
python3 dashboard.py
```

**That's it! Your bot is running! 🎉**

---

## Next Steps

1. **Run for 1 day locally**
   - Monitor performance
   - Check logs
   - Verify stability

2. **Deploy to cloud server**
   - Follow cloud setup above
   - Start with testnet
   - Monitor remotely

3. **Go live**
   - Switch to mainnet
   - Start with small amounts
   - Scale gradually

---

## Quick Help

| What | Command |
|------|---------|
| Start bot | `./start_bot.sh` |
| Stop bot | `./stop_bot.sh` |
| Check status | `./status.sh` |
| View logs | `tail -f live_trading_*.log` |
| Dashboard | `python3 dashboard.py` |
| Reconnect | `screen -r tradingbot` |

---

**Full documentation:** `DEPLOYMENT_GUIDE.md`

**Ready to deploy? Start with:** `./start_bot.sh` 🚀
