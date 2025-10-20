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
            const labels = bots.map(b => b.symbol.replace('USDT', ''));
            const profits = bots.map(b => b.profit || 0);
            
            const ctx = document.getElementById('profitChart').getContext('2d');
            
            if (profitChart) {
                profitChart.destroy();
            }
            
            profitChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Profit ($)',
                        data: profits,
                        backgroundColor: profits.map(p => p >= 0 ? 'rgba(76, 175, 80, 0.6)' : 'rgba(244, 67, 54, 0.6)'),
                        borderColor: profits.map(p => p >= 0 ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)'),
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Profit: $' + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.05)' },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        },
                        x: {
                            grid: { display: false }
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
                            <div class="bot-stat-label">Trades</div>
                            <div class="bot-stat-value">${bot.trades || 0}</div>
                        </div>
                        <div class="bot-stat">
                            <div class="bot-stat-label">P&L</div>
                            <div class="bot-stat-value">$${(bot.profit || 0).toFixed(2)}</div>
                        </div>
                    </div>
                    
                    <div class="bot-actions">
                        ${bot.status === 'running' ? 
                            `<button class="btn btn-sm btn-danger" onclick="stopBot(${bot.id})">Stop</button>` :
                            `<button class="btn btn-sm btn-success" onclick="startBot(${bot.id})">Start</button>`
                        }
                    </div>
                </div>
            `).join('');
        }
        
        function startBot(id) {
            fetch(`/api/bot/${id}/start`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateDashboard();
                });
        }
        
        function stopBot(id) {
            if (confirm('Stop this bot?')) {
                fetch(`/api/bot/${id}/stop`, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateDashboard();
                    });
            }
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

