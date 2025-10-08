"""
Ticker-Based News Trading Strategy

Each bot:
- Tracks ONE specific ticker (BTC, ETH, SOL, etc.)
- Fetches news for that ticker hourly from CryptoNews API
- Uses AI to analyze news sentiment
- Makes trading decisions based on news
- Manages its own allocated capital independently
"""

import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TickerNewsStrategy:
    """Trading strategy driven by ticker-specific news analysis"""
    
    def __init__(self):
        self.name = "Ticker News Trading"
        
        # Ticker config (set by bot)
        self.ticker = None  # e.g., "BTC", "ETH", "SOL"
        self.symbol = None  # e.g., "BTCUSDT", "ETHUSDT"
        
        # News fetching
        self.news_api_key = os.getenv('CRYPTONEWS_API_KEY')
        self.last_news_fetch = None
        self.news_fetch_interval = 3600  # 1 hour in seconds
        self.cached_news = []
        self.cached_analysis = None
        
        # AI analysis
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        # Position tracking
        self.current_position = None  # 'long' or None
        self.entry_price = None
        self.entry_time = None
        
        # Risk management
        self.stop_loss_pct = 3.0  # 3% stop loss
        self.take_profit_pct = 5.0  # 5% take profit
        self.max_hold_hours = 48  # Max 48 hours per position
        
        # Confidence thresholds
        self.min_buy_confidence = 70  # 70% confidence to buy
        self.min_sell_confidence = 60  # 60% confidence to sell
        
        logger.info(f"✅ {self.name} initialized")
    
    def set_symbol(self, symbol):
        """Set the trading symbol and extract ticker"""
        self.symbol = symbol
        self.ticker = symbol.replace('USDT', '').replace('BUSD', '')
        logger.info(f"🎯 Ticker set to: {self.ticker} (Symbol: {self.symbol})")
    
    def set_position(self, symbol, entry_price):
        """Set position when bot buys"""
        self.current_position = 'long'
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        logger.info(f"📍 Position set: LONG @ ${entry_price:.2f}")
    
    def clear_position(self):
        """Clear position when bot sells"""
        self.current_position = None
        self.entry_price = None
        self.entry_time = None
        logger.info("✅ Position cleared")
    
    def should_fetch_news(self):
        """Check if it's time to fetch news"""
        if self.last_news_fetch is None:
            return True
        
        time_since_fetch = (datetime.now() - self.last_news_fetch).total_seconds()
        return time_since_fetch >= self.news_fetch_interval
    
    def fetch_ticker_news(self):
        """Fetch news specifically for this ticker"""
        try:
            import requests
            
            if not self.news_api_key:
                logger.warning("⚠️ No CryptoNews API key provided")
                return []
            
            # Fetch news for specific ticker
            url = f"https://cryptonews-api.com/api/v1"
            params = {
                'tickers': self.ticker,
                'items': 10,  # Get 10 articles
                'page': 1,
                'token': self.news_api_key
            }
            
            logger.info(f"📰 Fetching news for {self.ticker}...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('data', [])
            
            self.cached_news = articles
            self.last_news_fetch = datetime.now()
            
            logger.info(f"✅ Fetched {len(articles)} news articles for {self.ticker}")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Error fetching news for {self.ticker}: {e}")
            return []
    
    def analyze_news_with_ai(self, articles):
        """Use OpenAI to analyze news and make trading decision"""
        try:
            from openai import OpenAI
            
            if not self.openai_key:
                logger.warning("⚠️ No OpenAI API key provided")
                return None
            
            if not articles:
                logger.info("ℹ️ No articles to analyze")
                return None
            
            client = OpenAI(api_key=self.openai_key)
            
            # Prepare news summary for AI
            news_summary = ""
            for i, article in enumerate(articles[:10], 1):
                title = article.get('title', 'No title')
                text = article.get('text', '')[:200]  # First 200 chars
                sentiment = article.get('sentiment', 'neutral')
                news_summary += f"{i}. [{sentiment.upper()}] {title}\n   {text}...\n\n"
            
            # Create comprehensive prompt
            prompt = f"""You are an expert crypto trader analyzing news for {self.ticker}.

RECENT NEWS FOR {self.ticker}:
{news_summary}

Your task: Analyze this news and provide a clear trading recommendation.

Consider:
1. Overall sentiment (bullish/bearish/neutral)
2. News urgency and impact
3. Multiple article perspectives
4. Market implications

Respond in JSON format:
{{
    "signal": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "sentiment": "Positive" | "Negative" | "Neutral",
    "reasoning": "Brief explanation",
    "urgency": "low" | "medium" | "high",
    "risk_level": "low" | "medium" | "high"
}}

Be conservative - only recommend BUY/SELL with high confidence."""
            
            logger.info(f"🤖 Analyzing {len(articles)} articles with AI...")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert crypto trader and analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            content = response.choices[0].message.content
            
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(content)
            self.cached_analysis = analysis
            
            logger.info(f"🤖 AI Analysis: {analysis['signal']} ({analysis['confidence']}%) - {analysis['sentiment']}")
            logger.info(f"💡 Reasoning: {analysis['reasoning']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing news with AI: {e}")
            return None
    
    def check_technical_stops(self, current_price):
        """Check stop loss, take profit, and max hold time"""
        if not self.current_position:
            return None
        
        if not self.entry_price:
            return None
        
        # Calculate P&L
        pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        
        # Check stop loss
        if pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"🛑 STOP LOSS triggered: {pnl_pct:.2f}%")
            return {
                'signal': 'SELL',
                'reason': f'Stop loss triggered ({pnl_pct:.2f}%)',
                'confidence': 100
            }
        
        # Check take profit
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"💰 TAKE PROFIT triggered: {pnl_pct:.2f}%")
            return {
                'signal': 'SELL',
                'reason': f'Take profit triggered ({pnl_pct:.2f}%)',
                'confidence': 100
            }
        
        # Check max hold time
        if self.entry_time:
            hold_hours = (datetime.now() - self.entry_time).total_seconds() / 3600
            if hold_hours >= self.max_hold_hours:
                logger.warning(f"⏰ MAX HOLD TIME reached: {hold_hours:.1f} hours")
                return {
                    'signal': 'SELL',
                    'reason': f'Max hold time reached ({hold_hours:.1f}h)',
                    'confidence': 90
                }
        
        return None
    
    def analyze(self, klines, current_price=None, force_fresh_news=False):
        """
        Main analysis function
        
        Args:
            klines: Market data (not really used for news trading)
            current_price: Current price of the asset
            force_fresh_news: Force a fresh news fetch (ignore timer)
        
        Returns:
            dict: Signal data with 'signal', 'confidence', 'reasoning', etc.
        """
        try:
            if not self.ticker:
                logger.warning("⚠️ Ticker not set")
                return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'Ticker not configured'}
            
            # If we have a position, check technical stops first
            if self.current_position and current_price:
                stop_signal = self.check_technical_stops(current_price)
                if stop_signal:
                    return stop_signal
            
            # Check if we should fetch news
            if force_fresh_news or self.should_fetch_news():
                articles = self.fetch_ticker_news()
                
                if articles:
                    # Analyze with AI
                    analysis = self.analyze_news_with_ai(articles)
                    
                    if analysis:
                        signal = analysis['signal']
                        confidence = analysis['confidence']
                        
                        # Apply confidence thresholds
                        if signal == 'BUY' and confidence >= self.min_buy_confidence:
                            if self.current_position:
                                logger.info(f"📊 Already in position, ignoring BUY signal")
                                return {'signal': 'HOLD', 'confidence': confidence, 'reasoning': 'Already in position'}
                            else:
                                logger.info(f"🟢 BUY Signal: {confidence}% confidence")
                                return {
                                    'signal': 'BUY',
                                    'confidence': confidence,
                                    'reasoning': analysis['reasoning'],
                                    'sentiment': analysis.get('sentiment', 'Positive'),
                                    'urgency': analysis.get('urgency', 'medium')
                                }
                        
                        elif signal == 'SELL' and confidence >= self.min_sell_confidence:
                            if not self.current_position:
                                logger.info(f"📊 No position to sell, ignoring SELL signal")
                                return {'signal': 'HOLD', 'confidence': confidence, 'reasoning': 'No position to sell'}
                            else:
                                logger.info(f"🔴 SELL Signal: {confidence}% confidence")
                                return {
                                    'signal': 'SELL',
                                    'confidence': confidence,
                                    'reasoning': analysis['reasoning'],
                                    'sentiment': analysis.get('sentiment', 'Negative'),
                                    'urgency': analysis.get('urgency', 'medium')
                                }
                        
                        else:
                            logger.info(f"⏸️ HOLD: {signal} signal but confidence too low ({confidence}%)")
                            return {
                                'signal': 'HOLD',
                                'confidence': confidence,
                                'reasoning': f'{signal} signal but confidence below threshold'
                            }
                else:
                    logger.info("ℹ️ No news articles found, holding position")
                    return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'No news available'}
            else:
                # Not time to fetch news yet, use cached analysis or hold
                if self.cached_analysis:
                    time_since_fetch = (datetime.now() - self.last_news_fetch).total_seconds() / 60
                    logger.info(f"📋 Using cached analysis ({time_since_fetch:.0f} minutes old)")
                    return {
                        'signal': 'HOLD',
                        'confidence': self.cached_analysis.get('confidence', 0),
                        'reasoning': f"Waiting for next news cycle (last check: {time_since_fetch:.0f}m ago)"
                    }
                else:
                    return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'Waiting for first news fetch'}
            
            return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'No actionable signal'}
            
        except Exception as e:
            logger.error(f"❌ Error in analyze: {e}")
            import traceback
            traceback.print_exc()
            return {'signal': 'HOLD', 'confidence': 0, 'reasoning': f'Error: {str(e)}'}
    
    def generate_signal(self, klines, current_price=None, force_fresh_news=False):
        """Wrapper for analyze() for compatibility"""
        return self.analyze(klines, current_price, force_fresh_news)
