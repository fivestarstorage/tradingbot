"""
Binance API Client
==================

This module handles all communication with the Binance cryptocurrency exchange.
It provides simple methods for checking balances, placing trades, and getting market data.

Key Features:
- Connect to Binance (testnet or real trading)
- Check account balances
- Place buy/sell orders
- Get price data and charts
- Validate trading symbols

Author: Trading Bot
"""

from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Simplified Binance API wrapper
    
    This class makes it easy to interact with Binance without dealing with
    complex API details. Perfect for automated trading bots.
    """
    
    def __init__(self, api_key, api_secret, testnet=False):
        """
        Connect to Binance
        
        Args:
            api_key (str): Your Binance API key
            api_secret (str): Your Binance API secret key
            testnet (bool): If True, use fake money for testing. If False, real trading!
        
        Example:
            client = BinanceClient(
                api_key="your_key", 
                api_secret="your_secret",
                testnet=True  # Always start with testnet!
            )
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            if testnet:
                self.client.API_URL = 'https://testnet.binance.vision/api'
            
            mode = "TESTNET (Fake Money)" if testnet else "MAINNET (Real Money!)"
            logger.info(f"✅ Connected to Binance {mode}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance: {e}")
            raise
    
    def test_connection(self):
        """
        Test if your connection to Binance is working
        
        Returns:
            bool: True if connection works, False if there's a problem
        """
        try:
            status = self.client.get_system_status()
            logger.info("✅ Connection test successful!")
            return True
        except BinanceAPIException as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_account_balance(self, asset='USDT'):
        """
        Check how much of a coin you have in your account
        
        Args:
            asset (str): Which coin to check (default: USDT = US Dollar Tether)
        
        Returns:
            dict: Your balance with 'free' (available) and 'locked' (in orders) amounts
            
        Example:
            balance = client.get_account_balance('USDT')
            print(f"I have ${balance['free']} available")
        """
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return {
                        'free': float(balance['free']),      # Available to trade
                        'locked': float(balance['locked']),  # Currently in orders
                        'total': float(balance['free']) + float(balance['locked'])
                    }
            return {'free': 0.0, 'locked': 0.0, 'total': 0.0}
        except BinanceAPIException as e:
            logger.error(f"❌ Error checking balance: {e}")
            return None
    
    def get_symbol_info(self, symbol):
        """
        Get detailed information about a trading pair
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT' for Bitcoin/USDT)
        
        Returns:
            dict: Symbol information including minimum trade sizes and price precision
        """
        try:
            info = self.client.get_symbol_info(symbol)
            return info
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting symbol info: {e}")
            return None
    
    def get_klines(self, symbol, interval='5m', limit=100, startTime=None, endTime=None):
        """
        Get historical price data (candlestick chart data)
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
            interval (str): Time per candle ('1m', '5m', '15m', '1h', '4h', '1d')
            limit (int): How many candles to get (max 1000)
            startTime (int): Start time in milliseconds (optional)
            endTime (int): End time in milliseconds (optional)
        
        Returns:
            list: Price data for each time period
            
        Example:
            # Get last 100 five-minute candles for Bitcoin
            data = client.get_klines('BTCUSDT', interval='5m', limit=100)
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if startTime is not None:
                params['startTime'] = startTime
            if endTime is not None:
                params['endTime'] = endTime
            
            klines = self.client.get_klines(**params)
            return klines
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting price data: {e}")
            return None
    
    def get_current_price(self, symbol):
        """
        Get the current market price for a trading pair
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
        
        Returns:
            float: Current price
            
        Example:
            price = client.get_current_price('BTCUSDT')
            print(f"Bitcoin is currently ${price}")
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting current price: {e}")
            return None
    
    def place_market_order(self, symbol, side, quantity):
        """
        Place an instant buy or sell order at the current market price
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
            side (str): 'BUY' or 'SELL'
            quantity (float): How much to buy/sell
        
        Returns:
            dict: Order confirmation from Binance
            
        Example:
            # Buy 0.001 Bitcoin at current price
            order = client.place_market_order('BTCUSDT', 'BUY', 0.001)
        
        Warning:
            This executes immediately! Make sure you want to trade before calling.
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logger.info(f"✅ Order placed: {side} {quantity} {symbol}")
            return order
        except BinanceAPIException as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    def place_limit_order(self, symbol, side, quantity, price):
        """
        Place a buy or sell order at a specific price (not instant)
        
        Args:
            symbol (str): Trading pair
            side (str): 'BUY' or 'SELL'
            quantity (float): How much to buy/sell
            price (float): The exact price you want
        
        Returns:
            dict: Order confirmation
            
        Example:
            # Buy Bitcoin only if price drops to $50,000
            order = client.place_limit_order('BTCUSDT', 'BUY', 0.001, 50000)
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',  # Good 'til cancelled
                quantity=quantity,
                price=price
            )
            logger.info(f"✅ Limit order placed: {side} {quantity} {symbol} @ ${price}")
            return order
        except BinanceAPIException as e:
            logger.error(f"❌ Error placing limit order: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """
        See all your pending orders that haven't executed yet
        
        Args:
            symbol (str): Optional - check orders for specific pair only
        
        Returns:
            list: All your open orders
        """
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            return orders
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting open orders: {e}")
            return None
    
    def cancel_order(self, symbol, order_id):
        """
        Cancel a pending order
        
        Args:
            symbol (str): Trading pair
            order_id (int): The order ID to cancel
        
        Returns:
            dict: Cancellation confirmation
        """
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"✅ Order {order_id} cancelled")
            return result
        except BinanceAPIException as e:
            logger.error(f"❌ Error cancelling order: {e}")
            return None
    
    def is_symbol_tradeable(self, symbol):
        """
        Check if a trading pair is valid and currently available for trading
        
        Args:
            symbol (str): Trading pair to check (e.g., 'DOGEUSDT')
        
        Returns:
            bool: True if you can trade it, False if not available
            
        Example:
            if client.is_symbol_tradeable('DOGEUSDT'):
                print("Dogecoin is available!")
        """
        try:
            info = self.client.get_symbol_info(symbol)
            if info and info.get('status') == 'TRADING':
                logger.info(f"✅ {symbol} is available for trading")
                return True
            else:
                status = info.get('status') if info else 'UNKNOWN'
                logger.warning(f"⚠️ {symbol} not tradeable (status: {status})")
                return False
        except BinanceAPIException as e:
            logger.warning(f"❌ {symbol} not available: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking {symbol}: {e}")
            return False
    
    def get_24h_tickers(self):
        """
        Get 24-hour price change statistics for all trading pairs
        
        Returns:
            list: Array of ticker data with priceChangePercent, volume, etc.
            
        Example:
            tickers = client.get_24h_tickers()
            for ticker in tickers:
                if ticker['symbol'].endswith('USDT'):
                    print(f"{ticker['symbol']}: {ticker['priceChangePercent']}%")
        """
        try:
            # Get all tickers (no symbol parameter = all symbols)
            # Returns array with priceChangePercent, quoteVolume, etc.
            tickers = self.client.get_ticker()
            return tickers
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting 24h tickers: {e}")
            return []
    
    def get_ticker(self, symbol):
        """
        Get 24hr ticker statistics for a specific symbol
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT')
        
        Returns:
            dict: 24hr statistics including price change, volume, etc.
        """
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return ticker
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting ticker for {symbol}: {e}")
            return None
    
    def get_order_book(self, symbol, limit=20):
        """
        Get the order book (bids and asks) for a symbol
        
        Args:
            symbol (str): Trading pair
            limit (int): Number of orders to get (default 20)
        
        Returns:
            dict: Order book with 'bids' and 'asks' arrays
        """
        try:
            order_book = self.client.get_order_book(symbol=symbol, limit=limit)
            return order_book
        except BinanceAPIException as e:
            logger.error(f"❌ Error getting order book for {symbol}: {e}")
            return None