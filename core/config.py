"""
Trading Bot Configuration
==========================

This file manages all settings for your trading bot.
Everything is loaded from your .env file for security.

What's Configured Here:
- Binance API credentials
- Trading preferences (how much to invest, which coins)
- Strategy parameters (technical indicators)
- Risk management (stop losses, take profits)

Author: Trading Bot
"""

import os
from dotenv import load_dotenv

# Load settings from .env file
load_dotenv()


class Config:
    """
    All bot settings in one place
    
    This class reads your .env file and provides easy access to all settings.
    You should NEVER hardcode API keys or secrets in your code!
    """
    
    # =================================================================
    # BINANCE API CREDENTIALS
    # =================================================================
    # These are your keys to access Binance. Keep them secret!
    # Get these from: https://www.binance.com/en/my/settings/api-management
    
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # IMPORTANT: Always start with testnet = true!
    # Testnet = fake money (safe for learning)
    # Mainnet = real money (only use when confident)
    USE_TESTNET = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    
    # =================================================================
    # TRADING SETTINGS
    # =================================================================
    
    # Which cryptocurrency pair to trade
    # Examples: BTCUSDT (Bitcoin), ETHUSDT (Ethereum), DOGEUSDT (Dogecoin)
    TRADING_SYMBOL = os.getenv('TRADING_SYMBOL', 'BTCUSDT')
    
    # How much to invest per trade (in the first currency of the pair)
    # For BTCUSDT: this is amount of Bitcoin
    # For safety, start with very small amounts!
    TRADE_AMOUNT = float(os.getenv('TRADE_AMOUNT', '0.001'))
    
    # How often to check for trading signals (seconds)
    # 60 = check every minute
    # 300 = check every 5 minutes
    # 900 = check every 15 minutes (recommended for live trading)
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '900'))
    
    # =================================================================
    # TECHNICAL ANALYSIS SETTINGS
    # =================================================================
    # These control how the bot analyzes price movements
    
    # RSI (Relative Strength Index) - Measures if price is overbought/oversold
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))  # How many candles to analyze
    RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))  # Above this = overbought (sell signal)
    RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))  # Below this = oversold (buy signal)
    
    # Momentum - Measures price change speed
    MOMENTUM_PERIOD = int(os.getenv('MOMENTUM_PERIOD', '10'))  # Candles to measure momentum
    
    # =================================================================
    # RISK MANAGEMENT
    # =================================================================
    # These settings protect your money
    
    # Maximum position size (as decimal of your balance)
    # 0.01 = use maximum 1% of your account per trade
    # 0.1 = use maximum 10% of your account per trade
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.01'))
    
    # Stop Loss - Automatically sell if price drops this much (%)
    # 2.0 = sell if price drops 2% below buy price
    # This limits your losses on bad trades
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))
    
    # Take Profit - Automatically sell when you gain this much (%)
    # 5.0 = sell if price rises 5% above buy price
    # This locks in your profits
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '5.0'))
    
    # =================================================================
    # OPTIONAL: SMS NOTIFICATIONS (Twilio)
    # =================================================================
    # Get SMS alerts when your bot makes trades
    # Sign up at https://www.twilio.com
    
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    YOUR_PHONE_NUMBER = os.getenv('YOUR_PHONE_NUMBER', '')
    
    # =================================================================
    # VALIDATION METHODS
    # =================================================================
    
    @classmethod
    def validate(cls):
        """
        Check that all required settings are configured
        
        This runs before the bot starts to make sure everything is set up correctly.
        
        Returns:
            bool: True if config is valid
        
        Raises:
            ValueError: If required settings are missing
        """
        # Check API credentials
        if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
            raise ValueError(
                "❌ Missing Binance API credentials!\n"
                "   Add BINANCE_API_KEY and BINANCE_API_SECRET to your .env file\n"
                "   Get keys from: https://www.binance.com/en/my/settings/api-management"
            )
        
        # Check trade amount
        if cls.TRADE_AMOUNT <= 0:
            raise ValueError(
                "❌ TRADE_AMOUNT must be greater than 0\n"
                f"   Current value: {cls.TRADE_AMOUNT}"
            )
        
        # Check percentages are reasonable
        if cls.STOP_LOSS_PERCENT <= 0 or cls.STOP_LOSS_PERCENT > 50:
            raise ValueError(
                "❌ STOP_LOSS_PERCENT should be between 0 and 50\n"
                f"   Current value: {cls.STOP_LOSS_PERCENT}%"
            )
        
        if cls.TAKE_PROFIT_PERCENT <= 0 or cls.TAKE_PROFIT_PERCENT > 100:
            raise ValueError(
                "❌ TAKE_PROFIT_PERCENT should be between 0 and 100\n"
                f"   Current value: {cls.TAKE_PROFIT_PERCENT}%"
            )
        
        return True
    
    @classmethod
    def print_config(cls):
        """
        Display all current settings (hides sensitive data)
        
        Useful for checking your configuration before starting the bot.
        """
        print("\n" + "="*70)
        print("🤖 TRADING BOT CONFIGURATION")
        print("="*70)
        
        # Connection
        print("\n📡 CONNECTION:")
        print(f"   Mode: {'🧪 TESTNET (Fake Money)' if cls.USE_TESTNET else '💰 MAINNET (REAL MONEY!)'}")
        api_key_display = f"{'*' * 10}{cls.BINANCE_API_KEY[-4:]}" if cls.BINANCE_API_KEY else '❌ NOT SET'
        print(f"   API Key: {api_key_display}")
        
        # Trading
        print("\n💱 TRADING:")
        print(f"   Symbol: {cls.TRADING_SYMBOL}")
        print(f"   Trade Amount: {cls.TRADE_AMOUNT}")
        print(f"   Check Interval: {cls.CHECK_INTERVAL}s ({cls.CHECK_INTERVAL/60:.1f} minutes)")
        
        # Technical Analysis
        print("\n📊 TECHNICAL ANALYSIS:")
        print(f"   RSI Period: {cls.RSI_PERIOD}")
        print(f"   RSI Overbought: {cls.RSI_OVERBOUGHT}")
        print(f"   RSI Oversold: {cls.RSI_OVERSOLD}")
        print(f"   Momentum Period: {cls.MOMENTUM_PERIOD}")
        
        # Risk Management
        print("\n🛡️ RISK MANAGEMENT:")
        print(f"   Max Position Size: {cls.MAX_POSITION_SIZE * 100}% of account")
        print(f"   Stop Loss: {cls.STOP_LOSS_PERCENT}%")
        print(f"   Take Profit: {cls.TAKE_PROFIT_PERCENT}%")
        
        # SMS
        if cls.TWILIO_ACCOUNT_SID:
            print("\n📱 SMS NOTIFICATIONS: Enabled")
        else:
            print("\n📱 SMS NOTIFICATIONS: Disabled (optional)")
        
        print("\n" + "="*70 + "\n")
    
    @classmethod
    def get_summary(cls):
        """
        Get a simple one-line summary of current mode
        
        Returns:
            str: Summary string
        """
        mode = "Testnet" if cls.USE_TESTNET else "LIVE"
        return f"{cls.TRADING_SYMBOL} | Amount: {cls.TRADE_AMOUNT} | Mode: {mode}"
