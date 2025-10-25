"""
Portfolio Management Service
Monitors existing holdings and makes trading decisions based on:
1. News sentiment for the coin
2. Technical analysis (price candles)
3. Traditional trading strategies
4. Hybrid AI model (combines news + technical)
"""
from sqlalchemy.orm import Session
from core.binance_client import BinanceClient
from .models import NewsArticle, Signal, BotLog
from datetime import datetime, timedelta, timezone
import openai
import os
import json
import numpy as np

# SMS notifications
try:
    from .twilio_notifier import TwilioNotifier
except ImportError:
    TwilioNotifier = None


class PortfolioManager:
    def __init__(self, client: BinanceClient):
        self.client = client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        # Initialize SMS notifier
        self.sms_notifier = TwilioNotifier() if TwilioNotifier else None
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        if down == 0:
            return 100
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray) -> tuple:
        """Calculate MACD"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd = ema_12 - ema_26
        signal = macd  # Simplified - should be EMA of MACD
        return macd, signal
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def calculate_technical_indicators(self, symbol: str):
        """Calculate comprehensive technical indicators for a symbol"""
        try:
            # Get candles (5m, 50 periods = 4 hours of data)
            candles = self.get_recent_candles(symbol, interval='5m', limit=50)
            if not candles or len(candles) < 20:
                return None
            
            closes = np.array([float(c['close']) for c in candles])
            volumes = np.array([float(c['volume']) for c in candles])
            
            current_price = closes[-1]
            
            # Calculate indicators
            rsi = self._calculate_rsi(closes, period=14)
            macd, macd_signal = self._calculate_macd(closes)
            ema_20 = self._calculate_ema(closes, 20)
            ema_50 = self._calculate_ema(closes, 50)
            sma_20 = np.mean(closes[-20:])
            sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma_20
            
            # Price changes
            price_change_5m = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0
            price_change_1h = ((closes[-1] - closes[-13]) / closes[-13] * 100) if len(closes) >= 13 else 0
            
            # Volume analysis
            avg_volume = np.mean(volumes[:-1])
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Technical score (0-100)
            technical_score = 0
            
            # RSI contribution (30 points)
            if 40 <= rsi <= 60:
                technical_score += 30
            elif 30 <= rsi <= 70:
                technical_score += 20
            elif rsi < 30:  # Oversold
                technical_score += 10
            else:  # Overbought (> 70)
                technical_score += 5
            
            # MACD contribution (30 points)
            if macd > macd_signal:
                technical_score += 30
            elif macd > 0:
                technical_score += 15
            
            # Trend contribution (40 points)
            if current_price > ema_20 > ema_50:
                technical_score += 40
            elif current_price > ema_20:
                technical_score += 25
            elif current_price > ema_50:
                technical_score += 15
            
            return {
                'current_price': float(current_price),
                'rsi': float(rsi),
                'macd': float(macd),
                'macd_signal': float(macd_signal),
                'ema_20': float(ema_20),
                'ema_50': float(ema_50),
                'sma_20': float(sma_20),
                'sma_50': float(sma_50),
                'price_change_5m': float(price_change_5m),
                'price_change_1h': float(price_change_1h),
                'volume_ratio': float(volume_ratio),
                'technical_score': int(technical_score),
                'trend': 'up' if current_price > ema_20 > ema_50 else 'down'
            }
        except Exception as e:
            print(f"Error calculating technical indicators for {symbol}: {e}")
            return None
    
    def calculate_news_score(self, db: Session, asset: str) -> dict:
        """Calculate news sentiment score for an asset"""
        try:
            # Get news from last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            news = db.query(NewsArticle).filter(
                NewsArticle.tickers.like(f'%{asset}%'),
                NewsArticle.created_at >= since
            ).order_by(NewsArticle.created_at.desc()).limit(20).all()
            
            if not news:
                return {
                    'news_score': 50,  # Neutral
                    'news_count': 0,
                    'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0},
                    'trend': 'neutral',
                    'latest_headline': None
                }
            
            # Count sentiments
            positive = sum(1 for n in news if (n.sentiment or '').lower().startswith('pos'))
            negative = sum(1 for n in news if (n.sentiment or '').lower().startswith('neg'))
            neutral = len(news) - positive - negative
            
            # Calculate score (0-100)
            if len(news) > 0:
                news_score = (positive * 100 + neutral * 50) / len(news)
            else:
                news_score = 50
            
            # Determine trend
            recent_news = news[:5]
            recent_positive = sum(1 for n in recent_news if (n.sentiment or '').lower().startswith('pos'))
            if recent_positive >= 3:
                trend = 'improving'
            elif recent_positive <= 1:
                trend = 'declining'
            else:
                trend = 'stable'
            
            return {
                'news_score': int(news_score),
                'news_count': len(news),
                'sentiment_breakdown': {
                    'positive': positive,
                    'neutral': neutral,
                    'negative': negative
                },
                'trend': trend,
                'latest_headline': news[0].title if news else None
            }
        except Exception as e:
            print(f"Error calculating news score for {asset}: {e}")
            return {
                'news_score': 50,
                'news_count': 0,
                'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0},
                'trend': 'neutral',
                'latest_headline': None
            }
    
    def get_portfolio_holdings(self):
        """Get all non-zero holdings from Binance."""
        try:
            account = self.client.client.get_account()
            balances = account.get('balances', [])
            
            holdings = []
            for balance in balances:
                asset = balance.get('asset')
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked
                
                # Skip USDT and zero balances
                if asset == 'USDT' or total <= 0:
                    continue
                    
                symbol = f"{asset}USDT"
                # Only include if tradeable
                if self.client.is_symbol_tradeable(symbol):
                    holdings.append({
                        'asset': asset,
                        'symbol': symbol,
                        'quantity': total,
                        'free': free,
                        'locked': locked
                    })
            
            return holdings
        except Exception as e:
            print(f"Error getting portfolio: {e}")
            return []
    
    def get_recent_candles(self, symbol: str, interval='5m', limit=50):
        """Get recent price candles for technical analysis."""
        try:
            candles = self.client.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Format: [open_time, open, high, low, close, volume, ...]
            formatted = []
            for candle in candles:
                formatted.append({
                    'time': datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            return formatted
        except Exception as e:
            print(f"Error getting candles for {symbol}: {e}")
            return []
    
    def get_news_for_asset(self, db: Session, asset: str, hours: int = 6):
        """Get recent news mentioning this asset."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        news = db.query(NewsArticle).filter(
            NewsArticle.created_at >= since,
            NewsArticle.tickers.like(f'%{asset}%')
        ).order_by(NewsArticle.created_at.desc()).limit(10).all()
        
        return news
    
    def analyze_holding(self, db: Session, holding: dict):
        """
        Analyze a single holding using HYBRID news + technical data.
        Returns: {action, confidence, reasoning, news_score, technical_score, hybrid_score}
        """
        symbol = holding['symbol']
        asset = holding['asset']
        quantity = holding['quantity']
        
        # Calculate technical indicators
        technical = self.calculate_technical_indicators(symbol)
        
        # Calculate news score
        news_data = self.calculate_news_score(db, asset)
        
        if not technical:
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': 'No price data available',
                'symbol': symbol,
                'news_score': news_data['news_score'],
                'technical_score': 0,
                'hybrid_score': news_data['news_score'] // 2
            }
        
        current_price = technical['current_price']
        
        # Calculate hybrid score (weighted: 40% news, 60% technical)
        hybrid_score = int(news_data['news_score'] * 0.4 + technical['technical_score'] * 0.6)
        
        # Format news context for AI
        news = self.get_news_for_asset(db, asset, hours=6)
        news_context = ""
        if news:
            news_context = "Recent news:\n"
            for n in news[:5]:
                news_context += f"- {n.title} ({n.sentiment})\n"
        else:
            news_context = "No recent news for this asset."
        
        # AI analysis prompt with hybrid data
        prompt = f"""You are a crypto portfolio manager. Analyze this holding using BOTH technical and news data.

Asset: {asset} ({symbol})
Current Holdings: {quantity:.6f} {asset}
Current Price: ${current_price:.4f}
Value: ${current_price * quantity:.2f}

📊 TECHNICAL ANALYSIS (Score: {technical['technical_score']}/100):
- RSI: {technical['rsi']:.1f}
- MACD: {technical['macd']:.4f} (Signal: {technical['macd_signal']:.4f})
- EMA 20: ${technical['ema_20']:.4f}
- EMA 50: ${technical['ema_50']:.4f}
- Price change (5min): {technical['price_change_5m']:+.2f}%
- Price change (1hr): {technical['price_change_1h']:+.2f}%
- Volume ratio: {technical['volume_ratio']:.2f}x
- Trend: {technical['trend']}

📰 NEWS ANALYSIS (Score: {news_data['news_score']}/100):
- News count (24h): {news_data['news_count']}
- Sentiment: {news_data['sentiment_breakdown']['positive']} pos, {news_data['sentiment_breakdown']['neutral']} neu, {news_data['sentiment_breakdown']['negative']} neg
- Trend: {news_data['trend']}
{news_context}

🤖 HYBRID SCORE: {hybrid_score}/100
(40% news + 60% technical)

Based on this data, should we:
- SELL (take profits, cut losses, or exit on weak signals)
- HOLD (maintain position, strong fundamentals)
- BUY_MORE (add to position - only if strong conviction)

Respond in JSON format:
{{
  "action": "SELL" | "HOLD" | "BUY_MORE",
  "confidence": 0-100,
  "reasoning": "Brief explanation combining both technical and news analysis",
  "exit_reason": "technical" | "news" | "both" | null (if action is SELL)
}}

Trading philosophy:
- SELL if hybrid score < 40 (weak on both fronts)
- SELL if RSI > 70 AND news declining
- SELL if negative news AND broken technical support
- HOLD if hybrid score 40-75
- BUY_MORE only if hybrid score > 80 with strong conviction
- Consider risk management: stop losses on 5%+ drops
"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a prudent crypto portfolio manager focused on risk management. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add context and scores
            result['symbol'] = symbol
            result['current_price'] = current_price
            result['quantity'] = quantity
            result['value'] = current_price * quantity
            result['news_score'] = news_data['news_score']
            result['technical_score'] = technical['technical_score']
            result['hybrid_score'] = hybrid_score
            result['news_data'] = news_data
            result['technical_data'] = technical
            
            return result
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Analysis error: {str(e)}',
                'symbol': symbol,
                'news_score': news_data['news_score'],
                'technical_score': technical['technical_score'] if technical else 0,
                'hybrid_score': hybrid_score
            }
    
    def get_coin_insights(self, db: Session, symbol: str):
        """
        Get detailed insights for a specific coin including:
        - Technical indicators
        - News sentiment
        - Candle data for charting
        - AI analysis
        """
        asset = symbol.replace('USDT', '')
        
        # Get technical indicators
        technical = self.calculate_technical_indicators(symbol)
        
        # Get news score and data
        news_data = self.calculate_news_score(db, asset)
        
        # Get candle data for charting (last 100 candles = ~8 hours on 5m)
        candles = self.get_recent_candles(symbol, interval='5m', limit=100)
        
        # Get recent news articles
        news_articles = self.get_news_for_asset(db, asset, hours=24)
        
        # Calculate hybrid score
        hybrid_score = 50
        if technical:
            hybrid_score = int(news_data['news_score'] * 0.4 + technical['technical_score'] * 0.6)
        
        # Determine status
        if hybrid_score >= 80:
            status = 'STRONG_HOLD'
            status_label = '🟢 Strong Hold'
        elif hybrid_score >= 60:
            status = 'HOLD'
            status_label = '🟡 Hold'
        elif hybrid_score >= 40:
            status = 'WEAK_HOLD'
            status_label = '🟠 Weak Hold'
        else:
            status = 'SELL'
            status_label = '🔴 Sell Signal'
        
        return {
            'symbol': symbol,
            'asset': asset,
            'status': status,
            'status_label': status_label,
            'hybrid_score': hybrid_score,
            'technical': technical,
            'news': {
                **news_data,
                'articles': [{
                    'title': n.title,
                    'sentiment': n.sentiment,
                    'date': n.date.isoformat() if n.date else n.created_at.isoformat(),
                    'source': n.source_name or 'Unknown'
                } for n in news_articles[:10]]
            },
            'candles': [{
                'time': c['time'].isoformat() if isinstance(c['time'], datetime) else c['time'],
                'open': c['open'],
                'high': c['high'],
                'low': c['low'],
                'close': c['close'],
                'volume': c['volume']
            } for c in candles]
        }
    
    def manage_portfolio(self, db: Session, auto_execute: bool = False):
        """
        Analyze all holdings and optionally execute trades.
        Returns list of recommendations.
        """
        holdings = self.get_portfolio_holdings()
        
        if not holdings:
            return []
        
        recommendations = []
        
        for holding in holdings:
            analysis = self.analyze_holding(db, holding)
            recommendations.append(analysis)
            
            # Log the analysis
            log_msg = f"Portfolio: {analysis['symbol']} - {analysis['action']} ({analysis['confidence']}%) - {analysis['reasoning']}"
            db.add(BotLog(
                level='INFO',
                category='PORTFOLIO',
                message=log_msg
            ))
            
            # Auto-execute if enabled and high confidence
            if auto_execute and analysis['confidence'] >= 75:
                action = analysis['action']
                symbol = analysis['symbol']
                
                if action == 'SELL':
                    # Determine how much to sell
                    sell_pct = analysis.get('sell_percentage', 100)
                    sell_qty = (holding['free'] * sell_pct / 100)
                    
                    if sell_qty > 0:
                        try:
                            # Execute sell via trading service
                            from .trading_service import TradingService
                            trading = TradingService(self.client)
                            trade = trading.sell_market(db, symbol, sell_qty)
                            
                            if trade:
                                db.add(BotLog(
                                    level='INFO',
                                    category='TRADE',
                                    message=f"Portfolio mgmt SELL: {symbol} qty={sell_qty:.6f}"
                                ))
                                
                                # Send SMS notification
                                if self.sms_notifier:
                                    try:
                                        current_price = analysis.get('current_price', 0)
                                        profit = (current_price - analysis.get('entry_price', current_price)) * sell_qty
                                        profit_pct = analysis.get('profit_percent', 0)
                                        
                                        self.sms_notifier.send_trade_notification({
                                            'action': 'SELL',
                                            'symbol': symbol,
                                            'price': current_price,
                                            'quantity': sell_qty,
                                            'amount': current_price * sell_qty,
                                            'bot_name': 'Portfolio Manager',
                                            'profit': profit,
                                            'profit_percent': profit_pct,
                                            'reasoning': analysis['reasoning']
                                        })
                                    except Exception as e:
                                        print(f"SMS notification error: {e}")
                        except Exception as e:
                            print(f"Error executing sell for {symbol}: {e}")
                
                elif action == 'BUY_MORE':
                    # Only buy more if very high confidence
                    if analysis['confidence'] >= 85:
                        # Use a small fixed amount for adding to position
                        add_amount = float(os.getenv('PORTFOLIO_ADD_USDT', '25'))
                        
                        try:
                            from .trading_service import TradingService
                            trading = TradingService(self.client)
                            trade = trading.buy_market(db, symbol, add_amount)
                            
                            if trade:
                                db.add(BotLog(
                                    level='INFO',
                                    category='TRADE',
                                    message=f"Portfolio mgmt BUY MORE: {symbol} ${add_amount}"
                                ))
                                
                                # Send SMS notification
                                if self.sms_notifier:
                                    try:
                                        current_price = analysis.get('current_price', 0)
                                        quantity = add_amount / current_price if current_price > 0 else 0
                                        
                                        self.sms_notifier.send_trade_notification({
                                            'action': 'BUY',
                                            'symbol': symbol,
                                            'price': current_price,
                                            'quantity': quantity,
                                            'amount': add_amount,
                                            'bot_name': 'Portfolio Manager',
                                            'reasoning': f"Adding to position: {analysis['reasoning']}"
                                        })
                                    except Exception as e:
                                        print(f"SMS notification error: {e}")
                        except Exception as e:
                            print(f"Error adding to {symbol}: {e}")
        
        db.commit()
        return recommendations

