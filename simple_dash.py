"""
Simple Trading Dashboard - Clean & Modern with Charts
"""
from flask import Flask, jsonify, request
import json
import os
import subprocess
from datetime import datetime, timedelta
from binance_client import BinanceClient
from config import Config

app = Flask(__name__)

class BotManager:
    def __init__(self):
        self.bots_file = 'active_bots.json'
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
    
    def get_bots(self):
        """Load all active bots"""
        if not os.path.exists(self.bots_file):
            return []
        with open(self.bots_file, 'r') as f:
            bots = json.load(f)
        
        # Check actual status
        for bot in bots:
            result = subprocess.run(['screen', '-list'], capture_output=True, text=True)
            bot['status'] = 'running' if f'bot_{bot["id"]}' in result.stdout else 'stopped'
        
        return bots
    
    def get_account_info(self):
        """Get account info"""
        try:
            account = self.client.client.get_account()
            usdt_balance = next((b for b in account['balances'] if b['asset'] == 'USDT'), None)
            
            usdt_free = float(usdt_balance['free']) if usdt_balance else 0
            usdt_locked = float(usdt_balance['locked']) if usdt_balance else 0
            
            # Get all non-zero balances
            balances = []
            for b in account['balances']:
                free = float(b['free'])
                locked = float(b['locked'])
                if free + locked > 0 and b['asset'] != 'USDT':
                    balances.append({
                        'asset': b['asset'],
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    })
            
            return {
                'usdt_free': usdt_free,
                'usdt_locked': usdt_locked,
                'usdt_total': usdt_free + usdt_locked,
                'balances': balances
            }
        except:
            return None
    
    def start_bot(self, bot_id):
        """Start a bot"""
        try:
            bots = self.get_bots()
            bot = next((b for b in bots if b['id'] == bot_id), None)
            if not bot:
                return False, 'Bot not found'
            
            cmd = f"screen -dmS bot_{bot_id} python3 integrated_trader.py --bot-id {bot_id} --symbol {bot['symbol']} --strategy {bot['strategy']} --amount {bot['trade_amount']}"
            subprocess.run(cmd, shell=True)
            
            bot['status'] = 'running'
            with open(self.bots_file, 'w') as f:
                json.dump(bots, f, indent=2)
            
            return True, 'Bot started'
        except Exception as e:
            return False, str(e)
    
    def stop_bot(self, bot_id):
        """Stop a bot"""
        try:
            subprocess.run(['screen', '-S', f'bot_{bot_id}', '-X', 'quit'])
            
            bots = self.get_bots()
            bot = next((b for b in bots if b['id'] == bot_id), None)
            if bot:
                bot['status'] = 'stopped'
                with open(self.bots_file, 'w') as f:
                    json.dump(bots, f, indent=2)
            
            return True, 'Bot stopped'
        except Exception as e:
            return False, str(e)
    
    def update_bot(self, bot_id, updates):
        """Update bot settings"""
        try:
            bots = self.get_bots()
            bot = next((b for b in bots if b['id'] == bot_id), None)
            if not bot:
                return False, 'Bot not found'
            
            # Update fields
            bot.update(updates)
            
            with open(self.bots_file, 'w') as f:
                json.dump(bots, f, indent=2)
            
            return True, 'Bot updated'
        except Exception as e:
            return False, str(e)
    
    def get_bot_details(self, bot_id):
        """Get detailed bot info including logs and profit history"""
        try:
            bots = self.get_bots()
            bot = next((b for b in bots if b['id'] == bot_id), None)
            if not bot:
                return None
            
            # Get recent log entries
            log_file = f'bot_{bot_id}.log'
            recent_logs = []
            profit_history = []
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_logs = [line.strip() for line in lines[-20:]]
                    
                    # Extract profit history from trades
                    for line in lines:
                        if 'SELL' in line and 'Profit:' in line:
                            try:
                                # Extract timestamp and profit
                                parts = line.split()
                                timestamp = f"{parts[0]} {parts[1]}"
                                
                                # Find profit value
                                for i, part in enumerate(parts):
                                    if 'Profit:' in part and i + 1 < len(parts):
                                        profit_str = parts[i + 1].replace('$', '').replace('+', '')
                                        profit = float(profit_str)
                                        profit_history.append({
                                            'time': timestamp,
                                            'profit': profit
                                        })
                                        break
                            except:
                                continue
            
            # Get position info from logs
            position_info = None
            for line in reversed(recent_logs):
                if 'Position: LONG' in line:
                    position_info = line
                    break
            
            # Keep last 50 profit data points
            profit_history = profit_history[-50:]
            
            return {
                'bot': bot,
                'recent_logs': recent_logs,
                'position_info': position_info,
                'profit_history': profit_history
            }
        except Exception as e:
            return None

