"""
Integrated Live Trader - Called by Dashboard
Runs a single bot with specified parameters
"""
import sys
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from binance_client import BinanceClient
from config import Config
from twilio_notifier import TwilioNotifier

# Import all strategies
from strategies.simple_profitable_strategy import SimpleProfitableStrategy
from strategies.enhanced_strategy import EnhancedStrategy
from strategies.volatile_coins_strategy import VolatileCoinsStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.conservative_strategy import ConservativeStrategy
from strategies.ai_news_strategy import AINewsStrategy
from strategies.ai_autonomous_strategy import AIAutonomousStrategy
from strategies.ticker_news_strategy import TickerNewsStrategy

# Strategy mapping
STRATEGIES = {
    'ticker_news': TickerNewsStrategy,
    'simple_profitable': SimpleProfitableStrategy,
    'ai_autonomous': AIAutonomousStrategy,
    'ai_news': AINewsStrategy,
    'momentum': EnhancedStrategy,
    'mean_reversion': MeanReversionStrategy,
    'breakout': BreakoutStrategy,
    'conservative': ConservativeStrategy,
    'volatile': VolatileCoinsStrategy
}

class BotRunner:
    """Runs a single bot instance"""
    
    def __init__(self, bot_id, bot_name, symbol, strategy_name, trade_amount):
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.trade_amount = trade_amount
        
        # Setup logging (single log file per bot, no dates)
        log_file = f'bot_{bot_id}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize client and strategy
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        
        strategy_class = STRATEGIES.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        self.strategy = strategy_class()
        
        # Pass Binance client to strategy for dynamic symbol validation
        if hasattr(self.strategy, 'set_binance_client'):
            self.strategy.set_binance_client(self.client)
        
        # Store symbol in strategy for AI strategies
        if hasattr(self.strategy, 'set_symbol'):
            self.strategy.set_symbol(self.symbol)
        
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.trades_count = 0
        self.profit_total = 0.0
        
        # Track if this bot has made any trades yet (for proper trade_amount logic)
        # trade_amount = TOTAL investment, not per-trade amount
        self.has_traded = False
        self.initial_investment = 0.0
        
        # Initialize SMS notifier
        self.sms_notifier = TwilioNotifier()
        
        # 6-hour summary tracking
        self.summary_interval = 21600  # 6 hours in seconds
        self.last_summary_time = time.time()
        self.summary_stats = {
            'total_trades': 0,
            'buys': 0,
            'sells': 0,
            'total_profit': 0.0,
            'period_start_value': 0.0
        }
        
        # Position persistence file
        self.position_file = f'bot_{self.bot_id}_position.json'
        self._load_position()
        
        # Check for orphaned coins in wallet
        self._check_orphaned_positions()
    
    def _load_position(self):
        """Load saved position from file (if exists)"""
        try:
            import json
            if os.path.exists(self.position_file):
                with open(self.position_file, 'r') as f:
                    data = json.load(f)
                    self.position = data.get('position')
                    self.entry_price = data.get('entry_price')
                    self.stop_loss = data.get('stop_loss')
                    self.take_profit = data.get('take_profit')
                    self.symbol = data.get('symbol', self.symbol)
                    self.has_traded = data.get('has_traded', False)
                    self.initial_investment = data.get('initial_investment', 0.0)
                    capital_additions = data.get('capital_additions', [])
                    
                    self.logger.info("=" * 70)
                    self.logger.info(f"📂 LOADED EXISTING POSITION FROM FILE")
                    self.logger.info(f"   Symbol: {self.symbol}")
                    self.logger.info(f"   Entry: ${self.entry_price:.2f}")
                    self.logger.info(f"   Stop Loss: ${self.stop_loss:.2f}")
                    self.logger.info(f"   Take Profit: ${self.take_profit:.2f}")
                    if self.has_traded:
                        self.logger.info(f"   Total Investment: ${self.initial_investment:.2f}")
                        if capital_additions:
                            self.logger.info(f"   Capital Additions: {len(capital_additions)} time(s)")
                            for addition in capital_additions[-3:]:  # Show last 3
                                self.logger.info(f"      + ${addition['amount']:.2f} on {addition['timestamp'][:10]}")
                    self.logger.info("=" * 70)
                    
                    # CRITICAL: Tell the strategy about the loaded position!
                    if self.position == 'long' and hasattr(self.strategy, 'set_position'):
                        self.strategy.set_position(self.symbol, self.entry_price)
                        self.logger.info("✅ Informed strategy about existing position")
        except Exception as e:
            self.logger.error(f"Error loading position: {e}")
    
    def _save_position(self):
        """Save current position to file"""
        try:
            import json
            data = {
                'position': self.position,
                'entry_price': self.entry_price,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'symbol': self.symbol,
                'has_traded': self.has_traded,
                'initial_investment': self.initial_investment,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.position_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving position: {e}")
    
    def _clear_position_file(self):
        """Delete position file when position is closed"""
        try:
            if os.path.exists(self.position_file):
                os.remove(self.position_file)
                self.logger.info("🗑️ Cleared position file")
        except Exception as e:
            self.logger.error(f"Error deleting position file: {e}")
    
    def _update_bot_symbol(self, new_symbol):
        """Update bot's symbol in active_bots.json when AI switches coins"""
        try:
            bots_file = 'active_bots.json'
            if os.path.exists(bots_file):
                with open(bots_file, 'r') as f:
                    bots = json.load(f)
                
                # Find and update this bot
                for bot in bots:
                    if bot['id'] == self.bot_id:
                        bot['symbol'] = new_symbol
                        self.logger.info(f"✅ Updated bot config: {self.bot_name} → {new_symbol}")
                        break
                
                # Save updated config
                with open(bots_file, 'w') as f:
                    json.dump(bots, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error updating bot symbol: {e}")
    
    def _check_orphaned_positions(self):
        """Check if we have coins in wallet that bot doesn't know about"""
        if self.position:
            # Already have a tracked position
            return
        
        try:
            # Check what coins we have
            coin = self.symbol.replace('USDT', '')
            balance = self.client.get_account_balance(coin)
            
            if balance:
                amount = float(balance.get('free', 0))
                if amount > 0:
                    # We have coins but no tracked position!
                    self.logger.warning("=" * 70)
                    self.logger.warning(f"⚠️  ORPHANED POSITION DETECTED")
                    self.logger.warning("=" * 70)
                    self.logger.warning(f"Found {amount:.6f} {coin} in wallet")
                    self.logger.warning(f"But no position file exists for this bot")
                    self.logger.warning("")
                    self.logger.warning("🤖 Bot will now monitor this position")
                    self.logger.warning(f"   Will sell when:")
                    self.logger.warning(f"   • AI signals SELL")
                    self.logger.warning(f"   • Price drops significantly")
                    self.logger.warning("=" * 70)
                    
                    # Get current price
                    data = self.get_data(limit=10)
                    if data and len(data) > 0:
                        current_price = float(data[-1][4])
                        
                        # Set position (we don't know entry price, so use current - 3%)
                        self.position = 'LONG'
                        self.entry_price = current_price * 0.97  # Assume we're slightly in profit
                        self.stop_loss = current_price * 0.92  # 8% stop loss (wider since we don't know entry)
                        self.take_profit = current_price * 1.05  # 5% take profit
                        
                        # Mark as traded (this is an existing position)
                        self.has_traded = True
                        self.initial_investment = self.trade_amount  # Assume initial investment was trade_amount
                        
                        self.logger.info(f"📍 Tracking orphaned position:")
                        self.logger.info(f"   Current Price: ${current_price:.2f}")
                        self.logger.info(f"   Assumed Entry: ${self.entry_price:.2f} (est)")
                        self.logger.info(f"   Stop Loss: ${self.stop_loss:.2f}")
                        self.logger.info(f"   Take Profit: ${self.take_profit:.2f}")
                        self.logger.info(f"   Initial Investment: ${self.initial_investment:.2f} (assumed)")
                        
                        # Save this tracked position
                        self._save_position()
        
        except Exception as e:
            # Silently fail - this is just a nice-to-have feature
            pass
    
    def get_data(self, limit=100):
        """Fetch recent klines - return raw format for strategy.analyze()"""
        klines = self.client.get_klines(self.symbol, interval='5m', limit=limit)
        return klines if klines else []
    
    def format_quantity(self, symbol, quantity):
        """
        Format quantity to match Binance precision rules
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            quantity: Raw quantity value
            
        Returns:
            Properly formatted quantity string
        """
        try:
            # Get symbol info to find precision
            symbol_info = self.client.get_symbol_info(symbol)
            
            if not symbol_info or 'filters' not in symbol_info:
                self.logger.warning(f"No symbol info for {symbol}, using 6 decimals")
                return float(f"{quantity:.6f}")
            
            # Find LOT_SIZE filter
            filters = symbol_info.get('filters', [])
            if not filters:
                self.logger.warning(f"No filters for {symbol}, using 6 decimals")
                return float(f"{quantity:.6f}")
            
            for filter_item in filters:
                if filter_item.get('filterType') == 'LOT_SIZE':
                    step_size = float(filter_item.get('stepSize', 0.000001))
                    
                    # Calculate precision from step_size
                    # e.g., 0.00001 -> 5 decimal places
                    precision = 0
                    if step_size < 1:
                        step_size_str = f"{step_size:.10f}".rstrip('0')
                        if '.' in step_size_str:
                            precision = len(step_size_str.split('.')[1])
                    
                    # Round quantity to the correct precision
                    formatted = round(quantity, precision)
                    
                    # Remove trailing zeros
                    if precision > 0:
                        formatted = float(f"{formatted:.{precision}f}")
                    
                    self.logger.info(f"✅ Formatted quantity: {quantity:.8f} -> {formatted} (precision: {precision})")
                    return formatted
            
            # If no LOT_SIZE filter found, use 6 decimals
            self.logger.warning(f"No LOT_SIZE filter for {symbol}, using 6 decimals")
            return float(f"{quantity:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error formatting quantity: {e}, using 6 decimals")
            import traceback
            self.logger.error(traceback.format_exc())
            return float(f"{quantity:.6f}")
    
    def execute_trade(self, signal, current_price, signal_data=None):
        """Execute buy/sell orders"""
        try:
            if signal == 'BUY':
                # Check USDT balance first
                try:
                    usdt_balance = self.client.get_account_balance('USDT')
                    available_usdt = float(usdt_balance['free']) if usdt_balance else 0
                    self.logger.info(f"💰 USDT Balance Check:")
                    self.logger.info(f"   Available: ${available_usdt:.2f}")
                    self.logger.info(f"   Locked: ${float(usdt_balance.get('locked', 0)):.2f}")
                    self.logger.info(f"   Total: ${float(usdt_balance.get('free', 0)) + float(usdt_balance.get('locked', 0)):.2f}")
                except Exception as e:
                    self.logger.error(f"Error checking balance: {e}")
                    available_usdt = 0
                
                # Check if we have enough USDT to buy
                min_trade = 50  # Minimum $50 per trade (ensures we get enough crypto to sell later)
                if available_usdt < min_trade:
                    self.logger.warning("=" * 70)
                    self.logger.warning(f"⚠️  Cannot BUY: Insufficient USDT")
                    self.logger.warning(f"   Available: ${available_usdt:.2f}")
                    self.logger.warning(f"   Minimum needed: ${min_trade}")
                    self.logger.warning("=" * 70)
                    return False
                
                # Determine how much to invest
                if self.position:
                    # Already holding crypto - ignore BUY signals
                    # Bot can only SELL, then buy again with proceeds
                    self.logger.info("=" * 70)
                    self.logger.info("📊 Already holding position - ignoring BUY signal")
                    self.logger.info(f"   Current position: {self.symbol}")
                    self.logger.info(f"   Entry: ${self.entry_price:.2f}")
                    self.logger.info(f"   Current: ${current_price:.2f}")
                    self.logger.info(f"   Action: Waiting for SELL signal")
                    self.logger.info("=" * 70)
                    return False
                
                elif not self.has_traded:
                    # FIRST TRADE: Use trade_amount as initial investment
                    amount_to_invest = self.trade_amount
                    required_balance = amount_to_invest * 1.01  # +1% for fees
                    
                    self.logger.info("💎 FIRST TRADE - Initial Investment")
                    self.logger.info(f"   Investment Amount: ${amount_to_invest:.2f}")
                    self.logger.info(f"   Required Balance: ${required_balance:.2f} (includes 1% fees)")
                    self.logger.info(f"   Available Balance: ${available_usdt:.2f}")
                    
                    if available_usdt < required_balance:
                        self.logger.warning("=" * 70)
                        self.logger.warning("⚠️  INSUFFICIENT USDT FOR INITIAL INVESTMENT")
                        self.logger.warning("=" * 70)
                        self.logger.warning(f"Required: ${required_balance:.2f} (includes 1% for fees)")
                        self.logger.warning(f"Available: ${available_usdt:.2f}")
                        self.logger.warning(f"Shortfall: ${required_balance - available_usdt:.2f}")
                        self.logger.warning("")
                        self.logger.warning("💡 Solutions:")
                        self.logger.warning("   1. Add more USDT to your Binance account")
                        self.logger.warning("   2. Reduce bot trade amount")
                        self.logger.warning("=" * 70)
                        
                        import time
                        time.sleep(300)  # Sleep for 5 minutes
                        return False
                    
                    # Mark as traded and save initial investment
                    self.has_traded = True
                    self.initial_investment = amount_to_invest
                    
                else:
                    # SUBSEQUENT TRADES AFTER SELL: Use ALL available USDT from previous sell
                    # This trades the same money back and forth (sell high, buy low)
                    amount_to_invest = available_usdt * 0.99  # Leave 1% for fees
                    
                    self.logger.info("🔄 RE-INVESTING from previous sell")
                    self.logger.info(f"   Original Investment: ${self.initial_investment:.2f}")
                    self.logger.info(f"   Current Balance: ${available_usdt:.2f}")
                    self.logger.info(f"   Profit/Loss: ${available_usdt - self.initial_investment:.2f} ({((available_usdt / self.initial_investment - 1) * 100):.2f}%)")
                    self.logger.info(f"   Re-investing: ${amount_to_invest:.2f}")
                    
                    if amount_to_invest < 50:  # Minimum $50 to trade (ensures enough crypto to sell)
                        self.logger.warning("⚠️  Balance too low to continue trading (< $50)")
                        self.logger.warning(f"   Available: ${available_usdt:.2f}")
                        return False
                
                # Calculate quantity based on amount to invest
                raw_quantity = amount_to_invest / current_price
                
                # Format quantity to match Binance precision rules
                quantity = self.format_quantity(self.symbol, raw_quantity)
                
                self.logger.info(f"📊 Placing BUY order:")
                self.logger.info(f"   Symbol: {self.symbol}")
                self.logger.info(f"   Quantity: {quantity}")
                self.logger.info(f"   Investing: ${amount_to_invest:.2f}")
                
                # Place order
                order = self.client.place_market_order(
                    symbol=self.symbol,
                    side='BUY',
                    quantity=quantity
                )
                
                if order:
                    # If adding to position, calculate weighted average entry price
                    if self.position == 'LONG' and self.entry_price:
                        # Get current holdings
                        try:
                            asset = self.symbol.replace('USDT', '')
                            balance = self.client.get_account_balance(asset)
                            if balance:
                                old_quantity = float(balance['free']) - quantity  # Holdings before this buy
                                if old_quantity > 0:
                                    # Calculate weighted average
                                    old_value = old_quantity * self.entry_price
                                    new_value = quantity * current_price
                                    total_value = old_value + new_value
                                    total_quantity = old_quantity + quantity
                                    new_avg_entry = total_value / total_quantity
                                    
                                    self.logger.info("📊 Position Updated:")
                                    self.logger.info(f"   Old Entry: ${self.entry_price:.2f}")
                                    self.logger.info(f"   New Entry: ${new_avg_entry:.2f} (weighted average)")
                                    
                                    self.entry_price = new_avg_entry
                        except Exception as e:
                            self.logger.warning(f"Could not calculate weighted average: {e}")
                            # Keep using old entry price
                    else:
                        # First position
                        self.entry_price = current_price
                    
                    self.position = 'LONG'
                    self.stop_loss = self.entry_price * 0.98  # 2% stop loss from avg entry
                    self.take_profit = self.entry_price * 1.03  # 3% take profit from avg entry
                    
                    # SAVE POSITION TO FILE (persists across restarts!)
                    self._save_position()
                    
                    # Notify strategy about position (for AI strategies)
                    if hasattr(self.strategy, 'set_position'):
                        self.strategy.set_position(self.symbol, self.entry_price)
                    
                    # Track trade decision for dashboard
                    if hasattr(self.strategy, 'sentiment_tracker'):
                        reasoning = signal_data.get('reasoning', 'Trade executed') if signal_data else 'Trade executed'
                        self.strategy.sentiment_tracker.add_trade_decision(
                            'BUY', self.symbol, current_price, reasoning
                        )
                    
                    self.logger.info(f"🟢 OPENED POSITION: {self.bot_name}")
                    self.logger.info(f"   Symbol: {self.symbol}")
                    self.logger.info(f"   Entry: ${current_price:.2f}")
                    self.logger.info(f"   Quantity: {quantity:.6f}")
                    self.logger.info(f"   Amount: ${self.trade_amount:.2f}")
                    
                    # Send SMS notification (with AI reasoning if available)
                    # Track for 6-hour summary (no per-trade SMS)
                    self.summary_stats['total_trades'] += 1
                    self.summary_stats['buys'] += 1
                    self.logger.info(f"📊 Trade tracked in summary stats (no SMS sent)")
                    
                    return True
            
            elif signal == 'SELL' and self.position:
                # Get current balance
                asset = self.symbol.replace('USDT', '')
                balance = self.client.get_account_balance(asset)
                
                self.logger.info(f"🔴 SELL ATTEMPT - {asset} Balance Check:")
                self.logger.info(f"   Asset: {asset}")
                self.logger.info(f"   Free: {balance.get('free', 0) if balance else 'No balance'}")
                self.logger.info(f"   Locked: {balance.get('locked', 0) if balance else 'No balance'}")
                self.logger.info(f"   Total: {float(balance.get('free', 0)) + float(balance.get('locked', 0)) if balance else 'No balance'}")
                
                if balance and balance['free'] > 0:
                    raw_quantity = balance['free']
                    self.logger.info(f"   Raw quantity to sell: {raw_quantity}")
                    
                    # Format quantity to match Binance precision rules
                    quantity = self.format_quantity(self.symbol, raw_quantity)
                    self.logger.info(f"   Formatted quantity: {quantity}")
                    
                    # Check minimum order size (Binance requires minimum 0.001 BTC for BTCUSDT)
                    min_quantity = 0.001
                    if quantity < min_quantity:
                        self.logger.warning("=" * 70)
                        self.logger.warning("⚠️  QUANTITY TOO SMALL TO SELL")
                        self.logger.warning("=" * 70)
                        self.logger.warning(f"   Available: {quantity} BTC")
                        self.logger.warning(f"   Minimum required: {min_quantity} BTC")
                        self.logger.warning(f"   Shortfall: {min_quantity - quantity} BTC")
                        self.logger.warning("")
                        self.logger.warning("💡 This position is too small to sell on Binance")
                        self.logger.warning("   The bot will keep it and wait for it to grow")
                        self.logger.warning("   or you can manually sell it in Binance app")
                        self.logger.warning("=" * 70)
                        return False
                    
                    # Place order
                    order = self.client.place_market_order(
                        symbol=self.symbol,
                        side='SELL',
                        quantity=quantity
                    )
                    
                    if order:
                        # Calculate profit
                        profit = (current_price - self.entry_price) * quantity
                        profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                        
                        self.logger.info(f"🔴 CLOSED POSITION: {self.bot_name}")
                        self.logger.info(f"   Exit: ${current_price:.2f}")
                        self.logger.info(f"   Profit: ${profit:.2f} ({profit_pct:+.2f}%)")
                        
                        # Send SMS notification (with AI reasoning if available)
                        notification_data = {
                            'action': 'SELL',
                            'symbol': self.symbol,
                            'price': current_price,
                            'quantity': quantity,
                            'amount': current_price * quantity,
                            'profit': profit,
                            'profit_percent': profit_pct,
                            'bot_name': self.bot_name
                        }
                        
                        # Track for 6-hour summary (no per-trade SMS)
                        self.summary_stats['total_trades'] += 1
                        self.summary_stats['sells'] += 1
                        self.summary_stats['total_profit'] += profit
                        self.logger.info(f"📊 Trade tracked in summary stats (no SMS sent)")
                        
                        # Notify strategy about position close (for AI strategies)
                        if hasattr(self.strategy, 'clear_position'):
                            self.strategy.clear_position()
                        
                        # Update trade result for dashboard
                        if hasattr(self.strategy, 'sentiment_tracker'):
                            result = 'profit' if profit > 0 else 'loss'
                            self.strategy.sentiment_tracker.update_trade_result(
                                self.symbol, result, profit_pct
                            )
                        
                        self.position = None
                        self.entry_price = None
                        self.trades_count += 1
                        self.profit_total += profit
                        
                        # CLEAR POSITION FILE (no longer in position)
                        self._clear_position_file()
                        
                        return True
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
        
        return False
    
    def check_and_send_summary(self):
        """Check if 6 hours have passed and send summary SMS"""
        current_time = time.time()
        time_elapsed = current_time - self.last_summary_time
        
        if time_elapsed >= self.summary_interval:
            self.logger.info("\n⏰ 6 hours elapsed - sending trading summary...")
            self.send_summary()
            
            # Reset timer and stats
            self.last_summary_time = current_time
            self.summary_stats = {
                'total_trades': 0,
                'buys': 0,
                'sells': 0,
                'total_profit': 0.0,
                'period_start_value': 0.0
            }
    
    def send_summary(self):
        """Generate and send trading summary SMS"""
        try:
            # Get current account value
            account_value = 0.0
            
            # Get USDT balance
            usdt_balance = self.client.get_account_balance('USDT')
            if usdt_balance:
                usdt_amount = float(usdt_balance.get('free', 0)) + float(usdt_balance.get('locked', 0))
                account_value += usdt_amount
                
            # Add value of crypto holdings
            crypto_asset = self.symbol.replace('USDT', '')
            crypto_balance = self.client.get_account_balance(crypto_asset)
            if crypto_balance:
                crypto_amount = float(crypto_balance.get('free', 0)) + float(crypto_balance.get('locked', 0))
                if crypto_amount > 0:
                    current_price = float(self.client.client.get_symbol_ticker(symbol=self.symbol)['price'])
                    crypto_value = crypto_amount * current_price
                    account_value += crypto_value
            
            # Get current positions
            positions = []
            if self.position:
                positions.append(self.symbol.replace('USDT', ''))
            
            # Calculate profit percentage
            profit_percent = 0.0
            if account_value > 0 and self.summary_stats['period_start_value'] > 0:
                profit_percent = ((account_value - self.summary_stats['period_start_value']) / self.summary_stats['period_start_value']) * 100
            
            summary_data = {
                'bot_name': self.bot_name,
                'period': '6 hours',
                'total_trades': self.summary_stats['total_trades'],
                'buys': self.summary_stats['buys'],
                'sells': self.summary_stats['sells'],
                'total_profit': self.summary_stats['total_profit'],
                'profit_percent': profit_percent,
                'current_positions': positions,
                'account_value': account_value
            }
            
            self.sms_notifier.send_summary(summary_data)
            self.logger.info(f"✅ Summary SMS sent successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error sending summary: {e}")
    
    def run(self):
        """Main trading loop"""
        self.logger.info("=" * 70)
        self.logger.info(f"🤖 STARTING BOT: {self.bot_name}")
        self.logger.info("=" * 70)
        self.logger.info(f"Symbol: {self.symbol}")
        self.logger.info(f"Strategy: {self.strategy_name}")
        self.logger.info(f"Trade Amount: ${self.trade_amount}")
        self.logger.info(f"Mode: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
        self.logger.info("=" * 70)
        
        # STARTUP: Force fresh news fetch on bot start (only for news-based strategies)
        if self.strategy_name in ['ticker_news', 'ai_autonomous']:
            self.logger.info("")
            self.logger.info("🚀 STARTUP: Fetching fresh news from CryptoNews API...")
            self.logger.info("⚠️  This will use 1 of 3 daily API calls")
            try:
                # Call generate_signal with force_fresh_news=True
                data = self.get_data(limit=100)
                if data:
                    startup_signal = self.strategy.generate_signal(
                        data, 
                        symbol=self.symbol, 
                        force_fresh_news=True
                    )
                    self.logger.info(f"✅ Startup analysis complete: {startup_signal.get('signal', 'HOLD')}")
            except Exception as e:
                self.logger.error(f"Startup fetch error: {e}")
            self.logger.info("")
        else:
            # For technical strategies (like volatile), skip news fetch
            self.logger.info("")
            self.logger.info(f"📊 Using {self.strategy_name} strategy (pure technical analysis - no news)")
            self.logger.info("")
        
        while True:
            try:
                # Get market data
                data = self.get_data(limit=100)
                if not data or len(data) == 0:
                    self.logger.warning("No data received, retrying...")
                    time.sleep(60)
                    continue
                
                # Extract current price from raw klines
                current_price = float(data[-1][4])  # Close price is index 4
                
                # Get signal using strategy's analyze() method
                # This handles indicator calculation internally
                signal_data = self.strategy.analyze(data)
                signal = signal_data['signal']
                
                # For AI strategies, check if symbol should change
                if 'recommended_symbol' in signal_data and signal_data['recommended_symbol'] != self.symbol:
                    new_symbol = signal_data['recommended_symbol']
                    
                    # Only switch if we DON'T have an active position
                    if not self.position:
                        self.logger.info(f"🔄 AI switching to new opportunity: {new_symbol}")
                        self.symbol = new_symbol
                        
                        # Update bot configuration file with new symbol
                        self._update_bot_symbol(new_symbol)
                        
                        # Re-fetch data for new symbol
                        data = self.get_data(limit=100)
                        if data:
                            current_price = float(data[-1][4])
                    else:
                        # Already have a position - stay focused on current coin
                        self.logger.info(f"📌 Staying focused on {self.symbol} (have position, ignoring {new_symbol})")
                        # Tell AI strategy to keep monitoring current symbol
                        if hasattr(self.strategy, 'set_symbol'):
                            self.strategy.set_symbol(self.symbol)
                
                # Log status
                if self.position:
                    profit = (current_price - self.entry_price) / self.entry_price * 100
                    self.logger.info(f"📊 Position: LONG @ ${self.entry_price:.2f} | Current: ${current_price:.2f} | P&L: {profit:+.2f}%")
                else:
                    self.logger.info(f"⏳ Waiting for signal... (Current: {signal}, Price: ${current_price:.2f})")
                
                # Check stop loss / take profit (skip if strategy manages them)
                if self.position and not hasattr(self.strategy, 'current_position'):
                    if current_price <= self.stop_loss:
                        self.logger.warning("⚠️ Stop loss triggered!")
                        self.execute_trade('SELL', current_price, signal_data)
                    elif current_price >= self.take_profit:
                        self.logger.info("🎯 Take profit reached!")
                        self.execute_trade('SELL', current_price, signal_data)
                
                # Execute signals
                if signal in ['BUY', 'SELL']:
                    self.execute_trade(signal, current_price, signal_data)
                
                # Check if 6 hours passed and send summary
                self.check_and_send_summary()
                
                # Wait before next check
                # 60 = 1 minute, 300 = 5 minutes, 900 = 15 minutes, 3600 = 1 hour
                time.sleep(900)  # Check every 15 minutes
            
            except KeyboardInterrupt:
                self.logger.info("\n⏹️ Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(900)  # Wait 15 minutes before retry
        
        # Summary
        self.logger.info("=" * 70)
        self.logger.info("📊 BOT SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total Trades: {self.trades_count}")
        self.logger.info(f"Total Profit: ${self.profit_total:.2f}")
        self.logger.info("=" * 70)


if __name__ == '__main__':
    # Parse command line args
    # Usage: python integrated_trader.py BOT_ID BOT_NAME SYMBOL STRATEGY AMOUNT
    
    if len(sys.argv) != 6:
        print("Usage: python integrated_trader.py <bot_id> <bot_name> <symbol> <strategy> <amount>")
        print("Example: python integrated_trader.py 1 'BTC Bot' BTCUSDT simple_profitable 100")
        sys.exit(1)
    
    bot_id = int(sys.argv[1])
    bot_name = sys.argv[2]
    symbol = sys.argv[3]
    strategy = sys.argv[4]
    amount = float(sys.argv[5])
    
    try:
        Config.validate()
        bot = BotRunner(bot_id, bot_name, symbol, strategy, amount)
        bot.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
