"""
Configuration manager for the trading bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class to manage all bot settings"""
    
    # Binance API Credentials
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    USE_TESTNET = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    
    # Trading Parameters
    TRADING_SYMBOL = os.getenv('TRADING_SYMBOL', 'BTCUSDT')
    TRADE_AMOUNT = float(os.getenv('TRADE_AMOUNT', '0.001'))
    
    # Momentum Strategy Parameters
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))
    RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))
    MOMENTUM_PERIOD = int(os.getenv('MOMENTUM_PERIOD', '10'))
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
    
    # Risk Management
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.01'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '5.0'))
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is set"""
        if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env file")
        
        if cls.TRADE_AMOUNT <= 0:
            raise ValueError("TRADE_AMOUNT must be greater than 0")
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (hiding sensitive data)"""
        print("\n=== Trading Bot Configuration ===")
        print(f"Trading Symbol: {cls.TRADING_SYMBOL}")
        print(f"Trade Amount: {cls.TRADE_AMOUNT}")
        print(f"Using Testnet: {cls.USE_TESTNET}")
        print(f"RSI Period: {cls.RSI_PERIOD}")
        print(f"RSI Overbought: {cls.RSI_OVERBOUGHT}")
        print(f"RSI Oversold: {cls.RSI_OVERSOLD}")
        print(f"Momentum Period: {cls.MOMENTUM_PERIOD}")
        print(f"Check Interval: {cls.CHECK_INTERVAL}s")
        print(f"Stop Loss: {cls.STOP_LOSS_PERCENT}%")
        print(f"Take Profit: {cls.TAKE_PROFIT_PERCENT}%")
        print(f"API Key: {'*' * 10}{cls.BINANCE_API_KEY[-4:] if cls.BINANCE_API_KEY else 'NOT SET'}")
        print("================================\n")

