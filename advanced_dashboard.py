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
        
        # Auto-create bots for orphaned coins on startup
        self._auto_create_bots_for_orphaned_coins()
    
    def get_bots(self):
        """Load all active bots from file and check real status"""
        if not os.path.exists(self.bots_file):
            return []
        
        try:
            with open(self.bots_file, 'r') as f:
                bots = json.load(f)
            
            # Check actual screen session status and get position details
            for bot in bots:
                actual_status = self._check_bot_running(bot['id'])
                if actual_status != bot['status']:
                    # Update status to match reality
                    bot['status'] = actual_status
                
                # Add position details
                bot['position'] = self.get_bot_position(bot['id'])
            
            # Save corrected statuses
            self.save_bots(bots)
            
            return bots
        except:
            return []
    
    def get_bot_position(self, bot_id):
        """Extract current position details from bot logs"""
        log_file = f'bot_{bot_id}.log'
        
        if not os.path.exists(log_file):
            return None
        
        try:
            # Read last 100 lines of log
            with open(log_file, 'r') as f:
                lines = f.readlines()[-100:]
            
            position_info = {
                'has_position': False,
                'symbol': None,
                'entry_price': None,
                'current_price': None,
                'pnl_pct': 0,
                'stop_loss': None,
                'take_profit': None,
                'ai_reasoning': None,
                'news_headline': None,
                'time_held': None
            }
            
            # Parse logs for position info
            for line in reversed(lines):
                # Check for open position
                if 'OPENED POSITION' in line or '📍 Position set' in line:
                    position_info['has_position'] = True
                    # Extract entry price
                    if '@' in line and '$' in line:
                        try:
                            price_str = line.split('$')[1].split()[0]
                            position_info['entry_price'] = float(price_str)
                        except:
                            pass
                
                # Check for closed position
                if 'CLOSED POSITION' in line or '✅ Position cleared' in line:
                    position_info['has_position'] = False
                    break
                
                # Extract current symbol
                if 'Symbol:' in line:
                    try:
                        position_info['symbol'] = line.split('Symbol:')[1].strip().split()[0]
                    except:
                        pass
                
                # Extract current P&L
                if 'P&L:' in line:
                    try:
                        pnl_str = line.split('P&L:')[1].strip().split('%')[0]
                        position_info['pnl_pct'] = float(pnl_str.replace('+', ''))
                    except:
                        pass
                
                # Extract current price
                if 'Current:' in line and '$' in line:
                    try:
                        price_str = line.split('$')[1].split()[0]
                        position_info['current_price'] = float(price_str)
                    except:
                        pass
                
                # Extract AI reasoning
                if 'AI chose' in line or 'AI recommends' in line:
                    try:
                        position_info['ai_reasoning'] = line.split('|')[-1].strip()
                    except:
                        pass
            
            return position_info if position_info['has_position'] else None
        except Exception as e:
            print(f"Error reading bot position: {e}")
            return None
    
    def _check_bot_running(self, bot_id):
        """Check if bot screen session actually exists"""
        try:
            result = subprocess.run(
                ['screen', '-ls'],
                capture_output=True,
                text=True
            )
            
            # Check if bot_X appears in screen list
            if f'bot_{bot_id}' in result.stdout:
                return 'running'
            else:
                return 'stopped'
        except:
            return 'stopped'
    
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
    
    def _auto_create_bots_for_orphaned_coins(self):
        """Auto-create bots for coins in wallet that aren't being managed"""
        try:
            print("\n🔍 Checking for orphaned coins...")
            
            # Get all account balances
            account = self.client.client.get_account()
            balances = account['balances']
            
            # Get existing bots
            bots = self.get_bots()
            managed_symbols = set()
            for bot in bots:
                symbol = bot['symbol']
                coin = symbol.replace('USDT', '')
                managed_symbols.add(coin)
            
            # Find coins with balance > 0 that aren't managed
            orphaned_coins = []
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                # Skip USDT and coins with 0 balance
                if asset == 'USDT' or total == 0:
                    continue
                
                # Skip if already managed
                if asset in managed_symbols:
                    continue
                
                # Check if this coin can be traded on Binance
                trading_symbol = f"{asset}USDT"
                if self.client.is_symbol_tradeable(trading_symbol):
                    orphaned_coins.append({
                        'asset': asset,
                        'symbol': trading_symbol,
                        'balance': total
                    })
            
            # Auto-create bots for orphaned coins
            if orphaned_coins:
                print(f"\n⚠️  Found {len(orphaned_coins)} orphaned coin(s):")
                for coin in orphaned_coins:
                    print(f"   • {coin['asset']}: {coin['balance']:.8f}")
                
                print(f"\n🤖 Auto-creating management bots...")
                for coin in orphaned_coins:
                    # Create a bot with AI Autonomous strategy (best for unknown coins)
                    bot_name = f"Auto-Manager: {coin['asset']}"
                    
                    # Use a default trade amount of $100
                    # (bot won't buy more, just manage existing position)
                    new_bot = self.add_bot(
                        name=bot_name,
                        symbol=coin['symbol'],
                        strategy='ai_autonomous',
                        trade_amount=100.0
                    )
                    
                    print(f"   ✅ Created: {bot_name} (Bot #{new_bot['id']})")
                    print(f"      Symbol: {coin['symbol']}")
                    print(f"      Strategy: AI Autonomous (will manage sell timing)")
                
                print(f"\n💡 Auto-created bots are STOPPED by default.")
                print(f"   Start them via dashboard to begin management.")
                print(f"   They will detect existing positions and manage them.\n")
            else:
                print("   ✅ All coins are already managed or have 0 balance\n")
        
        except Exception as e:
            print(f"   ⚠️  Error checking orphaned coins: {e}\n")
            import traceback
            traceback.print_exc()
    
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

