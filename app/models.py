from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime, timezone
from .db import Base

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    news_url = Column(String)
    image_url = Column(String)
    text = Column(Text)
    source_name = Column(String)
    date = Column(DateTime)
    sentiment = Column(String)
    type = Column(String)
    tickers = Column(String)
    raw = Column(Text)  # JSON stored as text
    created_at = Column(DateTime)

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    action = Column(String)
    confidence = Column(Float)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    side = Column(String)
    quantity = Column(Float)
    entry_price = Column(Float)
    current_price = Column(Float)
    pnl = Column(Float)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    side = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

class SchedulerRun(Base):
    __tablename__ = 'scheduler_runs'
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    inserted = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    total = Column(Integer, default=0)
    signals = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

class BotLog(Base):
    __tablename__ = 'bot_logs'
    id = Column(Integer, primary_key=True)
    level = Column(String)
    category = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class MomentumTrade(Base):
    __tablename__ = 'momentum_trades'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    side = Column(String)
    quantity = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    status = Column(String)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

class TestPortfolio(Base):
    """Track virtual portfolio for test mode trading"""
    __tablename__ = 'test_portfolio'
    
    id = Column(Integer, primary_key=True)
    coin = Column(String, nullable=False, unique=True, index=True)
    usdt_balance = Column(Float, default=10000.0)  # Virtual USDT balance
    coin_balance = Column(Float, default=0.0)  # Virtual coin holdings
    position_quantity = Column(Float, default=0.0)  # Alias for coin_balance (for compatibility)
    total_invested = Column(Float, default=0.0)  # Total USDT invested
    total_withdrawn = Column(Float, default=0.0)  # Total USDT withdrawn
    realized_profit = Column(Float, default=0.0)  # Realized P&L
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            'coin': self.coin,
            'usdt_balance': self.usdt_balance,
            'coin_balance': self.coin_balance,
            'position_quantity': self.position_quantity or self.coin_balance,
            'total_invested': self.total_invested,
            'total_withdrawn': self.total_withdrawn,
            'realized_profit': self.realized_profit,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TestTrade(Base):
    """Track individual test trades"""
    __tablename__ = 'test_trades'
    
    id = Column(Integer, primary_key=True)
    coin = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    usdt_amount = Column(Float, nullable=False)
    decision_id = Column(Integer, nullable=True)  # Link to AITradingDecision
    
    # Track profit/loss for learning
    entry_price = Column(Float, nullable=True)  # Average entry price for this position
    pnl = Column(Float, nullable=True)  # Realized P&L for SELL trades
    pnl_percentage = Column(Float, nullable=True)  # Realized P&L %
    holding_period_seconds = Column(Integer, nullable=True)  # How long position was held
    
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def to_dict(self):
        from datetime import timezone as tz
        executed_at_utc = None
        if self.executed_at:
            if self.executed_at.tzinfo is None:
                executed_at_utc = self.executed_at.replace(tzinfo=tz.utc).isoformat()
            else:
                executed_at_utc = self.executed_at.isoformat()
        
        return {
            'id': self.id,
            'coin': self.coin,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'usdt_amount': self.usdt_amount,
            'decision_id': self.decision_id,
            'entry_price': self.entry_price,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'holding_period_seconds': self.holding_period_seconds,
            'executed_at': executed_at_utc
        }


