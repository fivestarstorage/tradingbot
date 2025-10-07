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

# Strategy mapping
STRATEGIES = {
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
        
        # Setup logging
        log_file = f'bot_{bot_id}_{datetime.now().strftime("%Y%m%d")}.log'
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
        
        # Initialize SMS notifier
        self.sms_notifier = TwilioNotifier()
        
        # Position persistence file
        self.position_file = f'bot_{self.bot_id}_position.json'
        self._load_position()
    
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
                    self.logger.info("=" * 70)
                    self.logger.info(f"📂 LOADED EXISTING POSITION FROM FILE")
                    self.logger.info(f"   Symbol: {self.symbol}")
                    self.logger.info(f"   Entry: ${self.entry_price:.2f}")
                    self.logger.info(f"   Stop Loss: ${self.stop_loss:.2f}")
                    self.logger.info(f"   Take Profit: ${self.take_profit:.2f}")
                    self.logger.info("=" * 70)
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
            
            if not symbol_info:
                # Default to 6 decimal places if can't get info
                return float(f"{quantity:.6f}")
            
            # Find LOT_SIZE filter
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_item['stepSize'])
                    
                    # Calculate precision from step_size
                    # e.g., 0.00001 -> 5 decimal places
                    precision = 0
                    if step_size < 1:
                        precision = len(str(step_size).rstrip('0').split('.')[1])
                    
                    # Round quantity to the correct precision
                    formatted = round(quantity, precision)
                    
                    # Remove trailing zeros
                    if precision > 0:
                        formatted = float(f"{formatted:.{precision}f}")
                    
                    self.logger.info(f"Formatted quantity: {quantity} -> {formatted} (precision: {precision})")
                    return formatted
            
            # If no LOT_SIZE filter found, use 6 decimals
            return float(f"{quantity:.6f}")
            
        except Exception as e:
            self.logger.error(f"Error formatting quantity: {e}, using 6 decimals")
            return float(f"{quantity:.6f}")
    
    def execute_trade(self, signal, current_price, signal_data=None):
        """Execute buy/sell orders"""
        try:
            if signal == 'BUY' and not self.position:
                # Calculate quantity
                raw_quantity = self.trade_amount / current_price
                
                # Format quantity to match Binance precision rules
                quantity = self.format_quantity(self.symbol, raw_quantity)
                
                # Place order
                order = self.client.place_market_order(
                    symbol=self.symbol,
                    side='BUY',
                    quantity=quantity
                )
                
                if order:
                    self.position = 'LONG'
                    self.entry_price = current_price
                    self.stop_loss = current_price * 0.98  # 2% stop loss
                    self.take_profit = current_price * 1.03  # 3% take profit
                    
                    # SAVE POSITION TO FILE (persists across restarts!)
                    self._save_position()
                    
                    # Notify strategy about position (for AI strategies)
                    if hasattr(self.strategy, 'set_position'):
                        self.strategy.set_position(self.symbol, current_price)
                    
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
                    
                    # Send SMS notification
                    self.sms_notifier.send_trade_notification({
                        'action': 'BUY',
                        'symbol': self.symbol,
                        'price': current_price,
                        'quantity': quantity,
                        'amount': self.trade_amount,
                        'bot_name': self.bot_name
                    })
                    
                    return True
            
            elif signal == 'SELL' and self.position:
                # Get current balance
                balance = self.client.get_account_balance(self.symbol.replace('USDT', ''))
                if balance and balance['free'] > 0:
                    raw_quantity = balance['free']
                    
                    # Format quantity to match Binance precision rules
                    quantity = self.format_quantity(self.symbol, raw_quantity)
                    
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
                        
                        # Send SMS notification
                        self.sms_notifier.send_trade_notification({
                            'action': 'SELL',
                            'symbol': self.symbol,
                            'price': current_price,
                            'quantity': quantity,
                            'amount': current_price * quantity,
                            'profit': profit,
                            'profit_percent': profit_pct,
                            'bot_name': self.bot_name
                        })
                        
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
        
        # STARTUP: Force fresh news fetch on bot start (uses 1/3 daily calls)
        if hasattr(self.strategy, 'generate_signal'):
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
                    self.logger.info(f"🔄 AI switched to: {new_symbol}")
                    self.symbol = new_symbol
                    # Re-fetch data for new symbol
                    data = self.get_data(limit=100)
                    if data:
                        current_price = float(data[-1][4])
                
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
                
                # Wait before next check
                time.sleep(60)
            
            except KeyboardInterrupt:
                self.logger.info("\n⏹️ Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(60)
        
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
