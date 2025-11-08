#!/usr/bin/env python3
"""
Sentiment-Based Trading Engine
Makes trading decisions based ONLY on news sentiment analysis
No ML, no complex technical indicators - just news sentiment
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import AITradingDecision, TestPortfolio, TestTrade, NewsArticle
from core.binance_client import BinanceClient


class AITradingEngine:
    def __init__(self, binance_client: BinanceClient, db: Session):
        """Initialize the sentiment-based trading engine"""
        self.binance = binance_client
        self.db = db
        
        # Sentiment thresholds
        self.SELL_THRESHOLD = 30  # Sell when sentiment drops below this
        self.BUY_THRESHOLD = 50   # Buy when sentiment recovers above this
        
        print("📰 Sentiment-Based Trading Engine initialized")
        print(f"   Sell Threshold: {self.SELL_THRESHOLD}")
        print(f"   Buy Threshold: {self.BUY_THRESHOLD}")
    
    def make_decision(self, coin: str, test_mode: bool = False) -> AITradingDecision:
        """
        Make a trading decision based ONLY on news sentiment
        
        Strategy:
        - Get recent news sentiment (last 24 hours)
        - If sentiment < 30: SELL (negative news)
        - If sentiment > 50: BUY (positive news)
        - Otherwise: HOLD
        
        Args:
            coin: Coin symbol (BTC, ETH, XRP, etc.)
            test_mode: If True, simulate trading without executing
            
        Returns:
            AITradingDecision object
        """
        print(f"\n{'='*80}")
        print(f"📰 Making SENTIMENT-BASED decision for {coin}")
        print(f"🧪 Test Mode: {'ON' if test_mode else 'OFF'}")
        print(f"{'='*80}")
        
        symbol = f"{coin}USDT"
        
        # 1. Fetch news sentiment
        print("\n📰 Step 1: Analyzing recent news sentiment...")
        news_sentiment_data = self._analyze_news_sentiment(coin)
        
        # 2. Get current price
        print("\n💰 Step 2: Fetching current price...")
        try:
            ticker = self.binance.get_ticker(symbol)
            current_price = float(ticker['lastPrice'])
            price_change_24h = float(ticker.get('priceChangePercent', 0))
        except Exception as e:
            print(f"❌ Error fetching price: {e}")
            current_price = 0
            price_change_24h = 0
        
        # 3. Check current position and calculate stop-loss
        print("\n📊 Step 3: Checking current position...")
        if test_mode:
            portfolio = self.db.query(TestPortfolio).filter(
                TestPortfolio.coin == coin
            ).first()
            in_position = portfolio and portfolio.position_quantity > 0
            
            # Calculate stop-loss conditions
            stop_loss_triggered = False
            stop_loss_reason = ""
            
            if in_position and portfolio:
                position_value = portfolio.position_quantity * current_price
                cost_basis = portfolio.total_invested - portfolio.total_withdrawn
                
                # Stop-loss 1: Position value < 10% of net deposits
                if cost_basis > 0 and position_value < (cost_basis * 0.10):
                    stop_loss_triggered = True
                    loss_pct = ((cost_basis - position_value) / cost_basis) * 100
                    stop_loss_reason = f"STOP-LOSS: Position value (${position_value:.2f}) < 10% of cost basis (${cost_basis:.2f}). Loss: {loss_pct:.1f}%"
                
                # Stop-loss 2: Loss > 10%
                elif cost_basis > 0:
                    loss_pct = ((position_value - cost_basis) / cost_basis) * 100
                    if loss_pct < -10:
                        stop_loss_triggered = True
                        stop_loss_reason = f"STOP-LOSS: Loss exceeds 10% ({loss_pct:.1f}%). Cutting losses to protect capital."
                
                if stop_loss_triggered:
                    print(f"   🚨 STOP-LOSS TRIGGERED!")
                    print(f"      Position Value: ${position_value:.2f}")
                    print(f"      Cost Basis: ${cost_basis:.2f}")
                    print(f"      Current Loss: {((position_value - cost_basis) / cost_basis * 100):.1f}%")
        else:
            # For live trading, check real portfolio (implement later)
            in_position = False
            stop_loss_triggered = False
            stop_loss_reason = ""
        
        # 4. Make decision based on sentiment OR stop-loss
        print("\n🧠 Step 4: Making decision...")
        sentiment_score = news_sentiment_data['score']
        sentiment_label = news_sentiment_data['label']
        
        print(f"   Sentiment Score: {sentiment_score:.1f}/100 ({sentiment_label})")
        print(f"   Current Position: {'YES' if in_position else 'NO'}")
        print(f"   Sell Threshold: {self.SELL_THRESHOLD}")
        print(f"   Buy Threshold: {self.BUY_THRESHOLD}")
        
        # Decision logic - STOP-LOSS TAKES PRIORITY
        if stop_loss_triggered:
            decision = 'SELL'
            confidence = 99
            reasoning = stop_loss_reason
        elif sentiment_score < self.SELL_THRESHOLD and in_position:
            decision = 'SELL'
            confidence = min(95, (self.SELL_THRESHOLD - sentiment_score) * 2 + 50)
            reasoning = f"Negative sentiment detected ({sentiment_score:.0f}/100). News indicates bearish outlook. Selling to protect capital."
        elif sentiment_score > self.BUY_THRESHOLD and not in_position:
            decision = 'BUY'
            confidence = min(95, (sentiment_score - self.BUY_THRESHOLD) + 50)
            reasoning = f"Positive sentiment detected ({sentiment_score:.0f}/100). News indicates bullish outlook. Buying position."
        else:
            decision = 'HOLD'
            confidence = 70
            if in_position:
                reasoning = f"Sentiment neutral ({sentiment_score:.0f}/100). Holding current position."
            else:
                reasoning = f"Sentiment neutral ({sentiment_score:.0f}/100). Waiting for clearer signal."
        
        print(f"   📝 Decision: {decision}")
        print(f"   🎯 Confidence: {confidence:.0f}%")
        print(f"   💬 Reasoning: {reasoning}")
        
        # 5. Create decision record
        decision_obj = AITradingDecision(
            coin=coin,
            decision=decision,
            confidence=confidence,
            news_count=news_sentiment_data['count'],
            news_sentiment=sentiment_label,
            news_sentiment_score=sentiment_score,
            news_summary=news_sentiment_data['summary'],
            ml_prediction=None,  # No ML anymore
            ml_confidence=None,
            ml_model_used=None,
            current_price=current_price,
            price_change_1h=None,
            price_change_24h=price_change_24h,
            volume_24h=None,
            rsi=None,  # No technical indicators anymore
            macd=None,
            ai_reasoning=reasoning,
            openai_response=None,
            test_mode=test_mode,
            executed=False
        )
        
        # 6. Execute trade if BUY or SELL
        trade_id = None
        execution_result = {}
        if decision in ['BUY', 'SELL']:
            if test_mode:
                print(f"\n💰 Step 5: Executing TEST {decision} trade...")
                execution_result = self._execute_test_trade(
                    coin, decision, current_price
                )
            else:
                print(f"\n⚠️  Real trading not implemented yet - use test mode")
                decision_obj.execution_error = "Real trading not implemented"
            
            if 'success' in execution_result:
                decision_obj.executed = execution_result['success']
                decision_obj.execution_price = execution_result.get('price')
                decision_obj.execution_quantity = execution_result.get('quantity')
                decision_obj.execution_error = execution_result.get('error')
            if execution_result['success']:
                    decision_obj.executed_at = datetime.now(timezone.utc)
        else:
            print(f"\n✅ Step 5: {decision} decision recorded (HOLD)")
        
        # 7. Save to database
        self.db.add(decision_obj)
        self.db.commit()
        self.db.refresh(decision_obj)
        
        # 8. Link trade to decision
        if test_mode and decision_obj.executed:
            latest_trade = self.db.query(TestTrade).filter(
                TestTrade.coin == coin
            ).order_by(TestTrade.executed_at.desc()).first()
            
            if latest_trade:
                latest_trade.decision_id = decision_obj.id
                self.db.commit()
        
        print(f"\n✅ Decision ID: {decision_obj.id}")
        print(f"📊 Decision: {decision_obj.decision} ({decision_obj.confidence:.0f}% confidence)")
        print(f"💡 Reasoning: {decision_obj.ai_reasoning}")
        print(f"{'='*80}\n")
        
        return decision_obj
    
    def _analyze_news_sentiment(self, coin: str) -> Dict:
        """
        Analyze news sentiment from database articles (last 24 hours)
        Returns sentiment score (0-100) based on AI-analyzed news
        """
        try:
            # Get recent news articles from database (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Query all recent articles and filter by ticker
            # Note: database stores dates as naive UTC datetime
            # Use created_at as fallback if date is NULL
            cutoff_naive = cutoff_time.replace(tzinfo=None)
            from sqlalchemy import or_
            all_recent_articles = self.db.query(NewsArticle).filter(
                or_(
                    NewsArticle.date >= cutoff_naive,
                    NewsArticle.created_at >= cutoff_naive
                )
            ).order_by(NewsArticle.created_at.desc()).all()
            
            # Filter articles that mention this coin's ticker
            articles = []
            for article in all_recent_articles:
                if article.tickers:
                    tickers_list = [t.strip().upper() for t in article.tickers.split(',')]
                    # Check for coin symbol (e.g., BTC, ETH) or full symbol (BTCUSDT)
                    if coin.upper() in tickers_list or f"{coin.upper()}USDT" in tickers_list:
                        articles.append(article)
            
            if not articles:
                print(f"   No recent news found for {coin} (last 24h)")
                return {
                    'count': 0,
                    'score': 50.0,  # Neutral
                    'label': 'NEUTRAL',
                    'summary': f'No recent news found for {coin} in last 24 hours'
                }
            
            # Limit to 10 most recent
            articles = articles[:10]
            print(f"   Found {len(articles)} articles")
            
            # Calculate average sentiment from articles
            sentiments = [a.sentiment for a in articles if a.sentiment]
            
            if not sentiments:
                score = 50.0  # Neutral default
            else:
                # Map sentiment labels to scores
                positive_count = sum(1 for s in sentiments if s.upper() in ['BULLISH', 'POSITIVE'])
                negative_count = sum(1 for s in sentiments if s.upper() in ['BEARISH', 'NEGATIVE'])
                
                if len(sentiments) > 0:
                    score = 50 + ((positive_count - negative_count) / len(sentiments)) * 50
                else:
                    score = 50.0  # Neutral default
            
            # Clamp to 0-100
            score = max(0, min(100, score))
            
            # Determine label
            if score >= 60:
                label = 'BULLISH'
            elif score <= 40:
                label = 'BEARISH'
            else:
                label = 'NEUTRAL'
            
            # Create summary
            recent_titles = [a.title for a in articles[:3]]
            summary = " | ".join(recent_titles)
            
            return {
                'count': len(articles),
                'score': round(score, 1),
                'label': label,
                'summary': summary
            }
            
        except Exception as e:
            print(f"❌ Error analyzing sentiment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'count': 0,
                'score': 50.0,
                'label': 'NEUTRAL',
                'summary': f'Error: {str(e)}'
            }
    
    def _execute_test_trade(self, coin: str, action: str, price: float) -> Dict:
        """Execute a virtual trade in test mode"""
        try:
            # Get or create test portfolio for this coin
            portfolio = self.db.query(TestPortfolio).filter(TestPortfolio.coin == coin).first()
            if not portfolio:
                # Initialize with $10,000 already invested
                initial_investment = 10000.0
                coin_quantity = initial_investment / price
                
                portfolio = TestPortfolio(
                    coin=coin,
                    usdt_balance=0.0,
                    coin_balance=coin_quantity,
                    total_invested=initial_investment,
                    total_withdrawn=0.0,
                    realized_profit=0.0
                )
                self.db.add(portfolio)
                self.db.commit()
                self.db.refresh(portfolio)
                
                # Record initial purchase
                initial_trade = TestTrade(
                    coin=coin,
                    side='BUY',
                    quantity=coin_quantity,
                    price=price,
                    usdt_amount=initial_investment
                )
                self.db.add(initial_trade)
                self.db.commit()
                
                print(f"✅ Initialized {coin} test portfolio: {coin_quantity:.8f} {coin} @ ${price:,.2f}")
            
            if action == 'BUY':
                # If we have coins, we can't buy more (need to sell first)
                if portfolio.coin_balance > 0:
                    return {
                        'success': False,
                        'error': 'Already holding position - sell first before buying'
                    }
                
                # Use 50% of available USDT
                usdt_to_spend = portfolio.usdt_balance * 0.5
                
                if usdt_to_spend < 10:  # Minimum trade size
                    return {
                        'success': False,
                        'error': f'Insufficient USDT balance (have ${portfolio.usdt_balance:.2f}, need at least $20)'
                    }
                
                quantity = usdt_to_spend / price
                
                # Calculate new average entry price
                old_position_value = portfolio.coin_balance * (portfolio.total_invested / portfolio.coin_balance if portfolio.coin_balance > 0 else 0)
                new_position_value = old_position_value + usdt_to_spend
                new_total_quantity = portfolio.coin_balance + quantity
                avg_entry_price = new_position_value / new_total_quantity if new_total_quantity > 0 else price
                
                # Update portfolio
                portfolio.usdt_balance -= usdt_to_spend
                portfolio.coin_balance += quantity
                portfolio.total_invested += usdt_to_spend
                
                # Record trade with entry price tracking
                trade = TestTrade(
                    coin=coin,
                    side='BUY',
                    quantity=quantity,
                    price=price,
                    usdt_amount=usdt_to_spend,
                    entry_price=avg_entry_price,
                    pnl=None,  # No P&L on BUY
                    pnl_percentage=None,
                    holding_period_seconds=None
                )
                self.db.add(trade)
                self.db.commit()
                
                print(f"  ✅ TEST BUY: {quantity:.8f} {coin} @ ${price:,.2f} = ${usdt_to_spend:,.2f} (Avg Entry: ${avg_entry_price:,.2f})")
                
                return {
                    'success': True,
                    'price': price,
                    'quantity': quantity
                }
            
            elif action == 'SELL':
                # Sell all holdings
                if portfolio.coin_balance <= 0:
                    return {
                        'success': False,
                        'error': 'No coins to sell'
                    }
                
                quantity = portfolio.coin_balance
                usdt_received = quantity * price
                
                # Calculate P&L metrics
                cost_basis = portfolio.total_invested - portfolio.total_withdrawn  # What we paid for current holdings
                pnl = usdt_received - cost_basis
                pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                
                # Calculate average entry price
                avg_entry_price = cost_basis / quantity if quantity > 0 else 0
                
                # Calculate holding period (time since first BUY)
                first_buy = self.db.query(TestTrade).filter(
                    TestTrade.coin == coin,
                    TestTrade.side == 'BUY'
                ).order_by(TestTrade.executed_at.desc()).first()
                
                holding_period_seconds = None
                if first_buy and first_buy.executed_at:
                    holding_period_seconds = int((datetime.now(timezone.utc) - first_buy.executed_at).total_seconds())
                
                # Update portfolio
                portfolio.usdt_balance += usdt_received
                portfolio.coin_balance = 0
                portfolio.total_withdrawn += usdt_received
                
                # Calculate realized profit
                portfolio.realized_profit = portfolio.total_withdrawn - portfolio.total_invested
                
                # Record trade with full P&L data
                trade = TestTrade(
                    coin=coin,
                    side='SELL',
                    quantity=quantity,
                    price=price,
                    usdt_amount=usdt_received,
                    entry_price=avg_entry_price,
                    pnl=pnl,
                    pnl_percentage=pnl_percentage,
                    holding_period_seconds=holding_period_seconds
                )
                self.db.add(trade)
                self.db.commit()
                
                holding_str = f" (held {holding_period_seconds//3600}h {(holding_period_seconds%3600)//60}m)" if holding_period_seconds else ""
                pnl_str = f"{'📈' if pnl >= 0 else '📉'} P&L: ${pnl:,.2f} ({pnl_percentage:+.2f}%)"
                print(f"  ✅ TEST SELL: {quantity:.8f} {coin} @ ${price:,.2f} = ${usdt_received:,.2f}{holding_str}")
                print(f"     {pnl_str}")
                
                return {
                    'success': True,
                    'price': price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'pnl_percentage': pnl_percentage
                }
            
            return {
                'success': False,
                'error': 'Invalid action'
            }
            
        except Exception as e:
            print(f"❌ Error executing test trade: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

