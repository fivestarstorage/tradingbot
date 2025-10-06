"""
Position manager for tracking trades and risk management
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions and risk management"""
    
    def __init__(self, stop_loss_percent=2.0, take_profit_percent=5.0):
        """
        Initialize position manager
        
        Args:
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
        """
        self.position = None
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        logger.info(f"Initialized PositionManager: SL={stop_loss_percent}%, TP={take_profit_percent}%")
    
    def has_position(self):
        """Check if there's an open position"""
        return self.position is not None
    
    def open_position(self, symbol, side, quantity, entry_price):
        """
        Open a new position
        
        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Position quantity
            entry_price: Entry price
        """
        if self.has_position():
            logger.warning("Attempted to open position while one already exists")
            return False
        
        stop_loss = entry_price * (1 - self.stop_loss_percent / 100) if side == 'BUY' else entry_price * (1 + self.stop_loss_percent / 100)
        take_profit = entry_price * (1 + self.take_profit_percent / 100) if side == 'BUY' else entry_price * (1 - self.take_profit_percent / 100)
        
        self.position = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'highest_price': entry_price if side == 'BUY' else None,
            'lowest_price': entry_price if side == 'SELL' else None
        }
        
        logger.info(f"Opened {side} position: {quantity} {symbol} @ {entry_price}")
        logger.info(f"Stop Loss: {stop_loss:.2f}, Take Profit: {take_profit:.2f}")
        return True
    
    def close_position(self, exit_price, reason='Manual'):
        """
        Close the current position
        
        Args:
            exit_price: Exit price
            reason: Reason for closing
            
        Returns:
            Position details dict
        """
        if not self.has_position():
            logger.warning("Attempted to close position when none exists")
            return None
        
        position = self.position.copy()
        entry_price = position['entry_price']
        side = position['side']
        
        # Calculate P&L
        if side == 'BUY':
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['pnl_percent'] = pnl_percent
        position['close_reason'] = reason
        
        duration = position['exit_time'] - position['entry_time']
        
        logger.info(f"Closed {side} position: {position['symbol']} @ {exit_price}")
        logger.info(f"P&L: {pnl_percent:+.2f}% | Duration: {duration} | Reason: {reason}")
        
        self.position = None
        return position
    
    def check_exit_conditions(self, current_price):
        """
        Check if position should be closed based on stop loss or take profit
        
        Args:
            current_price: Current market price
            
        Returns:
            Tuple (should_exit: bool, reason: str)
        """
        if not self.has_position():
            return False, None
        
        side = self.position['side']
        stop_loss = self.position['stop_loss']
        take_profit = self.position['take_profit']
        
        # Update trailing stop for long positions
        if side == 'BUY':
            if current_price > self.position['highest_price']:
                self.position['highest_price'] = current_price
            
            # Check stop loss
            if current_price <= stop_loss:
                return True, f"Stop Loss hit ({current_price:.2f} <= {stop_loss:.2f})"
            
            # Check take profit
            if current_price >= take_profit:
                return True, f"Take Profit hit ({current_price:.2f} >= {take_profit:.2f})"
        
        # Update trailing stop for short positions
        else:
            if current_price < self.position['lowest_price']:
                self.position['lowest_price'] = current_price
            
            # Check stop loss
            if current_price >= stop_loss:
                return True, f"Stop Loss hit ({current_price:.2f} >= {stop_loss:.2f})"
            
            # Check take profit
            if current_price <= take_profit:
                return True, f"Take Profit hit ({current_price:.2f} <= {take_profit:.2f})"
        
        return False, None
    
    def get_position_info(self):
        """Get current position information"""
        if not self.has_position():
            return None
        
        return self.position.copy()
    
    def calculate_unrealized_pnl(self, current_price):
        """
        Calculate unrealized P&L for current position
        
        Args:
            current_price: Current market price
            
        Returns:
            P&L percentage
        """
        if not self.has_position():
            return 0.0
        
        entry_price = self.position['entry_price']
        side = self.position['side']
        
        if side == 'BUY':
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        return pnl_percent