class AITradingDecision(Base):
    """Store AI trading decisions combining news, ML, and market data"""
    __tablename__ = 'ai_trading_decisions'
    
    id = Column(Integer, primary_key=True)
    coin = Column(String, nullable=False, index=True)
    decision = Column(String, nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)  # 0-1
    
    # News data
    news_count = Column(Integer, default=0)
    news_sentiment = Column(String, nullable=True)  # POSITIVE, NEGATIVE, NEUTRAL
    news_sentiment_score = Column(Float, nullable=True)  # 0-100 score
    news_summary = Column(Text, nullable=True)
    
    # ML model data
    ml_prediction = Column(String, nullable=True)  # BUY, SELL, HOLD
    ml_confidence = Column(Float, nullable=True)
    ml_model_used = Column(String, nullable=True)
    
    # Market data
    current_price = Column(Float, nullable=False)
    price_change_1h = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    
    # AI reasoning
    ai_reasoning = Column(Text, nullable=True)
    openai_response = Column(Text, nullable=True)
    
    # Execution
    test_mode = Column(Boolean, default=False)
    executed = Column(Boolean, default=False)
    execution_price = Column(Float, nullable=True)
    execution_quantity = Column(Float, nullable=True)
    execution_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        from datetime import timezone as tz
        
        # Ensure timestamps are properly formatted as UTC
        created_at_utc = None
        if self.created_at:
            # If timestamp is naive (no timezone), treat it as UTC
            if self.created_at.tzinfo is None:
                created_at_utc = self.created_at.replace(tzinfo=tz.utc).isoformat()
            else:
                created_at_utc = self.created_at.isoformat()
        
        executed_at_utc = None
        if self.executed_at:
            if self.executed_at.tzinfo is None:
                executed_at_utc = self.executed_at.replace(tzinfo=tz.utc).isoformat()
            else:
                executed_at_utc = self.executed_at.isoformat()
        
        return {
            'id': self.id,
            'coin': self.coin,
            'decision': self.decision,
            'confidence': self.confidence,
            'news_count': self.news_count,
            'news_sentiment': self.news_sentiment,
            'news_sentiment_score': self.news_sentiment_score,
            'news_summary': self.news_summary,
            'ml_prediction': self.ml_prediction,
            'ml_confidence': self.ml_confidence,
            'ml_model_used': self.ml_model_used,
            'current_price': self.current_price,
            'price_change_1h': self.price_change_1h,
            'price_change_24h': self.price_change_24h,
            'volume_24h': self.volume_24h,
            'rsi': self.rsi,
            'macd': self.macd,
            'ai_reasoning': self.ai_reasoning,
            'test_mode': self.test_mode,
            'executed': self.executed,
            'execution_price': self.execution_price,
            'execution_quantity': self.execution_quantity,
            'execution_error': self.execution_error,
            'created_at': created_at_utc,
            'executed_at': executed_at_utc,
            'price_change_since_last': self.price_change_since_last if hasattr(self, 'price_change_since_last') else None,
        }


class CommunityTip(Base):
    """Store community sentiment tips from Binance Square hashtags"""
    __tablename__ = 'community_tips'
    
    id = Column(Integer, primary_key=True)
    coin = Column(String, nullable=False, index=True)  # Extracted coin symbol
    coin_name = Column(String, nullable=True)  # Full coin name
    
    # Sentiment tracking
    sentiment_score = Column(Float, default=50.0)  # 0-100 scale
    sentiment_label = Column(String, nullable=True)  # BULLISH, BEARISH, NEUTRAL
    mention_count = Column(Integer, default=1)  # How many times mentioned
    enthusiasm_score = Column(Float, default=50.0)  # How enthusiastic users are (0-100)
    
    # Aggregated community opinion
    community_summary = Column(Text, nullable=True)  # AI-generated summary
    trending_reason = Column(Text, nullable=True)  # Why this coin is trending
    
    # Source tracking
    sources = Column(Text, nullable=True)  # JSON array of hashtags/URLs it came from
    post_snippets = Column(Text, nullable=True)  # JSON array of relevant post excerpts
    
    # Market data (optional, filled when available)
    current_price = Column(Float, nullable=True)
    price_change_1h = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    price_change_7d = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    market_cap = Column(String, nullable=True)
    
    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    
    # Decay mechanism - sentiment decays over time if not reinforced
    decay_factor = Column(Float, default=1.0)  # Multiplier that decreases over time
    
    def to_dict(self):
        from datetime import timezone as tz
        import json
        
        first_seen_utc = None
        if self.first_seen:
            if self.first_seen.tzinfo is None:
                first_seen_utc = self.first_seen.replace(tzinfo=tz.utc).isoformat()
            else:
                first_seen_utc = self.first_seen.isoformat()
        
        last_updated_utc = None
        if self.last_updated:
            if self.last_updated.tzinfo is None:
                last_updated_utc = self.last_updated.replace(tzinfo=tz.utc).isoformat()
            else:
                last_updated_utc = self.last_updated.isoformat()
        
        # Parse JSON fields
        sources_list = []
        if self.sources:
            try:
                sources_list = json.loads(self.sources)
            except:
                sources_list = [self.sources]
        
        snippets_list = []
        if self.post_snippets:
            try:
                snippets_list = json.loads(self.post_snippets)
            except:
                snippets_list = [self.post_snippets]
        
        return {
            'id': self.id,
            'coin': self.coin,
            'coin_name': self.coin_name,
            'sentiment_score': self.sentiment_score,
            'sentiment_label': self.sentiment_label,
            'mention_count': self.mention_count,
            'enthusiasm_score': self.enthusiasm_score,
            'community_summary': self.community_summary,
            'trending_reason': self.trending_reason,
            'sources': sources_list,
            'post_snippets': snippets_list,
            'current_price': self.current_price,
            'price_change_1h': self.price_change_1h,
            'price_change_24h': self.price_change_24h,
            'price_change_7d': self.price_change_7d,
            'volume_24h': self.volume_24h,
            'market_cap': self.market_cap,
            'first_seen': first_seen_utc,
            'last_updated': last_updated_utc,
            'decay_factor': self.decay_factor,
            'effective_sentiment': self.sentiment_score * self.decay_factor  # Decayed sentiment
        }