bot_manager = BotManager()

# API Routes
@app.route('/')
def index():
    return HTML

@app.route('/api/overview')
def overview():
    try:
        bots = bot_manager.get_bots()
        account = bot_manager.get_account_info()
        
        total_profit = sum(b.get('profit', 0) for b in bots)
        total_trades = sum(b.get('trades', 0) for b in bots)
        running_bots = len([b for b in bots if b['status'] == 'running'])
        
        return jsonify({
            'success': True,
            'bots': bots,
            'account': account,
            'stats': {
                'total_profit': total_profit,
                'total_trades': total_trades,
                'running_bots': running_bots,
                'total_bots': len(bots)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/<int:bot_id>/start', methods=['POST'])
def start_bot(bot_id):
    success, message = bot_manager.start_bot(bot_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/bot/<int:bot_id>/stop', methods=['POST'])
def stop_bot(bot_id):
    success, message = bot_manager.stop_bot(bot_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/bot/<int:bot_id>/details')
def get_bot_details(bot_id):
    details = bot_manager.get_bot_details(bot_id)
    if details:
        return jsonify({'success': True, 'data': details})
    else:
        return jsonify({'success': False, 'error': 'Bot not found'})

@app.route('/api/bot/<int:bot_id>/update', methods=['POST'])
def update_bot(bot_id):
    data = request.get_json()
    success, message = bot_manager.update_bot(bot_id, data)
    return jsonify({'success': success, 'message': message})

@app.route('/api/send_alert', methods=['POST'])
def send_alert():
    try:
        from twilio_notifier import TwilioNotifier
        
        bots = bot_manager.get_bots()
        account = bot_manager.get_account_info()
        
        total_trades = sum(b.get('trades', 0) for b in bots)
        total_profit = sum(b.get('profit', 0) for b in bots)
        running_bots = [b for b in bots if b['status'] == 'running']
        
        positions = [b['symbol'].replace('USDT', '') for b in running_bots]
        
        summary_data = {
            'bot_name': f"Dashboard ({len(running_bots)} bots)",
            'period': 'Manual Alert',
            'total_trades': total_trades,
            'buys': 0,
            'sells': 0,
            'total_profit': total_profit,
            'profit_percent': 0.0,
            'current_positions': positions,
            'account_value': account['usdt_total'] if account else 0
        }
        
        notifier = TwilioNotifier()
        result = notifier.send_summary(summary_data)
        
        return jsonify({'success': True if result else False, 'message': 'Alert sent!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 28px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102,126,234,0.4);
        }
        
        .btn-secondary {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }
        
        .btn-secondary:hover {
            background: #667eea;
            color: white;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .card-title {
            font-size: 16px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .card-value {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .card-subtitle {
            font-size: 14px;
            color: #999;
            margin-top: 4px;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            width: 100%;
        }
        
        .bots-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .bot-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .bot-info {
            flex: 1;
        }
        
        .bot-name {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .bot-details {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .bot-stats {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .bot-stat {
            text-align: center;
        }
        
        .bot-stat-label {
            font-size: 11px;
            opacity: 0.8;
            text-transform: uppercase;
        }
        
        .bot-stat-value {
            font-size: 20px;
            font-weight: 700;
        }
        
        .bot-actions {
            display: flex;
            gap: 8px;
        }
        
        .btn-sm {
            padding: 8px 16px;
            font-size: 12px;
        }
        
        .btn-success {
            background: #4caf50;
            color: white;
        }
        
        .btn-danger {
            background: #f44336;
            color: white;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-running {
            background: #4caf50;
            color: white;
        }
        
        .status-stopped {
            background: rgba(255,255,255,0.3);
            color: white;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 0;
            max-width: 700px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 24px;
            border-bottom: 1px solid #eee;
        }
        
        .modal-header h2 {
            margin: 0;
            font-size: 20px;
        }
        
        .modal-header h3 {
            margin: 0 0 12px 0;
            font-size: 14px;
            color: #666;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 32px;
            color: #999;
            cursor: pointer;
            line-height: 1;
            padding: 0;
            width: 32px;
            height: 32px;
        }
        
        .modal-close:hover {
            color: #333;
        }
        
        .modal-body {
            padding: 24px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Trading Dashboard</h1>
            <div class="header-actions">
                <button class="btn btn-secondary" onclick="updateDashboard()">🔄 Refresh</button>
                <button class="btn btn-primary" onclick="sendAlert()">📱 Send Alert</button>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div class="grid">
            <div class="card">
                <div class="card-title">Account Balance</div>
                <div class="card-value" id="balance">$0.00</div>
                <div class="card-subtitle">Available: $<span id="available">0.00</span></div>
            </div>
            
            <div class="card">
                <div class="card-title">Total Profit</div>
                <div class="card-value" id="profit">$0.00</div>
                <div class="card-subtitle"><span id="trades">0</span> trades</div>
            </div>
            
            <div class="card">
                <div class="card-title">Running Bots</div>
                <div class="card-value" id="running">0</div>
                <div class="card-subtitle">of <span id="total">0</span> total</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="chart-card">
            <div class="chart-title">📈 Performance Overview</div>
            <div class="chart-container">
                <canvas id="profitChart"></canvas>
            </div>
        </div>
        
        <!-- Bots Section -->
        <div class="bots-section">
            <div class="section-title">
                <span>🤖 Active Bots</span>
            </div>
            <div id="bots-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <!-- Bot Details Modal -->
        <div id="details-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="details-bot-name">Bot Details</h2>
                    <button class="modal-close" onclick="hideDetailsModal()">×</button>
                </div>
                <div class="modal-body">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div><strong>Symbol:</strong> <span id="details-symbol"></span></div>
                        <div><strong>Strategy:</strong> <span id="details-strategy"></span></div>
                        <div><strong>Budget:</strong> <span id="details-budget"></span></div>
                        <div><strong>Trades:</strong> <span id="details-trades"></span></div>
                        <div><strong>Profit:</strong> <span id="details-profit"></span></div>
                        <div><strong>Status:</strong> <span id="details-status"></span></div>
                    </div>
                    
                    <h3>📈 Profit Performance</h3>
                    <div style="background: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; height: 250px;">
                        <canvas id="botProfitChart"></canvas>
                    </div>
                    
                    <h3>Current Position</h3>
                    <div id="details-position" style="background: #f5f5f5; padding: 10px; border-radius: 6px; margin-bottom: 20px; font-family: monospace;"></div>
                    
                    <h3>Recent Activity (Last 20 lines)</h3>
                    <div id="details-logs" style="background: #1e1e1e; color: #00ff00; padding: 12px; border-radius: 6px; max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 11px;"></div>
                </div>
            </div>
        </div>
        
        <!-- Edit Bot Modal -->
        <div id="edit-modal" class="modal">
            <div class="modal-content" style="max-width: 400px;">
                <div class="modal-header">
                    <h2>Edit Bot</h2>
                    <button class="modal-close" onclick="hideEditModal()">×</button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="edit-bot-id">
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Bot Name:</label>
                        <input type="text" id="edit-bot-name" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Trade Amount (USDT):</label>
                        <input type="number" id="edit-bot-amount" min="1" step="1" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                        <small style="color: #666;">How much USDT this bot uses per trade</small>
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-primary" onclick="saveBot()" style="flex: 1;">Save Changes</button>
                        <button class="btn btn-secondary" onclick="hideEditModal()" style="flex: 1;">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let profitChart = null;
        
        function updateDashboard() {
            fetch('/api/overview')
                .then(r => r.json())
                .then(data => {
                    if (!data.success) return;
                    
                    // Update stats
                    document.getElementById('balance').textContent = '$' + (data.account?.usdt_total || 0).toFixed(2);
                    document.getElementById('available').textContent = (data.account?.usdt_free || 0).toFixed(2);
                    document.getElementById('profit').textContent = '$' + (data.stats.total_profit || 0).toFixed(2);
                    document.getElementById('trades').textContent = data.stats.total_trades;
                    document.getElementById('running').textContent = data.stats.running_bots;
                    document.getElementById('total').textContent = data.stats.total_bots;
                    
                    // Update chart
                    updateChart(data.bots);
                    
                    // Update bots list
                    renderBots(data.bots);
                })
                .catch(e => console.error(e));
        }
        
        function updateChart(bots) {
            const ctx = document.getElementById('profitChart').getContext('2d');
            
            if (profitChart) {
                profitChart.destroy();
            }
            
            // Create cumulative profit data for each bot
            const now = new Date();
            const datasets = bots.map((bot, index) => {
                const colors = [
                    'rgb(102, 126, 234)',
                    'rgb(118, 75, 162)',
                    'rgb(76, 175, 80)',
                    'rgb(255, 193, 7)',
                    'rgb(244, 67, 54)',
                    'rgb(33, 150, 243)',
                    'rgb(156, 39, 176)',
                    'rgb(255, 87, 34)'
                ];
                const color = colors[index % colors.length];
                
                return {
                    label: bot.symbol.replace('USDT', ''),
                    data: [{
                        x: new Date(now.getTime() - 3600000),
                        y: 0
                    }, {
                        x: now,
                        y: bot.profit || 0
                    }],
                    borderColor: color,
                    backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                };
            });
            
            profitChart = new Chart(ctx, {
                type: 'line',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': $' + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'hour',
                                displayFormats: {
                                    hour: 'HH:mm'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Time'
                            },
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Profit ($)'
                            },
                            grid: { color: 'rgba(0,0,0,0.05)' },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function renderBots(bots) {
            const container = document.getElementById('bots-container');
            
            if (bots.length === 0) {
                container.innerHTML = '<div class="empty-state">No bots yet</div>';
                return;
            }
            
            container.innerHTML = bots.map(bot => `
                <div class="bot-card">
                    <div class="bot-info">
                        <div class="bot-name">
                            ${bot.name} 
                            <span class="status-badge status-${bot.status}">${bot.status}</span>
                        </div>
                        <div class="bot-details">
                            ${bot.symbol} • ${bot.strategy.toUpperCase()}
                        </div>
                    </div>
                    
                    <div class="bot-stats">
                        <div class="bot-stat">
                            <div class="bot-stat-label">Budget</div>
                            <div class="bot-stat-value">$${(bot.trade_amount || 0).toFixed(0)}</div>
                        </div>
                        <div class="bot-stat">
                            <div class="bot-stat-label">Trades</div>
                            <div class="bot-stat-value">${bot.trades || 0}</div>
                        </div>
                        <div class="bot-stat">
                            <div class="bot-stat-label">P&L</div>
                            <div class="bot-stat-value">$${(bot.profit || 0).toFixed(2)}</div>
                        </div>
                    </div>
                    
                    <div class="bot-actions">
                        <button class="btn btn-sm" style="background: #667eea;" onclick="showBotDetails(${bot.id})">View</button>
                        <button class="btn btn-sm" style="background: #f0ad4e;" onclick="showEditBot(${bot.id})">Edit</button>
                        ${bot.status === 'running' ? 
                            `<button class="btn btn-sm btn-danger" onclick="stopBot(${bot.id})">Stop</button>` :
                            `<button class="btn btn-sm btn-success" onclick="startBot(${bot.id})">Start</button>`
                        }
                    </div>
                </div>
            `).join('');
        }
        
        function startBot(id) {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = 'Starting...';
            
            fetch(`/api/bot/${id}/start`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    setTimeout(() => updateDashboard(), 1000);
                })
                .catch(e => {
                    btn.disabled = false;
                    btn.textContent = 'Start';
                });
        }
        
        function stopBot(id) {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = 'Stopping...';
            
            fetch(`/api/bot/${id}/stop`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    setTimeout(() => updateDashboard(), 1000);
                })
                .catch(e => {
                    btn.disabled = false;
                    btn.textContent = 'Stop';
                });
        }
        
        function sendAlert() {
            if (confirm('Send trading alert SMS now?')) {
                fetch('/api/send_alert', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.success ? '✅ Alert sent!' : '❌ Error: ' + data.error);
                    });
            }
        }
        
        // Bot details modal
        let botDetailChart = null;
        
        function showBotDetails(id) {
            fetch(`/api/bot/${id}/details`)
                .then(r => r.json())
                .then(data => {
                    if (!data.success) return alert('Error loading bot details');
                    
                    const bot = data.data.bot;
                    const logs = data.data.recent_logs;
                    const position = data.data.position_info;
                    const profitHistory = data.data.profit_history || [];
                    
                    document.getElementById('details-bot-name').textContent = bot.name;
                    document.getElementById('details-symbol').textContent = bot.symbol;
                    document.getElementById('details-strategy').textContent = bot.strategy.toUpperCase();
                    document.getElementById('details-budget').textContent = '$' + (bot.trade_amount || 0).toFixed(2);
                    document.getElementById('details-trades').textContent = bot.trades || 0;
                    document.getElementById('details-profit').textContent = '$' + (bot.profit || 0).toFixed(2);
                    document.getElementById('details-status').textContent = bot.status.toUpperCase();
                    
                    document.getElementById('details-position').textContent = position || 'No active position';
                    
                    const logsHtml = logs.length > 0 ? 
                        logs.map(l => `<div style="padding: 4px 0; font-size: 12px; font-family: monospace;">${l}</div>`).join('') :
                        '<div>No logs available</div>';
                    document.getElementById('details-logs').innerHTML = logsHtml;
                    
                    // Render bot profit chart
                    renderBotChart(profitHistory, bot.name);
                    
                    document.getElementById('details-modal').style.display = 'flex';
                });
        }
        
        function renderBotChart(profitHistory, botName) {
            const ctx = document.getElementById('botProfitChart').getContext('2d');
            
            if (botDetailChart) {
                botDetailChart.destroy();
            }
            
            if (profitHistory.length === 0) {
                // No data yet
                ctx.font = '14px sans-serif';
                ctx.fillStyle = '#999';
                ctx.textAlign = 'center';
                ctx.fillText('No trade history yet', ctx.canvas.width / 2, ctx.canvas.height / 2);
                return;
            }
            
            // Calculate cumulative profit
            let cumulative = 0;
            const chartData = profitHistory.map(item => {
                cumulative += item.profit;
                return {
                    x: new Date(item.time),
                    y: cumulative
                };
            });
            
            botDetailChart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Cumulative Profit',
                        data: chartData,
                        borderColor: 'rgb(102, 126, 234)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: `${botName} - Profit Over Time`
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Profit: $' + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'MMM d',
                                    hour: 'HH:mm'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Cumulative Profit ($)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function hideDetailsModal() {
            document.getElementById('details-modal').style.display = 'none';
        }
        
        // Edit bot modal
        function showEditBot(id) {
            fetch(`/api/bot/${id}/details`)
                .then(r => r.json())
                .then(data => {
                    if (!data.success) return alert('Error loading bot');
                    
                    const bot = data.data.bot;
                    document.getElementById('edit-bot-id').value = bot.id;
                    document.getElementById('edit-bot-name').value = bot.name;
                    document.getElementById('edit-bot-amount').value = bot.trade_amount || 0;
                    
                    document.getElementById('edit-modal').style.display = 'flex';
                });
        }
        
        function hideEditModal() {
            document.getElementById('edit-modal').style.display = 'none';
        }
        
        function saveBot() {
            const id = document.getElementById('edit-bot-id').value;
            const name = document.getElementById('edit-bot-name').value;
            const amount = parseFloat(document.getElementById('edit-bot-amount').value);
            
            if (!name || amount <= 0) {
                return alert('Please enter valid values');
            }
            
            fetch(`/api/bot/${id}/update`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: name,
                    trade_amount: amount
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    hideEditModal();
                    updateDashboard();
                } else {
                    alert('Error: ' + data.message);
                }
            });
        }
        
        // Auto-refresh every 30 seconds
        setInterval(updateDashboard, 30000);
        
        // Initial load
        updateDashboard();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)

