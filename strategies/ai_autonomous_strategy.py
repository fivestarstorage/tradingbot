"""
AI Autonomous Trading Strategy

The AI decides WHICH coin to buy based on news analysis.
Monitors all crypto news and picks the best trading opportunity.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from news_monitor import NewsMonitor
from ai_analyzer import AINewsAnalyzer

logger = logging.getLogger(__name__)

class AIAutonomousStrategy:
    """
    Fully autonomous AI trading - AI picks the coin!
    
    Features:
    - Monitors ALL crypto news (not just one coin)
    - AI analyzes and recommends which coin to trade
    - Filters for crypto/blockchain news only
    - Trades the highest confidence opportunity
    """
    
    def __init__(self, newsapi_key=None, openai_key=None):
        self.name = "AI Autonomous Trading"
        
        # Load from environment if not provided
        import os
        if newsapi_key is None:
            newsapi_key = os.getenv('NEWSAPI_KEY')
        if openai_key is None:
            openai_key = os.getenv('OPENAI_API_KEY')
        
        self.news_monitor = NewsMonitor(newsapi_key=newsapi_key)
        self.ai_analyzer = AINewsAnalyzer(api_key=openai_key)
        
        # Configuration
        self.min_confidence = 80  # Higher threshold for autonomous trading
        self.max_articles_per_cycle = 20  # Analyze MORE news articles
        
        # Supported trading pairs on Binance
        self.supported_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT',
            'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'ATOMUSDT', 'ETCUSDT'
        ]
        
        # Position Management
        self.current_position = None  # Which coin we're holding
        self.entry_price = None
        self.entry_time = None
        self.position_confidence = 0
        
        # Risk Management
        self.stop_loss_pct = 0.03  # 3% stop loss
        self.take_profit_pct = 0.05  # 5% take profit
        self.max_hold_hours = 24  # Max time to hold a position
        
        # Cache analyses
        self.recent_analyses = []
        self.max_cache = 50
        
        # Last decision
        self.last_decision = None
    
    def analyze(self, klines):
        """Wrapper for compatibility with live trader"""
        # Extract current price if we have a position
        current_price = None
        if klines and len(klines) > 0:
            current_price = float(klines[-1][4])  # Close price
        
        return self.generate_signal(data=None, symbol='BTCUSDT', current_price=current_price)
    
    def set_position(self, symbol, entry_price):
        """Called when a position is opened"""
        from datetime import datetime
        self.current_position = symbol
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        logger.info(f"📍 Position set: {symbol} @ ${entry_price:.2f}")
    
    def clear_position(self):
        """Called when a position is closed"""
        logger.info(f"✅ Position cleared: {self.current_position}")
        self.current_position = None
        self.entry_price = None
        self.entry_time = None
        self.position_confidence = 0
    
    def check_technical_stops(self, current_price):
        """Check if stop loss or take profit is hit"""
        if not self.current_position or not self.entry_price:
            return None
        
        # Calculate P&L
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Stop loss hit
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"🛑 STOP LOSS HIT: {pnl_pct*100:.2f}%")
            return {
                'signal': 'SELL',
                'confidence': 95,
                'reasoning': f'Stop loss triggered at {pnl_pct*100:.2f}% loss',
                'recommended_symbol': self.current_position,
                'risk': {
                    'stop_loss': self.entry_price * (1 - self.stop_loss_pct),
                    'take_profit': self.entry_price * (1 + self.take_profit_pct),
                    'position_multiplier': 1.0,
                    'atr_value': 0
                }
            }
        
        # Take profit hit
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"🎯 TAKE PROFIT HIT: {pnl_pct*100:.2f}%")
            return {
                'signal': 'SELL',
                'confidence': 95,
                'reasoning': f'Take profit triggered at {pnl_pct*100:.2f}% gain',
                'recommended_symbol': self.current_position,
                'risk': {
                    'stop_loss': self.entry_price * (1 - self.stop_loss_pct),
                    'take_profit': self.entry_price * (1 + self.take_profit_pct),
                    'position_multiplier': 1.0,
                    'atr_value': 0
                }
            }
        
        # Check max hold time
        if self.entry_time:
            from datetime import datetime, timedelta
            hold_duration = datetime.now() - self.entry_time
            if hold_duration > timedelta(hours=self.max_hold_hours):
                logger.info(f"⏰ MAX HOLD TIME REACHED: {hold_duration.total_seconds()/3600:.1f}h")
                return {
                    'signal': 'SELL',
                    'confidence': 80,
                    'reasoning': f'Maximum hold time ({self.max_hold_hours}h) reached',
                    'recommended_symbol': self.current_position,
                    'risk': {
                        'stop_loss': self.entry_price * (1 - self.stop_loss_pct),
                        'take_profit': self.entry_price * (1 + self.take_profit_pct),
                        'position_multiplier': 1.0,
                        'atr_value': 0
                    }
                }
        
        return None
    
    def generate_signal(self, data=None, symbol='BTCUSDT', current_price=None):
        """
        Generate trading signal - AI picks the coin!
        
        ENHANCED with Position Management:
        - If we have a position: Monitor that coin + check stops
        - If no position: Scan ALL news for best opportunity
        
        Args:
            data: Not used (AI fetches news)
            symbol: Default symbol (overridden by AI)
            current_price: Current price for position management
        
        Returns:
            Dict with:
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0-100,
                'reasoning': str,
                'recommended_symbol': str (which coin to trade),
                'indicators': dict,
                'risk': dict (stop loss, take profit)
            }
        """
        try:
            # === POSITION MANAGEMENT MODE ===
            if self.current_position:
                logger.info(f"📊 Managing position: {self.current_position}")
                
                # Check technical stops first
                if current_price:
                    stop_signal = self.check_technical_stops(current_price)
                    if stop_signal:
                        return stop_signal
                
                # Monitor news for the held coin
                logger.info(f"📰 Checking news for {self.current_position}...")
                coin_name = self.current_position.replace('USDT', '').lower()
                
                articles = self.news_monitor.fetch_crypto_news(
                    symbols=[coin_name, 'crypto', 'cryptocurrency'],
                    hours_back=1  # Recent news only
                )
                
                if articles:
                    for article in articles[:5]:  # Check recent articles
                        analysis = self.ai_analyzer.analyze_news(article)
                        
                        # If negative news with high confidence, sell
                        if analysis['signal'] == 'SELL' and analysis['confidence'] >= 75:
                            logger.warning(f"📉 Negative news detected for {self.current_position}!")
                            return {
                                'signal': 'SELL',
                                'confidence': analysis['confidence'],
                                'reasoning': f"Negative news: {analysis['reasoning']}",
                                'recommended_symbol': self.current_position,
                                'indicators': {
                                    'news_headline': article['title'],
                                    'sentiment': analysis['sentiment'],
                                    'impact': analysis['impact']
                                },
                                'risk': {
                                    'stop_loss': self.entry_price * (1 - self.stop_loss_pct),
                                    'take_profit': self.entry_price * (1 + self.take_profit_pct),
                                    'position_multiplier': 1.0,
                                    'atr_value': 0
                                }
                            }
                
                # Position OK, no action needed
                pnl_pct = ((current_price - self.entry_price) / self.entry_price * 100) if current_price else 0
                return {
                    'signal': 'HOLD',
                    'confidence': 70,
                    'reasoning': f'Holding {self.current_position} (P&L: {pnl_pct:+.2f}%)',
                    'recommended_symbol': self.current_position,
                    'indicators': {'position': True, 'pnl_pct': pnl_pct},
                    'risk': {
                        'stop_loss': self.entry_price * (1 - self.stop_loss_pct),
                        'take_profit': self.entry_price * (1 + self.take_profit_pct),
                        'position_multiplier': 1.0,
                        'atr_value': 0
                    }
                }
            
            # === OPPORTUNITY SCANNING MODE ===
            logger.info("🤖 AI scanning all crypto news for opportunities...")
            
            # Fetch broad crypto news
            articles = self.news_monitor.fetch_crypto_news(
                symbols=[
                    'cryptocurrency', 'crypto', 'bitcoin', 'ethereum', 
                    'blockchain', 'defi', 'web3', 'altcoin', 'binance'
                ],
                hours_back=2  # Last 2 hours
            )
            
            if not articles:
                logger.info("No new crypto news found")
                return {
                    'signal': 'HOLD',
                    'confidence': 0,
                    'reasoning': 'No recent crypto news',
                    'recommended_symbol': symbol,  # Default
                    'indicators': {'articles_found': 0}
                }
            
            logger.info(f"📰 Found {len(articles)} articles, AI analyzing...")
            
            # Analyze all articles and collect recommendations
            recommendations = []
            
            for article in articles[:self.max_articles_per_cycle]:
                analysis = self.ai_analyzer.analyze_news(article)
                
                # Extract mentioned symbols
                mentioned = self.news_monitor.extract_mentioned_symbols(
                    article['title'] + ' ' + article['description']
                )
                
                # Use AI-provided symbols or extracted ones
                symbols_to_consider = analysis.get('symbols', mentioned) or mentioned
                
                # Filter to supported symbols
                valid_symbols = [s for s in symbols_to_consider if s in self.supported_symbols]
                
                if valid_symbols and analysis['signal'] in ['BUY', 'SELL']:
                    for sym in valid_symbols:
                        recommendations.append({
                            'symbol': sym,
                            'signal': analysis['signal'],
                            'confidence': analysis['confidence'],
                            'sentiment': analysis['sentiment'],
                            'impact': analysis['impact'],
                            'urgency': analysis['urgency'],
                            'reasoning': analysis['reasoning'],
                            'article_title': article['title'],
                            'article_time': article['published_at']
                        })
                
                # Cache for display
                self.recent_analyses.append({
                    'time': datetime.now().isoformat(),
                    'article': article['title'],
                    'analysis': analysis,
                    'symbols': valid_symbols
                })
            
            # Limit cache
            self.recent_analyses = self.recent_analyses[-self.max_cache:]
            
            if not recommendations:
                return {
                    'signal': 'HOLD',
                    'confidence': 50,
                    'reasoning': f'Analyzed {len(articles[:self.max_articles_per_cycle])} articles - no high-confidence signals',
                    'recommended_symbol': symbol,
                    'indicators': {
                        'articles_analyzed': len(articles[:self.max_articles_per_cycle]),
                        'recommendations': 0
                    }
                }
            
            # Find best opportunity
            buy_recs = [r for r in recommendations if r['signal'] == 'BUY' and r['confidence'] >= self.min_confidence]
            sell_recs = [r for r in recommendations if r['signal'] == 'SELL' and r['confidence'] >= self.min_confidence]
            
            best_rec = None
            
            if buy_recs:
                # Sort by: high impact > high confidence > urgent
                buy_recs.sort(key=lambda x: (
                    x['impact'] == 'high',
                    x['confidence'],
                    x['urgency'] == 'immediate'
                ), reverse=True)
                best_rec = buy_recs[0]
                
                logger.info(f"🎯 AI recommends BUY {best_rec['symbol']} (confidence: {best_rec['confidence']}%)")
                
                return {
                    'signal': 'BUY',
                    'confidence': best_rec['confidence'],
                    'reasoning': f"AI chose {best_rec['symbol']}: {best_rec['reasoning']}",
                    'recommended_symbol': best_rec['symbol'],
                    'indicators': {
                        'articles_analyzed': len(articles[:self.max_articles_per_cycle]),
                        'total_recommendations': len(recommendations),
                        'buy_opportunities': len(buy_recs),
                        'sell_opportunities': len(sell_recs),
                        'news_headline': best_rec['article_title'],
                        'sentiment': best_rec['sentiment'],
                        'impact': best_rec['impact'],
                        'urgency': best_rec['urgency']
                    }
                }
            
            elif sell_recs:
                sell_recs.sort(key=lambda x: (
                    x['impact'] == 'high',
                    x['confidence'],
                    x['urgency'] == 'immediate'
                ), reverse=True)
                best_rec = sell_recs[0]
                
                logger.info(f"⚠️ AI recommends SELL {best_rec['symbol']} (confidence: {best_rec['confidence']}%)")
                
                return {
                    'signal': 'SELL',
                    'confidence': best_rec['confidence'],
                    'reasoning': f"AI chose {best_rec['symbol']}: {best_rec['reasoning']}",
                    'recommended_symbol': best_rec['symbol'],
                    'indicators': {
                        'articles_analyzed': len(articles[:self.max_articles_per_cycle]),
                        'total_recommendations': len(recommendations),
                        'buy_opportunities': len(buy_recs),
                        'sell_opportunities': len(sell_recs),
                        'news_headline': best_rec['article_title'],
                        'sentiment': best_rec['sentiment'],
                        'impact': best_rec['impact']
                    }
                }
            
            else:
                return {
                    'signal': 'HOLD',
                    'confidence': 60,
                    'reasoning': f'Found {len(recommendations)} signals but none above {self.min_confidence}% confidence',
                    'recommended_symbol': symbol,
                    'indicators': {
                        'articles_analyzed': len(articles[:self.max_articles_per_cycle]),
                        'total_recommendations': len(recommendations),
                        'highest_confidence': max([r['confidence'] for r in recommendations]) if recommendations else 0
                    }
                }
        
        except Exception as e:
            logger.error(f"Error in autonomous AI strategy: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'reasoning': f'Error: {str(e)}',
                'recommended_symbol': symbol,
                'indicators': {}
            }
    
    def get_recent_analyses(self, limit=10):
        """Get recent analyses for dashboard"""
        return self.recent_analyses[-limit:]


def test_strategy():
    """Test the autonomous AI strategy"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 70)
    print("🤖 TESTING AI AUTONOMOUS TRADING STRATEGY")
    print("=" * 70)
    print()
    
    newsapi_key = os.getenv('NEWSAPI_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not newsapi_key:
        print("❌ No NEWSAPI_KEY found")
        return
    
    if not openai_key:
        print("❌ No OPENAI_API_KEY found")
        return
    
    strategy = AIAutonomousStrategy(newsapi_key=newsapi_key, openai_key=openai_key)
    
    print("🔍 AI scanning crypto news and picking best opportunity...")
    print()
    
    signal_data = strategy.generate_signal()
    
    print("=" * 70)
    print("🎯 AI DECISION")
    print("=" * 70)
    print(f"Signal: {signal_data['signal']}")
    print(f"Recommended Coin: {signal_data['recommended_symbol']}")
    print(f"Confidence: {signal_data['confidence']}%")
    print(f"Reasoning: {signal_data['reasoning']}")
    
    if signal_data['indicators']:
        print(f"\n📊 Details:")
        for key, value in signal_data['indicators'].items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("📰 RECENT ANALYSES")
    print("=" * 70)
    
    for i, item in enumerate(strategy.get_recent_analyses()[:5], 1):
        print(f"\n{i}. {item['article']}")
        print(f"   Symbols: {', '.join(item['symbols']) if item['symbols'] else 'None'}")
        print(f"   Signal: {item['analysis']['signal']} ({item['analysis']['confidence']}%)")
        print(f"   Sentiment: {item['analysis']['sentiment']} | Impact: {item['analysis']['impact']}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_strategy()
