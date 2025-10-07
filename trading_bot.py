"""
Main trading bot implementation
"""
import time
import logging
from datetime import datetime
from binance_client import BinanceClient
from momentum_strategy import MomentumStrategy
from position_manager import PositionManager
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        """Initialize the trading bot"""
        logger.info("=" * 60)
        logger.info("Initializing Trading Bot...")
        logger.info("=" * 60)
        
        # Validate configuration
        Config.validate()
        Config.print_config()
        
        # Initialize components
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        
        self.strategy = MomentumStrategy(
            rsi_period=Config.RSI_PERIOD,
            rsi_overbought=Config.RSI_OVERBOUGHT,
            rsi_oversold=Config.RSI_OVERSOLD,
            momentum_period=Config.MOMENTUM_PERIOD
        )
        
        self.position_manager = PositionManager(
            stop_loss_percent=Config.STOP_LOSS_PERCENT,
            take_profit_percent=Config.TAKE_PROFIT_PERCENT
        )
        
        self.symbol = Config.TRADING_SYMBOL
        self.trade_amount = Config.TRADE_AMOUNT
        self.check_interval = Config.CHECK_INTERVAL
        
        self.is_running = False
        self.trade_history = []
        
        logger.info("Trading Bot initialized successfully")
    
    def test_connection(self):
        """Test connection to Binance"""
        logger.info("Testing connection to Binance...")
        return self.client.test_connection()
    
    def get_account_info(self):
        """Get and display account information"""
        balance = self.client.get_account_balance('USDT')
        if balance:
            logger.info(f"Account Balance - USDT: {balance['free']:.2f} (Free), {balance['locked']:.2f} (Locked)")
        
        current_price = self.client.get_current_price(self.symbol)
        if current_price:
            logger.info(f"Current {self.symbol} price: {current_price:.2f}")
        
        return balance, current_price
    
    def execute_trade(self, signal, current_price):
        """
        Execute trade based on signal
        
        Args:
            signal: Trading signal dict
            current_price: Current market price
        """
        signal_type = signal['signal']
        confidence = signal['confidence']
        
        # Require minimum confidence to trade
        if confidence < 50:
            logger.info(f"Signal confidence too low ({confidence}%), skipping trade")
            return
        
        # Handle BUY signal
        if signal_type == 'BUY' and not self.position_manager.has_position():
            logger.info(f"BUY signal detected with {confidence}% confidence")
            logger.info(f"Reasons: {', '.join(signal['reasons'])}")
            
            # Calculate quantity based on current price
            quantity = self.trade_amount
            
            # Place market buy order
            order = self.client.place_market_order(self.symbol, 'BUY', quantity)
            
            if order:
                # Open position in position manager
                fill_price = current_price  # In real scenario, get from order response
                self.position_manager.open_position(self.symbol, 'BUY', quantity, fill_price)
                
                logger.info(f"✓ BUY order executed: {quantity} {self.symbol} @ {fill_price:.2f}")
            else:
                logger.error("✗ Failed to execute BUY order")
        
        # Handle SELL signal
        elif signal_type == 'SELL' and self.position_manager.has_position():
            position = self.position_manager.get_position_info()
            
            if position['side'] == 'BUY':
                logger.info(f"SELL signal detected with {confidence}% confidence")
                logger.info(f"Reasons: {', '.join(signal['reasons'])}")
                
                # Place market sell order to close position
                quantity = position['quantity']
                order = self.client.place_market_order(self.symbol, 'SELL', quantity)
                
                if order:
                    # Close position
                    closed_position = self.position_manager.close_position(current_price, 'Signal')
                    self.trade_history.append(closed_position)
                    
                    logger.info(f"✓ SELL order executed: {quantity} {self.symbol} @ {current_price:.2f}")
                else:
                    logger.error("✗ Failed to execute SELL order")
    
    def check_risk_management(self, current_price):
        """
        Check risk management conditions
        
        Args:
            current_price: Current market price
        """
        if not self.position_manager.has_position():
            return
        
        # Check stop loss and take profit
        should_exit, reason = self.position_manager.check_exit_conditions(current_price)
        
        if should_exit:
            position = self.position_manager.get_position_info()
            logger.warning(f"Risk Management Exit: {reason}")
            
            # Place market sell order to close position
            quantity = position['quantity']
            order = self.client.place_market_order(self.symbol, 'SELL', quantity)
            
            if order:
                closed_position = self.position_manager.close_position(current_price, reason)
                self.trade_history.append(closed_position)
                logger.info(f"✓ Position closed via risk management")
            else:
                logger.error("✗ Failed to execute risk management exit")
    
    def print_status(self, signal, current_price):
        """
        Print current bot status
        
        Args:
            signal: Latest trading signal
            current_price: Current market price
        """
        print("\n" + "=" * 80)
        print(f"Status Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"Symbol: {self.symbol} | Price: {current_price:.2f}")
        print(f"Signal: {signal['signal']} | Confidence: {signal['confidence']}%")
        print(f"Indicators: RSI={signal['indicators']['rsi']:.2f}, "
              f"Momentum={signal['indicators']['momentum']:.2f}%, "
              f"Trend={'UP' if signal['indicators']['trend'] == 1 else 'DOWN'}")
        
        if self.position_manager.has_position():
            position = self.position_manager.get_position_info()
            unrealized_pnl = self.position_manager.calculate_unrealized_pnl(current_price)
            print(f"\n📊 Open Position: {position['side']} {position['quantity']} @ {position['entry_price']:.2f}")
            print(f"   Unrealized P&L: {unrealized_pnl:+.2f}%")
            print(f"   Stop Loss: {position['stop_loss']:.2f} | Take Profit: {position['take_profit']:.2f}")
        else:
            print("\n📊 No open position")
        
        print(f"\nTotal Trades: {len(self.trade_history)}")
        if self.trade_history:
            total_pnl = sum(trade['pnl_percent'] for trade in self.trade_history)
            winning_trades = sum(1 for trade in self.trade_history if trade['pnl_percent'] > 0)
            print(f"Win Rate: {(winning_trades/len(self.trade_history)*100):.1f}%")
            print(f"Total P&L: {total_pnl:+.2f}%")
        
        print("=" * 80 + "\n")
    
    def run(self):
        """Main trading loop"""
        logger.info("Starting trading bot...")
        
        # Test connection
        if not self.test_connection():
            logger.error("Connection test failed. Exiting...")
            return
        
        # Get initial account info
        self.get_account_info()
        
        self.is_running = True
        
        try:
            while self.is_running:
                try:
                    # Get market data
                    klines = self.client.get_klines(
                        symbol=self.symbol,
                        interval='5m',  # 5-minute candles
                        limit=100
                    )
                    
                    if not klines:
                        logger.error("Failed to get market data")
                        time.sleep(self.check_interval)
                        continue
                    
                    # Get current price
                    current_price = self.client.get_current_price(self.symbol)
                    
                    if not current_price:
                        logger.error("Failed to get current price")
                        time.sleep(self.check_interval)
                        continue
                    
                    # Analyze market with strategy
                    signal = self.strategy.analyze(klines)
                    
                    # Check risk management first
                    self.check_risk_management(current_price)
                    
                    # Execute trades based on signal
                    self.execute_trade(signal, current_price)
                    
                    # Print status
                    self.print_status(signal, current_price)
                    
                    # Wait before next check
                    time.sleep(self.check_interval)
                
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}", exc_info=True)
                    time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received...")
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.is_running = False
        
        # Close any open positions
        if self.position_manager.has_position():
            logger.warning("Closing open position...")
            current_price = self.client.get_current_price(self.symbol)
            position = self.position_manager.get_position_info()
            
            if current_price:
                order = self.client.place_market_order(self.symbol, 'SELL', position['quantity'])
                if order:
                    closed_position = self.position_manager.close_position(current_price, 'Bot Shutdown')
                    self.trade_history.append(closed_position)
                    logger.info("Position closed successfully")
        
        # Print final statistics
        logger.info("\n" + "=" * 60)
        logger.info("Trading Session Summary")
        logger.info("=" * 60)
        logger.info(f"Total Trades: {len(self.trade_history)}")
        
        if self.trade_history:
            total_pnl = sum(trade['pnl_percent'] for trade in self.trade_history)
            winning_trades = sum(1 for trade in self.trade_history if trade['pnl_percent'] > 0)
            losing_trades = len(self.trade_history) - winning_trades
            
            logger.info(f"Winning Trades: {winning_trades}")
            logger.info(f"Losing Trades: {losing_trades}")
            logger.info(f"Win Rate: {(winning_trades/len(self.trade_history)*100):.1f}%")
            logger.info(f"Total P&L: {total_pnl:+.2f}%")
            
            if winning_trades > 0:
                avg_win = sum(trade['pnl_percent'] for trade in self.trade_history if trade['pnl_percent'] > 0) / winning_trades
                logger.info(f"Average Win: {avg_win:.2f}%")
            
            if losing_trades > 0:
                avg_loss = sum(trade['pnl_percent'] for trade in self.trade_history if trade['pnl_percent'] < 0) / losing_trades
                logger.info(f"Average Loss: {avg_loss:.2f}%")
        
        logger.info("=" * 60)
        logger.info("Trading bot stopped successfully")


def main():
    """Main entry point"""
    bot = TradingBot()
    bot.run()


if __name__ == '__main__':
    main()

