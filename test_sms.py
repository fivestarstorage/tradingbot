#!/usr/bin/env python3
"""
Quick SMS Test Script
Tests Twilio SMS notifications for trading bot
"""
from dotenv import load_dotenv
load_dotenv()

from app.twilio_notifier import TwilioNotifier

def main():
    print("=" * 70)
    print("📱 TESTING SMS NOTIFICATIONS")
    print("=" * 70)
    print()
    
    notifier = TwilioNotifier()
    
    if not notifier.client:
        print("❌ Twilio not configured!")
        print()
        print("Add to .env:")
        print("  TWILIO_ACCOUNT_SID=your_account_sid")
        print("  TWILIO_AUTH_TOKEN=your_auth_token")
        print()
        return
    
    print("✅ Twilio configured successfully!")
    print()
    print("Sending test SMS to:")
    for recipient in notifier.recipients:
        print(f"  • {recipient['name']}: {recipient['number']}")
    print()
    
    # Test message
    print("Sending test message...")
    result = notifier.test_sms()
    print(result)
    print()
    
    # Test trade notification
    print("Sending test BUY notification...")
    buy_trade = {
        'action': 'BUY',
        'symbol': 'BTCUSDT',
        'price': 62450.00,
        'quantity': 0.0016,
        'amount': 100.00,
        'bot_name': 'Test Bot',
        'reasoning': 'Testing SMS notifications for the trading bot'
    }
    
    notifier.send_trade_notification(buy_trade)
    print()
    
    print("=" * 70)
    print("✅ Test complete! Check your phones for SMS messages.")
    print("=" * 70)

if __name__ == '__main__':
    main()

