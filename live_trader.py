"""
Live Trading Launcher - Deploy Your Strategy to Binance

Features:
- Choose which strategy to run
- Set your trading amount
- Automatic execution
- Safety features
- Emergency stop
"""
import sys
import time
import logging
from datetime import datetime
from binance_client import BinanceClient
from config import Config

# Import all strategies
from strategies.simple_profitable_strategy import SimpleProfitableStrategy
from strategies.enhanced_strategy import EnhancedStrategy
from strategies.volatile_coins_strategy import VolatileCoinsStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.conservative_strategy import ConservativeStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'live_trading_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Available strategies
STRATEGIES = {
    '1': {'name': 'Simple Profitable ⭐', 'class': SimpleProfitableStrategy, 'recommended': True},
    '2': {'name': 'Enhanced Momentum', 'class': EnhancedStrategy},
    '3': {'name': 'Volatile Coins', 'class': VolatileCoinsStrategy},
    '4': {'name': 'Mean Reversion', 'class': MeanReversionStrategy},
    '5': {'name': 'Breakout', 'class': BreakoutStrategy},
    '6': {'name': 'Conservative', 'class': ConservativeStrategy}
}


class LiveTrader:
    """Live trading bot with safety features"""
    
    def __init__(self, strategy_class, symbol, trade_amount_usdt, check_interval=60):
        """
        Initialize live trader
        
        Args:
            strategy_class: Strategy class to use
            symbol: Trading pair (e.g., 'BTCUSDT')
            trade_amount_usdt: Amount in USDT to trade per position
            check_interval: Seconds between checks (default 60)
        """
        self.symbol = symbol
        self.trade_amount_usdt = trade_amount_usdt
        self.check_interval = check_interval
        
        # Initialize strategy
        self.strategy = strategy_class()
        
        # Initialize Binance client
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        
        # Trading state
        self.position = None
        self.trades = []
        self.is_running = False
        self.total_profit = 0
        
        logger.info("=" * 70)
        logger.info(f"Live Trader Initialized")
        logger.info(f"Strategy: {self.strategy.name if hasattr(self.strategy, 'name') else 'Custom'}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Trade Amount: ${trade_amount_usdt} USDT")
        logger.info(f"Check Interval: {check_interval}s")
        logger.info(f"Using: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
        logger.info("=" * 70)
    
    def get_account_balance(self):
        """Get USDT balance"""
        balance = self.client.get_account_balance('USDT')
        if balance:
            return balance['free']
        return 0
    
    def get_current_price(self):
        """Get current market price"""
        return self.client.get_current_price(self.symbol)
    
    def fetch_data(self):
        """Fetch recent candle data"""
        # Fetch last 200 candles (enough for indicators)
        klines = self.client.get_klines(
            symbol=self.symbol,
            interval='5m',  # 5-minute candles
            limit=200
        )
        return klines
    
    def check_position_exit(self, current_price):
        """Check if we should exit current position"""
        if not self.position:
            return False, None
        
        entry_price = self.position['entry_price']
        stop_loss = self.position['stop_loss']
        take_profit = self.position['take_profit']
        
        # Check stop loss
        if current_price <= stop_loss:
            return True, "Stop Loss"
        
        # Check take profit
        if current_price >= take_profit:
            return True, "Take Profit"
        
        return False, None
    
    def open_position(self, price, signal):
        """Open a new position"""
        try:
            # Calculate quantity
            quantity = self.trade_amount_usdt / price
            
            # Place market buy order
            order = self.client.place_market_order(self.symbol, 'BUY', quantity)
            
            if order:
                # Get risk management from signal
                risk = signal.get('risk', {})
                stop_loss = risk.get('stop_loss', price * 0.95)
                take_profit = risk.get('take_profit', price * 1.10)
                
                self.position = {
                    'entry_price': price,
                    'entry_time': datetime.now(),
                    'quantity': quantity,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'order': order
                }
                
                logger.info(f"✅ OPENED POSITION: BUY {quantity:.8f} {self.symbol} @ ${price:.2f}")
                logger.info(f"   Stop Loss: ${stop_loss:.2f} | Take Profit: ${take_profit:.2f}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to open position: {e}")
        
        return False
    
    def close_position(self, price, reason):
        """Close current position"""
        if not self.position:
            return False
        
        try:
            quantity = self.position['quantity']
            entry_price = self.position['entry_price']
            
            # Place market sell order
            order = self.client.place_market_order(self.symbol, 'SELL', quantity)
            
            if order:
                # Calculate P&L
                profit_usdt = (price - entry_price) * quantity
                profit_percent = ((price - entry_price) / entry_price) * 100
                
                trade = {
                    'entry_time': self.position['entry_time'],
                    'exit_time': datetime.now(),
                    'entry_price': entry_price,
                    'exit_price': price,
                    'quantity': quantity,
                    'profit_usdt': profit_usdt,
                    'profit_percent': profit_percent,
                    'reason': reason
                }
                
                self.trades.append(trade)
                self.total_profit += profit_usdt
                
                logger.info(f"✅ CLOSED POSITION: SELL {quantity:.8f} {self.symbol} @ ${price:.2f}")
                logger.info(f"   Profit: ${profit_usdt:+.2f} ({profit_percent:+.2f}%) | Reason: {reason}")
                logger.info(f"   Total Profit: ${self.total_profit:+.2f}")
                
                self.position = None
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
        
        return False
    
    def run(self):
        """Main trading loop"""
        logger.info("\n🚀 Starting live trading...")
        logger.info("Press Ctrl+C to stop\n")
        
        # Test connection
        if not self.client.test_connection():
            logger.error("❌ Connection test failed. Exiting.")
            return
        
        # Check balance
        balance = self.get_account_balance()
        logger.info(f"💰 Available Balance: ${balance:.2f} USDT")
        
        if balance < self.trade_amount_usdt:
            logger.error(f"❌ Insufficient balance (need ${self.trade_amount_usdt}, have ${balance:.2f})")
            return
        
        self.is_running = True
        
        try:
            while self.is_running:
                try:
                    # Fetch latest data
                    klines = self.fetch_data()
                    current_price = self.get_current_price()
                    
                    if not klines or not current_price:
                        logger.warning("Failed to fetch data, retrying...")
                        time.sleep(10)
                        continue
                    
                    # Generate signal
                    signal = self.strategy.analyze(klines)
                    
                    # Check if we have a position
                    if self.position:
                        # Check if we should exit
                        should_exit, reason = self.check_position_exit(current_price)
                        
                        if should_exit:
                            self.close_position(current_price, reason)
                        elif signal['signal'] == 'SELL' and signal['confidence'] >= 50:
                            self.close_position(current_price, "Sell Signal")
                        else:
                            # Update status
                            entry_price = self.position['entry_price']
                            unrealized_pnl = ((current_price - entry_price) / entry_price) * 100
                            logger.info(f"📊 Position Open: ${current_price:.2f} | Unrealized: {unrealized_pnl:+.2f}%")
                    
                    else:
                        # Check for entry signal
                        if signal['signal'] == 'BUY' and signal['confidence'] >= 50:
                            logger.info(f"🎯 BUY Signal Detected (Confidence: {signal['confidence']}%)")
                            logger.info(f"   Reasons: {', '.join(signal['reasons'][:3])}")
                            self.open_position(current_price, signal)
                        else:
                            logger.info(f"⏳ Waiting for signal... (Current: {signal['signal']}, Price: ${current_price:.2f})")
                    
                    # Sleep until next check
                    time.sleep(self.check_interval)
                
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}")
                    time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("\n🛑 Stop signal received...")
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop trading and cleanup"""
        logger.info("Stopping live trading...")
        self.is_running = False
        
        # Close any open position
        if self.position:
            logger.warning("Closing open position...")
            current_price = self.get_current_price()
            if current_price:
                self.close_position(current_price, "Bot Stopped")
        
        # Print summary
        self.print_summary()
        
        logger.info("✅ Live trading stopped")
    
    def print_summary(self):
        """Print trading summary"""
        logger.info("\n" + "=" * 70)
        logger.info("TRADING SESSION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total Trades: {len(self.trades)}")
        
        if self.trades:
            wins = [t for t in self.trades if t['profit_usdt'] > 0]
            losses = [t for t in self.trades if t['profit_usdt'] <= 0]
            
            logger.info(f"Winning Trades: {len(wins)}")
            logger.info(f"Losing Trades: {len(losses)}")
            logger.info(f"Win Rate: {len(wins)/len(self.trades)*100:.1f}%")
            logger.info(f"Total Profit: ${self.total_profit:+.2f}")
            
            if wins:
                avg_win = sum(t['profit_percent'] for t in wins) / len(wins)
                logger.info(f"Average Win: {avg_win:+.2f}%")
            
            if losses:
                avg_loss = sum(t['profit_percent'] for t in losses) / len(losses)
                logger.info(f"Average Loss: {avg_loss:+.2f}%")
        
        logger.info("=" * 70)


def main():
    """Main entry point"""
    print("=" * 70)
    print("🚀 LIVE TRADING LAUNCHER")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will trade with REAL money!")
    print("   Make sure you've backtested thoroughly first.")
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Show testnet status
    if Config.USE_TESTNET:
        print("✅ Using TESTNET (safe - fake money)")
    else:
        print("⚠️  Using MAINNET (real money!)")
        confirm = input("\n   Are you sure? This is REAL trading! (type 'YES'): ").strip()
        if confirm != 'YES':
            print("❌ Cancelled for safety")
            return
    
    print()
    
    # Select strategy
    print("SELECT STRATEGY:")
    print("-" * 70)
    for key, strat in STRATEGIES.items():
        rec = " ⭐ RECOMMENDED" if strat.get('recommended') else ""
        print(f"{key}. {strat['name']}{rec}")
    print("-" * 70)
    
    strategy_choice = input("\nChoose strategy (1-6) [1]: ").strip() or '1'
    
    if strategy_choice not in STRATEGIES:
        print("❌ Invalid choice")
        return
    
    strategy_info = STRATEGIES[strategy_choice]
    print(f"✓ Selected: {strategy_info['name']}")
    
    # Select coin
    symbol = input("\nTrading symbol (e.g., BTCUSDT): ").strip().upper()
    if not symbol:
        symbol = 'BTCUSDT'
    print(f"✓ Trading: {symbol}")
    
    # Set amount
    print("\nTRADE AMOUNT:")
    amount = input("Amount in USDT per trade [100]: ").strip()
    try:
        trade_amount = float(amount) if amount else 100
    except:
        print("❌ Invalid amount")
        return
    
    if trade_amount < 10:
        print("❌ Minimum $10 USDT required")
        return
    
    print(f"✓ Trade Amount: ${trade_amount:.2f} USDT per position")
    
    # Check interval
    interval = input("\nCheck interval in seconds [60]: ").strip()
    try:
        check_interval = int(interval) if interval else 60
    except:
        check_interval = 60
    
    print(f"✓ Check every {check_interval} seconds")
    
    # Final confirmation
    print("\n" + "=" * 70)
    print("CONFIGURATION:")
    print("-" * 70)
    print(f"Strategy:      {strategy_info['name']}")
    print(f"Symbol:        {symbol}")
    print(f"Amount:        ${trade_amount:.2f} USDT per trade")
    print(f"Check Every:   {check_interval}s")
    print(f"Mode:          {'TESTNET' if Config.USE_TESTNET else 'MAINNET ⚠️'}")
    print("=" * 70)
    print()
    
    confirm = input("Start live trading? (yes/no) [no]: ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Initialize and run trader
    trader = LiveTrader(
        strategy_class=strategy_info['class'],
        symbol=symbol,
        trade_amount_usdt=trade_amount,
        check_interval=check_interval
    )
    
    trader.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
