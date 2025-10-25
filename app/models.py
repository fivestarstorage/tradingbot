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


