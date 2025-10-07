"""
Advanced Trading Management Dashboard

Full-featured dashboard to manage multiple trading bots:
- View all bots and their performance
- Start/stop/edit bots
- Adjust trade amounts
- View balance and withdraw
- Add new strategies
"""
from flask import Flask, render_template, jsonify, request
import json
import os
import signal
import subprocess
from datetime import datetime
from binance_client import BinanceClient
from config import Config

app = Flask(__name__)

class BotManager:
    def __init__(self):
        self.bots_file = 'active_bots.json'
        self.pids_file = 'bot_pids.json'
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
    
    def get_bots(self):
        """Load all active bots from file"""
        if not os.path.exists(self.bots_file):
            return []
        
        try:
            with open(self.bots_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def save_bots(self, bots):
        """Save bots to file"""
        with open(self.bots_file, 'w') as f:
            json.dump(bots, f, indent=2)
    
    def add_bot(self, name, symbol, strategy, trade_amount):
        """Add a new bot"""
        bots = self.get_bots()
        
        new_bot = {
            'id': len(bots) + 1,
            'name': name,
            'symbol': symbol,
            'strategy': strategy,
            'trade_amount': trade_amount,
            'status': 'stopped',
            'created': datetime.now().isoformat(),
            'trades': 0,
            'profit': 0.0
        }
        
        bots.append(new_bot)
        self.save_bots(bots)
        return new_bot
    
    def update_bot(self, bot_id, updates):
        """Update bot settings"""
        bots = self.get_bots()
        
        for bot in bots:
            if bot['id'] == bot_id:
                bot.update(updates)
                break
        
        self.save_bots(bots)
    
    def delete_bot(self, bot_id):
        """Delete a bot"""
        bots = self.get_bots()
        bots = [b for b in bots if b['id'] != bot_id]
        self.save_bots(bots)
    
    def get_account_info(self):
        """Get current account balance - shows ALL assets"""
        try:
            # Get all balances
            account = self.client.client.get_account()
            
            total_value_usdt = 0.0
            total_locked_usdt = 0.0
            balances_list = []
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                
                if free > 0 or locked > 0:
                    asset = balance['asset']
                    
                    # Convert to USDT value
                    if asset == 'USDT':
                        value_usdt = free + locked
                        free_usdt = free
                        locked_usdt = locked
                    else:
                        # Get current price in USDT
                        try:
                            symbol = f"{asset}USDT"
                            price = self.client.get_current_price(symbol)
                            if price:
                                value_usdt = (free + locked) * price
                                free_usdt = free * price
                                locked_usdt = locked * price
                            else:
                                continue
                        except:
                            continue
                    
                    total_value_usdt += value_usdt
                    total_locked_usdt += locked_usdt
                    
                    balances_list.append({
                        'asset': asset,
                        'free': free,
                        'locked': locked,
                        'value_usdt': value_usdt
                    })
            
            # Sort by value (highest first)
            balances_list.sort(key=lambda x: x['value_usdt'], reverse=True)
            
            return {
                'available': total_value_usdt - total_locked_usdt,
                'locked': total_locked_usdt,
                'total': total_value_usdt,
                'mode': 'TESTNET' if Config.USE_TESTNET else 'MAINNET',
                'balances': balances_list[:10]  # Top 10 assets
            }
        
        except Exception as e:
            print(f"Error getting account info: {e}")
            return {
                'available': 0,
                'locked': 0,
                'total': 0,
                'mode': 'TESTNET' if Config.USE_TESTNET else 'MAINNET',
                'balances': [],
                'error': str(e)
            }
    
    def get_recent_trades(self, limit=20):
        """Get recent trades from log files"""
        today = datetime.now().strftime("%Y%m%d")
        log_file = f'live_trading_{today}.log'
        
        trades = []
        
        if not os.path.exists(log_file):
            return trades
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if 'CLOSED POSITION' in line or 'OPENED POSITION' in line:
                    trades.append({
                        'time': line.split(' ')[0] + ' ' + line.split(' ')[1],
                        'info': line.split(':', 2)[2].strip() if ':' in line else line
                    })
        except:
            pass
        
        return trades[-limit:]
    
    def get_pids(self):
        """Load bot PIDs from file"""
        if not os.path.exists(self.pids_file):
            return {}
        
        try:
            with open(self.pids_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_pids(self, pids):
        """Save bot PIDs to file"""
        with open(self.pids_file, 'w') as f:
            json.dump(pids, f, indent=2)
    
    def start_bot(self, bot_id):
        """Actually start a bot trading process"""
        bots = self.get_bots()
        bot = None
        
        for b in bots:
            if b['id'] == bot_id:
                bot = b
                break
        
        if not bot:
            return False, "Bot not found"
        
        if bot['status'] == 'running':
            return False, "Bot is already running"
        
        try:
            # Start the bot process in background using screen
            cmd = f"screen -dmS bot_{bot_id} python3 integrated_trader.py {bot_id} '{bot['name']}' {bot['symbol']} {bot['strategy']} {bot['trade_amount']}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Update bot status
                self.update_bot(bot_id, {'status': 'running'})
                return True, f"✅ Bot '{bot['name']}' started successfully!"
            else:
                return False, f"Failed to start bot: {result.stderr}"
        
        except Exception as e:
            return False, f"Error starting bot: {str(e)}"
    
    def stop_bot(self, bot_id):
        """Stop a bot trading process"""
        bots = self.get_bots()
        bot = None
        
        for b in bots:
            if b['id'] == bot_id:
                bot = b
                break
        
        if not bot:
            return False, "Bot not found"
        
        if bot['status'] == 'stopped':
            return False, "Bot is already stopped"
        
        try:
            # Kill the screen session
            cmd = f"screen -X -S bot_{bot_id} quit"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Update bot status
            self.update_bot(bot_id, {'status': 'stopped'})
            
            return True, f"🛑 Bot '{bot['name']}' stopped successfully!"
        
        except Exception as e:
            return False, f"Error stopping bot: {str(e)}"

manager = BotManager()

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('advanced_dashboard.html')

@app.route('/api/overview')
def overview():
    """Get account overview"""
    try:
        account = manager.get_account_info()
        bots = manager.get_bots()
        trades = manager.get_recent_trades(20)
        
        # Calculate total allocated
        total_allocated = sum(bot['trade_amount'] for bot in bots if bot['status'] == 'running')
        
        return jsonify({
            'success': True,
            'account': account,
            'bots': bots,
            'trades': trades,
            'total_allocated': total_allocated,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/add', methods=['POST'])
def add_bot():
    """Add a new bot"""
    try:
        data = request.json
        bot = manager.add_bot(
            name=data['name'],
            symbol=data['symbol'],
            strategy=data['strategy'],
            trade_amount=float(data['trade_amount'])
        )
        return jsonify({'success': True, 'bot': bot})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/<int:bot_id>/update', methods=['POST'])
def update_bot(bot_id):
    """Update bot settings"""
    try:
        data = request.json
        manager.update_bot(bot_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/<int:bot_id>/delete', methods=['POST'])
def delete_bot(bot_id):
    """Delete a bot"""
    try:
        manager.delete_bot(bot_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/<int:bot_id>/start', methods=['POST'])
def start_bot(bot_id):
    """Start a bot - actually spawns the trading process"""
    try:
        success, message = manager.start_bot(bot_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/<int:bot_id>/stop', methods=['POST'])
def stop_bot(bot_id):
    """Stop a bot - kills the trading process"""
    try:
        success, message = manager.stop_bot(bot_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== HTML TEMPLATE ====================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Management Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #fff;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 1.8em;
        }
        
        .mode-badge {
            padding: 8px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }
        
        .account-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: #16161f;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a2a3e;
        }
        
        .summary-card h3 {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .summary-card .value {
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .section {
            background: #16161f;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #2a2a3e;
            margin-bottom: 30px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section h2 {
            font-size: 1.3em;
        }
        
        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.85em;
        }
        
        .btn-success {
            background: #4caf50;
        }
        
        .btn-success:hover {
            background: #45a049;
        }
        
        .btn-danger {
            background: #f44336;
        }
        
        .btn-danger:hover {
            background: #da190b;
        }
        
        .btn-secondary {
            background: #555;
        }
        
        .btn-secondary:hover {
            background: #666;
        }
        
        .bots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .bot-card {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #2a2a3e;
        }
        
        .bot-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        
        .bot-title {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .bot-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .bot-status.running {
            background: #4caf5033;
            color: #4caf50;
        }
        
        .bot-status.stopped {
            background: #f4433633;
            color: #f44336;
        }
        
        .bot-info {
            margin-bottom: 15px;
        }
        
        .bot-info div {
            margin: 5px 0;
            font-size: 0.9em;
            color: #aaa;
        }
        
        .bot-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .bot-stat {
            text-align: center;
            padding: 10px;
            background: #0f0f1e;
            border-radius: 5px;
        }
        
        .bot-stat .label {
            font-size: 0.75em;
            color: #888;
            margin-bottom: 5px;
        }
        
        .bot-stat .value {
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .bot-controls {
            display: flex;
            gap: 10px;
        }
        
        .bot-controls button {
            flex: 1;
        }
        
        .trades-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .trade-item {
            background: #1a1a2e;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 5px;
            border-left: 3px solid #667eea;
            font-size: 0.9em;
        }
        
        .trade-time {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: #16161f;
            padding: 30px;
            border-radius: 10px;
            max-width: 500px;
            width: 90%;
            border: 1px solid #2a2a3e;
        }
        
        .modal h2 {
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
            font-size: 0.9em;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 10px;
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 5px;
            color: white;
            font-size: 1em;
        }
        
        .form-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .form-actions button {
            flex: 1;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Trading Management Dashboard</h1>
        <div class="mode-badge" id="mode">Loading...</div>
    </div>
    
    <div class="container">
        <!-- Account Summary -->
        <div class="account-summary">
            <div class="summary-card">
                <h3>💰 Available Balance</h3>
                <div class="value" id="available">Loading...</div>
            </div>
            
            <div class="summary-card">
                <h3>🔒 In Orders</h3>
                <div class="value" id="locked">Loading...</div>
            </div>
            
            <div class="summary-card">
                <h3>💵 Total Balance</h3>
                <div class="value" id="total">Loading...</div>
            </div>
            
            <div class="summary-card">
                <h3>🤖 Allocated to Bots</h3>
                <div class="value" id="allocated">$0.00</div>
            </div>
        </div>
        
        <!-- Asset Breakdown -->
        <div class="section">
            <div class="section-header">
                <h2>💎 Your Assets</h2>
            </div>
            <div id="assets-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
                <div class="empty-state">Loading assets...</div>
            </div>
        </div>
        
        <!-- Bots Section -->
        <div class="section">
            <div class="section-header">
                <h2>🤖 Trading Bots</h2>
                <button class="btn" onclick="showAddBotModal()">➕ Add New Bot</button>
            </div>
            
            <div class="bots-grid" id="bots-grid">
                <div class="empty-state">No bots yet. Add your first bot!</div>
            </div>
        </div>
        
        <!-- Recent Trades -->
        <div class="section">
            <div class="section-header">
                <h2>📊 Recent Trades</h2>
            </div>
            
            <div class="trades-list" id="trades-list">
                <div class="empty-state">No trades yet...</div>
            </div>
        </div>
    </div>
    
    <!-- Add Bot Modal -->
    <div class="modal" id="add-bot-modal">
        <div class="modal-content">
            <h2>➕ Add New Trading Bot</h2>
            
            <div class="form-group">
                <label>Bot Name</label>
                <input type="text" id="bot-name" placeholder="e.g. BTC Momentum Bot">
            </div>
            
            <div class="form-group">
                <label>Strategy</label>
                <select id="bot-strategy" onchange="updateSymbolHelp()">
                    <option value="simple_profitable">Simple Profitable (Recommended)</option>
                    <option value="ai_autonomous">🤖 AI Autonomous (AI Picks Coin!)</option>
                    <option value="ai_news">🤖 AI News Trading (Single Coin)</option>
                    <option value="momentum">Momentum</option>
                    <option value="mean_reversion">Mean Reversion</option>
                    <option value="breakout">Breakout</option>
                    <option value="conservative">Conservative</option>
                    <option value="volatile">Volatile Coins</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Trading Symbol <span id="symbol-help" style="color: #888; font-size: 0.85em;"></span></label>
                <input type="text" id="bot-symbol" placeholder="e.g. BTCUSDT" value="BTCUSDT">
            </div>
            
            <div class="form-group">
                <label>Trade Amount (USDT) <span style="color: #888; font-size: 0.85em;">- Money to spend per trade</span></label>
                <input type="number" id="bot-amount" placeholder="100" value="100">
                <div style="color: #888; font-size: 0.8em; margin-top: 5px;">
                    Example: $100 = Bot spends $100 each time it buys crypto
                </div>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideAddBotModal()">Cancel</button>
                <button class="btn" onclick="addBot()">Create Bot</button>
            </div>
        </div>
    </div>
    
    <!-- Edit Bot Modal -->
    <div class="modal" id="edit-bot-modal">
        <div class="modal-content">
            <h2>✏️ Edit Bot Settings</h2>
            
            <input type="hidden" id="edit-bot-id">
            
            <div class="form-group">
                <label>Bot Name</label>
                <input type="text" id="edit-bot-name">
            </div>
            
            <div class="form-group">
                <label>Trade Amount (USDT)</label>
                <input type="number" id="edit-bot-amount">
            </div>
            
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideEditBotModal()">Cancel</button>
                <button class="btn" onclick="saveBot()">Save Changes</button>
            </div>
        </div>
    </div>
    
    <script>
        let currentData = {};
        
        // Update dashboard
        function updateDashboard() {
            fetch('/api/overview')
                .then(response => response.json())
                .then(result => {
                    if (!result.success) {
                        console.error('Error:', result.error);
                        document.getElementById('available').textContent = 'Error';
                        document.getElementById('locked').textContent = 'Error';
                        document.getElementById('total').textContent = 'Error';
                        document.getElementById('mode').textContent = 'ERROR';
                        return;
                    }
                    
                    currentData = result;
                    
                    // Update account info
                    document.getElementById('available').textContent = '$' + result.account.available.toFixed(2);
                    document.getElementById('locked').textContent = '$' + result.account.locked.toFixed(2);
                    document.getElementById('total').textContent = '$' + result.account.total.toFixed(2);
                    document.getElementById('allocated').textContent = '$' + result.total_allocated.toFixed(2);
                    document.getElementById('mode').textContent = result.account.mode;
                    
                    // Show error if present
                    if (result.account.error) {
                        console.error('Account error:', result.account.error);
                        alert('API Error: ' + result.account.error + '\\n\\nCheck your .env file and API keys!');
                    }
                    
                    // Update assets
                    renderAssets(result.account.balances || []);
                    
                    // Update bots
                    renderBots(result.bots);
                    
                    // Update trades
                    renderTrades(result.trades);
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    document.getElementById('available').textContent = 'Connection Error';
                    document.getElementById('locked').textContent = 'Connection Error';
                    document.getElementById('total').textContent = 'Connection Error';
                });
        }
        
        // Render assets
        function renderAssets(balances) {
            const list = document.getElementById('assets-list');
            
            if (balances.length === 0) {
                list.innerHTML = '<div class="empty-state">No assets found. Check API connection.</div>';
                return;
            }
            
            list.innerHTML = balances.map(bal => `
                <div class="summary-card">
                    <h3>${bal.asset}</h3>
                    <div class="value" style="font-size: 1.3em;">${bal.free.toFixed(8)}</div>
                    <div style="color: #888; font-size: 0.9em; margin-top: 5px;">
                        ≈ $${bal.value_usdt.toFixed(2)}
                    </div>
                </div>
            `).join('');
        }
        
        // Render bots
        function renderBots(bots) {
            const grid = document.getElementById('bots-grid');
            
            if (bots.length === 0) {
                grid.innerHTML = '<div class="empty-state">No bots yet. Add your first bot!</div>';
                return;
            }
            
            grid.innerHTML = bots.map(bot => `
                <div class="bot-card">
                    <div class="bot-header">
                        <div class="bot-title">${bot.name}</div>
                        <div class="bot-status ${bot.status}">${bot.status.toUpperCase()}</div>
                    </div>
                    
                    <div class="bot-info">
                        <div>📈 ${bot.symbol}</div>
                        <div>🎯 ${bot.strategy.replace('_', ' ').toUpperCase()}</div>
                        <div>💵 $${bot.trade_amount} per trade</div>
                    </div>
                    
                    <div class="bot-stats">
                        <div class="bot-stat">
                            <div class="label">TRADES</div>
                            <div class="value">${bot.trades}</div>
                        </div>
                        <div class="bot-stat">
                            <div class="label">PROFIT</div>
                            <div class="value" style="color: ${bot.profit >= 0 ? '#4caf50' : '#f44336'}">
                                ${bot.profit >= 0 ? '+' : ''}$${bot.profit.toFixed(2)}
                            </div>
                        </div>
                    </div>
                    
                    <div class="bot-controls">
                        ${bot.status === 'stopped' 
                            ? `<button class="btn btn-sm btn-success" onclick="startBot(${bot.id})">▶ Start</button>`
                            : `<button class="btn btn-sm btn-danger" onclick="stopBot(${bot.id})">⏹ Stop</button>`
                        }
                        <button class="btn btn-sm btn-secondary" onclick="editBot(${bot.id})">✏️ Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteBot(${bot.id})">🗑️</button>
                    </div>
                </div>
            `).join('');
        }
        
        // Render trades
        function renderTrades(trades) {
            const list = document.getElementById('trades-list');
            
            if (trades.length === 0) {
                list.innerHTML = '<div class="empty-state">No trades yet...</div>';
                return;
            }
            
            list.innerHTML = trades.map(trade => `
                <div class="trade-item">
                    <div class="trade-time">${trade.time}</div>
                    <div>${trade.info}</div>
                </div>
            `).reverse().join('');
        }
        
        // Update symbol help text based on strategy
        function updateSymbolHelp() {
            const strategy = document.getElementById('bot-strategy').value;
            const helpText = document.getElementById('symbol-help');
            
            if (strategy === 'ai_autonomous') {
                helpText.textContent = '(ignored - AI picks the coin!)';
                helpText.style.color = '#f39c12';
            } else if (strategy === 'ai_news') {
                helpText.textContent = '(which coin to monitor)';
                helpText.style.color = '#888';
            } else {
                helpText.textContent = '';
            }
        }
        
        // Show/hide modals
        function showAddBotModal() {
            document.getElementById('add-bot-modal').style.display = 'flex';
            updateSymbolHelp(); // Initialize help text
        }
        
        function hideAddBotModal() {
            document.getElementById('add-bot-modal').style.display = 'none';
        }
        
        function hideEditBotModal() {
            document.getElementById('edit-bot-modal').style.display = 'none';
        }
        
        // Add bot
        function addBot() {
            const data = {
                name: document.getElementById('bot-name').value,
                symbol: document.getElementById('bot-symbol').value.toUpperCase(),
                strategy: document.getElementById('bot-strategy').value,
                trade_amount: parseFloat(document.getElementById('bot-amount').value)
            };
            
            if (!data.name || !data.symbol || !data.trade_amount) {
                alert('Please fill all fields');
                return;
            }
            
            fetch('/api/bot/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    hideAddBotModal();
                    updateDashboard();
                    
                    // Clear form
                    document.getElementById('bot-name').value = '';
                    document.getElementById('bot-symbol').value = 'BTCUSDT';
                    document.getElementById('bot-amount').value = '100';
                } else {
                    alert('Error: ' + result.error);
                }
            });
        }
        
        // Edit bot
        function editBot(botId) {
            const bot = currentData.bots.find(b => b.id === botId);
            if (!bot) return;
            
            document.getElementById('edit-bot-id').value = botId;
            document.getElementById('edit-bot-name').value = bot.name;
            document.getElementById('edit-bot-amount').value = bot.trade_amount;
            
            document.getElementById('edit-bot-modal').style.display = 'flex';
        }
        
        function saveBot() {
            const botId = parseInt(document.getElementById('edit-bot-id').value);
            const data = {
                name: document.getElementById('edit-bot-name').value,
                trade_amount: parseFloat(document.getElementById('edit-bot-amount').value)
            };
            
            fetch(`/api/bot/${botId}/update`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    hideEditBotModal();
                    updateDashboard();
                } else {
                    alert('Error: ' + result.error);
                }
            });
        }
        
        // Start/Stop bot
        function startBot(botId) {
            if (!confirm('Start this bot?\\n\\nThis will begin LIVE TRADING with real orders!')) return;
            
            fetch(`/api/bot/${botId}/start`, {method: 'POST'})
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        updateDashboard();
                        alert(result.message + '\\n\\nBot is now trading live! Check logs with:\\nscreen -r bot_' + botId);
                    } else {
                        alert('Error: ' + (result.error || result.message));
                    }
                });
        }
        
        function stopBot(botId) {
            if (!confirm('Stop this bot?\\n\\nThis will halt all trading immediately.')) return;
            
            fetch(`/api/bot/${botId}/stop`, {method: 'POST'})
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        updateDashboard();
                        alert(result.message);
                    } else {
                        alert('Error: ' + (result.error || result.message));
                    }
                });
        }
        
        // Delete bot
        function deleteBot(botId) {
            if (!confirm('Delete this bot? This cannot be undone.')) return;
            
            fetch(`/api/bot/${botId}/delete`, {method: 'POST'})
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        updateDashboard();
                    } else {
                        alert('Error: ' + result.error);
                    }
                });
        }
        
        // Close modal on outside click
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
        
        // Initial update
        updateDashboard();
        
        // Auto-refresh every 5 seconds
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>"""

def create_template():
    """Create templates directory and HTML file"""
    os.makedirs('templates', exist_ok=True)
    with open('templates/advanced_dashboard.html', 'w') as f:
        f.write(HTML_TEMPLATE)

def main():
    """Run the advanced dashboard"""
    print("=" * 70)
    print("🌐 ADVANCED TRADING DASHBOARD")
    print("=" * 70)
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    print(f"✓ Mode: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
    
    # Create template
    create_template()
    
    print("\n🚀 Starting advanced dashboard...")
    print("\nAccess dashboard at:")
    print("  http://localhost:5000")
    print("  http://127.0.0.1:5000")
    print("\n✨ Features:")
    print("  • Manage multiple trading bots")
    print("  • Start/stop/edit bots")
    print("  • Adjust trade amounts")
    print("  • View real-time performance")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTo install Flask:")
        print("  pip install flask")
