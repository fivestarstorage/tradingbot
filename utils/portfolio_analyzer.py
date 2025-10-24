"""
Portfolio Analyzer - AI Analysis of All Coins in Your Wallet
Shows what the AI thinks about each coin you own
"""
import os
from dotenv import load_dotenv
from binance_client import BinanceClient
from news_monitor import NewsMonitor
from ai_analyzer import AINewsAnalyzer
from datetime import datetime

load_dotenv()

class PortfolioAnalyzer:
    """Analyzes all coins in wallet and shows AI recommendations"""
    
    def __init__(self):
        self.client = BinanceClient()
        self.news_monitor = NewsMonitor()
        self.ai_analyzer = AINewsAnalyzer()
    
    def get_all_balances(self):
        """Get all non-zero balances from Binance"""
        try:
            account = self.client.client.get_account()
            balances = []
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0 and asset != 'USDT':  # Exclude USDT (that's our trading capital)
                    # Get current price in USDT
                    try:
                        symbol = f"{asset}USDT"
                        ticker = self.client.client.get_symbol_ticker(symbol=symbol)
                        price = float(ticker['price'])
                        value_usdt = total * price
                        
                        balances.append({
                            'asset': asset,
                            'total': total,
                            'free': free,
                            'locked': locked,
                            'symbol': symbol,
                            'price': price,
                            'value_usdt': value_usdt
                        })
                    except:
                        # Can't get price (maybe not a USDT pair)
                        pass
            
            # Sort by value (highest first)
            balances.sort(key=lambda x: x['value_usdt'], reverse=True)
            return balances
            
        except Exception as e:
            print(f"Error getting balances: {e}")
            return []
    
    def analyze_coin(self, asset, symbol):
        """Get AI's opinion on a specific coin"""
        try:
            # Fetch recent news for this coin
            coin_name = asset.lower()
            articles = self.news_monitor.fetch_crypto_news(
                symbols=[coin_name, asset, 'crypto'],
                hours_back=24  # Last 24 hours
            )
            
            if not articles:
                return {
                    'signal': 'HOLD',
                    'confidence': 0,
                    'reasoning': 'No recent news found',
                    'news_count': 0
                }
            
            # Use batch analysis (efficient!)
            result = self.ai_analyzer.batch_analyze_comprehensive(
                articles=articles[:5],  # Top 5 articles
                max_articles=5
            )
            
            return {
                'signal': result['signal'],
                'confidence': result['confidence'],
                'reasoning': result['reasoning'],
                'sentiment': result.get('sentiment', 'neutral'),
                'impact': result.get('impact', 'low'),
                'news_count': len(articles),
                'articles_analyzed': result.get('articles_analyzed', 0)
            }
            
        except Exception as e:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasoning': f'Error: {str(e)}',
                'news_count': 0
            }
    
    def run_analysis(self):
        """Analyze all coins in portfolio"""
        print("=" * 80)
        print("🔍 PORTFOLIO ANALYZER - AI Analysis of Your Holdings")
        print("=" * 80)
        print()
        
        # Get all balances
        print("📊 Fetching your wallet balances...")
        balances = self.get_all_balances()
        
        if not balances:
            print("❌ No coins found in wallet (or all balances are zero)")
            print("\n💡 Tip: Make sure you have crypto (not just USDT) in your Binance account")
            return
        
        print(f"✅ Found {len(balances)} coins in your wallet\n")
        
        # Calculate total portfolio value
        total_value = sum(b['value_usdt'] for b in balances)
        print(f"💰 Total Portfolio Value: ${total_value:,.2f} USDT")
        print()
        print("=" * 80)
        print()
        
        # Analyze each coin
        for i, coin in enumerate(balances, 1):
            print(f"{'='*80}")
            print(f"🪙 COIN #{i}: {coin['asset']}")
            print(f"{'='*80}")
            print(f"Holdings:     {coin['total']:.6f} {coin['asset']}")
            print(f"Current Price: ${coin['price']:,.2f}")
            print(f"Portfolio Value: ${coin['value_usdt']:,.2f} ({coin['value_usdt']/total_value*100:.1f}% of portfolio)")
            print()
            
            # Get AI analysis
            print(f"🤖 Fetching AI analysis for {coin['asset']}...")
            analysis = self.analyze_coin(coin['asset'], coin['symbol'])
            
            print()
            print(f"📰 News Found: {analysis['news_count']} articles (analyzed {analysis.get('articles_analyzed', 0)})")
            print()
            
            # Display AI recommendation
            signal = analysis['signal']
            confidence = analysis['confidence']
            
            if signal == 'BUY':
                signal_color = '🟢'
                action = "✅ AI RECOMMENDS: HOLD/ACCUMULATE"
            elif signal == 'SELL':
                signal_color = '🔴'
                action = "⚠️  AI RECOMMENDS: CONSIDER SELLING"
            else:
                signal_color = '⚪'
                action = "⏸️  AI RECOMMENDS: HOLD (NEUTRAL)"
            
            print(f"{signal_color} AI SIGNAL: {signal} ({confidence}% confidence)")
            print(f"{action}")
            print()
            print(f"📝 AI Reasoning:")
            print(f"   {analysis['reasoning']}")
            print()
            
            if 'sentiment' in analysis:
                print(f"📊 Sentiment: {analysis['sentiment']} | Impact: {analysis.get('impact', 'N/A')}")
                print()
            
            # What would bot do?
            print("🤖 Bot Action:")
            if signal == 'SELL' and confidence >= 70:
                print(f"   If bot was managing this position, it would SELL now")
                print(f"   (Confidence {confidence}% meets threshold)")
            elif signal == 'BUY' and confidence >= 70:
                print(f"   Bot would BUY MORE if it had capital")
                print(f"   (Bullish signal with {confidence}% confidence)")
            else:
                print(f"   Bot would HOLD and continue monitoring")
                print(f"   (Signal: {signal}, Confidence: {confidence}%)")
            
            print()
        
        print("=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print("💡 Tips:")
        print("   • Run this regularly to monitor your portfolio")
        print("   • High confidence SELL signals (>75%) might warrant action")
        print("   • Consider setting up an AI bot to automatically manage positions")
        print()


def main():
    """Run the portfolio analyzer"""
    analyzer = PortfolioAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
