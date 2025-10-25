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
    
    def send_summary(self, summary_data):
        """
        Send 6-hour trading summary
        
        Args:
            summary_data: Dict with summary info
            {
                'bot_name': 'AI Trader',
                'period': '6 hours',
                'total_trades': 5,
                'buys': 3,
                'sells': 2,
                'total_profit': 12.50,
                'profit_percent': 2.5,
                'current_positions': ['BTC', 'ETH'],
                'account_value': 1250.00
            }
        """
        if not self.client:
            logger.warning("Twilio not configured - skipping summary SMS")
            return False
        
        try:
            message = self._format_summary_message(summary_data)
            
            # Send to all recipients
            results = []
            for recipient in self.recipients:
                try:
                    sent_message = self.client.messages.create(
                        body=message,
                        messaging_service_sid=self.messaging_service_sid,
                        to=recipient['number']
                    )
                    logger.info(f"✅ Summary SMS sent to {recipient['name']} ({recipient['number']})")
                    results.append({'success': True, 'to': recipient['name']})
                except Exception as e:
                    logger.error(f"❌ Failed to send summary SMS to {recipient['name']}: {e}")
                    results.append({'success': False, 'to': recipient['name'], 'error': str(e)})
            
            return results
        
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            return False
    
    def _format_summary_message(self, summary_data):
        """Format trading summary into SMS message"""
        bot_name = summary_data.get('bot_name', 'Trading Bot')
        period = summary_data.get('period', '6 hours')
        total_trades = summary_data.get('total_trades', 0)
        buys = summary_data.get('buys', 0)
        sells = summary_data.get('sells', 0)
        total_profit = summary_data.get('total_profit', 0)
        profit_percent = summary_data.get('profit_percent', 0)
        positions = summary_data.get('current_positions', [])
        account_value = summary_data.get('account_value', 0)
        
        # Emoji based on performance
        if total_profit > 0:
            profit_emoji = '📈'
        elif total_profit < 0:
            profit_emoji = '📉'
        else:
            profit_emoji = '➡️'
        
        message = f"🤖 {period.upper()} SUMMARY\n"
        message += f"Bot: {bot_name}\n\n"
        
        message += f"📊 Trading Activity:\n"
        message += f"  Total Trades: {total_trades}\n"
        message += f"  • Buys: {buys}\n"
        message += f"  • Sells: {sells}\n\n"
        
        message += f"{profit_emoji} Performance:\n"
        message += f"  Profit: ${total_profit:+.2f} ({profit_percent:+.2f}%)\n\n"
        
        if positions:
            message += f"💼 Open Positions:\n"
            message += f"  {', '.join(positions)}\n\n"
        
        message += f"💰 Account Value: ${account_value:,.2f}"
        
        return message
    
    def send_news_summary(self, news_data):
        """
        Send AI-generated news summary SMS
        
        Args:
            news_data: Dict with news summary info
            {
                'total_articles': 25,
                'new_articles': 10,
                'sentiment_positive': 15,
                'sentiment_negative': 5,
                'sentiment_neutral': 5,
                'top_tickers': ['BTC', 'ETH', 'XRP'],
                'top_stories': [
                    {'title': '...', 'sentiment': 'Positive'},
                    ...
                ],
                'ai_summary': 'Market is showing bullish momentum...',
                'key_insight': 'XRP leading gains on institutional adoption'
            }
        """
        if not self.client:
            logger.warning("Twilio not configured - skipping news summary SMS")
            return False
        
        try:
            message = self._format_news_summary(news_data)
            
            # Send to all recipients
            results = []
            for recipient in self.recipients:
                try:
                    sent_message = self.client.messages.create(
                        body=message,
                        messaging_service_sid=self.messaging_service_sid,
                        to=recipient['number']
                    )
                    logger.info(f"✅ News summary SMS sent to {recipient['name']}")
                    results.append({'success': True, 'to': recipient['name']})
                except Exception as e:
                    logger.error(f"❌ Failed to send news summary to {recipient['name']}: {e}")
                    results.append({'success': False, 'to': recipient['name'], 'error': str(e)})
            
            return results
        
        except Exception as e:
            logger.error(f"Error sending news summary: {e}")
            return False
    
    def _format_news_summary(self, news_data):
        """Format news summary into SMS message"""
        total = news_data.get('total_articles', 0)
        new = news_data.get('new_articles', 0)
        pos = news_data.get('sentiment_positive', 0)
        neg = news_data.get('sentiment_negative', 0)
        neu = news_data.get('sentiment_neutral', 0)
        tickers = news_data.get('top_tickers', [])
        ai_summary = news_data.get('ai_summary', '')
        key_insight = news_data.get('key_insight', '')
        top_stories = news_data.get('top_stories', [])
        
        # Determine market sentiment emoji
        if pos > neg * 1.5:
            sentiment_emoji = '📈'
            sentiment_text = 'BULLISH'
        elif neg > pos * 1.5:
            sentiment_emoji = '📉'
            sentiment_text = 'BEARISH'
        else:
            sentiment_emoji = '➡️'
            sentiment_text = 'MIXED'
        
        message = f"📰 NEWS UPDATE\n\n"
        
        message += f"{sentiment_emoji} Market Sentiment: {sentiment_text}\n"
        message += f"• Positive: {pos}\n"
        message += f"• Negative: {neg}\n"
        message += f"• Neutral: {neu}\n\n"
        
        if tickers:
            message += f"🔥 Trending: {', '.join(tickers[:5])}\n\n"
        
        if ai_summary:
            # Truncate if too long (SMS limit ~400 chars for summary)
            if len(ai_summary) > 300:
                ai_summary = ai_summary[:297] + "..."
            message += f"💡 AI Analysis:\n{ai_summary}\n\n"
        
        if key_insight:
            if len(key_insight) > 150:
                key_insight = key_insight[:147] + "..."
            message += f"⚡ Key Insight:\n{key_insight}\n\n"
        
        message += f"📊 Processed {new} new articles (Total: {total})"
        
        return message
    
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