@app.route('/api/sentiment')
def get_sentiment():
    """Get AI sentiment analysis data for dashboard"""
    try:
        from ai_sentiment_tracker import AISentimentTracker
        tracker = AISentimentTracker()
        data = tracker.get_dashboard_data()
        
        return jsonify({
            'success': True,
            **data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/git/status')
def get_git_status():
    """Get git repository status"""
    try:
        import subprocess
        import sys
        
        # Get current branch
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd='.').decode('utf-8').strip()
        
        # Get latest commit info
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd='.').decode('utf-8').strip()
        commit_message = subprocess.check_output(['git', 'log', '-1', '--pretty=%B'], cwd='.').decode('utf-8').strip()
        commit_author = subprocess.check_output(['git', 'log', '-1', '--pretty=%an'], cwd='.').decode('utf-8').strip()
        commit_date = subprocess.check_output(['git', 'log', '-1', '--pretty=%ar'], cwd='.').decode('utf-8').strip()
        
        # Get uncommitted changes
        status_output = subprocess.check_output(['git', 'status', '--porcelain'], cwd='.').decode('utf-8').strip()
        has_changes = len(status_output) > 0
        changes_count = len(status_output.split('\n')) if status_output else 0
        
        # Fetch remote info
        try:
            subprocess.check_output(['git', 'fetch'], cwd='.', stderr=subprocess.DEVNULL)
        except:
            pass
        
        # Compare with remote
        try:
            local = subprocess.check_output(['git', 'rev-parse', '@'], cwd='.').decode('utf-8').strip()
            remote = subprocess.check_output(['git', 'rev-parse', '@{u}'], cwd='.').decode('utf-8').strip()
            
            if local == remote:
                remote_status = 'up-to-date'
                behind = 0
                ahead = 0
            else:
                # Count commits behind/ahead
                behind_output = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD..@{u}'], cwd='.').decode('utf-8').strip()
                ahead_output = subprocess.check_output(['git', 'rev-list', '--count', '@{u}..HEAD'], cwd='.').decode('utf-8').strip()
                behind = int(behind_output) if behind_output else 0
                ahead = int(ahead_output) if ahead_output else 0
                
                if behind > 0 and ahead > 0:
                    remote_status = 'diverged'
                elif behind > 0:
                    remote_status = 'behind'
                elif ahead > 0:
                    remote_status = 'ahead'
                else:
                    remote_status = 'up-to-date'
        except:
            remote_status = 'unknown'
            behind = 0
            ahead = 0
        
        # Get Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Get working directory
        working_dir = os.getcwd()
        
        return jsonify({
            'success': True,
            'branch': branch,
            'commit': {
                'hash': commit_hash,
                'message': commit_message,
                'author': commit_author,
                'date': commit_date
            },
            'status': {
                'clean': not has_changes,
                'changes_count': changes_count
            },
            'remote': {
                'status': remote_status,
                'behind': behind,
                'ahead': ahead
            },
            'python_version': python_version,
            'working_dir': working_dir
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/coin/<symbol>')
def get_coin_details(symbol):
    """Get detailed information about a specific coin"""
    try:
        manager = BotManager()
        
        # Find which bots are managing this symbol
        bots = manager.get_bots()
        managing_bots = []
        
        for bot in bots:
            if bot['symbol'].startswith(symbol) or bot['symbol'] == f"{symbol}USDT":
                bot_info = {
                    'id': bot['id'],
                    'name': bot['name'],
                    'status': bot['status'],
                    'strategy': bot['strategy'],
                    'position': bot.get('position', None)
                }
                managing_bots.append(bot_info)
        
        # Get current balance
        coin_balance = manager.client.get_account_balance(symbol)
        free_balance = float(coin_balance.get('free', 0)) if coin_balance else 0
        locked_balance = float(coin_balance.get('locked', 0)) if coin_balance else 0
        total_balance = free_balance + locked_balance
        
        # Get current price
        trading_symbol = f"{symbol}USDT"
        current_price = 0
        try:
            ticker = manager.client.client.get_symbol_ticker(symbol=trading_symbol)
            current_price = float(ticker['price']) if ticker else 0
        except:
            pass
        
        # Calculate USDT value
        usdt_value = total_balance * current_price
        
        # Get historical trades for this symbol
        trade_history = []
        import glob
        log_files = glob.glob('bot_*.log')
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                for line in lines[-200:]:  # Last 200 lines
                    if symbol in line and ('BUY' in line or 'SELL' in line):
                        trade_history.append(line.strip())
            except:
                pass
        
        # Load position files for more details
        position_details = []
        for bot in managing_bots:
            position_file = f"bot_{bot['id']}_position.json"
            if os.path.exists(position_file):
                try:
                    with open(position_file, 'r') as f:
                        pos_data = json.load(f)
                        position_details.append({
                            'bot_id': bot['id'],
                            'bot_name': bot['name'],
                            **pos_data
                        })
                except:
                    pass
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'balance': {
                'free': free_balance,
                'locked': locked_balance,
                'total': total_balance
            },
            'price': {
                'current': current_price,
                'usdt_value': usdt_value
            },
            'managing_bots': managing_bots,
            'position_details': position_details,
            'trade_history': trade_history[-10:],  # Last 10 trades
            'is_being_managed': len(managing_bots) > 0
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/logs')
def get_logs():
    """Get all bot logs with filtering"""
    try:
        bot_id = request.args.get('bot_id', None)
        log_type = request.args.get('type', None)
        search = request.args.get('search', '').lower()
        limit = int(request.args.get('limit', 200))
        
        logs = []
        
        # Get all log files
        import glob
        log_files = glob.glob('bot_*.log') + glob.glob('live_trading_*.log')
        
        for log_file in sorted(log_files, reverse=True):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                for line in lines[-500:]:  # Last 500 lines per file
                    if len(line) < 20:
                        continue
                    
                    try:
                        parts = line.split(' - ')
                        if len(parts) < 3:
                            continue
                        
                        timestamp = parts[0]
                        level = parts[1]
                        message = ' - '.join(parts[2:]).strip()
                        
                        # Determine log type
                        msg_lower = message.lower()
                        if 'opened position' in msg_lower or '🟢' in message:
                            type_tag = 'buy'
                        elif 'closed position' in msg_lower or '🔴' in message:
                            type_tag = 'sell'
                        elif 'signal' in msg_lower or 'analyzing' in msg_lower:
                            type_tag = 'signal'
                        elif 'error' in msg_lower or 'failed' in msg_lower:
                            type_tag = 'error'
                        elif 'waiting' in msg_lower or 'hold' in msg_lower:
                            type_tag = 'hold'
                        else:
                            type_tag = 'info'
                        
                        # Extract bot ID from filename
                        if log_file.startswith('bot_'):
                            file_bot_id = log_file.split('_')[1].split('.')[0]
                        else:
                            file_bot_id = 'main'
                        
                        # Apply filters
                        if bot_id and file_bot_id != bot_id:
                            continue
                        
                        if log_type and type_tag != log_type:
                            continue
                        
                        if search and search not in message.lower():
                            continue
                        
                        logs.append({
                            'timestamp': timestamp,
                            'level': level,
                            'message': message,
                            'type': type_tag,
                            'bot_id': file_bot_id,
                            'file': log_file
                        })
                    
                    except:
                        continue
            
            except:
                continue
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'logs': logs[:limit],
            'total': len(logs)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

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

@app.route('/api/bot/<int:bot_id>/add_funds', methods=['POST'])
def add_funds_to_bot(bot_id):
    """Add more funds to an existing bot"""
    try:
        data = request.json
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be greater than 0'})
        
        # Get available USDT balance
        usdt_balance = manager.client.get_account_balance('USDT')
        available = float(usdt_balance.get('free', 0)) if usdt_balance else 0
        
        if available < amount:
            return jsonify({
                'success': False, 
                'error': f'Insufficient USDT. Available: ${available:.2f}, Requested: ${amount:.2f}'
            })
        
        # Update bot's position file if it exists
        position_file = f'bot_{bot_id}_position.json'
        if os.path.exists(position_file):
            import json
            with open(position_file, 'r') as f:
                position_data = json.load(f)
            
            # Track capital additions
            if 'capital_additions' not in position_data:
                position_data['capital_additions'] = []
            
            position_data['capital_additions'].append({
                'amount': amount,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update initial investment
            old_investment = position_data.get('initial_investment', 0)
            position_data['initial_investment'] = old_investment + amount
            
            with open(position_file, 'w') as f:
                json.dump(position_data, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': f'Added ${amount:.2f} to bot. Total investment now: ${position_data["initial_investment"]:.2f}',
                'new_total': position_data['initial_investment']
            })
        else:
            # Bot hasn't traded yet, just update trade_amount
            bots = manager.get_bots()
            for bot in bots:
                if bot['id'] == bot_id:
                    old_amount = bot['trade_amount']
                    bot['trade_amount'] = old_amount + amount
                    manager.save_bots(bots)
                    return jsonify({
                        'success': True,
                        'message': f'Added ${amount:.2f} to bot. Initial investment set to: ${bot["trade_amount"]:.2f}',
                        'new_total': bot['trade_amount']
                    })
            
            return jsonify({'success': False, 'error': 'Bot not found'})
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })


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
        
        .summary-card.clickable {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .summary-card.clickable:hover {
            transform: translateY(-2px);
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
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
        
        .position-panel {
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1e 100%);
            border: 1px solid #2a2a3e;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .position-header {
            font-weight: bold;
            color: #4caf50;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .position-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 0.9em;
        }
        
        .position-detail {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }
        
        .position-detail .label {
            color: #888;
        }
        
        .position-detail .value {
            font-weight: bold;
            color: #fff;
        }
        
        .ai-reasoning {
            margin-top: 10px;
            padding: 10px;
            background: rgba(76, 175, 80, 0.1);
            border-left: 3px solid #4caf50;
            border-radius: 4px;
            font-size: 0.85em;
            color: #aaa;
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
        
        .tabs {
            display: flex;
            gap: 5px;
            background: #16161f;
            padding: 10px 20px 0 20px;
            border-bottom: 2px solid #2a2a3e;
        }
        
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            background: #1e1e2e;
            color: #888;
            border: none;
            font-size: 1em;
            transition: all 0.2s;
        }
        
        .tab:hover {
            background: #252535;
            color: #fff;
        }
        
        .tab.active {
            background: #0d0d17;
            color: #667eea;
            font-weight: bold;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Trading Management Dashboard</h1>
        <div class="mode-badge" id="mode">Loading...</div>
    </div>
    
    <!-- Tab Navigation -->
    <div class="tabs">
        <button class="tab active" onclick="switchTab('overview')">📊 Overview</button>
        <button class="tab" onclick="switchTab('logs')">📋 Logs</button>
        <button class="tab" onclick="switchTab('system')">⚙️ System</button>
    </div>
    
    <div class="container">
        <!-- Overview Tab Content -->
        <div id="overview-tab" class="tab-content active">
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
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-sm" onclick="updateDashboard()" title="Refresh status from actual screen sessions">🔄 Refresh Status</button>
                    <button class="btn" onclick="showAddBotModal()">➕ Add New Bot</button>
                </div>
            </div>
            
            <div class="bots-grid" id="bots-grid">
                <div class="empty-state">No bots yet. Add your first bot!</div>
            </div>
        </div>
        
        <!-- AI Sentiment Analysis Dashboard -->
        <div class="section">
            <div class="section-header">
                <h2>🧠 AI Sentiment Analysis</h2>
                <button onclick="refreshSentiment()" class="btn btn-sm">🔄 Refresh</button>
            </div>
            
            <!-- Sentiment Summary -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div class="summary-card">
                    <h3>🟢 Bullish</h3>
                    <div class="value" style="color: #4caf50;" id="sentiment-positive">0%</div>
                    <div style="color: #888; font-size: 0.9em;" id="sentiment-positive-count">0 articles</div>
                </div>
                <div class="summary-card">
                    <h3>🔴 Bearish</h3>
                    <div class="value" style="color: #f44336;" id="sentiment-negative">0%</div>
                    <div style="color: #888; font-size: 0.9em;" id="sentiment-negative-count">0 articles</div>
                </div>
                <div class="summary-card">
                    <h3>⚪ Neutral</h3>
                    <div class="value" style="color: #888;" id="sentiment-neutral">0%</div>
                    <div style="color: #888; font-size: 0.9em;" id="sentiment-neutral-count">0 articles</div>
                </div>
                <div class="summary-card">
                    <h3>📰 Total Analyzed</h3>
                    <div class="value" id="sentiment-total">0</div>
                    <div style="color: #888; font-size: 0.9em;">articles</div>
                </div>
            </div>
            
            <!-- Top Recommendations -->
            <div style="background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">🎯 Top AI Recommendations</h3>
                <div id="recommendations-list">
                    <div class="empty-state">No recommendations yet...</div>
                </div>
            </div>
            
            <!-- Recent Analyses -->
            <div style="background: #1e1e1e; padding: 15px; border-radius: 8px;">
                <h3 style="margin-top: 0;">📊 Recent AI Analyses</h3>
                <div id="analyses-list" style="max-height: 400px; overflow-y: auto;">
                    <div class="empty-state">No analyses yet...</div>
                </div>
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
        
        </div><!-- End Overview Tab -->
        
        <!-- Logs Tab Content -->
        <div id="logs-tab" class="tab-content">
        <!-- Bot Logs Viewer -->
        <div class="section">
            <div class="section-header">
                <h2>📜 Bot Logs</h2>
                <button class="btn btn-sm" onclick="refreshLogs()">🔄 Refresh</button>
            </div>
            
            <!-- Log Filters -->
            <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                <select id="log-bot-filter" onchange="refreshLogs()" style="padding: 8px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 5px; color: white;">
                    <option value="">All Bots</option>
                </select>
                
                <select id="log-type-filter" onchange="refreshLogs()" style="padding: 8px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 5px; color: white;">
                    <option value="">All Types</option>
                    <option value="buy">🟢 Buys</option>
                    <option value="sell">🔴 Sells</option>
                    <option value="signal">📊 Signals</option>
                    <option value="error">❌ Errors</option>
                    <option value="hold">⏸️ Holds</option>
                    <option value="info">ℹ️ Info</option>
                </select>
                
                <input type="text" id="log-search" placeholder="Search logs..." onkeyup="refreshLogs()" style="flex: 1; min-width: 200px; padding: 8px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 5px; color: white;">
                
                <button class="btn btn-sm" onclick="clearLogFilters()">Clear Filters</button>
            </div>
            
            <!-- Logs Display -->
            <div id="logs-container" style="max-height: 600px; overflow-y: auto; background: #0f0f1e; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace; font-size: 0.85em;">
                <div style="color: #888; text-align: center;">Loading logs...</div>
            </div>
        </div>
        </div><!-- End Logs Tab -->
        
        <!-- System Tab Content -->
        <div id="system-tab" class="tab-content">
            <!-- Git Status Section -->
            <div class="section">
                <div class="section-header">
                    <h2>📦 Git Repository Status</h2>
                    <button class="btn btn-sm" onclick="refreshGitStatus()">🔄 Refresh</button>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div class="summary-card">
                        <h3>🌿 Current Branch</h3>
                        <div class="value" style="font-size: 1.3em;" id="git-branch">Loading...</div>
                    </div>
                    
                    <div class="summary-card">
                        <h3>📊 Status</h3>
                        <div class="value" style="font-size: 1.3em;" id="git-status">Loading...</div>
                    </div>
                    
                    <div class="summary-card">
                        <h3>📝 Latest Commit</h3>
                        <div style="font-size: 0.9em; color: #888; margin-top: 10px;" id="git-commit">Loading...</div>
                    </div>
                    
                    <div class="summary-card">
                        <h3>🔄 Remote Status</h3>
                        <div class="value" style="font-size: 1.3em;" id="git-remote">Loading...</div>
                    </div>
                </div>
                
                <!-- Detailed Info -->
                <div style="background: #1a1a2e; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <h3 style="margin-top: 0;">📋 Detailed Information</h3>
                    <div id="git-details" style="font-family: 'Courier New', monospace; font-size: 0.9em; line-height: 1.8;">
                        Loading git information...
                    </div>
                </div>
                
                <!-- Update Actions -->
                <div style="background: #1e1e2e; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #2a2a3e;">
                    <h3 style="margin-top: 0;">🚀 Update Actions</h3>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        <button class="btn" style="background: #4caf50;" onclick="pullUpdates()">⬇️ Pull Latest Changes</button>
                        <button class="btn" style="background: #ff9800;" onclick="restartDashboard()">🔄 Restart Dashboard</button>
                        <button class="btn btn-secondary" onclick="viewUpdateLog()">📜 View Update Log</button>
                    </div>
                    <div id="update-status" style="margin-top: 15px; padding: 10px; background: #0d0d17; border-radius: 5px; font-family: 'Courier New', monospace; font-size: 0.85em; display: none;"></div>
                </div>
            </div>
            
            <!-- Server Info Section -->
            <div class="section">
                <div class="section-header">
                    <h2>🖥️ Server Information</h2>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                    <div class="summary-card">
                        <h3>💻 Python Version</h3>
                        <div class="value" style="font-size: 1.1em;" id="python-version">Loading...</div>
                    </div>
                    
                    <div class="summary-card">
                        <h3>📂 Working Directory</h3>
                        <div style="font-size: 0.85em; color: #888; margin-top: 10px; word-break: break-all;" id="working-dir">Loading...</div>
                    </div>
                    
                    <div class="summary-card">
                        <h3>⏱️ Dashboard Uptime</h3>
                        <div class="value" style="font-size: 1.1em;" id="dashboard-uptime">Loading...</div>
                    </div>
                </div>
            </div>
        </div><!-- End System Tab -->
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
    
    <!-- Add Funds Modal -->
    <div class="modal" id="add-funds-modal">
        <div class="modal-content">
            <h2>💰 Add Funds to Bot</h2>
            
            <input type="hidden" id="add-funds-bot-id">
            
            <div class="form-group">
                <label>Available USDT Balance</label>
                <div id="available-usdt" style="font-size: 1.5em; font-weight: bold; color: #4caf50; margin: 10px 0;">
                    Loading...
                </div>
            </div>
            
            <div class="form-group">
                <label>Amount to Add (USDT)</label>
                <input type="number" id="add-funds-amount" placeholder="Enter amount" min="1" step="0.01">
                <small style="color: #888; display: block; margin-top: 5px;">
                    This will increase the bot's total investment. The bot will use this additional capital on its next buy.
                </small>
            </div>
            
            <div class="form-group">
                <label>Quick Add</label>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button class="btn btn-sm btn-secondary" onclick="setAddAmount(10)">+$10</button>
                    <button class="btn btn-sm btn-secondary" onclick="setAddAmount(25)">+$25</button>
                    <button class="btn btn-sm btn-secondary" onclick="setAddAmount(50)">+$50</button>
                    <button class="btn btn-sm btn-secondary" onclick="setAddAmount(100)">+$100</button>
                    <button class="btn btn-sm btn-secondary" onclick="setAddAmountMax()">Max</button>
                </div>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideAddFundsModal()">Cancel</button>
                <button class="btn" style="background: #4caf50;" onclick="addFunds()">Add Funds</button>
            </div>
        </div>
    </div>
    
    <!-- Coin Details Modal -->
    <div class="modal" id="coin-details-modal">
        <div class="modal-content" style="max-width: 800px;">
            <h2 id="coin-modal-title">💎 Coin Details</h2>
            
            <div id="coin-modal-body">
                <!-- Dynamic content loaded here -->
                <div style="text-align: center; padding: 40px; color: #888;">
                    Loading coin details...
                </div>
            </div>
            
            <div class="form-actions" style="margin-top: 20px;">
                <button class="btn btn-secondary" onclick="hideCoinModal()">Close</button>
            </div>
        </div>
    </div>
    
    <script>
        let currentData = {};
        let dashboardStartTime = Date.now();
        
        // Format date to local timezone in dd/mm/yyyy hh:mm am/pm format
        function formatDateTime(dateString) {
            if (!dateString) return 'N/A';
            
            const date = new Date(dateString);
            
            // Check if valid date
            if (isNaN(date.getTime())) return dateString;
            
            // Get date components
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            
            // Get time components
            let hours = date.getHours();
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const ampm = hours >= 12 ? 'pm' : 'am';
            
            // Convert to 12-hour format
            hours = hours % 12;
            hours = hours ? hours : 12; // 0 should be 12
            hours = String(hours).padStart(2, '0');
            
            return `${day}/${month}/${year} ${hours}:${minutes} ${ampm}`;
        }
        
        // Format time only (for shorter display)
        function formatTime(dateString) {
            if (!dateString) return 'N/A';
            
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return dateString;
            
            let hours = date.getHours();
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const ampm = hours >= 12 ? 'pm' : 'am';
            
            hours = hours % 12;
            hours = hours ? hours : 12;
            hours = String(hours).padStart(2, '0');
            
            return `${hours}:${minutes} ${ampm}`;
        }
        
        // Format date only
        function formatDate(dateString) {
            if (!dateString) return 'N/A';
            
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return dateString;
            
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            
            return `${day}/${month}/${year}`;
        }
        
        // Tab switching
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // Add active class to clicked button
            event.target.classList.add('active');
            
            // Load data for the tab if needed
            if (tabName === 'logs') {
                refreshLogs();
            } else if (tabName === 'system') {
                refreshGitStatus();
                updateServerInfo();
            }
        }
        
        // Git status functions
        function refreshGitStatus() {
            fetch('/api/git/status')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        renderGitStatus(result);
                    } else {
                        document.getElementById('git-branch').textContent = 'Error';
                        document.getElementById('git-status').textContent = 'Error';
                        document.getElementById('git-commit').innerHTML = 'Error: ' + result.error;
                        document.getElementById('git-remote').textContent = 'Error';
                    }
                })
                .catch(error => {
                    console.error('Error fetching git status:', error);
                });
        }
        
        function renderGitStatus(data) {
            // Branch
            document.getElementById('git-branch').textContent = data.branch;
            
            // Status
            const statusEl = document.getElementById('git-status');
            if (data.status.clean) {
                statusEl.innerHTML = '<span style="color: #4caf50;">✓ Clean</span>';
            } else {
                statusEl.innerHTML = `<span style="color: #ff9800;">⚠️ ${data.status.changes_count} change(s)</span>`;
            }
            
            // Commit
            document.getElementById('git-commit').innerHTML = `
                <div style="margin-bottom: 5px;"><strong>${data.commit.hash}</strong></div>
                <div style="color: #bbb;">${data.commit.message}</div>
                <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
                    by ${data.commit.author} • ${data.commit.date}
                </div>
            `;
            
            // Remote status
            const remoteEl = document.getElementById('git-remote');
            if (data.remote.status === 'up-to-date') {
                remoteEl.innerHTML = '<span style="color: #4caf50;">✓ Up to date</span>';
            } else if (data.remote.status === 'behind') {
                remoteEl.innerHTML = `<span style="color: #ff9800;">⬇️ ${data.remote.behind} behind</span>`;
            } else if (data.remote.status === 'ahead') {
                remoteEl.innerHTML = `<span style="color: #2196f3;">⬆️ ${data.remote.ahead} ahead</span>`;
            } else if (data.remote.status === 'diverged') {
                remoteEl.innerHTML = `<span style="color: #f44336;">⚠️ Diverged</span>`;
            } else {
                remoteEl.innerHTML = '<span style="color: #888;">Unknown</span>';
            }
            
            // Detailed info
            let details = `<div style="color: #4caf50; margin-bottom: 10px;">✓ Git repository found</div>`;
            details += `<div><strong>Branch:</strong> ${data.branch}</div>`;
            details += `<div><strong>Latest Commit:</strong> ${data.commit.hash} - ${data.commit.message}</div>`;
            details += `<div><strong>Author:</strong> ${data.commit.author}</div>`;
            details += `<div><strong>Date:</strong> ${data.commit.date}</div>`;
            details += `<div><strong>Working Tree:</strong> ${data.status.clean ? 'Clean ✓' : data.status.changes_count + ' uncommitted changes ⚠️'}</div>`;
            
            if (data.remote.status === 'behind') {
                details += `<div style="color: #ff9800; margin-top: 10px;"><strong>⚠️ Your code is ${data.remote.behind} commit(s) behind origin/${data.branch}</strong></div>`;
                details += `<div style="color: #888;">Click "Pull Latest Changes" to update</div>`;
            } else if (data.remote.status === 'up-to-date') {
                details += `<div style="color: #4caf50; margin-top: 10px;"><strong>✓ Your code is up to date!</strong></div>`;
            }
            
            document.getElementById('git-details').innerHTML = details;
        }
        
        function updateServerInfo() {
            fetch('/api/git/status')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        document.getElementById('python-version').textContent = result.python_version;
                        document.getElementById('working-dir').textContent = result.working_dir;
                        
                        // Calculate uptime
                        const uptime = Math.floor((Date.now() - dashboardStartTime) / 1000);
                        const hours = Math.floor(uptime / 3600);
                        const minutes = Math.floor((uptime % 3600) / 60);
                        const seconds = uptime % 60;
                        document.getElementById('dashboard-uptime').textContent = 
                            `${hours}h ${minutes}m ${seconds}s`;
                    }
                })
                .catch(error => console.error('Error fetching server info:', error));
        }
        
        function pullUpdates() {
            if (!confirm('Pull latest changes from git?\n\nThis will update your code to the latest version.')) {
                return;
            }
            
            const statusEl = document.getElementById('update-status');
            statusEl.style.display = 'block';
            statusEl.innerHTML = '⏳ Pulling latest changes...';
            
            // Note: This would need a new API endpoint to actually execute git pull
            // For now, just show a message
            setTimeout(() => {
                statusEl.innerHTML = '⚠️ Manual update required. Run: git pull origin main';
            }, 1000);
        }
        
        function restartDashboard() {
            alert('To restart the dashboard, run on your server:\n\nscreen -S dashboard -X quit\nscreen -dmS dashboard python3 advanced_dashboard.py');
        }
        
        function viewUpdateLog() {
            alert('To view update log, run on your server:\n\ntail -f /root/tradingbot/auto_update.log');
        }
        
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
                <div class="summary-card clickable" onclick="showCoinDetails('${bal.asset}')">
                    <h3>${bal.asset} <span style="font-size: 0.8em; color: #667eea;">🔍 Click for details</span></h3>
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
                        <div class="bot-status ${bot.status}" title="Verified against screen sessions">
                            ${bot.status.toUpperCase()} ✓
                        </div>
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
                    
                    ${bot.position ? `
                    <div class="position-panel">
                        <div class="position-header">
                            📊 ACTIVE POSITION
                        </div>
                        <div class="position-details">
                            <div class="position-detail">
                                <span class="label">Symbol:</span>
                                <span class="value">${bot.position.symbol || bot.symbol}</span>
                            </div>
                            <div class="position-detail">
                                <span class="label">Entry:</span>
                                <span class="value">$${bot.position.entry_price?.toFixed(2) || 'N/A'}</span>
                            </div>
                            <div class="position-detail">
                                <span class="label">Current:</span>
                                <span class="value">$${bot.position.current_price?.toFixed(2) || 'N/A'}</span>
                            </div>
                            <div class="position-detail">
                                <span class="label">P&L:</span>
                                <span class="value" style="color: ${bot.position.pnl_pct >= 0 ? '#4caf50' : '#f44336'}">
                                    ${bot.position.pnl_pct >= 0 ? '+' : ''}${bot.position.pnl_pct.toFixed(2)}%
                                </span>
                            </div>
                        </div>
                        ${bot.position.ai_reasoning ? `
                        <div class="ai-reasoning">
                            <strong>🤖 AI:</strong> ${bot.position.ai_reasoning}
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}
                    
                    <div class="bot-controls">
                        ${bot.status === 'stopped' 
                            ? `<button class="btn btn-sm btn-success" onclick="startBot(${bot.id})">▶ Start</button>`
                            : `<button class="btn btn-sm btn-danger" onclick="stopBot(${bot.id})">⏹ Stop</button>`
                        }
                        <button class="btn btn-sm btn-secondary" onclick="editBot(${bot.id})">✏️ Edit</button>
                        <button class="btn btn-sm" style="background: #4caf50;" onclick="showAddFundsModal(${bot.id})">💰 Add Funds</button>
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
            
            list.innerHTML = trades.map(trade => {
                // Try to format trade time if it's a valid date
                let formattedTime = trade.time;
                try {
                    const date = new Date(trade.time);
                    if (!isNaN(date.getTime())) {
                        formattedTime = formatDateTime(trade.time);
                    }
                } catch (e) {
                    // If parsing fails, keep original
                }
                
                return `
                    <div class="trade-item">
                        <div class="trade-time">${formattedTime}</div>
                        <div>${trade.info}</div>
                    </div>
                `;
            }).reverse().join('');
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
            try {
                const modal = document.getElementById('add-bot-modal');
                if (!modal) {
                    console.error('❌ Modal not found!');
                    alert('Error: Modal element not found. Try refreshing the page.');
                    return;
                }
                console.log('✓ Opening Add Bot modal');
                modal.style.display = 'flex';
                updateSymbolHelp(); // Initialize help text
            } catch (error) {
                console.error('❌ Error opening modal:', error);
                alert('Error opening modal: ' + error.message);
            }
        }
        
        function hideAddBotModal() {
            document.getElementById('add-bot-modal').style.display = 'none';
        }
        
        function hideEditBotModal() {
            document.getElementById('edit-bot-modal').style.display = 'none';
        }
        
        // Show/hide add funds modal
        function showAddFundsModal(botId) {
            document.getElementById('add-funds-bot-id').value = botId;
            document.getElementById('add-funds-amount').value = '';
            document.getElementById('add-funds-modal').style.display = 'flex';
            
            // Fetch and display available USDT balance
            fetch('/api/overview')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        document.getElementById('available-usdt').textContent = 
                            '$' + result.account.available.toFixed(2);
                    } else {
                        document.getElementById('available-usdt').textContent = 'Error loading';
                    }
                })
                .catch(error => {
                    document.getElementById('available-usdt').textContent = 'Error loading';
                });
        }
        
        function hideAddFundsModal() {
            document.getElementById('add-funds-modal').style.display = 'none';
        }
        
        function setAddAmount(amount) {
            document.getElementById('add-funds-amount').value = amount;
        }
        
        function setAddAmountMax() {
            // Get available balance from the displayed value
            const availableText = document.getElementById('available-usdt').textContent;
            const available = parseFloat(availableText.replace('$', '').replace(',', ''));
            if (!isNaN(available)) {
                document.getElementById('add-funds-amount').value = available.toFixed(2);
            }
        }
        
        function addFunds() {
            const botId = parseInt(document.getElementById('add-funds-bot-id').value);
            const amount = parseFloat(document.getElementById('add-funds-amount').value);
            
            if (!amount || amount <= 0) {
                alert('Please enter a valid amount');
                return;
            }
            
            if (!confirm(`Add $${amount.toFixed(2)} to this bot?\n\nThis will increase the bot's total investment and it will use the additional capital on its next buy.`)) {
                return;
            }
            
            fetch(`/api/bot/${botId}/add_funds`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ amount: amount })
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    hideAddFundsModal();
                    updateDashboard();
                    alert(result.message);
                } else {
                    alert('Error: ' + result.error);
                }
            })
            .catch(error => {
                alert('Error adding funds: ' + error.message);
            });
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
        
        // Show/hide coin details modal
        function showCoinDetails(symbol) {
            document.getElementById('coin-details-modal').style.display = 'flex';
            document.getElementById('coin-modal-title').textContent = `💎 ${symbol} Details`;
            document.getElementById('coin-modal-body').innerHTML = `
                <div style="text-align: center; padding: 40px; color: #888;">
                    <div class="spinner"></div>
                    Loading ${symbol} details...
                </div>
            `;
            
            // Fetch coin details
            fetch(`/api/coin/${symbol}`)
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        renderCoinDetails(result);
                    } else {
                        document.getElementById('coin-modal-body').innerHTML = `
                            <div style="text-align: center; padding: 40px; color: #f44336;">
                                ❌ Error loading coin details: ${result.error}
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    document.getElementById('coin-modal-body').innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #f44336;">
                            ❌ Connection error: ${error.message}
                        </div>
                    `;
                });
        }
        
        function hideCoinModal() {
            document.getElementById('coin-details-modal').style.display = 'none';
        }
        
        function renderCoinDetails(data) {
            const modalBody = document.getElementById('coin-modal-body');
            
            // Calculate P&L if there's a position
            let pnlHtml = '';
            if (data.position_details && data.position_details.length > 0) {
                const pos = data.position_details[0];
                const currentPrice = data.price.current;
                const entryPrice = pos.entry_price || 0;
                const pnl = ((currentPrice - entryPrice) / entryPrice * 100).toFixed(2);
                const pnlColor = pnl >= 0 ? '#4caf50' : '#f44336';
                
                pnlHtml = `
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid ${pnl >= 0 ? '#4caf50' : '#f44336'};">
                        <h4 style="margin: 0 0 10px 0;">📊 Position P&L</h4>
                        <div style="font-size: 1.8em; font-weight: bold; color: ${pnlColor};">
                            ${pnl >= 0 ? '+' : ''}${pnl}%
                        </div>
                        <div style="color: #888; margin-top: 5px;">
                            Entry: $${entryPrice.toFixed(2)} → Current: $${currentPrice.toFixed(2)}
                        </div>
                    </div>
                `;
            }
            
            modalBody.innerHTML = `
                <!-- Balance Summary -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.9em; margin-bottom: 5px;">Total Balance</div>
                        <div style="font-size: 1.3em; font-weight: bold;">${data.balance.total.toFixed(8)}</div>
                        <div style="color: #888; font-size: 0.85em; margin-top: 3px;">${data.symbol}</div>
                    </div>
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.9em; margin-bottom: 5px;">Current Price</div>
                        <div style="font-size: 1.3em; font-weight: bold;">$${data.price.current.toFixed(2)}</div>
                        <div style="color: #888; font-size: 0.85em; margin-top: 3px;">USDT</div>
                    </div>
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.9em; margin-bottom: 5px;">Total Value</div>
                        <div style="font-size: 1.3em; font-weight: bold; color: #4caf50;">$${data.price.usdt_value.toFixed(2)}</div>
                        <div style="color: #888; font-size: 0.85em; margin-top: 3px;">USDT</div>
                    </div>
                </div>
                
                ${pnlHtml}
                
                <!-- Management Status -->
                <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="margin: 0 0 10px 0;">🤖 Management Status</h4>
                    ${data.is_being_managed ? `
                        <div style="color: #4caf50; margin-bottom: 10px;">
                            ✅ Currently managed by ${data.managing_bots.length} bot(s)
                        </div>
                        ${data.managing_bots.map(bot => `
                            <div style="background: #16161f; padding: 10px; border-radius: 6px; margin-top: 8px; border-left: 3px solid #667eea;">
                                <div style="font-weight: bold;">${bot.name}</div>
                                <div style="color: #888; font-size: 0.9em; margin-top: 3px;">
                                    Strategy: ${bot.strategy.replace('_', ' ').toUpperCase()} | 
                                    Status: <span style="color: ${bot.status === 'running' ? '#4caf50' : '#f44336'};">
                                        ${bot.status.toUpperCase()}
                                    </span>
                                </div>
                                ${bot.position ? `
                                    <div style="margin-top: 8px; padding: 8px; background: #0d0d15; border-radius: 4px;">
                                        <div style="font-size: 0.85em; color: #888;">AI Reasoning:</div>
                                        <div style="font-size: 0.9em; margin-top: 4px;">${bot.position.reasoning || 'No reasoning available'}</div>
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    ` : `
                        <div style="color: #ff9800;">
                            ⚠️ Not currently managed by any bot
                        </div>
                        <div style="color: #888; font-size: 0.9em; margin-top: 8px;">
                            This coin is in your wallet but no active bot is managing it.
                            Consider starting a bot or selling manually via Binance.
                        </div>
                    `}
                </div>
                
                <!-- Position Details -->
                ${data.position_details && data.position_details.length > 0 ? `
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <h4 style="margin: 0 0 10px 0;">📋 Position Details</h4>
                        ${data.position_details.map(pos => `
                            <div style="background: #16161f; padding: 10px; border-radius: 6px; margin-top: 8px;">
                                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 0.9em;">
                                    <div>
                                        <span style="color: #888;">Entry Price:</span>
                                        <span style="font-weight: bold; margin-left: 5px;">$${pos.entry_price?.toFixed(2) || 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span style="color: #888;">Stop Loss:</span>
                                        <span style="font-weight: bold; margin-left: 5px; color: #f44336;">$${pos.stop_loss?.toFixed(2) || 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span style="color: #888;">Take Profit:</span>
                                        <span style="font-weight: bold; margin-left: 5px; color: #4caf50;">$${pos.take_profit?.toFixed(2) || 'N/A'}</span>
                                    </div>
                                    <div>
                                        <span style="color: #888;">Position:</span>
                                        <span style="font-weight: bold; margin-left: 5px;">${pos.position || 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                <!-- Recent Trades -->
                ${data.trade_history && data.trade_history.length > 0 ? `
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <h4 style="margin: 0 0 10px 0;">📜 Recent Trade History</h4>
                        <div style="max-height: 200px; overflow-y: auto;">
                            ${data.trade_history.map(trade => `
                                <div style="background: #16161f; padding: 8px; border-radius: 4px; margin-top: 6px; font-size: 0.85em; font-family: monospace;">
                                    ${trade}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : `
                    <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: center; color: #888;">
                        No recent trade history for this coin
                    </div>
                `}
            `;
        }
        
        // Close modal on outside click
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
        
        // Logs functionality
        function refreshLogs() {
            const botFilter = document.getElementById('log-bot-filter').value;
            const typeFilter = document.getElementById('log-type-filter').value;
            const searchFilter = document.getElementById('log-search').value;
            
            let url = '/api/logs?limit=200';
            if (botFilter) url += `&bot_id=${botFilter}`;
            if (typeFilter) url += `&type=${typeFilter}`;
            if (searchFilter) url += `&search=${encodeURIComponent(searchFilter)}`;
            
            fetch(url)
                .then(response => response.json())
                .then(result => {
                    if (!result.success) {
                        document.getElementById('logs-container').innerHTML = 
                            '<div style="color: #f44336;">Error loading logs</div>';
                        return;
                    }
                    
                    const logsContainer = document.getElementById('logs-container');
                    
                    if (result.logs.length === 0) {
                        logsContainer.innerHTML = '<div style="color: #888; text-align: center;">No logs found</div>';
                        return;
                    }
                    
                    // Update bot filter dropdown
                    const botIds = [...new Set(result.logs.map(log => log.bot_id))];
                    const currentBotFilter = document.getElementById('log-bot-filter').value;
                    const botFilterHtml = '<option value="">All Bots</option>' + 
                        botIds.map(id => `<option value="${id}" ${id === currentBotFilter ? 'selected' : ''}>Bot ${id}</option>`).join('');
                    document.getElementById('log-bot-filter').innerHTML = botFilterHtml;
                    
                    // Render logs
                    logsContainer.innerHTML = result.logs.map(log => {
                        let color = '#fff';
                        let icon = '';
                        
                        switch(log.type) {
                            case 'buy': color = '#4caf50'; icon = '🟢'; break;
                            case 'sell': color = '#f44336'; icon = '🔴'; break;
                            case 'signal': color = '#2196f3'; icon = '📊'; break;
                            case 'error': color = '#ff5722'; icon = '❌'; break;
                            case 'hold': color = '#888'; icon = '⏸️'; break;
                            default: color = '#aaa'; icon = 'ℹ️';
                        }
                        
                        return `
                            <div style="margin-bottom: 8px; padding: 8px; background: #1a1a2e; border-radius: 4px; border-left: 3px solid ${color};">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: #888; font-size: 0.9em;">${formatDateTime(log.timestamp)}</span>
                                    <span style="color: ${color}; font-weight: bold;">${icon} Bot ${log.bot_id} | ${log.level}</span>
                                </div>
                                <div style="color: ${color};">${log.message}</div>
                            </div>
                        `;
                    }).join('');
                })
                .catch(error => {
                    console.error('Error fetching logs:', error);
                    document.getElementById('logs-container').innerHTML = 
                        '<div style="color: #f44336;">Connection error</div>';
                });
        }
        
        function clearLogFilters() {
            document.getElementById('log-bot-filter').value = '';
            document.getElementById('log-type-filter').value = '';
            document.getElementById('log-search').value = '';
            refreshLogs();
        }
        
        // Sentiment Analysis Dashboard
        function refreshSentiment() {
            fetch('/api/sentiment')
                .then(response => response.json())
                .then(result => {
                    if (!result.success) {
                        console.error('Sentiment error:', result.error);
                        return;
                    }
                    
                    // Update sentiment summary
                    const summary = result.sentiment_summary;
                    document.getElementById('sentiment-positive').textContent = summary.Positive_pct ? summary.Positive_pct + '%' : '0%';
                    document.getElementById('sentiment-positive-count').textContent = summary.Positive + ' articles';
                    document.getElementById('sentiment-negative').textContent = summary.Negative_pct ? summary.Negative_pct + '%' : '0%';
                    document.getElementById('sentiment-negative-count').textContent = summary.Negative + ' articles';
                    document.getElementById('sentiment-neutral').textContent = summary.Neutral_pct ? summary.Neutral_pct + '%' : '0%';
                    document.getElementById('sentiment-neutral-count').textContent = summary.Neutral + ' articles';
                    document.getElementById('sentiment-total').textContent = summary.total;
                    
                    // Render recommendations
                    renderRecommendations(result.recommendations || []);
                    
                    // Render recent analyses
                    renderAnalyses(result.recent_analyses || []);
                })
                .catch(error => {
                    console.error('Error fetching sentiment:', error);
                });
        }
        
        function renderRecommendations(recommendations) {
            const list = document.getElementById('recommendations-list');
            
            if (recommendations.length === 0) {
                list.innerHTML = '<div class="empty-state">No recommendations yet...</div>';
                return;
            }
            
            list.innerHTML = recommendations.map(rec => {
                const time = formatDateTime(rec.timestamp);
                const signalColor = rec.signal === 'BUY' ? '#4caf50' : '#f44336';
                const sentimentEmoji = rec.sentiment === 'Positive' ? '🟢' : (rec.sentiment === 'Negative' ? '🔴' : '⚪');
                
                return `
                    <div style="background: #2a2a2a; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid ${signalColor};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-weight: bold; color: ${signalColor};">${rec.signal} ${rec.symbols.join(', ')}</div>
                            <div style="color: #888; font-size: 0.85em;">${time}</div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span>${sentimentEmoji} ${rec.sentiment}</span>
                            <span style="color: #ffa726;">⭐ ${rec.confidence}% confidence</span>
                        </div>
                        <div style="color: #ccc; font-size: 0.9em; font-style: italic;">${rec.reasoning}</div>
                    </div>
                `;
            }).join('');
        }
        
        function renderAnalyses(analyses) {
            const list = document.getElementById('analyses-list');
            
            if (analyses.length === 0) {
                list.innerHTML = '<div class="empty-state">No analyses yet...</div>';
                return;
            }
            
            list.innerHTML = analyses.map(analysis => {
                const time = formatDateTime(analysis.timestamp);
                const signalColor = analysis.signal === 'BUY' ? '#4caf50' : (analysis.signal === 'SELL' ? '#f44336' : '#888');
                const sentimentColor = analysis.sentiment === 'Positive' ? '#4caf50' : (analysis.sentiment === 'Negative' ? '#f44336' : '#888');
                
                return `
                    <div style="background: #2a2a2a; padding: 10px; border-radius: 6px; margin-bottom: 8px; font-size: 0.9em;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <div style="font-weight: 500; color: #fff;">${analysis.article.substring(0, 60)}${analysis.article.length > 60 ? '...' : ''}</div>
                            <div style="color: #888; font-size: 0.85em;">${time}</div>
                        </div>
                        <div style="display: flex; gap: 15px; color: #ccc;">
                            <span style="color: ${signalColor};">📊 ${analysis.signal}</span>
                            <span style="color: ${sentimentColor};">${analysis.sentiment}</span>
                            <span style="color: #ffa726;">${analysis.confidence}%</span>
                            ${analysis.symbols.length > 0 ? '<span>💹 ' + analysis.symbols.slice(0, 3).join(', ') + '</span>' : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Initial update
        updateDashboard();
        refreshLogs();
        refreshSentiment();
        
        // Auto-refresh every 5 seconds
        setInterval(updateDashboard, 5000);
        setInterval(refreshLogs, 10000); // Refresh logs every 10 seconds
        setInterval(refreshSentiment, 30000); // Refresh sentiment every 30 seconds
        setInterval(updateServerInfo, 1000); // Update uptime every second
        
        // Verify dashboard loaded
        console.log('✅ Dashboard JavaScript loaded successfully');
        console.log('✅ Modal functions available:', typeof showAddBotModal === 'function');
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
