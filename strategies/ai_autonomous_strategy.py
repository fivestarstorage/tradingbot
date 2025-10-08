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
        
        # Sentiment tracking for dashboard
        from ai_sentiment_tracker import AISentimentTracker
        self.sentiment_tracker = AISentimentTracker()
        
        # Configuration
        self.min_confidence = 70  # Lowered threshold for more trading opportunities
        self.max_articles_per_cycle = 5  # Analyze 5 articles in ONE OpenAI call
        
        # NO MORE HARDCODED LIST! 
        # We now dynamically check if coins are tradeable on Binance!
        self.binance_client = None  # Will be set by the trader
        
        # Cache of validated symbols to avoid repeated Binance API calls
        self.validated_symbols_cache = {}  # {symbol: is_tradeable}
        
        # Position Management
        self.current_position = None  # Which coin we're holding
        self.entry_price = None
        self.entry_time = None
        self.position_confidence = 0
        
        # Risk Management (BASE VALUES - AI can adjust these!)
        self.stop_loss_pct = 0.03  # 3% stop loss (base)
        self.take_profit_pct = 0.05  # 5% take profit (base)
        self.max_hold_hours = 24  # Max time to hold a position
        
        # Dynamic risk adjustment
        self.current_stop_loss = self.stop_loss_pct
        self.current_take_profit = self.take_profit_pct
        self.current_confidence_threshold = self.min_confidence
        
        # Cache analyses
        self.recent_analyses = []
        self.max_cache = 50
        
        # AI ANALYSIS CACHE (1 HOUR to ensure fresh news hourly!)
        self.ai_analysis_cache = {}  # article_id -> analysis result
        self.analysis_cache_time = {}  # article_id -> timestamp
        self.analysis_cache_duration = 3600  # 1 HOUR (not 8!) - Fresh news every hour!
        
        # Last decision
        self.last_decision = None
    
    def set_binance_client(self, client):
        """Set the Binance client for dynamic symbol validation"""
        self.binance_client = client
        logger.info("✅ Binance client connected - can now validate ANY coin dynamically!")
    
    def set_symbol(self, symbol):
        """Force strategy to focus on a specific symbol (used when holding position)"""
        logger.info(f"🔒 Strategy locked to {symbol} (position management mode)")
        # This is called by integrated_trader when we have a position
        # The strategy will respect this in generate_signal by checking current_position
    
    def is_symbol_valid(self, symbol):
        """
        Check if a symbol is tradeable on Binance (with caching)
        
        Args:
            symbol: Trading pair like 'BTCUSDT'
            
        Returns:
            Boolean: True if tradeable on Binance
        """
        # Check cache first
        if symbol in self.validated_symbols_cache:
            return self.validated_symbols_cache[symbol]
        
        # Validate with Binance
        if self.binance_client:
            is_valid = self.binance_client.is_symbol_tradeable(symbol)
            self.validated_symbols_cache[symbol] = is_valid
            return is_valid
        
        # Fallback: assume USDT pairs are valid
        logger.warning("No Binance client available, assuming symbol is valid")
        return symbol.endswith('USDT')
    
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
        
        # Stop loss hit (using DYNAMIC stop loss!)
        if pnl_pct <= -self.current_stop_loss:
            logger.warning(f"🛑 STOP LOSS HIT: {pnl_pct*100:.2f}% (limit: -{self.current_stop_loss*100:.1f}%)")
            return {
                'signal': 'SELL',
                'confidence': 95,
                'reasoning': f'Stop loss triggered at {pnl_pct*100:.2f}% loss',
                'recommended_symbol': self.current_position,
                'risk': {
                    'stop_loss': self.entry_price * (1 - self.current_stop_loss),
                    'take_profit': self.entry_price * (1 + self.current_take_profit),
                    'position_multiplier': 1.0,
                    'atr_value': 0
                }
            }
        
        # Take profit hit (using DYNAMIC take profit!)
        if pnl_pct >= self.current_take_profit:
            logger.info(f"🎯 TAKE PROFIT HIT: {pnl_pct*100:.2f}% (target: +{self.current_take_profit*100:.1f}%)")
            return {
                'signal': 'SELL',
                'confidence': 95,
                'reasoning': f'Take profit triggered at {pnl_pct*100:.2f}% gain',
                'recommended_symbol': self.current_position,
                'risk': {
                    'stop_loss': self.entry_price * (1 - self.current_stop_loss),
                    'take_profit': self.entry_price * (1 + self.current_take_profit),
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
    
    def adjust_strategy_from_ai_analysis(self, ai_decision):
        """
        🎯 DYNAMIC STRATEGY ADJUSTMENT
        
        The AI analysis influences trading parameters!
        Based on news sentiment, urgency, and risk level:
        - Adjusts stop-loss and take-profit
        - Changes confidence thresholds
        - Modifies trading aggressiveness
        """
        if not ai_decision:
            return
        
        sentiment = ai_decision.get('sentiment', 'neutral')
        urgency = ai_decision.get('urgency', 'moderate')
        risk_level = ai_decision.get('risk_level', 'medium')
        confidence = ai_decision.get('confidence', 50)
        
        # 1. ADJUST STOP-LOSS & TAKE-PROFIT BASED ON RISK
        if risk_level == 'high':
            # High risk news = tighter stops, smaller profits
            self.current_stop_loss = 0.02  # 2% stop (tighter)
            self.current_take_profit = 0.03  # 3% profit (take early)
            logger.info("🔴 HIGH RISK detected: Tighter stops (2%/-3%)")
        elif risk_level == 'low':
            # Low risk news = wider stops, bigger profits
            self.current_stop_loss = 0.04  # 4% stop (wider)
            self.current_take_profit = 0.08  # 8% profit (let it run)
            logger.info("🟢 LOW RISK detected: Wider stops (4%/-8%)")
        else:
            # Medium risk = normal settings
            self.current_stop_loss = self.stop_loss_pct
            self.current_take_profit = self.take_profit_pct
        
        # 2. ADJUST CONFIDENCE THRESHOLD BASED ON URGENCY
        if urgency == 'immediate':
            # Breaking news = act fast, lower threshold
            self.current_confidence_threshold = max(50, self.min_confidence - 10)
            logger.info(f"⚡ URGENT news: Lower confidence threshold to {self.current_confidence_threshold}%")
        elif urgency == 'high':
            self.current_confidence_threshold = max(55, self.min_confidence - 5)
            logger.info(f"🔥 High urgency: Confidence threshold at {self.current_confidence_threshold}%")
        else:
            # Normal urgency = normal threshold
            self.current_confidence_threshold = self.min_confidence
        
        # 3. ADJUST HOLD TIME BASED ON SENTIMENT STRENGTH
        if confidence >= 85 and sentiment in ['bullish', 'very bullish']:
            # Very strong bullish signal = hold longer
            self.max_hold_hours = 48
            logger.info("🚀 Strong bullish signal: Extended hold time to 48h")
        elif sentiment in ['bearish', 'very bearish'] and confidence >= 75:
            # Strong bearish signal = shorter hold, exit quickly
            self.max_hold_hours = 12
            logger.info("📉 Strong bearish signal: Reduced hold time to 12h")
        else:
            self.max_hold_hours = 24  # Default
        
        # Log the adjusted strategy
        logger.info(f"📊 Strategy adjusted: SL={self.current_stop_loss*100:.1f}% | TP={self.current_take_profit*100:.1f}% | Confidence={self.current_confidence_threshold}% | Hold={self.max_hold_hours}h")
    
    def generate_signal(self, data=None, symbol='BTCUSDT', current_price=None, force_fresh_news=False):
        """
        Generate trading signal - AI picks the coin!
        
        ENHANCED with Position Management:
        - If we have a position: Monitor that coin + check stops
        - If no position: Scan ALL news for best opportunity
        
        Args:
            data: Not used (AI fetches news)
            symbol: Default symbol (overridden by AI)
            current_price: Current price for position management
            force_fresh_news: If True, fetch fresh news (bypassing cache) - used on startup
        
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
                    hours_back=1,  # Recent news only
                    force_fresh=force_fresh_news
                )
                
                if articles:
                    # Use BATCH ANALYSIS with caching for position management too!
                    cache_key = f"position_{self.current_position}_" + "_".join([a.get('title', '')[:20] for a in articles[:3]])
                    
                    if cache_key in self.ai_analysis_cache:
                        cache_time = self.analysis_cache_time.get(cache_key, 0)
                        time_since_analysis = datetime.now().timestamp() - cache_time
                        
                        if time_since_analysis < self.analysis_cache_duration:
                            # Use cached AI analysis!
                            position_analysis = self.ai_analysis_cache[cache_key]
                            logger.info(f"💾 Using cached position analysis ({int(self.analysis_cache_duration - time_since_analysis)}s until refresh)")
                        else:
                            # Cache expired, analyze fresh
                            logger.info(f"🤖 Analyzing {len(articles[:3])} articles for {self.current_position}...")
                            position_analysis = self.ai_analyzer.batch_analyze_comprehensive(
                                articles=articles,
                                max_articles=3  # Just check top 3 for positions
                            )
                            # Update cache
                            self.ai_analysis_cache[cache_key] = position_analysis
                            self.analysis_cache_time[cache_key] = datetime.now().timestamp()
                    else:
                        # No cache, analyze fresh
                        logger.info(f"🤖 Analyzing {len(articles[:3])} articles for {self.current_position}...")
                        position_analysis = self.ai_analyzer.batch_analyze_comprehensive(
                            articles=articles,
                            max_articles=3  # Just check top 3 for positions
                        )
                        # Cache the result
                        self.ai_analysis_cache[cache_key] = position_analysis
                        self.analysis_cache_time[cache_key] = datetime.now().timestamp()
                    
                    # If negative news with high confidence, sell
                    if position_analysis['signal'] == 'SELL' and position_analysis['confidence'] >= 75:
                        logger.warning(f"📉 Negative news detected for {self.current_position}!")
                        return {
                            'signal': 'SELL',
                            'confidence': position_analysis['confidence'],
                            'reasoning': f"Negative news: {position_analysis['reasoning']}",
                            'recommended_symbol': self.current_position,
                            'indicators': {
                                'sentiment': position_analysis['sentiment'],
                                'impact': position_analysis['impact']
                            },
                            'risk': {
                                'stop_loss': self.entry_price * (1 - self.current_stop_loss),
                                'take_profit': self.entry_price * (1 + self.current_take_profit),
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
                hours_back=2,  # Last 2 hours
                force_fresh=force_fresh_news
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
            
            logger.info(f"📰 Found {len(articles)} articles")
            
            # CHECK AI ANALYSIS CACHE FIRST!
            # Create cache key from first few article titles (represents this batch)
            cache_key = "_".join([a.get('title', '')[:30] for a in articles[:5]])
            
            # Check if we've analyzed this batch recently
            if cache_key in self.ai_analysis_cache:
                cache_time = self.analysis_cache_time.get(cache_key, 0)
                time_since_analysis = datetime.now().timestamp() - cache_time
                
                if time_since_analysis < self.analysis_cache_duration:
                    # Use cached AI analysis!
                    batch_result = self.ai_analysis_cache[cache_key]
                    logger.info(f"💾 Using cached AI analysis ({int(self.analysis_cache_duration - time_since_analysis)}s until refresh)")
                    logger.info(f"   Saved OpenAI API call! Last analyzed {int(time_since_analysis)}s ago")
                else:
                    # Cache expired, analyze fresh
                    logger.info(f"🤖 Sending {min(len(articles), self.max_articles_per_cycle)} articles to AI in ONE batch analysis...")
                    batch_result = self.ai_analyzer.batch_analyze_comprehensive(
                        articles=articles,
                        max_articles=self.max_articles_per_cycle
                    )
                    # Update cache
                    self.ai_analysis_cache[cache_key] = batch_result
                    self.analysis_cache_time[cache_key] = datetime.now().timestamp()
            else:
                # No cache, analyze fresh
                logger.info(f"🤖 Sending {min(len(articles), self.max_articles_per_cycle)} articles to AI in ONE batch analysis...")
                batch_result = self.ai_analyzer.batch_analyze_comprehensive(
                    articles=articles,
                    max_articles=self.max_articles_per_cycle
                )
                # Cache the result
                self.ai_analysis_cache[cache_key] = batch_result
                self.analysis_cache_time[cache_key] = datetime.now().timestamp()
            
            logger.info(f"✅ Batch analysis complete:")
            logger.info(f"   Signal: {batch_result['signal']}")
            logger.info(f"   Confidence: {batch_result['confidence']}%")
            logger.info(f"   Recommended: {batch_result.get('recommended_symbol', 'N/A')}")
            logger.info(f"   Reasoning: {batch_result['reasoning'][:100]}...")
            
            # 🎯 DYNAMICALLY ADJUST STRATEGY BASED ON AI ANALYSIS!
            self.adjust_strategy_from_ai_analysis(batch_result)
            
            # Track for dashboard
            self.sentiment_tracker.add_analysis(
                article_title=f"Batch Analysis ({batch_result['articles_analyzed']} articles)",
                analysis=batch_result,
                mentioned_symbols=[batch_result.get('recommended_symbol', 'BTCUSDT')]
            )
            
            # Validate the recommended symbol
            recommended_symbol = batch_result.get('recommended_symbol', 'BTCUSDT')
            if self.is_symbol_valid(recommended_symbol):
                logger.info(f"✅ {recommended_symbol} is tradeable on Binance")
                
                # Track trade decision if confidence is high enough (use DYNAMIC threshold!)
                if batch_result['signal'] in ['BUY', 'SELL'] and batch_result['confidence'] >= self.current_confidence_threshold:
                    logger.info(f"🎯 AI recommends {batch_result['signal']} {recommended_symbol} (confidence: {batch_result['confidence']}% >= {self.current_confidence_threshold}%)")
                    
                    return {
                        'signal': batch_result['signal'],
                        'confidence': batch_result['confidence'],
                        'reasoning': batch_result['reasoning'],
                        'recommended_symbol': recommended_symbol,
                        'indicators': {
                            'articles_analyzed': batch_result['articles_analyzed'],
                            'sentiment': batch_result['sentiment'],
                            'impact': batch_result['impact'],
                            'urgency': batch_result['urgency'],
                            'risk_level': batch_result.get('risk_level', 'medium')
                        }
                    }
                else:
                    logger.info(f"⏸️ Confidence {batch_result['confidence']}% below threshold {self.min_confidence}%")
                    return {
                        'signal': 'HOLD',
                        'confidence': batch_result['confidence'],
                        'reasoning': f"Confidence {batch_result['confidence']}% below threshold",
                        'recommended_symbol': symbol,
                        'indicators': {
                            'articles_analyzed': batch_result['articles_analyzed']
                        }
                    }
            else:
                logger.warning(f"❌ {recommended_symbol} not tradeable on Binance")
                return {
                    'signal': 'HOLD',
                    'confidence': 50,
                    'reasoning': f"{recommended_symbol} not available for trading",
                    'recommended_symbol': symbol,
                    'indicators': {}
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
        return []  # No longer used with batch analysis
    
    # OLD CODE REMOVED - Using batch_analyze_comprehensive now
    # This reduces OpenAI calls from 50/cycle to 1/cycle!


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
