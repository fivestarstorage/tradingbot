from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True, index=True)
    news_url = Column(Text, nullable=False)
    image_url = Column(Text)
    title = Column(Text, nullable=False)
    text = Column(Text)
    source_name = Column(String(255))
    date = Column(DateTime, index=True)
    sentiment = Column(String(32))
    type = Column(String(64))
    tickers = Column(Text)  # comma-separated tickers
    raw = Column(JSON)  # full payload
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint('news_url', name='uq_news_url'),
        Index('ix_news_tickers', 'tickers'),
    )


class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), index=True)
    action = Column(String(8))  # BUY/SELL/HOLD
    confidence = Column(Integer)
    reasoning = Column(Text)
    ref_article_url = Column(Text)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class BotLog(Base):
    __tablename__ = 'bot_logs'
    id = Column(Integer, primary_key=True)
    level = Column(String(16), default='INFO', index=True)
    category = Column(String(32), index=True)  # e.g., NEWS, AI, TRADE
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), index=True)
    side = Column(String(8))  # LONG
    entry_price = Column(Float)
    quantity = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(16), default='OPEN', index=True)  # OPEN/CLOSED
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime)


class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), index=True)
    side = Column(String(8))  # BUY/SELL
    quantity = Column(Float)
    price = Column(Float)
    notional = Column(Float)
    binance_order_id = Column(String(64))
    status = Column(String(16), default='FILLED', index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    position_id = Column(Integer, index=True)
    meta = Column(JSON)


class SchedulerRun(Base):
    __tablename__ = 'scheduler_runs'
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    inserted = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    total = Column(Integer, default=0)
    positive = Column(Integer, default=0)
    negative = Column(Integer, default=0)
    neutral = Column(Integer, default=0)
    signals = Column(Integer, default=0)
    buys = Column(Integer, default=0)
    sells = Column(Integer, default=0)
    notes = Column(Text)
    meta = Column(JSON)


# === Momentum Trading Models ===

class MomentumSignal(Base):
    __tablename__ = 'momentum_signals'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), index=True, nullable=False)
    interval = Column(String(8), index=True)  # 1m, 5m, 15m, 1h
    price_change_pct = Column(Float)  # % change that triggered signal
    volume_24h = Column(Float)
    volume_ratio = Column(Float)  # Current volume vs avg
    ai_confidence = Column(Float)  # 0-1 from AI model
    predicted_exit = Column(Float)  # AI suggested exit price
    technical_score = Column(Float)  # RSI, MACD, EMA score
    status = Column(String(16), default='ACTIVE', index=True)  # ACTIVE/EXPIRED/TRADED
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)
    meta = Column(JSON)  # Additional data: RSI, MACD, order book, etc.


class MomentumTrade(Base):
    __tablename__ = 'momentum_trades'
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, index=True)  # FK to MomentumSignal
    symbol = Column(String(32), index=True, nullable=False)
    side = Column(String(8), nullable=False)  # BUY/SELL
    entry_price = Column(Float)
    exit_price = Column(Float)
    quantity = Column(Float)
    usdt_value = Column(Float)
    profit_loss = Column(Float)
    profit_loss_pct = Column(Float)
    ai_entry_confidence = Column(Float)  # AI confidence at entry
    ai_exit_confidence = Column(Float)  # AI confidence at exit
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(16), default='OPEN', index=True)  # OPEN/CLOSED/STOPPED
    binance_order_id_entry = Column(String(64))
    binance_order_id_exit = Column(String(64))
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, index=True)
    duration_seconds = Column(Integer)  # Trade duration
    exit_reason = Column(String(32))  # AI_EXIT, STOP_LOSS, TAKE_PROFIT, MANUAL
    meta = Column(JSON)


class MarketSnapshot(Base):
    __tablename__ = 'market_snapshots'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), index=True, nullable=False)
    interval = Column(String(8), index=True)  # 1m, 5m, 15m, 1h
    price = Column(Float)
    volume = Column(Float)
    high = Column(Float)
    low = Column(Float)
    price_change_pct = Column(Float)
    volume_24h = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    ema_20 = Column(Float)
    ema_50 = Column(Float)
    order_book_spread_pct = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(JSON)  # Full candle + ticker data


