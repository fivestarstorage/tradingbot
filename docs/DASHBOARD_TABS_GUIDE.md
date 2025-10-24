# 📑 **Dashboard Tabs & Git Status Guide**

## **✨ New Feature: Tabbed Navigation + Git Status!**

Your dashboard now has multiple tabs for better organization and includes a full Git status monitor!

---

## **🎯 What's New**

### **3 Tabs:**
1. **📊 Overview** - Your main trading dashboard (bots, balance, assets)
2. **📋 Logs** - Centralized log viewer for all bots
3. **⚙️ System** - Git status, server info, and update tools

---

## **📊 Overview Tab (Main Dashboard)**

### **What's Here:**
- 💰 **Account Balance** (Available, Locked, Total)
- 💎 **Your Assets** (All coins with clickable details)
- 🤖 **Trading Bots** (All bots with controls)
- 🧠 **AI Sentiment** (Analysis from news)
- 📊 **Recent Trades**

### **Use This For:**
- Monitoring your bots
- Adding/editing/starting/stopping bots
- Checking balances
- Viewing AI sentiment

---

## **📋 Logs Tab**

### **What's Here:**
- **All bot logs** in one place
- **Filters** (by bot, by type, by keyword)
- **Search** functionality
- **Auto-refresh** every 10 seconds

### **Filters Available:**
- 🟢 **Buys** - Only show buy orders
- 🔴 **Sells** - Only show sell orders
- 📊 **Signals** - Trading signals
- ❌ **Errors** - Error messages
- ⏸️ **Holds** - Hold signals
- ℹ️ **Info** - General information

### **Use This For:**
- Debugging bot behavior
- Seeing recent trades
- Finding errors
- Monitoring all bots at once

---

## **⚙️ System Tab (NEW!)**

### **What's Here:**

#### **📦 Git Repository Status**
Shows your code status:

**Current Branch**
- Which branch you're on (usually `main`)

**Status**
- ✓ **Clean** - No uncommitted changes
- ⚠️ **X change(s)** - Files modified but not committed

**Latest Commit**
- Commit hash (e.g., `12dcacc`)
- Commit message
- Author and date

**Remote Status**
- ✓ **Up to date** - Your code matches remote
- ⬇️ **X behind** - Remote has new commits (you need to update!)
- ⬆️ **X ahead** - You have commits not pushed yet
- ⚠️ **Diverged** - Both local and remote have different commits

#### **📋 Detailed Information**
Full git status with:
- Branch name
- Latest commit details
- Working tree status
- Instructions if behind

#### **🚀 Update Actions**
Buttons to:
- **⬇️ Pull Latest Changes** - Shows instructions to update
- **🔄 Restart Dashboard** - Shows restart commands
- **📜 View Update Log** - View auto-update logs

#### **🖥️ Server Information**
- **💻 Python Version** - Current Python version
- **📂 Working Directory** - Where your code is
- **⏱️ Dashboard Uptime** - How long dashboard has been running

---

## **🚀 How to Use**

### **Switching Tabs:**
1. Click any tab button at the top
2. Content instantly switches
3. Data auto-loads when needed

### **Example: Checking if Code is Up to Date**
```
1. Click "⚙️ System" tab
2. Look at "🔄 Remote Status" card
3. See one of:
   ✓ Up to date → You're good!
   ⬇️ 2 behind → You need to update!
```

### **Example: Updating Your Code**
```
1. Go to System tab
2. See "⬇️ 2 behind" in Remote Status
3. SSH to server: ssh root@134.199.159.103
4. Run: cd /root/tradingbot && git pull origin main
5. Restart dashboard if needed
6. Refresh System tab → Should show "✓ Up to date"
```

### **Example: Viewing Bot Logs**
```
1. Click "📋 Logs" tab
2. Select bot from dropdown (or "All Bots")
3. Select type (or "All Types")
4. See filtered logs
5. Use search box to find specific text
```

---

## **📊 Git Status Explained**

### **Remote Status Meanings:**

#### **✓ Up to date**
```
Your code = Remote code
Action: Nothing! You're current.
```

#### **⬇️ X behind**
```
Remote has new commits you don't have
Action: Pull updates!

Commands:
  ssh root@134.199.159.103
  cd /root/tradingbot
  git pull origin main
  screen -S dashboard -X quit
  screen -dmS dashboard python3 advanced_dashboard.py
```

