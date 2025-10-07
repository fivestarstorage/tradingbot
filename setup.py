"""
Setup helper script for the trading bot
"""
import os
import sys


def create_env_file():
    """Create .env file from template"""
    env_template = """# Binance API Credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Trading Configuration
TRADING_SYMBOL=BTCUSDT
TRADE_AMOUNT=0.001
USE_TESTNET=true

# Momentum Strategy Parameters
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
MOMENTUM_PERIOD=10
CHECK_INTERVAL=60

# Risk Management
MAX_POSITION_SIZE=0.01
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=5.0
"""
    
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (yes/no): ")
        if response.lower() != 'yes':
            print("Skipping .env file creation.")
            return False
    
    with open('.env', 'w') as f:
        f.write(env_template)
    
    print("✓ Created .env file")
    print("\n⚠️  IMPORTANT: Edit the .env file and add your Binance API credentials!")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'binance',
        'pandas',
        'numpy',
        'ta',
        'dotenv',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package if package != 'dotenv' else 'dotenv')
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("⚠️  Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall them with: pip install -r requirements.txt")
        return False
    
    print("✓ All required packages are installed")
    return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("Trading Bot Setup")
    print("=" * 60)
    print()
    
    # Check dependencies
    print("1. Checking dependencies...")
    deps_ok = check_dependencies()
    print()
    
    # Create .env file
    print("2. Setting up configuration...")
    env_created = create_env_file()
    print()
    
    # Final instructions
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    
    if not deps_ok:
        print("⚠️  Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Run setup again: python setup.py")
    elif env_created:
        print("📝 Next steps:")
        print("   1. Edit .env file with your Binance API credentials")
        print("   2. Get testnet API keys: https://testnet.binance.vision/")
        print("   3. Set USE_TESTNET=true for testing")
        print("   4. Run the bot: python trading_bot.py")
    else:
        print("📝 Next steps:")
        print("   1. Verify your .env file has correct API credentials")
        print("   2. Run the bot: python trading_bot.py")
    
    print()
    print("📖 For more information, see README.md")
    print()


if __name__ == '__main__':
    main()

