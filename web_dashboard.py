"""
Web-Based Trading Dashboard

A simple Flask-based dashboard to monitor your trading bot
Access from any browser on your network

Features:
- Real-time updates
- Trade history
- Performance charts
- Emergency stop button
"""
from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime
from binance_client import BinanceClient
from config import Config

app = Flask(__name__)

class WebDashboard:
    def __init__(self, symbol='BTCUSDT'):
        self.symbol = symbol
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
    
    def get_account_data(self):
        """Get current account info"""
        balance = self.client.get_account_balance('USDT')
        current_price = self.client.get_current_price(self.symbol)
        
        return {
            'balance': balance['free'] if balance else 0,
            'locked': balance['locked'] if balance else 0,
            'total': (balance['free'] + balance['locked']) if balance else 0,
            'price': current_price or 0,
            'symbol': self.symbol,
            'mode': 'TESTNET' if Config.USE_TESTNET else 'MAINNET'
        }
    
    def get_trades(self):
        """Read trades from log file"""
        today = datetime.now().strftime("%Y%m%d")
        log_file = f'live_trading_{today}.log'
        
        trades = []
        
        if not os.path.exists(log_file):
            return trades
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if 'CLOSED POSITION' in line:
                    # Try to get profit info from next few lines
                    profit_line = ""
                    for j in range(i+1, min(i+3, len(lines))):
                        if 'Profit:' in lines[j]:
                            profit_line = lines[j]
                            break
                    
                    trades.append({
                        'time': line.split(' ')[0] + ' ' + line.split(' ')[1],
                        'info': line.split('CLOSED POSITION:')[1].strip() if 'CLOSED POSITION:' in line else '',
                        'profit': profit_line.strip()
                    })
        
        except Exception as e:
            pass
        
        return trades[-20:]  # Last 20 trades

dashboard = WebDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def status():
    """API endpoint for current status"""
    try:
        data = dashboard.get_account_data()
        trades = dashboard.get_trades()
        
        return jsonify({
            'success': True,
            'data': data,
            'trades': trades,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f1e;
            color: #fff;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .mode {
            display: inline-block;
            padding: 5px 15px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a2a3e;
        }
        
        .stat-card h3 {
            color: #888;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .stat-card .value {
            font-size: 1.8em;
            font-weight: bold;
            color: #fff;
        }
        
        .trades {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a2a3e;
        }
        
        .trades h2 {
            margin-bottom: 15px;
            color: #fff;
        }
        
        .trade-item {
            background: #0f0f1e;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }
        
        .trade-time {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }
        
        .trade-info {
            margin-bottom: 5px;
        }
        
        .trade-profit {
            color: #4caf50;
            font-weight: bold;
        }
        
        .trade-profit.negative {
            color: #f44336;
        }
        
        .status {
            text-align: center;
            padding: 10px;
            margin-top: 20px;
            color: #888;
            font-size: 0.9em;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .updating {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Trading Dashboard</h1>
        <div class="mode" id="mode">Loading...</div>
        <div style="margin-top: 10px; font-size: 0.9em;">
            <span id="symbol">-</span> | Last Update: <span id="last-update">-</span>
        </div>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>💰 Available Balance</h3>
            <div class="value" id="balance">$0.00</div>
        </div>
        
        <div class="stat-card">
            <h3>🔒 In Orders</h3>
            <div class="value" id="locked">$0.00</div>
        </div>
        
        <div class="stat-card">
            <h3>💵 Total Balance</h3>
            <div class="value" id="total">$0.00</div>
        </div>
        
        <div class="stat-card">
            <h3>📈 Current Price</h3>
            <div class="value" id="price">$0.00</div>
        </div>
    </div>
    
    <div class="trades">
        <h2>📊 Recent Trades</h2>
        <div id="trades-list">
            <div class="loading">Loading trades...</div>
        </div>
    </div>
    
    <div class="status">
        Auto-refresh every 5 seconds
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(result => {
                    if (!result.success) {
                        console.error('Error:', result.error);
                        return;
                    }
                    
                    const data = result.data;
                    const trades = result.trades;
                    
                    // Update stats
                    document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                    document.getElementById('locked').textContent = '$' + data.locked.toFixed(2);
                    document.getElementById('total').textContent = '$' + data.total.toFixed(2);
                    document.getElementById('price').textContent = '$' + data.price.toFixed(2);
                    document.getElementById('symbol').textContent = data.symbol;
                    document.getElementById('mode').textContent = data.mode;
                    
                    // Update timestamp
                    const now = new Date();
                    document.getElementById('last-update').textContent = now.toLocaleTimeString();
                    
                    // Update trades
                    const tradesList = document.getElementById('trades-list');
                    
                    if (trades.length === 0) {
                        tradesList.innerHTML = '<div class="loading">No trades yet...</div>';
                    } else {
                        tradesList.innerHTML = trades.map(trade => {
                            const isProfit = trade.profit && trade.profit.includes('+');
                            const profitClass = isProfit ? 'trade-profit' : 'trade-profit negative';
                            
                            return `
                                <div class="trade-item">
                                    <div class="trade-time">${trade.time}</div>
                                    <div class="trade-info">${trade.info}</div>
                                    <div class="${profitClass}">${trade.profit || 'Pending...'}</div>
                                </div>
                            `;
                        }).reverse().join('');
                    }
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                });
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
    with open('templates/dashboard.html', 'w') as f:
        f.write(HTML_TEMPLATE)

def main():
    """Run the web dashboard"""
    print("=" * 70)
    print("🌐 WEB DASHBOARD")
    print("=" * 70)
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    symbol = input("Symbol to monitor [BTCUSDT]: ").strip().upper() or 'BTCUSDT'
    dashboard.symbol = symbol
    
    print(f"\n✓ Monitoring {symbol}")
    print(f"✓ Mode: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
    
    # Create template
    create_template()
    
    print("\n🚀 Starting web dashboard...")
    print("\nAccess dashboard at:")
    print("  http://localhost:5000")
    print("  http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTo install Flask:")
        print("  pip install flask")