#### **⬆️ X ahead**
```
You have commits not on remote
Action: Usually nothing (you're developing)
Or: git push origin main (if intentional)
```

#### **⚠️ Diverged**
```
Both you and remote have different commits
Action: Usually:
  git pull origin main
  Resolve any conflicts
```

### **Working Tree Status:**

#### **✓ Clean**
```
No modified files
Everything committed
Safe to pull updates
```

#### **⚠️ X change(s)**
```
Files modified but not committed
Action: Usually okay for config files
If problems: git stash, then git pull
```

---

## **💡 Common Workflows**

### **Workflow 1: Daily Check-In**
```
1. Open dashboard → System tab
2. Check "Remote Status"
3. If behind:
   a. SSH to server
   b. Pull updates
   c. Restart dashboard
4. Check "Latest Commit" to see what's new
```

### **Workflow 2: Troubleshooting Bot**
```
1. Overview tab → See bot is having issues
2. Logs tab → Filter by that bot ID
3. Search for "error"
4. Find issue in logs
5. System tab → Check if code is up to date
6. If behind → Update code → Restart bot
```

### **Workflow 3: After Making Changes Locally**
```
1. Make changes on local machine
2. Commit: git commit -m "Your changes"
3. Push: git push origin main
4. Go to server dashboard → System tab
5. See "⬇️ 1 behind"
6. Pull updates on server
7. Restart affected components
```

---

## **🎨 What the System Tab Looks Like**

### **Git Status Cards:**
```
┌────────────────────┐ ┌────────────────────┐
│ 🌿 Current Branch  │ │ 📊 Status          │
│ main               │ │ ✓ Clean            │
└────────────────────┘ └────────────────────┘

┌────────────────────┐ ┌────────────────────┐
│ 📝 Latest Commit   │ │ 🔄 Remote Status   │
│ 12dcacc            │ │ ✓ Up to date       │
│ ADD: Tab nav...    │ │                    │
│ by you • 2 mins ago│ │                    │
└────────────────────┘ └────────────────────┘
```

### **Detailed Information:**
```
┌──────────────────────────────────────┐
│ 📋 Detailed Information              │
├──────────────────────────────────────┤
│ ✓ Git repository found               │
│ Branch: main                         │
│ Latest Commit: 12dcacc - ADD: Tab... │
│ Author: Your Name                    │
│ Date: 2 minutes ago                  │
│ Working Tree: Clean ✓                │
│                                      │
│ ✓ Your code is up to date!           │
└──────────────────────────────────────┘
```

### **Update Actions:**
```
┌──────────────────────────────────────┐
│ 🚀 Update Actions                    │
├──────────────────────────────────────┤
│ [⬇️ Pull Latest Changes]             │
│ [🔄 Restart Dashboard]               │
│ [📜 View Update Log]                 │
│                                      │
│ Status: (shows after clicking)       │
└──────────────────────────────────────┘
```

### **Server Info:**
```
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ 💻 Python     │ │ 📂 Working    │ │ ⏱️ Uptime     │
│ 3.13.0        │ │ /root/        │ │ 0h 15m 42s    │
│               │ │ tradingbot    │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## **🔧 Update Your Server to Get This Feature**

```bash
# SSH to server
ssh root@134.199.159.103

# Pull updates
cd /root/tradingbot
git pull origin main

# Restart dashboard
screen -S dashboard -X quit
screen -dmS dashboard python3 advanced_dashboard.py

