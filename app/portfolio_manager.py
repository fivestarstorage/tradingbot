"""
Portfolio Management Service
Monitors existing holdings and makes trading decisions based on:
1. News sentiment for the coin
2. Technical analysis (price candles)
3. Traditional trading strategies
"""
from sqlalchemy.orm import Session
from core.binance_client import BinanceClient
from .models import NewsArticle, Signal, BotLog
from datetime import datetime, timedelta, timezone
import openai
import os
import json

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
        Analyze a single holding using news + technical data.
        Returns: {action, confidence, reasoning}
        """
        symbol = holding['symbol']
        asset = holding['asset']
        quantity = holding['quantity']
        
        # Get recent news
        news = self.get_news_for_asset(db, asset, hours=6)
        
        # Get technical data
        candles = self.get_recent_candles(symbol, interval='5m', limit=50)
        
        if not candles:
            return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'No price data available'}
        
        # Current price
        current_price = candles[-1]['close']
        
        # Calculate simple technical indicators
        prices = [c['close'] for c in candles]
        sma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else current_price
        sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else current_price
        
        # Price change %
        price_change_5m = ((current_price - candles[-2]['close']) / candles[-2]['close'] * 100) if len(candles) >= 2 else 0
        price_change_1h = ((current_price - candles[0]['close']) / candles[0]['close'] * 100) if len(candles) >= 12 else 0
        
        # Volume analysis
        recent_volume = sum([c['volume'] for c in candles[-10:]])
        avg_volume = sum([c['volume'] for c in candles]) / len(candles)
        volume_ratio = recent_volume / (avg_volume * 10) if avg_volume > 0 else 1
        
        # Format news context
        news_context = ""
        if news:
            news_context = "Recent news:\n"
            for n in news[:5]:
                news_context += f"- {n.title} ({n.sentiment})\n"
        else:
            news_context = "No recent news for this asset."
        
        # AI analysis prompt
        prompt = f"""You are a crypto portfolio manager. Analyze this holding and recommend an action.

Asset: {asset} ({symbol})
Current Holdings: {quantity:.6f} {asset}
Current Price: ${current_price:.4f}
Value: ${current_price * quantity:.2f}

Technical Analysis:
- Price change (5min): {price_change_5m:+.2f}%
- Price change (1hr): {price_change_1h:+.2f}%
- SMA 20: ${sma_20:.4f}
- SMA 50: ${sma_50:.4f}
- Volume ratio (recent vs avg): {volume_ratio:.2f}x

{news_context}

Based on this data, should we:
- SELL (take profits or cut losses)
- HOLD (maintain position)
- BUY_MORE (add to position - only if strong conviction)

Respond in JSON format:
{{
  "action": "SELL" | "HOLD" | "BUY_MORE",
  "confidence": 0-100,
  "reasoning": "Brief explanation",
  "sell_percentage": 0-100 (only if action is SELL)
}}

Trading philosophy:
- Take profits on 10%+ gains
- Cut losses on 5%+ drops with negative news
- Hold positions with positive momentum
- Only buy more on strong conviction (85%+ confidence)
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
            
            # Add context
            result['symbol'] = symbol
            result['current_price'] = current_price
            result['quantity'] = quantity
            result['value'] = current_price * quantity
            
            return result
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'Analysis error: {str(e)}',
                'symbol': symbol
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