class TradingCoin(Base):
    """Store dynamically added coins for trading with their ML strategies"""
    __tablename__ = 'trading_coins'
    
    id = Column(Integer, primary_key=True)
    coin = Column(String, nullable=False, unique=True, index=True)  # e.g., "ZEC"
    coin_name = Column(String, nullable=True)  # e.g., "Zcash"
    symbol = Column(String, nullable=False)  # e.g., "ZECUSDT"
    
    # ML Training Results
    ml_model_type = Column(String, nullable=True)  # "RandomForest", "GradientBoosting", etc.
    ml_strategy = Column(String, nullable=True)  # JSON with strategy params
    ml_accuracy = Column(Float, nullable=True)  # Model accuracy on test data
    ml_sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted returns
    ml_win_rate = Column(Float, nullable=True)  # Percentage of winning trades
    training_period_days = Column(Integer, default=1095)  # 3 years = 1095 days
    
    # Trading Configuration
    enabled = Column(Boolean, default=True)  # Is this coin active for trading?
    ai_decisions_enabled = Column(Boolean, default=True)  # Enable 15-min AI decisions?
    test_mode = Column(Boolean, default=True)  # Start in test mode
    
    # Status
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    last_decision_at = Column(DateTime(timezone=True), nullable=True)
    total_trades = Column(Integer, default=0)
    
    def to_dict(self):
        from datetime import timezone as tz
        import json
        
        added_at_utc = None
        if self.added_at:
            if self.added_at.tzinfo is None:
                added_at_utc = self.added_at.replace(tzinfo=tz.utc).isoformat()
            else:
                added_at_utc = self.added_at.isoformat()
        
        last_decision_at_utc = None
        if self.last_decision_at:
            if self.last_decision_at.tzinfo is None:
                last_decision_at_utc = self.last_decision_at.replace(tzinfo=tz.utc).isoformat()
            else:
                last_decision_at_utc = self.last_decision_at.isoformat()
        
        # Parse ML strategy JSON
        ml_strategy_dict = {}
        if self.ml_strategy:
            try:
                ml_strategy_dict = json.loads(self.ml_strategy)
            except:
                ml_strategy_dict = {}
        
        return {
            'id': self.id,
            'coin': self.coin,
            'coin_name': self.coin_name,
            'symbol': self.symbol,
            'ml_model_type': self.ml_model_type,
            'ml_strategy': ml_strategy_dict,
            'ml_accuracy': self.ml_accuracy,
            'ml_sharpe_ratio': self.ml_sharpe_ratio,
            'ml_win_rate': self.ml_win_rate,
            'training_period_days': self.training_period_days,
            'enabled': self.enabled,
            'ai_decisions_enabled': self.ai_decisions_enabled,
            'test_mode': self.test_mode,
            'added_at': added_at_utc,
            'last_decision_at': last_decision_at_utc,
            'total_trades': self.total_trades
        }