# Open dashboard
# Go to: http://134.199.159.103:5000
# See new tabs at the top!
```

**Or wait for auto-deploy** (if you set it up) - it'll deploy in max 5 minutes!

---

## **🎯 Benefits**

### **Better Organization**
- Main dashboard less cluttered
- Logs in dedicated space
- System info separate

### **Easy Updates**
- See at a glance if code is current
- Know exactly how many commits behind
- Quick access to update instructions

### **Faster Troubleshooting**
- Logs tab for debugging
- System tab to check if code is up to date
- All info in one place

### **Monitor Uptime**
- See how long dashboard has been running
- Python version check
- Working directory confirmation

---

## **⚙️ Technical Details**

### **API Endpoints:**
```
/api/overview    - Main dashboard data
/api/logs        - Bot logs with filtering
/api/git/status  - Git repository status
/api/sentiment   - AI sentiment data
```

### **Git Commands Used:**
```bash
git rev-parse --abbrev-ref HEAD          # Get branch
git rev-parse --short HEAD               # Get commit hash
git log -1 --pretty=%B                   # Get commit message
git status --porcelain                   # Get working tree changes
git fetch                                # Update remote info
git rev-list --count HEAD..@{u}          # Commits behind
git rev-list --count @{u}..HEAD          # Commits ahead
```

### **Auto-Refresh:**
```javascript
updateDashboard()   every 5 seconds
refreshLogs()       every 10 seconds
refreshSentiment()  every 30 seconds
updateServerInfo()  every 1 second (for uptime)
```

---

## **🐛 Troubleshooting**

### **Issue: System tab shows "Error"**
**Cause:** Git not installed or not a git repository

**Solution:**
```bash
# Check if git is installed
git --version

# Check if in a git repository
cd /root/tradingbot
git status

# If not a repo, clone it:
cd /root
git clone <your-repo-url> tradingbot
```

### **Issue: Remote status shows "Unknown"**
**Cause:** Can't connect to remote or no upstream set

**Solution:**
```bash
# Set upstream if needed
git branch --set-upstream-to=origin/main main

# Check remote
git remote -v
```

### **Issue: Shows "behind" but git pull doesn't work**
**Cause:** Uncommitted changes or conflicts

**Solution:**
```bash
# Stash changes
git stash

# Pull updates
git pull origin main

# Apply stash if needed
git stash pop
```

### **Issue: Tabs not switching**
**Cause:** JavaScript error or browser cache

**Solution:**
1. Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
2. Check browser console (F12) for errors
3. Restart dashboard

---

## **💡 Pro Tips**

### **1. Check Before Updates**
Before manually updating bots:
```
1. System tab → Check if code is behind
2. If behind → Pull first, then update bots
3. If up to date → Safe to proceed
```

### **2. Use Logs for Debugging**
When bot isn't trading:
```
1. Logs tab → Filter by bot ID
2. Search for "error" or "insufficient"
3. See exact issue
4. Fix and restart
```

### **3. Monitor Auto-Deploy**
If using auto-deploy:
```
1. System tab → Check Remote Status periodically
2. Should stay "up to date" automatically
3. If suddenly "behind" → Auto-deploy may not be working
```

### **4. Bookmark Tabs**
```
Overview: http://134.199.159.103:5000
Logs:     (click Logs tab)
System:   (click System tab)

Can't bookmark tabs directly, but fast to switch!
```

---

## **❓ FAQ**

**Q: Will tabs remember my position if I refresh?**
A: No, always starts on Overview tab. Just click to switch.

**Q: Can I have multiple tabs open at once?**
A: No, it's a tab system - one visible at a time. But switching is instant!

**Q: Does the git status update automatically?**
A: Only when you click "Refresh" or switch to System tab. Not continuous (to avoid spamming git commands).

**Q: What if I'm on a different branch?**
A: System tab will show your current branch name. Most users should be on `main`.

**Q: Can I pull updates directly from the dashboard?**
A: Not yet - shows instructions for manual pull. Future version may add one-click pull.

**Q: Why does uptime reset?**
A: Uptime shows how long the dashboard process has been running. Resets when you restart dashboard (not when bots restart).

**Q: Can I see git history in the dashboard?**
A: Not yet - only shows latest commit. Use `git log` on server for full history.

---

## **🎯 Summary**

### **What You Get:**
- ✅ 3 tabs (Overview, Logs, System)
- ✅ Git status monitoring
- ✅ Remote comparison (up to date / behind / ahead)
- ✅ Server info (Python version, working dir, uptime)
- ✅ Update action buttons
- ✅ Better organization

### **Main Use Cases:**
1. **Check if code is current** (System tab)
2. **Debug bot issues** (Logs tab)
3. **Monitor everything** (Overview tab)
4. **Update when behind** (System tab shows status)

### **Update Now:**
```bash
ssh root@134.199.159.103
cd /root/tradingbot
git pull origin main
screen -S dashboard -X quit
screen -dmS dashboard python3 advanced_dashboard.py
```

**Then enjoy your new tabbed dashboard! 🚀📊⚙️**
