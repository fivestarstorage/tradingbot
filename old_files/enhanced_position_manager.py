"""
Enhanced Position Manager with Trailing Stops and Dynamic Risk Management
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedPositionManager:
    """
    Advanced position manager with:
    - Trailing stop loss based on ATR
    - Dynamic position sizing
    - Partial profit taking
    - Risk-adjusted exits
    """
    
    def __init__(self, base_stop_loss_percent=2.0, base_take_profit_percent=5.0):
        """
        Initialize enhanced position manager
        
        Args:
            base_stop_loss_percent: Base stop loss percentage (can be overridden dynamically)
            base_take_profit_percent: Base take profit percentage (can be overridden dynamically)
        """
        self.position = None
        self.base_stop_loss_percent = base_stop_loss_percent
        self.base_take_profit_percent = base_take_profit_percent
        self.trailing_stop_enabled = False
        logger.info(f"Initialized EnhancedPositionManager with dynamic risk management")
    
    def has_position(self):
        """Check if there's an open position"""
        return self.position is not None
    
    def open_position(self, symbol, side, quantity, entry_price, stop_loss_price=None, 
                     take_profit_price=None, trailing_stop_mult=2.0, atr_value=None):
        """
        Open a new position with dynamic risk management
        
        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Position quantity
            entry_price: Entry price
            stop_loss_price: Specific stop loss price (optional)
            take_profit_price: Specific take profit price (optional)
            trailing_stop_mult: Multiplier for trailing stop (ATR multiplier)
            atr_value: ATR value for dynamic trailing stops
        """
        if self.has_position():
            logger.warning("Attempted to open position while one already exists")
            return False
        
        # Calculate stop loss and take profit if not provided
        if stop_loss_price is None:
            stop_loss_price = entry_price * (1 - self.base_stop_loss_percent / 100) if side == 'BUY' else entry_price * (1 + self.base_stop_loss_percent / 100)
        
        if take_profit_price is None:
            take_profit_price = entry_price * (1 + self.base_take_profit_percent / 100) if side == 'BUY' else entry_price * (1 - self.base_take_profit_percent / 100)
        
        self.position = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss_price,
            'initial_stop_loss': stop_loss_price,  # Keep track of initial SL
            'take_profit': take_profit_price,
            'highest_price': entry_price if side == 'BUY' else None,
            'lowest_price': entry_price if side == 'SELL' else None,
            'trailing_stop_mult': trailing_stop_mult,
            'atr_value': atr_value,
            'trailing_stop_enabled': False,  # Enable after price moves favorably
            'profit_target_1_hit': False,  # For partial profit taking
            'profit_target_2_hit': False,
            'peak_profit_percent': 0  # Track peak profit for drawdown protection
        }
        
        logger.info(f"Opened {side} position: {quantity} {symbol} @ {entry_price:.2f}")
        logger.info(f"Stop Loss: {stop_loss_price:.2f}, Take Profit: {take_profit_price:.2f}")
        if atr_value:
            logger.info(f"ATR: {atr_value:.2f}, Trailing Stop Mult: {trailing_stop_mult}x")
        return True
    
    def update_trailing_stop(self, current_price):
        """
        Update trailing stop based on price movement
        
        Args:
            current_price: Current market price
        """
        if not self.has_position():
            return
        
        side = self.position['side']
        atr_value = self.position.get('atr_value', None)
        trailing_mult = self.position['trailing_stop_mult']
        
        if side == 'BUY':
            # Update highest price
            if current_price > self.position['highest_price']:
                self.position['highest_price'] = current_price
                
                # Calculate unrealized profit
                profit_percent = ((current_price - self.position['entry_price']) / self.position['entry_price']) * 100
                
                # Update peak profit
                if profit_percent > self.position['peak_profit_percent']:
                    self.position['peak_profit_percent'] = profit_percent
                
                # Enable trailing stop after 1% profit
                if profit_percent > 1.0:
                    self.position['trailing_stop_enabled'] = True
                
                # Update trailing stop if enabled
                if self.position['trailing_stop_enabled']:
                    if atr_value:
                        # ATR-based trailing stop
                        new_stop = current_price - (atr_value * trailing_mult)
                    else:
                        # Percentage-based trailing stop (fallback)
                        new_stop = current_price * 0.98  # 2% trailing
                    
                    # Only move stop loss up, never down
                    if new_stop > self.position['stop_loss']:
                        old_stop = self.position['stop_loss']
                        self.position['stop_loss'] = new_stop
                        logger.info(f"Trailing stop updated: {old_stop:.2f} -> {new_stop:.2f} (Peak: ${current_price:.2f})")
        
        else:  # SELL position
            # Update lowest price
            if self.position['lowest_price'] is None or current_price < self.position['lowest_price']:
                self.position['lowest_price'] = current_price
                
                profit_percent = ((self.position['entry_price'] - current_price) / self.position['entry_price']) * 100
                
                if profit_percent > self.position['peak_profit_percent']:
                    self.position['peak_profit_percent'] = profit_percent
                
                if profit_percent > 1.0:
                    self.position['trailing_stop_enabled'] = True
                
                if self.position['trailing_stop_enabled']:
                    if atr_value:
                        new_stop = current_price + (atr_value * trailing_mult)
                    else:
                        new_stop = current_price * 1.02
                    
                    if new_stop < self.position['stop_loss']:
                        old_stop = self.position['stop_loss']
                        self.position['stop_loss'] = new_stop
                        logger.info(f"Trailing stop updated: {old_stop:.2f} -> {new_stop:.2f} (Low: ${current_price:.2f})")
    
    def check_partial_exits(self, current_price):
        """
        Check if we should take partial profits
        
        Args:
            current_price: Current market price
            
        Returns:
            Tuple (should_partial_exit: bool, exit_percent: float, reason: str)
        """
        if not self.has_position():
            return False, 0, None
        
        side = self.position['side']
        entry_price = self.position['entry_price']
        
        # Calculate profit percentage
        if side == 'BUY':
            profit_percent = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_percent = ((entry_price - current_price) / entry_price) * 100
        
        # First profit target: 50% position at 2% profit
        if not self.position['profit_target_1_hit'] and profit_percent >= 2.0:
            self.position['profit_target_1_hit'] = True
            return True, 0.5, "Partial exit 1: 50% at +2%"
        
        # Second profit target: 25% more at 4% profit
        if not self.position['profit_target_2_hit'] and profit_percent >= 4.0:
            self.position['profit_target_2_hit'] = True
            return True, 0.25, "Partial exit 2: 25% at +4%"
        
        return False, 0, None
    
    def check_exit_conditions(self, current_price):
        """
        Check if position should be closed based on stop loss, take profit, or other conditions
        
        Args:
            current_price: Current market price
            
        Returns:
            Tuple (should_exit: bool, reason: str)
        """
        if not self.has_position():
            return False, None
        
        # First update trailing stop
        self.update_trailing_stop(current_price)
        
        side = self.position['side']
        stop_loss = self.position['stop_loss']
        take_profit = self.position['take_profit']
        entry_price = self.position['entry_price']
        
        # Calculate current profit
        if side == 'BUY':
            profit_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Check stop loss
            if current_price <= stop_loss:
                return True, f"Stop Loss hit ({current_price:.2f} <= {stop_loss:.2f})"
            
            # Check take profit
            if current_price >= take_profit:
                return True, f"Take Profit hit ({current_price:.2f} >= {take_profit:.2f})"
            
            # Profit protection: If we hit 5%+ profit and now falling below 2%
            if self.position['peak_profit_percent'] >= 5.0 and profit_percent < 2.0:
                return True, f"Profit protection (Peak: {self.position['peak_profit_percent']:.1f}%, Now: {profit_percent:.1f}%)"
        
        else:  # SELL position
            profit_percent = ((entry_price - current_price) / entry_price) * 100
            
            # Check stop loss
            if current_price >= stop_loss:
                return True, f"Stop Loss hit ({current_price:.2f} >= {stop_loss:.2f})"
            
            # Check take profit
            if current_price <= take_profit:
                return True, f"Take Profit hit ({current_price:.2f} <= {take_profit:.2f})"
            
            # Profit protection
            if self.position['peak_profit_percent'] >= 5.0 and profit_percent < 2.0:
                return True, f"Profit protection (Peak: {self.position['peak_profit_percent']:.1f}%, Now: {profit_percent:.1f}%)"
        
        return False, None
    
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
        
        logger.info(f"Closed {side} position: {position['symbol']} @ {exit_price:.2f}")
        logger.info(f"P&L: {pnl_percent:+.2f}% | Duration: {duration} | Reason: {reason}")
        
        if position['trailing_stop_enabled']:
            logger.info(f"Trailing stop was active. Peak profit: {position['peak_profit_percent']:.2f}%")
        
        self.position = None
        return position
    
    def partial_close(self, exit_price, close_percent, reason='Partial Exit'):
        """
        Partially close the position
        
        Args:
            exit_price: Exit price
            close_percent: Percentage of position to close (0.0 to 1.0)
            reason: Reason for partial close
            
        Returns:
            Trade details dict for the closed portion
        """
        if not self.has_position():
            logger.warning("Attempted to partially close position when none exists")
            return None
        
        if close_percent <= 0 or close_percent >= 1:
            logger.warning(f"Invalid close_percent: {close_percent}")
            return None
        
        # Calculate quantity to close
        close_quantity = self.position['quantity'] * close_percent
        remaining_quantity = self.position['quantity'] - close_quantity
        
        # Calculate P&L for closed portion
        entry_price = self.position['entry_price']
        side = self.position['side']
        
        if side == 'BUY':
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        # Create trade record for closed portion
        closed_trade = {
            'symbol': self.position['symbol'],
            'side': side,
            'quantity': close_quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': self.position['entry_time'],
            'exit_time': datetime.now(),
            'pnl_percent': pnl_percent,
            'close_reason': reason,
            'is_partial': True
        }
        
        # Update position with remaining quantity
        self.position['quantity'] = remaining_quantity
        
        logger.info(f"Partial close: {close_percent*100:.0f}% of position @ {exit_price:.2f}")
        logger.info(f"P&L on closed portion: {pnl_percent:+.2f}%")
        logger.info(f"Remaining quantity: {remaining_quantity:.8f}")
        
        return closed_trade
    
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
    
    def get_risk_reward_ratio(self, current_price):
        """
        Calculate current risk/reward ratio
        
        Args:
            current_price: Current market price
            
        Returns:
            Risk/reward ratio
        """
        if not self.has_position():
            return 0
        
        entry_price = self.position['entry_price']
        stop_loss = self.position['stop_loss']
        take_profit = self.position['take_profit']
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - current_price)
        
        if risk == 0:
            return 0
        
        return reward / risk
