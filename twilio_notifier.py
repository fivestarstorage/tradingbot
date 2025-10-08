"""
Twilio SMS Notifier
Sends trade notifications via SMS
"""
import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

class TwilioNotifier:
    """Send SMS notifications for trades"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.messaging_service_sid = 'MG00a1831705f28abc4958c7986fcad688'
        
        # Notification recipients
        self.recipients = [
            {'name': 'Riley Martin', 'number': '+61431269296'},
            {'name': 'Neal Martin', 'number': '+61422335161'}
        ]
        
        # Initialize client if credentials available
        self.client = None
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio SMS notifier initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {e}")
        else:
            logger.warning("⚠️ Twilio credentials not found - SMS notifications disabled")
    
    def send_trade_notification(self, trade_data):
        """
        Send SMS notification for a trade
        
        Args:
            trade_data: Dict with trade info
            {
                'action': 'BUY' or 'SELL',
                'symbol': 'BTCUSDT',
                'price': 62450.00,
                'quantity': 0.0016,
                'amount': 100.00,
                'bot_name': 'AI Trader',
                'profit': 5.20 (optional, for sells),
                'profit_percent': 5.2 (optional, for sells),
                'reasoning': 'AI reasoning for the trade' (optional)
            }
        """
        if not self.client:
            logger.warning("Twilio not configured - skipping SMS notification")
            return False
        
        try:
            message = self._format_trade_message(trade_data)
            
            # Send to all recipients
            results = []
            for recipient in self.recipients:
                try:
                    sent_message = self.client.messages.create(
                        body=message,
                        messaging_service_sid=self.messaging_service_sid,
                        to=recipient['number']
                    )
                    logger.info(f"✅ SMS sent to {recipient['name']} ({recipient['number']}). SID: {sent_message.sid}")
                    results.append({
                        'success': True,
                        'to': recipient['name'],
                        'sid': sent_message.sid
                    })
                except Exception as e:
                    logger.error(f"❌ Failed to send SMS to {recipient['name']}: {e}")
                    results.append({
                        'success': False,
                        'to': recipient['name'],
                        'error': str(e)
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
            return False
    
    def _format_trade_message(self, trade_data):
        """Format trade info into SMS message"""
        action = trade_data['action']
        symbol = trade_data['symbol']
        price = trade_data['price']
        quantity = trade_data['quantity']
        amount = trade_data['amount']
        bot_name = trade_data.get('bot_name', 'Trading Bot')
        reasoning = trade_data.get('reasoning', None)
        
        if action == 'BUY':
            emoji = '🟢'
            message = f"{emoji} BUY ALERT - {bot_name}\n\n"
            message += f"Coin: {symbol}\n"
            message += f"Price: ${price:,.2f}\n"
            message += f"Quantity: {quantity:.8f}\n"
            message += f"Total: ${amount:.2f}\n"
            message += f"\n💰 Position opened!"
        
        elif action == 'SELL':
            emoji = '🔴'
            profit = trade_data.get('profit', 0)
            profit_percent = trade_data.get('profit_percent', 0)
            profit_emoji = '📈' if profit >= 0 else '📉'
            
            message = f"{emoji} SELL ALERT - {bot_name}\n\n"
            message += f"Coin: {symbol}\n"
            message += f"Price: ${price:,.2f}\n"
            message += f"Quantity: {quantity:.8f}\n"
            message += f"Total: ${amount:.2f}\n"
            message += f"\n{profit_emoji} Profit: ${profit:+.2f} ({profit_percent:+.2f}%)"
        
        else:
            message = f"📊 TRADE ALERT - {bot_name}\n\n"
            message += f"{action}: {symbol} @ ${price:,.2f}"
        
        # Add AI reasoning if provided (keep it under 400 chars to avoid SMS length issues)
        if reasoning:
            # Truncate reasoning if too long
            max_reasoning_length = 400
            if len(reasoning) > max_reasoning_length:
                reasoning = reasoning[:max_reasoning_length-3] + "..."
            
            message += f"\n\n💡 Reasoning:\n{reasoning}"
        
        return message
    
    def send_bot_status(self, bot_name, status, message):
        """
        Send bot status notification (started, stopped, error)
        
        Args:
            bot_name: Name of the bot
            status: 'started', 'stopped', 'error'
            message: Additional message
        """
        if not self.client:
            return False
        
        try:
            if status == 'started':
                emoji = '🚀'
                title = 'BOT STARTED'
            elif status == 'stopped':
                emoji = '⏹️'
                title = 'BOT STOPPED'
            elif status == 'error':
                emoji = '❌'
                title = 'BOT ERROR'
            else:
                emoji = 'ℹ️'
                title = 'BOT STATUS'
            
            sms_message = f"{emoji} {title}\n\n"
            sms_message += f"Bot: {bot_name}\n"
            sms_message += f"{message}"
            
            # Send to all recipients
            for recipient in self.recipients:
                try:
                    self.client.messages.create(
                        body=sms_message,
                        messaging_service_sid=self.messaging_service_sid,
                        to=recipient['number']
                    )
                    logger.info(f"✅ Status SMS sent to {recipient['name']}")
                except Exception as e:
                    logger.error(f"❌ Failed to send status SMS to {recipient['name']}: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending status notification: {e}")
            return False
    
    def test_sms(self):
        """Send a test SMS to verify setup"""
        if not self.client:
            return "❌ Twilio not configured"
        
        test_message = "🤖 Test SMS from Trading Bot\n\nIf you received this, SMS notifications are working!"
        
        results = []
        for recipient in self.recipients:
            try:
                sent_message = self.client.messages.create(
                    body=test_message,
                    messaging_service_sid=self.messaging_service_sid,
                    to=recipient['number']
                )
                results.append(f"✅ Sent to {recipient['name']}: {sent_message.sid}")
            except Exception as e:
                results.append(f"❌ Failed to send to {recipient['name']}: {e}")
        
        return "\n".join(results)


def test_twilio():
    """Test Twilio SMS functionality"""
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 70)
    print("📱 TESTING TWILIO SMS NOTIFICATIONS")
    print("=" * 70)
    print()
    
    notifier = TwilioNotifier()
    
    if not notifier.client:
        print("❌ Twilio not configured!")
        print("Add to .env:")
        print("  TWILIO_ACCOUNT_SID=your_sid")
        print("  TWILIO_AUTH_TOKEN=your_token")
        return
    
    print("Sending test SMS...")
    print()
    
    result = notifier.test_sms()
    print(result)
    
    print()
    print("Testing trade notification...")
    print()
    
    # Test buy notification
    buy_trade = {
        'action': 'BUY',
        'symbol': 'BTCUSDT',
        'price': 62450.00,
        'quantity': 0.0016,
        'amount': 100.00,
        'bot_name': 'Test Bot'
    }
    
    notifier.send_trade_notification(buy_trade)
    
    print()
    print("Check your phones for SMS messages!")
    print("=" * 70)


if __name__ == '__main__':
    test_twilio()
