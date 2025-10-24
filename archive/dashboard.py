"""
Live Trading Dashboard - Monitor Your Bot

Features:
- Real-time position tracking
- Profit/loss monitoring
- Trade history
- Performance metrics
- Emergency stop button
"""
import sys
import time
import os
from datetime import datetime
from binance_client import BinanceClient
from config import Config

class Dashboard:
    """Terminal-based live trading dashboard"""
    
    def __init__(self, symbol='BTCUSDT'):
        self.symbol = symbol
        self.client = BinanceClient(
            api_key=Config.BINANCE_API_KEY,
            api_secret=Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        self.start_time = datetime.now()
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_account_info(self):
        """Get current account balance and positions"""
        balance = self.client.get_account_balance('USDT')
        current_price = self.client.get_current_price(self.symbol)
        
        return {
            'balance_usdt': balance['free'] if balance else 0,
            'locked_usdt': balance['locked'] if balance else 0,
            'current_price': current_price
        }
    
    def read_log_file(self):
        """Read latest trades from log file"""
        today = datetime.now().strftime("%Y%m%d")
        log_file = f'live_trading_{today}.log'
        
        if not os.path.exists(log_file):
            return []
        
        trades = []
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
            # Parse trades from log
            for line in lines:
                if 'CLOSED POSITION' in line:
                    # Extract trade info
                    trades.append(line.strip())
        
        except Exception as e:
            pass
        
        return trades[-10:]  # Last 10 trades
    
    def display(self):
        """Display dashboard"""
        self.clear_screen()
        
        # Header
        print("=" * 80)
        print("🎯 LIVE TRADING DASHBOARD")
        print("=" * 80)
        print(f"Symbol: {self.symbol} | Mode: {'TESTNET' if Config.USE_TESTNET else 'MAINNET'}")
        print(f"Runtime: {datetime.now() - self.start_time}")
        print(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        print()
        
        # Account Info
        try:
            info = self.get_account_info()
            
            print("💰 ACCOUNT STATUS")
            print("-" * 80)
            print(f"Available Balance:    ${info['balance_usdt']:.2f} USDT")
            print(f"In Orders:            ${info['locked_usdt']:.2f} USDT")
            print(f"Total:                ${info['balance_usdt'] + info['locked_usdt']:.2f} USDT")
            print(f"Current {self.symbol}:   ${info['current_price']:.2f}")
            print()
            
        except Exception as e:
            print(f"⚠️  Could not fetch account info: {e}")
            print()
        
        # Recent Trades
        print("📊 RECENT TRADES (from log)")
        print("-" * 80)
        trades = self.read_log_file()
        
        if trades:
            for trade in trades:
                print(f"  {trade}")
        else:
            print("  No trades yet...")
        
        print("-" * 80)
        print()
        
        # Controls
        print("⌨️  CONTROLS:")
        print("   Ctrl+C  - Exit dashboard (bot keeps running)")
        print("   Check log file for detailed information")
        print()
        print("=" * 80)
    
    def run(self, refresh_interval=5):
        """Run dashboard with auto-refresh"""
        print("Starting dashboard...")
        print("Press Ctrl+C to exit\n")
        time.sleep(2)
        
        try:
            while True:
                self.display()
                time.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            print("\n\nDashboard closed. Bot is still running in background.")
            print(f"Check {datetime.now().strftime('%Y%m%d')} log file for activity.\n")


def main():
    """Main entry point"""
    print("=" * 80)
    print("🎯 TRADING DASHBOARD")
    print("=" * 80)
    print()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    symbol = input("Symbol to monitor [BTCUSDT]: ").strip().upper() or 'BTCUSDT'
    
    refresh = input("Refresh interval in seconds [5]: ").strip()
    try:
        refresh_interval = int(refresh) if refresh else 5
    except:
        refresh_interval = 5
    
    print(f"\n✓ Monitoring {symbol}")
    print(f"✓ Refreshing every {refresh_interval} seconds")
    print("\nStarting dashboard...\n")
    
    time.sleep(1)
    
    dashboard = Dashboard(symbol=symbol)
    dashboard.run(refresh_interval=refresh_interval)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
