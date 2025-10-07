"""
AI News Trading Strategy

Monitors crypto news in real-time and uses AI to analyze sentiment
and generate trading signals based on breaking news.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from news_monitor import NewsMonitor
from ai_analyzer import AINewsAnalyzer

logger = logging.getLogger(__name__)

class AINewsStrategy:
    """
    Trading strategy based on AI analysis of crypto news
    
    Features:
    - Monitors multiple news sources
    - AI sentiment analysis with GPT-4
    - Automatic signal generation
    - Risk management based on confidence
    """
    
    def __init__(self, newsapi_key=None, openai_key=None):
        self.name = "AI News Trading"
        self.news_monitor = NewsMonitor(newsapi_key=newsapi_key)
        self.ai_analyzer = AINewsAnalyzer(api_key=openai_key)
        
        # Symbol to trade (set by live trader)
        self.symbol = 'BTCUSDT'
        
        # Configuration
        self.min_confidence = 75  # Minimum AI confidence to trade
        self.max_articles_per_cycle = 5  # Limit API costs
        self.check_interval = 300  # Check news every 5 minutes
        
        # Track last check time
        self.last_check = None
        
        # Cache recent analyses
        self.recent_analyses = []
        self.max_cache = 20
    
    def set_symbol(self, symbol):
        """Set the trading symbol for this strategy"""
        self.symbol = symbol
    
    def analyze(self, klines):
        """Wrapper for compatibility with live trader"""
        # Use the stored symbol (set by trader during initialization)
        return self.generate_signal(data=None, symbol=self.symbol)
    
    def generate_signal(self, data=None, symbol='BTCUSDT'):
        """
        Generate trading signal based on latest news
        
        This is called by the trading bot regularly
        
        Args:
            data: Not used (we fetch news ourselves)
            symbol: Trading pair to analyze for
            
        Returns:
            Dict with:
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0-100,
                'reasoning': str,
                'indicators': dict
            }
        """
        try:
            # Extract base symbol (BTC from BTCUSDT)
            base_symbol = symbol.replace('USDT', '').replace('BUSD', '')
            
            # Fetch latest news (last hour)
            logger.info(f"Checking news for {symbol}...")
            articles = self.news_monitor.fetch_crypto_news(
                symbols=[base_symbol, 'crypto', 'bitcoin', 'ethereum'],
                hours_back=1
            )
            
            if not articles:
                logger.info("No new articles found")
                return {
                    'signal': 'HOLD',
                    'confidence': 0,
                    'reasoning': 'No recent news',
                    'indicators': {'articles_found': 0}
                }
            
            logger.info(f"Found {len(articles)} articles, analyzing...")
            
            # Analyze articles
            analyses = []
            for article in articles[:self.max_articles_per_cycle]:
                analysis = self.ai_analyzer.analyze_news(article, symbol=symbol)
                analysis['article_title'] = article['title']
                analysis['article_time'] = article['published_at']
                analyses.append(analysis)
                
                # Cache for dashboard display
                self.recent_analyses.append({
                    'time': datetime.now().isoformat(),
                    'article': article['title'],
                    'analysis': analysis,
                    'symbol': symbol
                })
            
            # Limit cache size
            self.recent_analyses = self.recent_analyses[-self.max_cache:]
            
            if not analyses:
                return {
                    'signal': 'HOLD',
                    'confidence': 0,
                    'reasoning': 'AI analysis failed',
                    'indicators': {'articles_analyzed': 0}
                }
            
            # Aggregate results
            buy_signals = [a for a in analyses if a['signal'] == 'BUY' and a['confidence'] >= self.min_confidence]
            sell_signals = [a for a in analyses if a['signal'] == 'SELL' and a['confidence'] >= self.min_confidence]
            
            # Determine final signal
            if buy_signals and not sell_signals:
                # Strong buy signals, no sell signals
                avg_confidence = sum(a['confidence'] for a in buy_signals) / len(buy_signals)
                best_analysis = max(buy_signals, key=lambda x: x['confidence'])
                
                return {
                    'signal': 'BUY',
                    'confidence': int(avg_confidence),
                    'reasoning': f"AI detected bullish news: {best_analysis['reasoning']}",
                    'indicators': {
                        'articles_analyzed': len(analyses),
                        'buy_signals': len(buy_signals),
                        'sell_signals': len(sell_signals),
                        'top_article': best_analysis['article_title'],
                        'sentiment': best_analysis['sentiment'],
                        'impact': best_analysis['impact']
                    }
                }
            
            elif sell_signals and not buy_signals:
                # Strong sell signals, no buy signals
                avg_confidence = sum(a['confidence'] for a in sell_signals) / len(sell_signals)
                best_analysis = max(sell_signals, key=lambda x: x['confidence'])
                
                return {
                    'signal': 'SELL',
                    'confidence': int(avg_confidence),
                    'reasoning': f"AI detected bearish news: {best_analysis['reasoning']}",
                    'indicators': {
                        'articles_analyzed': len(analyses),
                        'buy_signals': len(buy_signals),
                        'sell_signals': len(sell_signals),
                        'top_article': best_analysis['article_title'],
                        'sentiment': best_analysis['sentiment'],
                        'impact': best_analysis['impact']
                    }
                }
            
            else:
                # Mixed signals or low confidence
                return {
                    'signal': 'HOLD',
                    'confidence': 50,
                    'reasoning': f"Mixed signals from {len(analyses)} articles",
                    'indicators': {
                        'articles_analyzed': len(analyses),
                        'buy_signals': len(buy_signals),
                        'sell_signals': len(sell_signals)
                    }
                }
        
        except Exception as e:
            logger.error(f"Error in news strategy: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasoning': f'Error: {str(e)}',
                'indicators': {}
            }
    
    def get_recent_analyses(self, limit=10):
        """Get recent news analyses for dashboard display"""
        return self.recent_analyses[-limit:]


def test_strategy():
    """Test the AI news strategy"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 70)
    print("🎯 TESTING AI NEWS TRADING STRATEGY")
    print("=" * 70)
    print()
    
    # Get API keys
    newsapi_key = os.getenv('NEWSAPI_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not newsapi_key:
        print("❌ No NEWSAPI_KEY found")
        print("Get free key at: https://newsapi.org/")
        return
    
    if not openai_key:
        print("❌ No OPENAI_API_KEY found")
        return
    
    # Create strategy
    strategy = AINewsStrategy(newsapi_key=newsapi_key, openai_key=openai_key)
    
    # Test on BTC
    print("Testing strategy on BTCUSDT...")
    print()
    
    signal_data = strategy.generate_signal(symbol='BTCUSDT')
    
    print("=" * 70)
    print("TRADING SIGNAL")
    print("=" * 70)
    print(f"Signal: {signal_data['signal']}")
    print(f"Confidence: {signal_data['confidence']}%")
    print(f"Reasoning: {signal_data['reasoning']}")
    
    if signal_data['indicators']:
        print(f"\nIndicators:")
        for key, value in signal_data['indicators'].items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("RECENT ANALYSES")
    print("=" * 70)
    
    for i, item in enumerate(strategy.get_recent_analyses()[:3], 1):
        print(f"\n{i}. {item['article']}")
        print(f"   Signal: {item['analysis']['signal']} ({item['analysis']['confidence']}%)")
        print(f"   Sentiment: {item['analysis']['sentiment']}")
        print(f"   Reasoning: {item['analysis']['reasoning']}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_strategy()
