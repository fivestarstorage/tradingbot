"""
Binance client wrapper for connecting to Binance API
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)


class BinanceClient:
    """Wrapper class for Binance API client"""
    
    def __init__(self, api_key, api_secret, testnet=False):
        """
        Initialize Binance client
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use testnet (default: False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            if testnet:
                self.client.API_URL = 'https://testnet.binance.vision/api'
            logger.info(f"Connected to Binance {'Testnet' if testnet else 'Mainnet'}")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    def test_connection(self):
        """Test the connection to Binance API"""
        try:
            status = self.client.get_system_status()
            logger.info(f"Connection test successful: {status}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_account_balance(self, asset='USDT'):
        """
        Get account balance for a specific asset
        
        Args:
            asset: Asset symbol (default: USDT)
            
        Returns:
            dict with free and locked balance
        """
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return {
                        'free': float(balance['free']),
                        'locked': float(balance['locked']),
                        'total': float(balance['free']) + float(balance['locked'])
                    }
            return {'free': 0.0, 'locked': 0.0, 'total': 0.0}
        except BinanceAPIException as e:
            logger.error(f"Error getting account balance: {e}")
            return None
    
    def get_symbol_info(self, symbol):
        """
        Get trading rules for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            Symbol information dict
        """
        try:
            info = self.client.get_symbol_info(symbol)
            return info
        except BinanceAPIException as e:
            logger.error(f"Error getting symbol info: {e}")
            return None
    
    def get_klines(self, symbol, interval='1m', limit=100, startTime=None, endTime=None):
        """
        Get historical klines/candlestick data
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (e.g., '1m', '5m', '1h')
            limit: Number of klines to retrieve (default: 100)
            startTime: Start time in milliseconds (optional)
            endTime: End time in milliseconds (optional)
            
        Returns:
            List of kline data
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            # Add optional time parameters if provided
            if startTime is not None:
                params['startTime'] = startTime
            if endTime is not None:
                params['endTime'] = endTime
            
            klines = self.client.get_klines(**params)
            return klines
        except BinanceAPIException as e:
            logger.error(f"Error getting klines: {e}")
            return None
    
    def get_current_price(self, symbol):
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Current price as float
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    def place_market_order(self, symbol, side, quantity):
        """
        Place a market order
        
        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Quantity to trade
            
        Returns:
            Order response dict
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logger.info(f"Market order placed: {side} {quantity} {symbol}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    def place_limit_order(self, symbol, side, quantity, price):
        """
        Place a limit order
        
        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Quantity to trade
            price: Limit price
            
        Returns:
            Order response dict
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
            logger.info(f"Limit order placed: {side} {quantity} {symbol} @ {price}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """
        Get all open orders
        
        Args:
            symbol: Trading pair symbol (optional, None for all symbols)
            
        Returns:
            List of open orders
        """
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            return orders
        except BinanceAPIException as e:
            logger.error(f"Error getting open orders: {e}")
            return None
    
    def cancel_order(self, symbol, order_id):
        """
        Cancel an order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response dict
        """
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return result
        except BinanceAPIException as e:
            logger.error(f"Error cancelling order: {e}")
            return None
