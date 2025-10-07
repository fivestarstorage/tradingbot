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
    
    def get_data(self, limit=100):
        """Fetch recent klines - return raw format for strategy.analyze()"""
        klines = self.client.get_klines(self.symbol, interval='5m', limit=limit)
        return klines if klines else []
    
    def execute_trade(self, signal, current_price, signal_data=None):
        """Execute buy/sell orders"""
        try:
            if signal == 'BUY' and not self.position:
                # Calculate quantity
                quantity = self.trade_amount / current_price
                
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
                    
                    # Notify strategy about position (for AI strategies)
                    if hasattr(self.strategy, 'set_position'):
                        self.strategy.set_position(self.symbol, current_price)
                    
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
                    quantity = balance['free']
                    
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
                        
                        self.position = None
                        self.entry_price = None
                        self.trades_count += 1
                        self.profit_total += profit
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
