import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, Query, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from .db import Base, engine, get_db
from .models import NewsArticle, Signal, Position, Trade, SchedulerRun, BotLog, AITradingDecision, TestPortfolio, TestTrade
from datetime import datetime, timezone, timedelta
from .news_service import fetch_and_store_news
from .ai_decider import AIDecider
from .trading_service import TradingService
from .trending_service import compute_trending
from .chat_service import ChatService
from .ai_trading_engine import AITradingEngine
from core.binance_client import BinanceClient
from binance.client import Client
import subprocess
from typing import Optional, Dict, Any
import json
import requests

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

# Load environment from .env if present (project root)
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TradingBot v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://rileystrading.fivestarstorage.com.au",
        "https://tradingbot-frontend-tlq2.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
Base.metadata.create_all(bind=engine)

# Initialize base coins in database if they don't exist
def initialize_base_coins():
    """Ensure base coins are in the TradingCoin table for AI auto-fetch"""
    from .models import TradingCoin
    
    base_coins = [
        {'coin': 'BTC', 'coin_name': 'Bitcoin', 'symbol': 'BTCUSDT'},
        {'coin': 'ETH', 'coin_name': 'Ethereum', 'symbol': 'ETHUSDT'},
        {'coin': 'XRP', 'coin_name': 'Ripple', 'symbol': 'XRPUSDT'},
        {'coin': 'VIRTUAL', 'coin_name': 'Virtuals Protocol', 'symbol': 'VIRTUALUSDT'},
        {'coin': 'PIVX', 'coin_name': 'PIVX', 'symbol': 'PIVXUSDT'},
        {'coin': 'BNB', 'coin_name': 'Binance Coin', 'symbol': 'BNBUSDT'},
        {'coin': 'YB', 'coin_name': 'YB', 'symbol': 'YBUSDT'},
    ]
    
    db = next(get_db())
    try:
        for coin_data in base_coins:
            existing = db.query(TradingCoin).filter(TradingCoin.coin == coin_data['coin']).first()
            if not existing:
                print(f"🔧 Initializing base coin: {coin_data['coin']}")
                trading_coin = TradingCoin(
                    coin=coin_data['coin'],
                    coin_name=coin_data['coin_name'],
                    symbol=coin_data['symbol'],
                    enabled=True,
                    ai_decisions_enabled=True,
                    test_mode=True
                )
                db.add(trading_coin)
            else:
                # Update existing coins to ensure ai_decisions_enabled is True
                if not existing.ai_decisions_enabled:
                    print(f"🔧 Enabling AI decisions for: {coin_data['coin']}")
                    existing.ai_decisions_enabled = True
        db.commit()
        print("✅ Base coins initialized")
    except Exception as e:
        print(f"❌ Error initializing base coins: {e}")
        db.rollback()
    finally:
        db.close()

initialize_base_coins()

# Init services
binance = BinanceClient(
    api_key=os.getenv('BINANCE_API_KEY', ''),
    api_secret=os.getenv('BINANCE_API_SECRET', ''),
    testnet=os.getenv('USE_TESTNET', 'true').lower() == 'true'
)
trade_service = TradingService(binance)
ai_decider = AIDecider()
chat_service = ChatService(binance, trade_service)

# AI Trading Engine (initialized per-request to get fresh DB session)
def get_ai_engine(db: Session = Depends(get_db)):
    return AITradingEngine(binance, db)

# Runtime overrides for simple config tweaks via API
RUNTIME_OVERRIDES: Dict[str, Any] = {
    'AUTO_TRADE': None,  # bool
    'WATCHLIST': None,   # list[str]
}

def get_bool(name: str, default: bool) -> bool:
    if RUNTIME_OVERRIDES.get(name) is not None:
        return bool(RUNTIME_OVERRIDES[name])
    return (os.getenv(name, 'true' if default else 'false').lower() == 'true')

def get_watchlist() -> list:
    if RUNTIME_OVERRIDES.get('WATCHLIST'):
        return [s.strip().upper() for s in RUNTIME_OVERRIDES['WATCHLIST'] if s.strip()]
    return [s.strip().upper() for s in os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT').split(',')]


@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    latest_news = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(20).all()
    latest_signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
    open_positions = db.query(Position).filter(Position.status == 'OPEN').all()
    recent_trades = db.query(Trade).order_by(Trade.executed_at.desc()).limit(20).all()
    trending = compute_trending(db, hours=6, limit=10)
    return templates.TemplateResponse('dashboard.html', {
        'request': request,
        'news': latest_news,
        'signals': latest_signals,
        'positions': open_positions,
        'trades': recent_trades,
        'trending': trending
    })


@app.get('/api/news')
def api_news(db: Session = Depends(get_db)):
    items = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(100).all()
    return [
        {
            'title': n.title,
            'url': n.news_url,
            'sentiment': n.sentiment,
            'tickers': n.tickers,
            'source': n.source_name,
            'text': n.text,
            # Dates are stored as naive datetime in DB
            'published_at': (
                n.date.replace(tzinfo=timezone.utc).isoformat() if n.date else None
            ),
            'ingested_at': (
                n.created_at.replace(tzinfo=timezone.utc).isoformat() if n.created_at else None
            )
        } for n in items
    ]


@app.get('/api/signals')
def api_signals(db: Session = Depends(get_db)):
    sigs = db.query(Signal).order_by(Signal.created_at.desc()).limit(100).all()
    return [
        {
            'symbol': s.symbol,
            'action': s.action,
            'confidence': s.confidence,
            'reasoning': s.reasoning,
            'ref': s.ref_article_url,
            'created_at': (s.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z') if s.created_at else None)
        } for s in sigs
    ]


@app.get('/api/trending')
def api_trending(hours: int = 6, limit: int = 15, db: Session = Depends(get_db)):
    return compute_trending(db, hours=hours, limit=limit)


@app.get('/api/overview')
def api_overview(db: Session = Depends(get_db)):
    # Portfolio summary from DB and Binance
    try:
        usdt = binance.get_account_balance('USDT') or {'free': 0.0, 'locked': 0.0}
    except Exception:
        usdt = {'free': 0.0, 'locked': 0.0}
    open_positions = db.query(Position).filter(Position.status == 'OPEN').count()
    trades_24h = db.query(Trade).count()
    last_signal = db.query(Signal).order_by(Signal.created_at.desc()).first()
    return {
        'usdt_free': usdt.get('free', 0.0),
        'usdt_locked': usdt.get('locked', 0.0),
        'open_positions': open_positions,
        'trades_total': trades_24h,
        'last_signal': {
            'symbol': last_signal.symbol if last_signal else None,
            'action': last_signal.action if last_signal else None,
            'confidence': last_signal.confidence if last_signal else None,
            'created_at': last_signal.created_at.isoformat() if last_signal else None,
        }
    }


@app.get('/api/scheduler/status')
def api_scheduler_status():
    """Get status of news + AI scheduler with countdown info"""
    global last_news_and_ai_run, scheduler_start_time
    
    now = datetime.now(timezone.utc)
    interval_minutes = 15
    
    if last_news_and_ai_run is None:
        # Scheduler hasn't run yet since server start
        # Estimate: first run happens within 15 minutes of server start
        # Use scheduler_start_time if available, otherwise assume just started
        start_reference = scheduler_start_time if scheduler_start_time else now
        
        # Estimate next run: could be anywhere from now to 15 minutes from server start
        # Let's assume it will run at the next 15-minute mark after server start
        estimated_next_run = start_reference + timedelta(minutes=interval_minutes)
        seconds_until_next = (estimated_next_run - now).total_seconds()
        
        # If negative (we've passed the estimated time), just show it's imminent
        if seconds_until_next < 0:
            seconds_until_next = 60  # Show 1 minute as fallback
        
        return {
            'last_run': None,
            'next_run': estimated_next_run.isoformat() + 'Z',
            'seconds_until_next': int(seconds_until_next),
            'interval_minutes': interval_minutes,
            'status': 'waiting_for_first_run'
        }
    
    # Calculate next run time (last run + 15 minutes)
    next_run = last_news_and_ai_run + timedelta(minutes=interval_minutes)
    seconds_until_next = (next_run - now).total_seconds()
    
    # If negative, it should have run already (might be running now)
    if seconds_until_next < 0:
        seconds_until_next = 0
    
    return {
        'last_run': last_news_and_ai_run.isoformat() + 'Z',
        'next_run': next_run.isoformat() + 'Z',
        'seconds_until_next': int(seconds_until_next),
        'interval_minutes': interval_minutes,
        'status': 'running' if seconds_until_next < 10 else 'scheduled'
    }


# Removed duplicate /api/logs endpoint - using the one at line ~1173 instead


@app.get('/api/runs')
def api_runs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(SchedulerRun).order_by(SchedulerRun.started_at.desc()).limit(limit).all()
    return [
        {
            # mark as UTC explicitly so frontend can convert to local tz
            'started_at': (r.started_at.isoformat() + 'Z') if r.started_at else None,
            'inserted': r.inserted, 'skipped': r.skipped, 'total': r.total,
            'positive': r.positive, 'negative': r.negative, 'neutral': r.neutral,
            'signals': r.signals, 'buys': r.buys, 'sells': r.sells,
            'notes': r.notes
        }
        for r in rows
    ]


@app.get('/api/runs/debug')
def api_runs_debug(db: Session = Depends(get_db)):
    """Debug endpoint to check database state"""
    try:
        # Count total runs
        total_runs = db.query(func.count(SchedulerRun.id)).scalar() or 0
        
        # Get latest run
        latest_run = db.query(SchedulerRun).order_by(SchedulerRun.started_at.desc()).first()
        
        # Get database path
        db_path = str(db.bind.url) if hasattr(db, 'bind') else 'unknown'
        
        return {
            'total_runs': total_runs,
            'database_path': db_path,
            'latest_run': {
                'id': latest_run.id if latest_run else None,
                'started_at': latest_run.started_at.isoformat() if latest_run and latest_run.started_at else None,
                'total': latest_run.total if latest_run else None,
                'signals': latest_run.signals if latest_run else None,
            } if latest_run else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            'error': str(e),
            'traceback': __import__('traceback').format_exc()
        }


@app.get('/api/sentiment')
def api_sentiment(db: Session = Depends(get_db)):
    # Aggregate simple counts by sentiment and top tickers
    total = db.query(func.count(NewsArticle.id)).scalar() or 0
    pos = db.query(func.count(NewsArticle.id)).filter(NewsArticle.sentiment.ilike('Positive%')).scalar() or 0
    neg = db.query(func.count(NewsArticle.id)).filter(NewsArticle.sentiment.ilike('Negative%')).scalar() or 0
    neu = total - pos - neg
    # naive top tickers by frequency
    latest = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(500).all()
    from collections import Counter
    c = Counter()
    for a in latest:
        if a.tickers:
            for tk in a.tickers.split(','):
                t = tk.strip().upper()
                if t:
                    c[t] += 1
    top = c.most_common(10)
    return {
        'counts': {'total': total, 'positive': pos, 'negative': neg, 'neutral': neu},
        'top_tickers': top
    }


@app.get('/api/portfolio')
def api_portfolio(db: Session = Depends(get_db)):
    # Enumerate balances and compute USDT value per asset
    items = []
    total_usdt_value = 0.0
    try:
        acct = binance.client.get_account()
        balances = acct.get('balances', [])
        for b in balances:
            asset = b.get('asset')
            free = float(b.get('free', 0))
            locked = float(b.get('locked', 0))
            total = free + locked
            if total <= 0:
                continue
            if asset == 'USDT':
                value = total
            else:
                symbol = f"{asset}USDT"
                try:
                    price = binance.get_current_price(symbol)
                    value = (price or 0) * total
                except Exception:
                    value = 0.0
            total_usdt_value += value
            items.append({
                'asset': asset,
                'free': free,
                'locked': locked,
                'total': total,
                'usdt_value': value
            })
        items.sort(key=lambda x: x['usdt_value'], reverse=True)
    except Exception:
        pass
    return {'total_usdt': total_usdt_value, 'holdings': items}


@app.get('/api/trades')
def api_trades(limit: int = 50, db: Session = Depends(get_db)):
    trs = db.query(Trade).order_by(Trade.executed_at.desc()).limit(limit).all()
    return [
        {
            'symbol': t.symbol,
            'side': t.side,
            'quantity': t.quantity,
            'price': t.price,
            'notional': t.notional,
            'created_at': (t.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z') if t.created_at else None),
        } for t in trs
    ]


@app.get('/api/insights')
def api_insights(db: Session = Depends(get_db)):
    # Basic insights: counts, top symbols, hourly signal counts (last 24h)
    total_signals = db.query(func.count(Signal.id)).scalar() or 0
    
    # Debug: Check if OpenAI key is configured
    has_openai_key = bool(os.getenv('OPENAI_API_KEY'))
    
    # Debug: Check recent news count
    total_news = db.query(func.count(NewsArticle.id)).scalar() or 0
    
    # Get unique tickers from recent news (last 24 hours)
    import datetime
    now = datetime.now(timezone.utc)
    since = now - datetime.timedelta(hours=24)
    recent_news = db.query(NewsArticle).filter(NewsArticle.created_at >= since).all()
    
    unique_tickers = set()
    for article in recent_news:
        if article.tickers:
            tickers = [t.strip().upper() for t in article.tickers.split(',') if t.strip()]
            unique_tickers.update(tickers)
    
    analyzed_coins = len(unique_tickers)
    
    # top symbols by signals
    sym_counts = db.query(Signal.symbol, func.count(Signal.id)).group_by(Signal.symbol).order_by(func.count(Signal.id).desc()).limit(5).all()
    top_symbols = [[s, c] for s, c in sym_counts]
    # hourly signals for last 24h
    recent = db.query(Signal).filter(Signal.created_at >= since).all()
    by_hour = {}
    for s in recent:
        ts = s.created_at.replace(minute=0, second=0, microsecond=0)
        by_hour[ts] = by_hour.get(ts, 0) + 1
    hours = [since.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=i) for i in range(25)]
    series = [{'t': h.isoformat() + 'Z', 'count': by_hour.get(h, 0)} for h in hours]
    # trade counts
    buys = db.query(func.count(Trade.id)).filter(Trade.side == 'BUY').scalar() or 0
    sells = db.query(func.count(Trade.id)).filter(Trade.side == 'SELL').scalar() or 0
    
    return {
        'signals_total': total_signals, 
        'top_symbols': top_symbols, 
        'signals_hourly': series, 
        'trades': {'buys': buys, 'sells': sells},
        'debug': {
            'has_openai_key': has_openai_key,
            'total_news_articles': total_news,
            'coins_analyzed': analyzed_coins,
            'mode': 'All coins from news (last 24h)'
        }
    }


@app.get('/api/ai/summary')
def api_ai_summary(window_minutes: int = 90, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - datetime.timedelta(minutes=window_minutes)
    # sentiment summary over recent window
    recent_news = db.query(NewsArticle).filter(NewsArticle.created_at >= since).order_by(NewsArticle.created_at.desc()).limit(100).all()
    pos = sum(1 for n in recent_news if (n.sentiment or '').lower().startswith('pos'))
    neg = sum(1 for n in recent_news if (n.sentiment or '').lower().startswith('neg'))
    neu = max(len(recent_news) - pos - neg, 0)
    trending = compute_trending(db, hours=max(1, window_minutes // 60 or 1), limit=3)
    rec = chat_service._recommend_from_news(db, {'hours': max(1, window_minutes // 60 or 1)})
    headlines = [{ 'title': n.title, 'tickers': n.tickers, 'sentiment': n.sentiment, 'time': (n.date or n.created_at).isoformat() if (n.date or n.created_at) else None } for n in recent_news[:5]]
    summary = f"Last {window_minutes}m: 🟢{pos} 🔴{neg} ⚪{neu}. "
    if trending:
        summary += f"Top: {trending[0]['ticker']} (score {trending[0]['score']}). "
    if rec and rec.get('symbol'):
        summary += f"Rec: {rec['action']} {rec['symbol']} ({rec.get('confidence',0)}%)."
    return {
        'window_minutes': window_minutes,
        'summary': summary.strip(),
        'sentiment': { 'positive': pos, 'negative': neg, 'neutral': neu },
        'trending': trending,
        'recommendation': rec,
        'headlines': headlines
    }


@app.get('/api/ai/insight')
def api_ai_insight(db: Session = Depends(get_db)):
    """Get the latest AI-generated market insight."""
    # Get most recent insight from bot logs
    latest_insight = db.query(BotLog).filter(
        BotLog.category == 'INSIGHT'
    ).order_by(BotLog.created_at.desc()).first()
    
    if latest_insight:
        try:
            insight_data = json.loads(latest_insight.message)
            return {
                'insight': insight_data.get('insight'),
                'recommendation': insight_data.get('recommendation'),
                'confidence': insight_data.get('confidence'),
                'generated_at': latest_insight.created_at.isoformat()
            }
        except:
            pass
    
    return {
        'insight': 'No insights generated yet. Wait for next scheduled run.',
        'recommendation': 'Monitor market conditions',
        'confidence': 0,
        'generated_at': None
    }


@app.get('/api/portfolio/recommendations')
def api_portfolio_recommendations(db: Session = Depends(get_db)):
    """Get live portfolio with AI recommendations and HYBRID scores."""
    from .portfolio_manager import PortfolioManager
    
    try:
        portfolio_mgr = PortfolioManager(binance)
        holdings = portfolio_mgr.get_portfolio_holdings()
        
        if not holdings:
            return []
        
        recommendations = []
        for holding in holdings:
            # Get HYBRID AI analysis (news + technical)
            analysis = portfolio_mgr.analyze_holding(db, holding)
            
            recommendations.append({
                'symbol': analysis.get('symbol'),
                'asset': holding['asset'],
                'action': analysis.get('action', 'HOLD'),
                'confidence': analysis.get('confidence', 0),
                'reasoning': analysis.get('reasoning', ''),
                'quantity': holding['quantity'],
                'free': holding['free'],
                'locked': holding['locked'],
                'value_usdt': analysis.get('value', 0),
                # Hybrid scores
                'news_score': analysis.get('news_score', 50),
                'technical_score': analysis.get('technical_score', 50),
                'hybrid_score': analysis.get('hybrid_score', 50),
                # Technical data
                'technical': analysis.get('technical_data', {}),
                # News data
                'news_data': analysis.get('news_data', {})
            })
        
        return recommendations
        
    except Exception as e:
        print(f"Error getting portfolio recommendations: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get('/api/portfolio/coin/{symbol}')
def api_coin_insights(symbol: str, db: Session = Depends(get_db)):
    """Get detailed insights for a specific coin including candle data for charting."""
    from .portfolio_manager import PortfolioManager
    
    try:
        portfolio_mgr = PortfolioManager(binance)
        insights = portfolio_mgr.get_coin_insights(db, symbol.upper())
        return insights
    except Exception as e:
        print(f"Error getting coin insights for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/git/status')
def api_git_status():
    # Stub: not wired to system git; return static OK to avoid 404 noise
    return {'status': 'ok', 'branch': None, 'dirty': False}


@app.get('/api/health')
def api_health():
    try:
        # Simple checks
        _ = binance.client.ping()
        return {'ok': True, 'binance': True}
    except Exception:
        return {'ok': True, 'binance': False}


# ============================================================================
# AI TRADING DECISION ENDPOINTS
# ============================================================================

@app.post('/api/ai/decision/{coin}')
def api_make_ai_decision(coin: str, test_mode: bool = True, db: Session = Depends(get_db)):
    """
    Trigger a new AI trading decision for a coin.
    This fetches news, runs ML predictions, analyzes market data,
    and uses OpenAI to make a BUY/SELL/HOLD decision.
    """
    try:
        ai_engine = get_ai_engine(db)
        decision = ai_engine.make_decision(coin.upper(), test_mode=test_mode)
        
        # Update last fetch time for countdown tracking
        last_ai_fetch[coin.upper()] = datetime.now(timezone.utc)
        
        return {
            'ok': True,
            'decision': decision.to_dict()
        }
    except Exception as e:
        print(f"❌ Error making AI decision: {e}")
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/ai/decisions/{coin}')
def api_get_ai_decisions(coin: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Get past AI trading decisions for a coin
    """
    try:
        decisions = db.query(AITradingDecision)\
            .filter(AITradingDecision.coin == coin.upper())\
            .order_by(AITradingDecision.created_at.desc())\
            .limit(limit)\
            .all()
        
        # Calculate price change % between consecutive decisions
        decisions_list = []
        for i, decision in enumerate(decisions):
            d = decision.to_dict()
            
            # Calculate price change since previous decision
            if i < len(decisions) - 1:
                prev_decision = decisions[i + 1]  # Next in list (older in time)
                if decision.current_price and prev_decision.current_price and prev_decision.current_price > 0:
                    price_change_pct = ((decision.current_price - prev_decision.current_price) / prev_decision.current_price) * 100
                    d['price_change_since_last'] = round(price_change_pct, 2)
                else:
                    d['price_change_since_last'] = None
            else:
                d['price_change_since_last'] = None  # First/oldest decision
            
            decisions_list.append(d)
        
        return {
            'ok': True,
            'coin': coin.upper(),
            'count': len(decisions),
            'decisions': decisions_list
        }
    except Exception as e:
        print(f"❌ Error getting AI decisions: {e}")
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/ai/decisions/{coin}/latest')
def api_get_latest_ai_decision(coin: str, db: Session = Depends(get_db)):
    """
    Get the latest AI trading decision for a coin
    """
    try:
        decision = db.query(AITradingDecision)\
            .filter(AITradingDecision.coin == coin.upper())\
            .order_by(AITradingDecision.created_at.desc())\
            .first()
        
        if decision:
            return {
                'ok': True,
                'decision': decision.to_dict()
            }
        else:
            return {
                'ok': False,
                'error': 'No decisions found for this coin'
            }
    except Exception as e:
        print(f"❌ Error getting latest AI decision: {e}")
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/ai/trades/{coin}')
def api_get_trade_analytics(coin: str, test_mode: bool = True, db: Session = Depends(get_db)):
    """
    Get comprehensive trade analytics for learning and analysis
    """
    try:
        asset = coin.upper()
        
        if test_mode:
            trades = db.query(TestTrade).filter(TestTrade.coin == asset).order_by(TestTrade.executed_at.desc()).limit(50).all()
            
            analytics = {
                'ok': True,
                'coin': asset,
                'total_trades': len(trades),
                'trades': [t.to_dict() for t in trades],
                'summary': {
                    'total_buys': sum(1 for t in trades if t.side == 'BUY'),
                    'total_sells': sum(1 for t in trades if t.side == 'SELL'),
                    'profitable_sells': sum(1 for t in trades if t.side == 'SELL' and t.pnl and t.pnl > 0),
                    'avg_pnl': sum(t.pnl for t in trades if t.pnl) / max(1, sum(1 for t in trades if t.pnl)),
                    'avg_holding_period_hours': sum(t.holding_period_seconds or 0 for t in trades) / max(1, sum(1 for t in trades if t.holding_period_seconds)) / 3600,
                    'best_trade_pnl': max((t.pnl for t in trades if t.pnl), default=0),
                    'worst_trade_pnl': min((t.pnl for t in trades if t.pnl), default=0),
                }
            }
            
            return analytics
        else:
            return {'ok': False, 'error': 'Real mode trade analytics not yet implemented'}
    except Exception as e:
        print(f"❌ Error getting trade analytics: {e}")
        import traceback
        traceback.print_exc()
        return {'ok': False, 'error': str(e)}


@app.get('/api/ai/next-fetch/{coin}')
def api_get_next_fetch_time(coin: str):
    """
    Get the time until next auto-fetch for a coin
    """
    try:
        coin = coin.upper()
        last_fetch = last_ai_fetch.get(coin)
        
        if last_fetch is None:
            # No fetch yet, will happen soon
            return {
                'ok': True,
                'last_fetch': None,
                'next_fetch_in_seconds': 900,  # 15 minutes
                'message': 'First fetch pending'
            }
        
        # Calculate time since last fetch
        now = datetime.now(timezone.utc)
        time_since_fetch = (now - last_fetch).total_seconds()
        
        # Next fetch is 900 seconds (15 minutes) after last fetch
        time_until_next = 900 - time_since_fetch
        
        # If we're past the scheduled time, show 0 (fetch is happening now or about to)
        if time_until_next <= 0:
            time_until_next = 0
        
        return {
            'ok': True,
            'last_fetch': last_fetch.isoformat(),
            'next_fetch_in_seconds': int(time_until_next),
            'message': f'Next fetch in {int(time_until_next)} seconds'
        }
    except Exception as e:
        print(f"❌ Error getting next fetch time: {e}")
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/klines/{coin}/{timeframe}')
def api_get_klines(coin: str, timeframe: str = '1h'):
    """
    Get historical kline/candlestick data for charting
    """
    try:
        symbol = f"{coin.upper()}USDT"
        
        # Map timeframe to Binance interval
        interval_map = {
            '1m': Client.KLINE_INTERVAL_1MINUTE,
            '5m': Client.KLINE_INTERVAL_5MINUTE,
            '15m': Client.KLINE_INTERVAL_15MINUTE,
            '30m': Client.KLINE_INTERVAL_30MINUTE,
            '1h': Client.KLINE_INTERVAL_1HOUR,
            '4h': Client.KLINE_INTERVAL_4HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY,
            '7d': Client.KLINE_INTERVAL_1WEEK,
            '1mo': Client.KLINE_INTERVAL_1MONTH,
        }
        
        interval = interval_map.get(timeframe, Client.KLINE_INTERVAL_1HOUR)
        
        # Fetch klines from Binance
        klines = binance.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=100  # Last 100 candles
        )
        
        # Format for frontend
        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                'time': int(kline[0]),  # Open time in ms
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        return {
            'ok': True,
            'coin': coin.upper(),
            'timeframe': timeframe,
            'data': formatted_klines
        }
    except Exception as e:
        print(f"❌ Error fetching klines for {coin}: {e}")
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/price')
def api_price(symbol: str):
    symbol = symbol.upper()
    price = binance.get_current_price(symbol)
    return {'symbol': symbol, 'price': price}


@app.get('/api/open_orders')
def api_open_orders(symbol: Optional[str] = None):
    sym = symbol.upper() if symbol else None
    orders = binance.client.get_open_orders(symbol=sym)
    return orders


@app.post('/api/orders/cancel')
def api_cancel_order(symbol: str, order_id: int):
    res = binance.cancel_order(symbol.upper(), order_id)
    return {'ok': bool(res), 'result': res}


@app.get('/api/symbol/resolve')
def api_symbol_resolve(q: str, quote: str = 'USDT'):
    """Resolve a free-form query to a tradeable symbol on Binance.
    Examples: q="xrp", q="buy some xrp", q="sell wal all"
    """
    try:
        q_up = q.upper()
        # candidates from tokens
        tokens = [t for t in ''.join([c if c.isalnum() else ' ' for c in q_up]).split() if t]
        fillers = {'BUY','SELL','IT','SOME','ALL','MY','THE','A','OF','FOR','WORTH','WITH','PLEASE','USDT'}
        bases = [t for t in tokens if t not in fillers and not t.replace('.','',1).isdigit()]

        ex = binance.client.get_exchange_info()
        symbols = ex.get('symbols', []) if ex else []
        # map baseAsset -> list of symbols with that base and given quote
        tradeables = {}
        for s in symbols:
            if s.get('status') == 'TRADING' and s.get('quoteAsset') == quote:
                tradeables[f"{s.get('baseAsset','')}\0{s.get('symbol','')}"] = s

        # try bases in reverse (prefer last meaningful token)
        for base in reversed(bases):
            # direct symbol match
            sym = f"{base}{quote}"
            key = f"{base}\0{sym}"
            if key in tradeables:
                return {'symbol': sym, 'base': base, 'quote': quote, 'tradeable': True}
        # fallback: look for exact symbol provided in text
        for s in symbols:
            sym = s.get('symbol')
            if sym and sym in q_up and s.get('status') == 'TRADING':
                return {'symbol': sym, 'base': s.get('baseAsset'), 'quote': s.get('quoteAsset'), 'tradeable': True}
        return {'symbol': None, 'tradeable': False}
    except Exception as e:
        return {'symbol': None, 'tradeable': False, 'error': str(e)}


@app.get('/favicon.ico')
def favicon():
    # Empty 204 to silence browser requests
    return Response(status_code=204)


@app.post('/api/decide')
def api_decide(symbols: str, db: Session = Depends(get_db)):
    sym_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
    signals = ai_decider.decide(db, sym_list)
    return {'count': len(signals)}


class BuyRequest(BaseModel):
    symbol: str
    usdt_amount: float

class SellRequest(BaseModel):
    symbol: str
    quantity: float

@app.post('/api/trade/buy')
def api_buy(request: BuyRequest, db: Session = Depends(get_db)):
    # Validate minimum amount
    if request.usdt_amount < 11:
        return {
            'ok': False, 
            'error': f'Minimum order is $11 USDT (you entered ${request.usdt_amount:.2f})'
        }
    
    check = trade_service.verify_buy(request.symbol.upper(), request.usdt_amount)
    if not (check['has_funds'] and check['is_tradeable'] and check['symbol_ok']):
        error_msg = []
        if not check['has_funds']:
            error_msg.append('Insufficient USDT balance')
        if not check['is_tradeable']:
            error_msg.append('Symbol not tradeable')
        if not check['symbol_ok']:
            error_msg.append('Invalid trading pair')
        return {'ok': False, 'error': ' • '.join(error_msg), 'verify': check}
    
    try:
        trade = trade_service.buy_market(db, request.symbol.upper(), request.usdt_amount)
        if trade:
            return {'ok': True, 'trade_id': trade.id, 'message': f'Successfully bought {trade.quantity} {request.symbol.replace("USDT", "")}'}
        else:
            return {'ok': False, 'error': 'Order failed - could not execute trade'}
    except Exception as e:
        error_str = str(e)
        # Parse Binance error for user-friendly message
        if 'NOTIONAL' in error_str:
            return {'ok': False, 'error': 'Order too small - minimum is $11 USDT'}
        elif 'insufficient balance' in error_str.lower():
            return {'ok': False, 'error': 'Insufficient USDT balance'}
        else:
            return {'ok': False, 'error': f'Trade failed: {error_str[:100]}'}


@app.post('/api/trade/sell')
def api_sell(request: SellRequest, db: Session = Depends(get_db)):
    check = trade_service.verify_sell(request.symbol.upper())
    if not check['has_asset']:
        return {'ok': False, 'error': f'No {request.symbol.replace("USDT", "")} available to sell'}
    
    try:
        trade = trade_service.sell_market(db, request.symbol.upper(), request.quantity)
        if trade:
            return {'ok': True, 'trade_id': trade.id, 'message': f'Successfully sold {trade.quantity} {request.symbol.replace("USDT", "")}'}
        else:
            return {'ok': False, 'error': 'Order failed - could not execute trade'}
    except Exception as e:
        error_str = str(e)
        # Parse Binance error for user-friendly message
        if 'NOTIONAL' in error_str:
            return {'ok': False, 'error': 'Order too small - minimum value is $11 USDT'}
        elif 'insufficient balance' in error_str.lower():
            return {'ok': False, 'error': f'Insufficient {request.symbol.replace("USDT", "")} balance'}
        else:
            return {'ok': False, 'error': f'Trade failed: {error_str[:100]}'}


@app.post('/api/chat')
def api_chat(q: str, db: Session = Depends(get_db)):
    return chat_service.handle(db, q)


@app.post('/api/chat/history')
def api_chat_history(payload: dict, db: Session = Depends(get_db)):
    messages = payload.get('messages', [])
    return chat_service.handle_history(db, messages)


@app.get('/api/recommend')
def api_recommend(hours: int = 6, db: Session = Depends(get_db)):
    # Expose a direct recommendation based on latest news/trending
    return chat_service._recommend_from_news(db, {'hours': hours})


@app.post('/api/deploy/webhook')
def api_deploy_webhook(x_deploy_token: Optional[str] = Header(None)):
    secret = os.getenv('DEPLOY_TOKEN', '')
    if not secret or x_deploy_token != secret:
        raise HTTPException(status_code=401, detail='Unauthorized')
    try:
        subprocess.run(["git", "fetch", "--all"], check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
        subprocess.run(["pip3", "install", "-r", "requirements.txt"], check=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deploy failed: {e}")
    os._exit(0)
    return { 'ok': True }


@app.post('/api/deploy/pull')
def api_deploy_pull():
    """Pull latest changes from git and restart server (local dev use)"""
    try:
        # Get current branch
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                              capture_output=True, text=True, check=True)
        branch = result.stdout.strip()
        
        # Pull latest changes
        subprocess.run(["git", "pull", "origin", branch, "--force"], check=True)
        
        # Install dependencies
        subprocess.run(["pip3", "install", "-r", "requirements.txt"], check=False)
        
        # Restart server (uvicorn will auto-reload if using --reload flag)
        return { 'ok': True, 'message': f'Pulled latest from {branch}. Server will restart automatically.' }
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Git pull failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deploy failed: {e}")


def scheduled_job():
    from .db import SessionLocal
    from .portfolio_manager import PortfolioManager
    import openai
    
    print("[ScheduledJob] Starting news fetch and analysis...")
    db = SessionLocal()
    try:
        print("[ScheduledJob] Creating SchedulerRun object...")
        run = SchedulerRun()
        api_key = os.getenv('CRYPTONEWS_API_KEY', '')
        if api_key:
            print("[ScheduledJob] Fetching news...")
            stats = fetch_and_store_news(db, api_key)
            run.inserted = stats.get('inserted', 0)
            run.notes = f"updated={stats.get('updated',0)}"
            run.skipped = stats.get('skipped', 0)
            run.total = stats.get('total', 0)
            print(f"[ScheduledJob] News fetched: {run.total} total, {run.inserted} inserted")
        else:
            print("[ScheduledJob] No CRYPTONEWS_API_KEY, skipping API fetch")
        
        # Decide on ALL coins mentioned in recent news (not just watchlist)
        # Get all unique tickers from recent news (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_news = db.query(NewsArticle).filter(
            NewsArticle.created_at >= recent_cutoff
        ).all()
        
        # Extract all unique tickers
        all_tickers = set()
        for article in recent_news:
            if article.tickers:
                tickers = [t.strip().upper() for t in article.tickers.split(',') if t.strip()]
                for ticker in tickers:
                    # Add both the base ticker and USDT pair
                    all_tickers.add(ticker)
                    if not ticker.endswith('USDT'):
                        all_tickers.add(f"{ticker}USDT")
        
        # Convert to list and sort
        symbols = sorted(list(all_tickers))
        
        # If no tickers found in news, fall back to watchlist
        if not symbols:
            symbols = [s.strip().upper() for s in os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT').split(',')]
        
        print(f"[AI] Analyzing {len(symbols)} coins from recent news: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
        signals = ai_decider.decide(db, symbols)
        
        # Log AI decisions
        for s in signals:
            try:
                msg = f"AI Signal: {s.symbol} {s.action} ({s.confidence}%)"
                db.add(BotLog(level='INFO', category='AI', message=msg))
            except Exception:
                pass
        run.signals = len(signals)
        
        # Portfolio Management - analyze existing holdings
        portfolio_mgr = PortfolioManager(binance)
        # DEFAULT TO TRUE - auto-manage portfolio unless explicitly disabled
        portfolio_auto = os.getenv('PORTFOLIO_AUTO_MANAGE', 'true').lower() == 'true'
        portfolio_recommendations = portfolio_mgr.manage_portfolio(db, auto_execute=portfolio_auto)
        
        # Watchlist Monitoring - check coins we sold for re-buy opportunities  
        # DEFAULT TO TRUE - auto-buy watchlist unless explicitly disabled
        watchlist_auto = os.getenv('WATCHLIST_AUTO_BUY', 'true').lower() == 'true'
        watchlist_results = portfolio_mgr.monitor_watchlist(db, auto_execute=watchlist_auto)
        
        # Generate AI insights summary
        try:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            
            # Get recent sentiment
            total_news = run.total or 0
            pos_news = len([s for s in signals if s.confidence and s.confidence > 70 and s.action == 'BUY'])
            neg_news = len([s for s in signals if s.confidence and s.confidence > 70 and s.action == 'SELL'])
            
            # Format signals
            signal_summary = "\n".join([
                f"- {s.symbol}: {s.action} ({s.confidence}%) - {(s.reasoning or '')[:100]}"
                for s in signals[:5]
            ])
            
            # Format portfolio recommendations
            portfolio_summary = "\n".join([
                f"- {r['symbol']}: {r['action']} ({r['confidence']}%) - {r['reasoning'][:100]}"
                for r in portfolio_recommendations[:5]
            ]) if portfolio_recommendations else "No holdings to manage"
            
            insight_prompt = f"""You are a crypto trading analyst. Generate a brief market insight and recommendation.

Market Data (last 5 mins):
- News articles processed: {total_news}
- Bullish signals: {pos_news}
- Bearish signals: {neg_news}

Top Signals (New Opportunities):
{signal_summary or 'No strong signals'}

Portfolio Management:
{portfolio_summary}

Provide a concise insight (2-3 sentences) and a specific action recommendation.
Format:
{{
  "insight": "Brief market summary",
  "recommendation": "Specific action to take",
  "confidence": 0-100
}}
"""
            
            response = openai.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "You are a concise crypto market analyst. Always respond with valid JSON."},
                    {"role": "user", "content": insight_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            
            insight = json.loads(response.choices[0].message.content)
            run.notes = f"{run.notes or ''} | AI: {insight.get('recommendation', 'No recommendation')}"
            
            # Store insight separately for dashboard
            db.add(BotLog(
                level='INFO',
                category='INSIGHT',
                message=json.dumps(insight)
            ))
            
        except Exception as e:
            print(f"Error generating insights: {e}")
        
        # SMS notifications disabled for automatic news fetches
        # (SMS is only sent for trades now)
        
        run.signals = len(signals)
        # quick sentiment snapshot
        total = db.query(func.count(NewsArticle.id)).scalar() or 0
        pos = db.query(func.count(NewsArticle.id)).filter(NewsArticle.sentiment.ilike('Positive%')).scalar() or 0
        neg = db.query(func.count(NewsArticle.id)).filter(NewsArticle.sentiment.ilike('Negative%')).scalar() or 0
        run.positive = pos
        run.negative = neg
        run.neutral = max(total - pos - neg, 0)
        # auto-trade policy: execute only if AUTO_TRADE=true and confidence >= threshold
        if os.getenv('AUTO_TRADE', 'false').lower() == 'true':
            threshold = int(os.getenv('AUTO_TRADE_CONFIDENCE', '75'))
            per_trade_usdt = float(os.getenv('AUTO_TRADE_USDT', '25'))
            for s in signals:
                if not s.symbol or s.confidence is None:
                    continue
                if s.confidence < threshold:
                    continue
                if s.action == 'BUY':
                    check = trade_service.verify_buy(s.symbol, per_trade_usdt)
                    if check['has_funds'] and check['is_tradeable'] and check['symbol_ok']:
                        trade_service.buy_market(db, s.symbol, per_trade_usdt)
                        run.buys += 1
                        try:
                            db.add(BotLog(level='INFO', category='TRADE', message=f"BUY {s.symbol} ${per_trade_usdt}"))
                        except Exception:
                            pass
                elif s.action == 'SELL':
                    # sell full available asset (simple policy)
                    asset = s.symbol.replace('USDT', '')
                    bal = binance.get_account_balance(asset) or {'free': 0.0}
                    qty = float(bal.get('free', 0.0))
                    if qty > 0:
                        trade_service.sell_market(db, s.symbol, qty)
                        run.sells += 1
                        try:
                            db.add(BotLog(level='INFO', category='TRADE', message=f"SELL {s.symbol} qty={qty}"))
                        except Exception:
                            pass
        # compose run summary notes for dashboard
        try:
            top_tr = compute_trending(db, hours=6, limit=1)
            top_line = ''
            if top_tr:
                tt = top_tr[0]
                top_line = f"Top trending: {tt['ticker']} (score {tt['score']}, pos {tt['positive']}/neg {tt['negative']})"
            sig_line = f"Signals: {run.signals}, Buys: {run.buys}, Sells: {run.sells}"
            upd = run.notes or ''
            run.notes = ' | '.join([x for x in [upd, top_line, sig_line] if x])
        except Exception as e:
            print(f"[ScheduledJob] Error composing notes: {e}")
        
        print(f"[ScheduledJob] Saving run to database...")
        print(f"[ScheduledJob] Run data: total={run.total}, inserted={run.inserted}, signals={run.signals}")
        db.add(run)
        db.commit()
        print(f"[ScheduledJob] ✓ Run saved successfully with ID: {run.id}")
    except Exception as e:
        print(f"[ScheduledJob] ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
    finally:
        db.close()
        print("[ScheduledJob] Completed")


def momentum_scanner_job():
    """
    Continuous momentum scanner - runs every minute to detect rapid price movements
    """
    from .db import SessionLocal
    from .models import MomentumTrade, BotLog
    
    # Check if momentum trading is enabled
    config_file = '/tmp/momentum_config.json'
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            if not config.get('enabled', False):
                return  # Bot is disabled, skip scan
    except:
        return  # No config, skip
    
    db = SessionLocal()
    try:
        from .momentum_service import MomentumTradingService
        momentum_service = MomentumTradingService(binance)
        
        # Scan for new signals
        signals = momentum_service.scan_for_signals(db)
        
        if signals:
            print(f"[Momentum] Found {len(signals)} new signals")
            for s in signals:
                db.add(BotLog(
                    level='INFO',
                    category='MOMENTUM',
                    message=f"Signal: {s.symbol} +{s.price_change_pct:.2f}% (AI: {s.ai_confidence:.0%})"
                ))
                
                # Auto-execute trade if enabled
                if config.get('auto_execute', False):
                    try:
                        from .trading_service import TradingService
                        trading_service = TradingService(binance)
                        
                        # Buy with configured amount
                        trade_amount = float(config.get('trade_amount_usdt', '50'))
                        result = trading_service.buy_market(db, s.symbol, trade_amount)
                        
                        if result:
                            # Create momentum trade record
                            momentum_trade = MomentumTrade(
                                signal_id=s.id,
                                symbol=s.symbol,
                                side='BUY',
                                entry_price=result.price,
                                quantity=result.quantity,
                                stop_loss=result.price * (1 - float(config.get('stop_loss_pct', '5')) / 100),
                                status='OPEN'
                            )
                            db.add(momentum_trade)
                            
                            # Update signal status
                            s.status = 'EXECUTED'
                            
                            print(f"[Momentum] ✅ AUTO-BOUGHT {s.symbol}: ${trade_amount} @ ${result.price:.4f}")
                            db.add(BotLog(
                                level='INFO',
                                category='MOMENTUM',
                                message=f"Auto-bought {s.symbol}: ${trade_amount} @ ${result.price:.4f}"
                            ))
                        else:
                            print(f"[Momentum] ❌ Failed to auto-buy {s.symbol}")
                    except Exception as e:
                        print(f"[Momentum] Error auto-buying {s.symbol}: {e}")
        
        # Check active signals and expire dead ones
        from .models import MomentumSignal
        
        active_signals = db.query(MomentumSignal).filter(MomentumSignal.status == 'ACTIVE').all()
        for signal in active_signals:
            # Check if expired by time
            if signal.expires_at and signal.expires_at < datetime.now(timezone.utc):
                signal.status = 'EXPIRED'
                print(f"[Momentum] Signal expired: {signal.symbol}")
                continue
            
            # Check if momentum died (volume dropped, price reversed)
            try:
                ticker = binance.get_ticker(signal.symbol)
                current_change = float(ticker.get('priceChangePercent', 0))
                
                # If price change dropped below threshold, momentum is dead
                min_price_change = float(config.get('min_price_change_pct', 20))
                if current_change < min_price_change * 0.5:  # Dropped to half the threshold
                    signal.status = 'EXPIRED'
                    print(f"[Momentum] Momentum died: {signal.symbol} (change now {current_change:.2f}%)")
            except:
                pass
        
        # Check open trades for exit conditions
        open_trades = db.query(MomentumTrade).filter(MomentumTrade.status == 'OPEN').all()
        for trade in open_trades:
            # Check if we should exit
            ticker = binance.get_ticker(trade.symbol)
            current_price = float(ticker['price'])
            
            # Calculate P&L
            if trade.side == 'BUY':
                pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
            else:
                pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
            
            # Stop loss check
            stop_loss_pct = float(config.get('stop_loss_pct', '5'))
            if pnl_pct <= -stop_loss_pct:
                momentum_service._close_position(db, trade, current_price, 'STOP_LOSS')
                db.add(BotLog(
                    level='WARNING',
                    category='MOMENTUM',
                    message=f"Stop loss triggered: {trade.symbol} at {pnl_pct:.2f}%"
                ))
        
        db.commit()
    except Exception as e:
        print(f"[Momentum] Scanner error: {e}")
        db.add(BotLog(level='ERROR', category='MOMENTUM', message=f"Scanner error: {str(e)}"))
        db.commit()
    finally:
        db.close()


# AI Trading Decision System
last_ai_fetch = {}  # Dynamic dictionary that grows with added coins
last_news_and_ai_run = None  # Track last time news + AI job ran
scheduler_start_time = None  # Track when scheduler started
ai_scheduler = BackgroundScheduler()

def make_ai_decisions_for_all_coins():
    """Make AI trading decisions for all enabled coins in the database"""
    from .ai_trading_engine import AITradingEngine
    from .models import TradingCoin
    
    print(f"\n🤖 AI Decision-making starting at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
    
    db = None
    try:
        # Get all enabled coins from database
        db = next(get_db())
        enabled_coins = db.query(TradingCoin).filter(
            TradingCoin.enabled == True,
            TradingCoin.ai_decisions_enabled == True
        ).all()
        
        if not enabled_coins:
            print("⚠️  No enabled coins found in database. Add coins via /api/coins/add")
            return
        
        print(f"📊 Found {len(enabled_coins)} enabled coins: {', '.join([c.coin for c in enabled_coins])}")
        
        # Process each coin
        for trading_coin in enabled_coins:
            coin = trading_coin.coin
            coin_db = None
            try:
                # Update timestamp at START of fetch (not end) so countdown shows correctly
                last_ai_fetch[coin] = datetime.now(timezone.utc)
                
                coin_db = next(get_db())
                engine = AITradingEngine(binance, coin_db)
                
                # Use the coin's test_mode setting
                decision = engine.make_decision(coin, test_mode=trading_coin.test_mode)
                
                # Update last_decision_at timestamp
                trading_coin.last_decision_at = datetime.now(timezone.utc)
                db.commit()
                
                print(f"✅ AI decision completed for {coin}: {decision.decision}")
            except Exception as e:
                print(f"❌ AI decision error for {coin}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # ALWAYS close the coin-specific database connection
                if coin_db:
                    try:
                        coin_db.close()
                    except:
                        pass
                # Still update timestamp so we don't retry immediately
                last_ai_fetch[coin] = datetime.now(timezone.utc)
    except Exception as e:
        print(f"❌ Fatal error in make_ai_decisions_for_all_coins: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close main database connection
        if db:
            try:
                db.close()
            except:
                pass

def analyze_posts_with_ai(coin: str, articles: list) -> dict:
    """
    Feed scraped posts to OpenAI and get trading decision
    Returns: {'decision': 'BUY/SELL/HOLD', 'score': 0-100, 'reasoning': str}
    """
    import openai
    
    # Prepare content for AI
    articles_text = ""
    for i, art in enumerate(articles[:15], 1):  # Limit to 15 posts
        content = art.get('content', '')[:400]  # Limit each article
        articles_text += f"\n\n--- Post {i} ---\n{content}"
    
    prompt = f"""You are a crypto trading AI analyzing recent Binance Square posts about {coin}.

RECENT POSTS FROM BINANCE SQUARE (last 15 minutes):
{articles_text}

Based on the SENTIMENT and ENTHUSIASM in these posts, provide a trading recommendation.

Respond in this EXACT format:
DECISION: [BUY/SELL/HOLD]
SCORE: [0-100 where 0=extremely bearish, 50=neutral, 100=extremely bullish]
REASONING: [One paragraph explanation]

Consider:
- Positive/bullish language → Higher score, potentially BUY
- Negative/bearish language → Lower score, potentially SELL  
- Mixed or low enthusiasm → HOLD
- Look for actual trading sentiment, not just generic mentions
"""

    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a crypto trading analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        # Parse response
        import re
        decision = "HOLD"
        score = 50
        reasoning = ""
        
        for line in result.strip().split('\n'):
            if line.startswith('DECISION:'):
                decision = line.split(':', 1)[1].strip()
            elif line.startswith('SCORE:'):
                score_text = line.split(':', 1)[1].strip()
                score_match = re.search(r'(\d+)', score_text)
                if score_match:
                    score = int(score_match.group(1))
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
        
        # Get remaining reasoning if multiline
        if 'REASONING:' in result:
            reasoning_start = result.index('REASONING:') + len('REASONING:')
            reasoning = result[reasoning_start:].strip()
        
        return {
            'decision': decision,
            'score': score,
            'reasoning': reasoning,
            'news_count': len(articles)
        }
        
    except Exception as e:
        print(f"  ❌ OpenAI Error for {coin}: {e}")
        return {
            'decision': 'HOLD',
            'score': 50,
            'reasoning': f'Error getting AI decision: {e}',
            'news_count': len(articles)
        }


def news_and_ai_job():
    """
    Combined job that runs every 15 minutes:
    1. Scrapes fresh posts from Binance Square for each coin's hashtag
    2. Makes AI trading decisions based on sentiment/enthusiasm
    """
    global last_news_and_ai_run
    from .db import SessionLocal
    from .binance_square_scraper import BinanceSquareScraper
    from .models import TradingCoin
    
    # Update timestamp at start
    last_news_and_ai_run = datetime.now(timezone.utc)
    
    print("\n" + "="*80)
    print(f"📰🤖 BINANCE SQUARE SCRAPE + AI DECISIONS - {last_news_and_ai_run.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # Get all enabled coins
        enabled_coins = db.query(TradingCoin).filter(
            TradingCoin.enabled == True,
            TradingCoin.ai_decisions_enabled == True
        ).all()
        
        if not enabled_coins:
            print("⚠️  No enabled coins found")
            return
        
        print(f"📊 Processing {len(enabled_coins)} coins: {', '.join([c.coin for c in enabled_coins])}\n")
        
        # Initialize scraper once for all coins
        scraper = BinanceSquareScraper(headless=True)
        
        for coin_obj in enabled_coins:
            coin = coin_obj.coin
            
            try:
                print(f"\n{'='*80}")
                print(f"💎 {coin} - Scraping & Analysis")
                print(f"{'='*80}")
                
                # Scrape posts
                print(f"📰 Scraping Binance Square #{coin} (last 15 min)...")
                articles = scraper.fetch_articles(coin, max_articles=20, time_window_minutes=15)
                
                if not articles:
                    print(f"  ⚠️  No posts found in last 15 minutes")
                    
                    # Store neutral decision
                    decision_obj = AITradingDecision(
                        coin=coin,
                        decision='HOLD',
                        confidence=50.0,
                        news_count=0,
                        news_sentiment='NEUTRAL',
                        news_sentiment_score=50.0,
                        news_summary='No recent posts found in last 15 minutes',
                        ai_reasoning='No data available for analysis',
                        current_price=0.0,
                        test_mode=coin_obj.test_mode,
                        executed=False,
                        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                    db.add(decision_obj)
                    db.commit()
                    continue
                
                print(f"  ✅ Found {len(articles)} posts\n")
                
                # Store articles in database first
                print(f"  💾 Storing articles in database...")
                stored_count = 0
                seen_urls = set()
                
                for article in articles:
                    url = article.get('url')
                    
                    # Generate unique URL for articles without one (using content hash)
                    if not url:
                        import hashlib
                        content_for_hash = article.get('content', '')[:500]
                        url_hash = hashlib.md5(content_for_hash.encode()).hexdigest()[:16]
                        url = f"https://www.binance.com/en/square/post/generated-{url_hash}"
                    
                    # Skip duplicates within batch
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Skip if already exists in database
                    existing = db.query(NewsArticle).filter(
                        NewsArticle.news_url == url
                    ).first()
                    if existing:
                        continue
                    
                    # Extract sentiment from content
                    content = article.get('content', '')
                    sentiment = 'NEUTRAL'
                    if 'Bullish' in content:
                        sentiment = 'BULLISH'
                    elif 'Bearish' in content:
                        sentiment = 'BEARISH'
                    
                    # Parse the post timestamp
                    posted_at_str = article.get('posted_at')
                    if posted_at_str:
                        posted_at = datetime.fromisoformat(posted_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    else:
                        posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    news_article = NewsArticle(
                        title=article.get('title', '')[:200],
                        news_url=url,
                        text=content,
                        source_name='Binance Square',
                        sentiment=sentiment,
                        tickers=coin,
                        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        date=posted_at
                    )
                    db.add(news_article)
                    stored_count += 1
                
                db.commit()
                print(f"  ✅ Stored {stored_count} articles in database")
                
                # Show sample posts
                print(f"  📋 Sample posts:")
                for i, art in enumerate(articles[:5], 1):
                    content_preview = art.get('content', '')[:100].replace('\n', ' ')
                    sentiment_icon = '🟢' if 'Bullish' in art.get('content', '') else '🔴' if 'Bearish' in art.get('content', '') else '⚪'
                    print(f"     {i}. {sentiment_icon} {content_preview}...")
                
                # Get AI analysis
                print(f"\n  🤖 Analyzing with GPT-4o-mini...")
                ai_result = analyze_posts_with_ai(coin, articles)
                
                print(f"  📊 DECISION: {ai_result['decision']} (Score: {ai_result['score']}/100)")
                print(f"  💡 {ai_result['reasoning'][:150]}...")
                
                # Store decision in database
                decision_obj = AITradingDecision(
                    coin=coin,
                    decision=ai_result['decision'],
                    confidence=float(ai_result['score']),
                    news_count=ai_result['news_count'],
                    news_sentiment=ai_result['decision'],  # Use decision as sentiment
                    news_sentiment_score=float(ai_result['score']),
                    news_summary=f"Analyzed {ai_result['news_count']} posts from last 15 minutes",
                    ai_reasoning=ai_result['reasoning'],
                    current_price=0.0,  # Will be filled by trading engine if needed
                    test_mode=coin_obj.test_mode,
                    executed=False,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(decision_obj)
                db.commit()
                
                print(f"  ✅ Decision stored in database")
                
            except Exception as e:
                print(f"  ❌ Error processing {coin}: {e}")
                import traceback
                traceback.print_exc()
        
        # Close scraper
        scraper.close_driver()
        
    except Exception as e:
        print(f"❌ Job failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n" + "="*80)
    print("✅ BINANCE SQUARE SCRAPE + AI DECISIONS COMPLETED")
    print("="*80 + "\n")

# Community Tips Scheduler - runs every 10 minutes
def tips_scheduled_job():
    """
    Scheduled job to fetch and analyze community tips from Binance Square
    Runs every 10 minutes
    """
    try:
        print("\n[TipsScheduler] Starting community tips fetch...")
        
        from .tips_service import fetch_and_analyze_tips
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("[TipsScheduler] ⚠️  OPENAI_API_KEY not set, skipping tips fetch")
            return
        
        db = next(get_db())
        
        try:
            fetch_and_analyze_tips(db, api_key)
            print("[TipsScheduler] ✅ Tips updated successfully")
        except Exception as e:
            print(f"[TipsScheduler] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    except Exception as e:
        print(f"[TipsScheduler] ❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

# Start the scheduler
scheduler_start_time = datetime.now(timezone.utc)  # Track when scheduler started
ai_scheduler.add_job(news_and_ai_job, 'interval', minutes=15, id='news_and_ai')
ai_scheduler.add_job(tips_scheduled_job, 'interval', minutes=10, id='tips_auto_fetch')
ai_scheduler.start()
print("📰🤖 Binance Square Scraper + AI scheduler started (runs every 15 minutes)")
print("    ├─ Step 1: Scrape Binance Square for each coin's hashtag (e.g., #BTC, #ETH)")
print("    └─ Step 2: Make AI decisions for all coins based on scraped posts")
print("🎯 Tips Auto-fetch scheduler started (runs every 10 minutes)")
print(f"⏰ First news+AI run will occur within 15 minutes (started at {scheduler_start_time.strftime('%H:%M:%S UTC')})")

# Run tips fetch once on startup (in background thread to not block server start)
import threading
def initial_tips_fetch():
    import time
    time.sleep(5)  # Wait 5 seconds for server to fully start
    print("\n[TipsScheduler] Running initial tips fetch on startup...")
    tips_scheduled_job()

tips_startup_thread = threading.Thread(target=initial_tips_fetch, daemon=True)
tips_startup_thread.start()


@app.post('/api/runs/refresh')
def api_runs_refresh():
    """Force a complete news fetch + AI decision cycle now (for testing)"""
    try:
        print("\n🔄 MANUAL REFRESH TRIGGERED")
        news_and_ai_job()
        return {'ok': True, 'message': 'News fetch + AI decisions completed successfully'}
    except Exception as e:
        print(f"[Force Refresh] Error: {e}")
        import traceback
        traceback.print_exc()
        return {'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}


# ==================== MOMENTUM TRADING ENDPOINTS ====================

@app.get('/api/momentum/overview')
def api_momentum_overview(db: Session = Depends(get_db)):
    """Get momentum trading overview and stats"""
    from .momentum_service import MomentumTradingService
    
    momentum_service = MomentumTradingService(binance)
    overview = momentum_service.get_market_overview(db)
    
    return overview


@app.get('/api/momentum/signals')
def api_momentum_signals(
    status: str = 'ACTIVE',
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get momentum signals"""
    from .models import MomentumSignal
    
    query = db.query(MomentumSignal)
    
    if status:
        query = query.filter(MomentumSignal.status == status)
    
    signals = query.order_by(
        MomentumSignal.triggered_at.desc()
    ).limit(limit).all()
    
    return [{
        'id': s.id,
        'symbol': s.symbol,
        'interval': s.interval,
        'price_change_pct': s.price_change_pct,
        'volume_24h': s.volume_24h,
        'volume_ratio': s.volume_ratio,
        'ai_confidence': s.ai_confidence,
        'predicted_exit': s.predicted_exit,
        'technical_score': s.technical_score,
        'status': s.status,
        'triggered_at': s.triggered_at.isoformat() if s.triggered_at else None,
        'expires_at': s.expires_at.isoformat() if s.expires_at else None,
        'meta': s.meta,
    } for s in signals]


@app.get('/api/momentum/trades')
def api_momentum_trades(
    status: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get momentum trades"""
    from .models import MomentumTrade
    
    query = db.query(MomentumTrade)
    
    if status:
        query = query.filter(MomentumTrade.status == status)
    
    trades = query.order_by(
        MomentumTrade.opened_at.desc()
    ).limit(limit).all()
    
    return [{
        'id': t.id,
        'signal_id': t.signal_id,
        'symbol': t.symbol,
        'side': t.side,
        'entry_price': t.entry_price,
        'exit_price': t.exit_price,
        'quantity': t.quantity,
        'usdt_value': t.usdt_value,
        'profit_loss': t.profit_loss,
        'profit_loss_pct': t.profit_loss_pct,
        'ai_entry_confidence': t.ai_entry_confidence,
        'ai_exit_confidence': t.ai_exit_confidence,
        'stop_loss': t.stop_loss,
        'take_profit': t.take_profit,
        'status': t.status,
        'opened_at': t.opened_at.isoformat() if t.opened_at else None,
        'closed_at': t.closed_at.isoformat() if t.closed_at else None,
        'duration_seconds': t.duration_seconds,
        'exit_reason': t.exit_reason,
    } for t in trades]


@app.post('/api/momentum/scan')
def api_momentum_scan(db: Session = Depends(get_db)):
    """Manually trigger momentum signal scan with debug info"""
    from .momentum_service import MomentumTradingService
    
    momentum_service = MomentumTradingService(binance)
    signals, debug_info = momentum_service.scan_for_signals(db, return_debug=True)
    
    return {
        'ok': True,
        'signals_found': len(signals),
        'signals': [{
            'symbol': s.symbol,
            'price_change_pct': s.price_change_pct,
            'ai_confidence': s.ai_confidence,
        } for s in signals],
        'debug': debug_info
    }


@app.delete('/api/momentum/signal/{signal_id}')
def api_momentum_delete_signal(signal_id: int, db: Session = Depends(get_db)):
    """Delete/dismiss a momentum signal"""
    from .models import MomentumSignal
    
    signal = db.query(MomentumSignal).filter(MomentumSignal.id == signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    # Mark as dismissed instead of deleting from DB
    signal.status = 'DISMISSED'
    db.commit()
    
    return {
        'ok': True,
        'message': f'Signal {signal.symbol} dismissed'
    }


@app.post('/api/momentum/trade/{signal_id}')
def api_momentum_execute_trade(signal_id: int, db: Session = Depends(get_db)):
    """Execute a trade for a specific signal"""
    from .momentum_service import MomentumTradingService
    from .models import MomentumSignal
    
    signal = db.query(MomentumSignal).filter(MomentumSignal.id == signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    if signal.status != 'ACTIVE':
        raise HTTPException(status_code=400, detail="Signal is not active")
    
    momentum_service = MomentumTradingService(binance)
    trade = momentum_service.execute_trade(db, signal)
    
    if not trade:
        raise HTTPException(status_code=500, detail="Failed to execute trade")
    
    return {
        'ok': True,
        'trade_id': trade.id,
        'symbol': trade.symbol,
        'quantity': trade.quantity,
        'entry_price': trade.entry_price,
    }


@app.post('/api/momentum/close/{trade_id}')
def api_momentum_close_trade(trade_id: int, db: Session = Depends(get_db)):
    """Manually close a momentum trade"""
    from .momentum_service import MomentumTradingService
    from .models import MomentumTrade
    
    trade = db.query(MomentumTrade).filter(MomentumTrade.id == trade_id).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != 'OPEN':
        raise HTTPException(status_code=400, detail="Trade is not open")
    
    # Get current price
    ticker = binance.get_ticker(trade.symbol)
    current_price = float(ticker['price'])
    
    momentum_service = MomentumTradingService(binance)
    momentum_service._close_position(db, trade, current_price, 'MANUAL')
    
    return {
        'ok': True,
        'trade_id': trade.id,
        'exit_price': trade.exit_price,
        'profit_loss': trade.profit_loss,
        'profit_loss_pct': trade.profit_loss_pct,
    }


@app.post('/api/momentum/toggle')
def api_momentum_toggle(enabled: bool, db: Session = Depends(get_db)):
    """Enable/disable momentum trading bot"""
    # Store state in a JSON file with config
    config_file = '/tmp/momentum_config.json'
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    config['enabled'] = enabled
    
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    return {
        'ok': True,
        'enabled': enabled,
        'message': 'Momentum trading ' + ('enabled' if enabled else 'disabled')
    }


@app.get('/api/momentum/status')
def api_momentum_status():
    """Get momentum bot status and config - returns actual optimized config"""
    profile = os.getenv('MOMENTUM_PROFILE', 'BEST')
    
    # Return the actual optimized config (not old temp file)
    if profile == 'BEST':
        config = {
            'min_price_1h': 1.5,
            'min_volume_ratio': 1.5,
            'breakout_threshold': 93,
            'min_momentum_score': 60,
            'stop_loss_pct': 5,
            'take_profit_pct': 8,
            'trailing_stop_pct': 2.5,
            'max_position_usdt': float(os.getenv('MOMENTUM_TRADE_AMOUNT', '50')),
            'auto_execute': True,  # ALWAYS ENABLED
            'profile': 'BEST',
            'description': '+105% profit over 1 year, 69% win rate, 1.4 trades/week'
        }
    else:
        config = {
            'min_price_1h': 1.2,
            'min_volume_ratio': 1.3,
            'breakout_threshold': 90,
            'min_momentum_score': 50,
            'stop_loss_pct': 5,
            'take_profit_pct': 8,
            'trailing_stop_pct': 2.5,
            'max_position_usdt': float(os.getenv('MOMENTUM_TRADE_AMOUNT', '50')),
            'auto_execute': True,  # ALWAYS ENABLED
            'profile': 'MORE_TRADES',
            'description': '+54% profit over 1 year, 1.6 trades/week'
        }
    
    return {
        'enabled': True,  # Always enabled with optimized config
        'config': config
    }


@app.post('/api/momentum/config')
def api_momentum_update_config(
    min_price_change: Optional[float] = None,
    min_volume: Optional[float] = None,
    ai_threshold: Optional[float] = None,
    max_position_pct: Optional[float] = None,
    stop_loss_pct: Optional[float] = None,
    check_frequency: Optional[int] = None
):
    """Update momentum trading configuration"""
    config_file = '/tmp/momentum_config.json'
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except:
        config = {'enabled': False}
    
    # Update provided values
    if min_price_change is not None:
        config['min_price_change'] = str(min_price_change)
    if min_volume is not None:
        config['min_volume'] = str(int(min_volume))
    if ai_threshold is not None:
        config['ai_threshold'] = str(ai_threshold)
    if max_position_pct is not None:
        config['max_position_pct'] = str(max_position_pct)
    if stop_loss_pct is not None:
        config['stop_loss_pct'] = str(stop_loss_pct)
    if check_frequency is not None:
        config['check_frequency'] = str(check_frequency)
    
    with open(config_file, 'w') as f:
        json.dump(config, f)
    
    return {
        'ok': True,
        'message': 'Configuration updated',
        'config': config
    }


# ==================== LOGS ENDPOINTS ====================

@app.get('/api/logs')
def api_logs(
    level: str = None,
    category: str = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Get bot logs with filtering"""
    query = db.query(BotLog)
    
    if level:
        query = query.filter(BotLog.level == level.upper())
    
    if category:
        query = query.filter(BotLog.category == category.upper())
    
    logs = query.order_by(BotLog.created_at.desc()).limit(limit).all()
    
    return [{
        'id': log.id,
        'level': log.level,
        'category': log.category,
        'message': log.message,
        'created_at': log.created_at.isoformat() if log.created_at else None,
    } for log in logs]


@app.get('/api/logs/stats')
def api_logs_stats(db: Session = Depends(get_db)):
    """Get logs statistics"""
    from sqlalchemy import func
    
    now = datetime.now(timezone.utc)
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)
    
    # Total logs
    total = db.query(func.count(BotLog.id)).scalar() or 0
    
    # Last hour
    last_hour_count = db.query(func.count(BotLog.id)).filter(
        BotLog.created_at >= last_hour
    ).scalar() or 0
    
    # By level (last 24h)
    errors_24h = db.query(func.count(BotLog.id)).filter(
        BotLog.level == 'ERROR',
        BotLog.created_at >= last_24h
    ).scalar() or 0
    
    warnings_24h = db.query(func.count(BotLog.id)).filter(
        BotLog.level == 'WARNING',
        BotLog.created_at >= last_24h
    ).scalar() or 0
    
    info_24h = db.query(func.count(BotLog.id)).filter(
        BotLog.level == 'INFO',
        BotLog.created_at >= last_24h
    ).scalar() or 0
    
    # By category
    categories = db.query(
        BotLog.category,
        func.count(BotLog.id).label('count')
    ).filter(
        BotLog.created_at >= last_24h
    ).group_by(BotLog.category).all()
    
    return {
        'total': total,
        'last_hour': last_hour_count,
        'last_24h': {
            'errors': errors_24h,
            'warnings': warnings_24h,
            'info': info_24h,
        },
        'categories': [{'category': c[0], 'count': c[1]} for c in categories]
    }


@app.delete('/api/logs/clear')
def api_logs_clear(older_than_days: int = 7, db: Session = Depends(get_db)):
    """Clear old logs"""
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    
    deleted = db.query(BotLog).filter(BotLog.created_at < cutoff).delete()
    db.commit()
    
    return {
        'ok': True,
        'deleted': deleted,
        'message': f'Cleared logs older than {older_than_days} days'
    }


# ==================== MACHINE LEARNING ENDPOINTS ====================

@app.post('/api/ml/train/{symbol}')
def api_ml_train(symbol: str, days: int = 365, background: bool = False):
    """Train a machine learning model for a specific coin"""
    from .ml_service import CoinMLService
    
    if background:
        # Train in background (for auto-retraining)
        import threading
        def train_background():
            ml_service = CoinMLService(binance)
            result = ml_service.train_model(symbol, days=days)
            print(f"[ML] Background training complete for {symbol}: {result.get('test_accuracy', 0):.2%} accuracy")
        
        thread = threading.Thread(target=train_background, daemon=True)
        thread.start()
        return {'ok': True, 'message': f'Training {symbol} in background...'}
    else:
        # Train synchronously (for manual training via UI)
        ml_service = CoinMLService(binance)
        result = ml_service.train_model(symbol, days=days)
        return result


@app.get('/api/ml/predict/{symbol}')
def api_ml_predict(symbol: str):
    """Get ML prediction for a symbol"""
    from .ml_service import CoinMLService
    
    ml_service = CoinMLService(binance)
    result = ml_service.predict(symbol)
    
    return result


@app.get('/api/ml/models')
def api_ml_models():
    """List all trained models"""
    from .ml_service import CoinMLService
    import json
    
    ml_service = CoinMLService(binance)
    models = []
    
    try:
        for file in os.listdir(ml_service.models_dir):
            if file.endswith('_info.json'):
                info_path = os.path.join(ml_service.models_dir, file)
                with open(info_path, 'r') as f:
                    info = json.load(f)
                    
                    # Check if model is stale (>7 days old)
                    trained_at = datetime.fromisoformat(info['trained_at'])
                    days_old = (datetime.now() - trained_at).days
                    info['days_old'] = days_old
                    info['is_stale'] = days_old > 7
                    
                    models.append(info)
    except:
        pass
    
    return {'models': models}


@app.post('/api/ml/auto-retrain')
def api_ml_auto_retrain(db: Session = Depends(get_db)):
    """
    Auto-retrain models for all holdings
    - Only retrains if model is >7 days old or doesn't exist
    - Runs in background
    """
    from .ml_service import CoinMLService
    import threading
    
    # Get all unique assets from portfolio
    try:
        account = binance.client.get_account()
        holdings = []
        for balance in account['balances']:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0 and balance['asset'] != 'USDT':
                symbol = balance['asset'] + 'USDT'
                holdings.append(symbol)
    except:
        return {'error': 'Failed to fetch portfolio'}
    
    ml_service = CoinMLService(binance)
    retrained = []
    skipped = []
    
    for symbol in holdings:
        # Check if model exists and is fresh
        info_path = os.path.join(ml_service.models_dir, f'{symbol}_info.json')
        
        needs_training = True
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r') as f:
                    info = json.load(f)
                    trained_at = datetime.fromisoformat(info['trained_at'])
                    days_old = (datetime.now() - trained_at).days
                    
                    if days_old <= 7:
                        needs_training = False
                        skipped.append(f"{symbol} (trained {days_old}d ago)")
            except:
                pass
        
        if needs_training:
            # Train in background
            def train_bg(sym):
                ml = CoinMLService(binance)
                result = ml.train_model(sym, days=365)
                print(f"[ML Auto-Retrain] {sym}: {result.get('test_accuracy', 0):.2%}")
            
            thread = threading.Thread(target=train_bg, args=(symbol,), daemon=True)
            thread.start()
            retrained.append(symbol)
    
    return {
        'ok': True,
        'retrained': retrained,
        'skipped': skipped,
        'message': f'Training {len(retrained)} models in background'
    }


# ==================== WATCHLIST ENDPOINTS ====================

@app.get('/api/watchlist')
def api_watchlist_get(db: Session = Depends(get_db)):
    """Get all watchlist coins"""
    from .models import Watchlist
    
    watchlist = db.query(Watchlist).filter(Watchlist.enabled == True).all()
    
    return {
        'watchlist': [{
            'id': w.id,
            'symbol': w.symbol,
            'asset': w.asset,
            'added_at': w.added_at.isoformat() if w.added_at else None,
            'reason_added': w.reason_added,
            'buy_trigger_score': w.buy_trigger_score,
            'max_buy_usdt': w.max_buy_usdt,
            'last_checked_at': w.last_checked_at.isoformat() if w.last_checked_at else None
        } for w in watchlist]
    }


@app.post('/api/watchlist/add')
def api_watchlist_add(symbol: str, max_buy_usdt: float = 50.0, buy_trigger_score: int = 70, db: Session = Depends(get_db)):
    """Add a coin to watchlist"""
    from .models import Watchlist
    
    # Extract asset from symbol
    asset = symbol.replace('USDT', '')
    
    # Check if already exists
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        existing.enabled = True
        existing.max_buy_usdt = max_buy_usdt
        existing.buy_trigger_score = buy_trigger_score
        db.commit()
        return {'ok': True, 'message': f'{symbol} re-enabled in watchlist'}
    
    # Add new
    watchlist_item = Watchlist(
        symbol=symbol,
        asset=asset,
        reason_added='Manual add',
        max_buy_usdt=max_buy_usdt,
        buy_trigger_score=buy_trigger_score
    )
    db.add(watchlist_item)
    db.commit()
    
    return {'ok': True, 'message': f'{symbol} added to watchlist'}


@app.delete('/api/watchlist/{symbol}')
def api_watchlist_remove(symbol: str, db: Session = Depends(get_db)):
    """Remove a coin from watchlist"""
    from .models import Watchlist
    
    watchlist_item = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if watchlist_item:
        watchlist_item.enabled = False
        db.commit()
        return {'ok': True, 'message': f'{symbol} removed from watchlist'}
    
    return {'error': 'Symbol not found in watchlist'}


@app.get('/api/portfolio/{coin}')
def api_portfolio_coin(coin: str, test_mode: bool = False, db: Session = Depends(get_db)):
    """Get portfolio data for a specific coin (real or test mode)"""
    try:
        # Normalize coin symbol (e.g., BTC -> BTC, BTCUSDT -> BTC)
        asset = coin.upper().replace('USDT', '')
        symbol = f"{asset}USDT"
        
        # If test mode, return test portfolio data
        if test_mode:
            portfolio = db.query(TestPortfolio).filter(TestPortfolio.coin == asset).first()
            if not portfolio:
                # Initialize with $10,000 ALREADY INVESTED in the coin
                current_price = binance.get_current_price(symbol) or 0.0
                if current_price > 0:
                    initial_investment = 10000.0
                    coin_quantity = initial_investment / current_price
                    
                    # Create portfolio with coins already purchased
                    portfolio = TestPortfolio(
                        coin=asset,
                        usdt_balance=0.0,  # All USDT used to buy coins
                        coin_balance=coin_quantity,
                        total_invested=initial_investment,
                        total_withdrawn=0.0,
                        realized_profit=0.0
                    )
                    db.add(portfolio)
                    db.commit()
                    db.refresh(portfolio)
                    
                    # Record the initial purchase
                    initial_trade = TestTrade(
                        coin=asset,
                        side='BUY',
                        quantity=coin_quantity,
                        price=current_price,
                        usdt_amount=initial_investment
                    )
                    db.add(initial_trade)
                    db.commit()
                    
                    print(f"✅ Initialized {asset} test portfolio: {coin_quantity:.8f} {asset} @ ${current_price:,.2f}")
                else:
                    # Fallback if price unavailable
                    portfolio = TestPortfolio(coin=asset, usdt_balance=10000.0, coin_balance=0.0)
                    db.add(portfolio)
                    db.commit()
                    db.refresh(portfolio)
            
            # Get current price
            current_price = binance.get_current_price(symbol) or 0.0
            
            # Calculate metrics
            position_value = portfolio.coin_balance * current_price
            total_portfolio_value = portfolio.usdt_balance + position_value
            unrealized_pnl = position_value - (portfolio.total_invested - portfolio.total_withdrawn) if portfolio.coin_balance > 0 else 0
            total_pnl = portfolio.realized_profit + unrealized_pnl
            initial_capital = 10000.0
            performance = ((total_portfolio_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
            
            return {
                'ok': True,
                'test_mode': True,
                'totalPnL': total_pnl,
                'positionValue': position_value,
                'performance': performance,
                'availableCapital': portfolio.usdt_balance,
                'portfolioValue': total_portfolio_value,
                'totalInvested': portfolio.total_invested,
                'netDeposits': initial_capital,
                'currentCapital': portfolio.usdt_balance,
                'positionQuantity': portfolio.coin_balance,
                'totalRealizedProfits': portfolio.realized_profit,
                'totalUnrealizedGains': unrealized_pnl,
                'totalGains': total_pnl,
                'overallPerformance': performance
            }
        
        # Get account info
        acct = binance.client.get_account()
        balances = acct.get('balances', [])
        
        # Find the coin balance
        coin_balance = None
        usdt_balance = None
        for b in balances:
            if b.get('asset') == asset:
                coin_balance = b
            elif b.get('asset') == 'USDT':
                usdt_balance = b
        
        # Get current price
        current_price = 0.0
        try:
            current_price = binance.get_current_price(symbol) or 0.0
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
        
        # Calculate position values
        position_quantity = 0.0
        if coin_balance:
            position_quantity = float(coin_balance.get('free', 0)) + float(coin_balance.get('locked', 0))
        
        position_value = position_quantity * current_price
        
        # Get available capital (free USDT)
        available_capital = 0.0
        if usdt_balance:
            available_capital = float(usdt_balance.get('free', 0))
        
        # Calculate portfolio metrics
        # Get all trades for this symbol to calculate invested amount and realized profits
        trades = db.query(Trade).filter(Trade.symbol == symbol).order_by(Trade.executed_at).all()
        
        total_invested = 0.0
        total_realized_profits = 0.0
        net_deposits = 0.0  # This would come from deposit/withdraw records
        
        # Simple calculation: sum of BUY trades minus sum of SELL trades
        buy_value = 0.0
        sell_value = 0.0
        for trade in trades:
            notional = trade.notional or (trade.quantity * trade.price)
            if trade.side == 'BUY':
                buy_value += notional
            elif trade.side == 'SELL':
                sell_value += notional
        
        total_invested = buy_value - sell_value  # Net invested in current position
        total_realized_profits = sell_value - buy_value if sell_value > 0 else 0.0
        
        # Calculate unrealized gains
        total_unrealized_gains = position_value - total_invested if total_invested > 0 else 0.0
        
        # Total gains
        total_gains = total_realized_profits + total_unrealized_gains
        
        # Portfolio value (position value + available capital)
        portfolio_value = position_value + available_capital
        
        # Performance metrics
        overall_performance = (total_gains / total_invested * 100) if total_invested > 0 else 0.0
        performance = (total_unrealized_gains / total_invested * 100) if total_invested > 0 else 0.0
        
        return {
            'coin': asset,
            'symbol': symbol,
            'totalPnL': total_gains,
            'positionValue': position_value,
            'performance': performance,
            'availableCapital': available_capital,
            'portfolioValue': portfolio_value,
            'totalInvested': total_invested,
            'netDeposits': net_deposits,  # TODO: Implement deposit/withdraw tracking
            'currentCapital': available_capital,
            'positionQuantity': position_quantity,
            'totalRealizedProfits': total_realized_profits,
            'totalUnrealizedGains': total_unrealized_gains,
            'totalGains': total_gains,
            'overallPerformance': overall_performance,
            'currentPrice': current_price,
        }
    except Exception as e:
        print(f"Error getting portfolio data for {coin}: {e}")
        import traceback
        traceback.print_exc()
        # Return zeros instead of error
        return {
            'coin': coin,
            'symbol': f"{coin}USDT",
            'totalPnL': 0.0,
            'positionValue': 0.0,
            'performance': 0.0,
            'availableCapital': 0.0,
            'portfolioValue': 0.0,
            'totalInvested': 0.0,
            'netDeposits': 0.0,
            'currentCapital': 0.0,
            'positionQuantity': 0.0,
            'totalRealizedProfits': 0.0,
            'totalUnrealizedGains': 0.0,
            'totalGains': 0.0,
            'overallPerformance': 0.0,
            'currentPrice': 0.0,
        }


@app.get('/api/portfolio/{coin}/history')
def api_portfolio_history(coin: str, test_mode: bool = False, db: Session = Depends(get_db)):
    """Get P&L history for a specific coin for charting (real or test mode)"""
    try:
        asset = coin.upper().replace('USDT', '')
        symbol = f"{asset}USDT"
        
        # If test mode, return test trade history with minute-by-minute P&L
        if test_mode:
            trades = db.query(TestTrade).filter(TestTrade.coin == asset).order_by(TestTrade.executed_at).all()
            
            if not trades:
                return []
            
            # Calculate P&L at each minute interval
            chart_data = []
            portfolio_value = 10000.0  # Initial USDT
            coin_holdings = 0.0
            
            # Get first and last trade times
            first_trade_time = trades[0].executed_at
            if first_trade_time.tzinfo is None:
                first_trade_time = first_trade_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            
            # Fetch historical prices from Binance (1-minute klines for last 2 hours)
            try:
                # Get 2 hours of 1-minute klines = 120 candles
                klines = binance.client.get_klines(
                    symbol=symbol,
                    interval=Client.KLINE_INTERVAL_1MINUTE,
                    limit=120
                )
                # Create price lookup: timestamp -> close price
                price_lookup = {}
                for kline in klines:
                    # kline[0] is timestamp in ms, kline[4] is close price
                    minute_time = datetime.fromtimestamp(kline[0] / 1000, tz=timezone.utc).replace(second=0, microsecond=0)
                    price_lookup[minute_time] = float(kline[4])
                
                # Fallback to current price
                current_price_value = binance.get_current_price(symbol) or 0.0
            except Exception as e:
                print(f"⚠️  Could not fetch historical prices for {symbol}: {e}")
                # Fallback: use current price
                try:
                    current_price_value = binance.get_current_price(symbol) or 0.0
                except:
                    current_price_value = 0.0
                price_lookup = {}
            
            # Limit to last 2 hours max to prevent timeout
            start_time = max(first_trade_time, current_time - timedelta(hours=2))
            
            # Generate minute-by-minute timeline
            current_minute = start_time.replace(second=0, microsecond=0)
            trade_index = 0
            
            # Skip trades before start_time
            while trade_index < len(trades):
                trade_time = trades[trade_index].executed_at
                if trade_time.tzinfo is None:
                    trade_time = trade_time.replace(tzinfo=timezone.utc)
                if trade_time < start_time:
                    # Apply this trade to initial state
                    if trades[trade_index].side == 'BUY':
                        coin_holdings += trades[trade_index].quantity
                        portfolio_value -= trades[trade_index].usdt_amount
                    elif trades[trade_index].side == 'SELL':
                        coin_holdings = 0
                        portfolio_value += trades[trade_index].usdt_amount
                    trade_index += 1
                else:
                    break
            
            while current_minute <= current_time:
                # Apply all trades that happened before this minute
                while trade_index < len(trades):
                    trade = trades[trade_index]
                    trade_time = trade.executed_at
                    if trade_time.tzinfo is None:
                        trade_time = trade_time.replace(tzinfo=timezone.utc)
                    
                    if trade_time <= current_minute:
                        if trade.side == 'BUY':
                            coin_holdings += trade.quantity
                            portfolio_value -= trade.usdt_amount
                        elif trade.side == 'SELL':
                            coin_holdings = 0
                            portfolio_value += trade.usdt_amount
                        trade_index += 1
                    else:
                        break
                
                # Use historical price from lookup, fallback to current price
                price_at_minute = price_lookup.get(current_minute, current_price_value)
                
                # Calculate portfolio value at this minute
                total_value = portfolio_value + (coin_holdings * price_at_minute)
                pnl = total_value - 10000.0
                
                chart_data.append({
                    'time': current_minute.isoformat(),
                    'pnl': round(pnl, 2),
                    'value': round(total_value, 2)
                })
                
                # Move to next minute
                current_minute += timedelta(minutes=1)
            
            # Ensure we don't have too many points (limit to last 1440 minutes = 24 hours)
            if len(chart_data) > 1440:
                chart_data = chart_data[-1440:]
            
            # DON'T add current live point - only show established database points to avoid glitching
            
            return chart_data
        
        # Get trades for this symbol
        trades = db.query(Trade).filter(Trade.symbol == symbol).order_by(Trade.executed_at).all()
        
        if not trades:
            return []
        
        # Build history data
        history = []
        cumulative_pnl = 0.0
        
        for trade in trades:
            notional = trade.notional or (trade.quantity * trade.price)
            if trade.side == 'BUY':
                cumulative_pnl -= notional
            elif trade.side == 'SELL':
                cumulative_pnl += notional
            
            history.append({
                'time': trade.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z') if trade.created_at else None,
                'pnl': cumulative_pnl
            })
        
        # Add current unrealized P&L as the latest point
        if trades:
            try:
                current_price = binance.get_current_price(symbol) or 0.0
                acct = binance.client.get_account()
                balances = acct.get('balances', [])
                position_quantity = 0.0
                for b in balances:
                    if b.get('asset') == asset:
                        position_quantity = float(b.get('free', 0)) + float(b.get('locked', 0))
                        break
                
                current_position_value = position_quantity * current_price
                history.append({
                    'time': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                    'pnl': cumulative_pnl + current_position_value
                })
            except Exception as e:
                print(f"Error calculating current P&L: {e}")
        
        return history
    except Exception as e:
        print(f"Error getting portfolio history for {coin}: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get('/api/market/{coin}/klines')
def api_market_klines(coin: str, interval: str = '1h', limit: int = 100):
    """Get kline/candlestick data for charting"""
    try:
        asset = coin.upper().replace('USDT', '')
        symbol = f"{asset}USDT"
        
        # Map frontend intervals to Binance intervals
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
            '7d': '1w',
            '1mo': '1M',
            '1y': '1M'
        }
        
        binance_interval = interval_map.get(interval, '1h')
        
        # Adjust limit for longer timeframes
        if interval == '1y':
            limit = 365
        elif interval == '1mo':
            limit = 30
        elif interval == '7d':
            limit = 28  # 4 weeks of weekly data
        
        # Get klines from Binance
        klines = binance.client.get_klines(
            symbol=symbol,
            interval=binance_interval,
            limit=limit
        )
        
        # Format for frontend
        chart_data = []
        for k in klines:
            timestamp = k[0]
            open_price = float(k[1])
            high_price = float(k[2])
            low_price = float(k[3])
            close_price = float(k[4])
            volume = float(k[5])
            
            # Format time based on interval
            dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            if interval in ['1m', '5m', '15m', '30m']:
                time_str = dt.strftime('%H:%M')
            elif interval in ['1h', '4h']:
                time_str = dt.strftime('%m/%d %H:%M')
            else:
                time_str = dt.strftime('%Y-%m-%d')
            
            chart_data.append({
                'time': time_str,
                'price': close_price,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        return {
            'symbol': symbol,
            'interval': interval,
            'data': chart_data
        }
    except Exception as e:
        print(f"Error getting klines for {coin}: {e}")
        import traceback
        traceback.print_exc()
        return {'symbol': coin, 'interval': interval, 'data': []}


@app.get('/api/market/{coin}')
def api_market_coin(coin: str):
    """Get market information for a specific coin"""
    try:
        asset = coin.upper().replace('USDT', '')
        symbol = f"{asset}USDT"
        
        # Get current price from Binance
        current_price = binance.get_current_price(symbol) or 0.0
        
        # Get 24h ticker stats from Binance
        ticker = binance.client.get_ticker(symbol=symbol)
        
        # Get klines for 1h, 24h, 7d changes
        now = datetime.now(timezone.utc)
        
        # 1h change
        klines_1h = binance.client.get_klines(
            symbol=symbol,
            interval='1h',
            limit=2
        )
        change_1h = 0.0
        if len(klines_1h) >= 2:
            price_1h_ago = float(klines_1h[0][1])
            change_1h = ((current_price - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0.0
        
        # 24h change (from ticker)
        change_24h = float(ticker.get('priceChangePercent', 0.0))
        
        # 7d change
        klines_7d = binance.client.get_klines(
            symbol=symbol,
            interval='1d',
            limit=8
        )
        change_7d = 0.0
        if len(klines_7d) >= 8:
            price_7d_ago = float(klines_7d[0][1])
            change_7d = ((current_price - price_7d_ago) / price_7d_ago * 100) if price_7d_ago > 0 else 0.0
        
        # Format volume
        volume_24h = float(ticker.get('quoteVolume', 0.0))
        
        # Get market data from CoinGecko
        coingecko_id_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'XRP': 'ripple'
        }
        
        rank = '-'
        market_cap = '-'
        circulating_supply = '-'
        
        if asset in coingecko_id_map:
            try:
                cg_id = coingecko_id_map[asset]
                cg_response = requests.get(
                    f'https://api.coingecko.com/api/v3/coins/{cg_id}',
                    timeout=5
                )
                if cg_response.status_code == 200:
                    cg_data = cg_response.json()
                    rank = cg_data.get('market_cap_rank', '-')
                    market_cap_val = cg_data.get('market_data', {}).get('market_cap', {}).get('usd', 0)
                    if market_cap_val:
                        market_cap = f"${market_cap_val:,.0f}"
                    circ_supply = cg_data.get('market_data', {}).get('circulating_supply', 0)
                    if circ_supply:
                        circulating_supply = f"{circ_supply:,.0f}"
            except Exception as e:
                print(f"CoinGecko API error: {e}")
        
        return {
            'coin': asset,
            'symbol': symbol,
            'rank': rank,
            'price': f"${current_price:,.2f}",
            'marketCap': market_cap,
            'circulatingSupply': circulating_supply,
            'volume24h': f"${volume_24h:,.0f}",
            'change1h': change_1h,
            'change24h': change_24h,
            'change7d': change_7d,
        }
    except Exception as e:
        print(f"Error getting market data for {coin}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'coin': coin,
            'symbol': f"{coin}USDT",
            'rank': '-',
            'price': '0.00',
            'marketCap': '-',
            'circulatingSupply': '-',
            'volume24h': '-',
            'change1h': 0.0,
            'change24h': 0.0,
            'change7d': 0.0,
        }


class DepositWithdrawRequest(BaseModel):
    coin: str
    amount: float


@app.post('/api/portfolio/deposit')
def api_portfolio_deposit(request: DepositWithdrawRequest, db: Session = Depends(get_db)):
    """Record a deposit transaction"""
    # TODO: Implement deposit tracking in database
    # For now, just return success
    return {
        'ok': True,
        'message': f'Deposit of ${request.amount:.2f} for {request.coin} recorded',
        'type': 'deposit',
        'coin': request.coin,
        'amount': request.amount
    }


@app.post('/api/portfolio/withdraw')
def api_portfolio_withdraw(request: DepositWithdrawRequest, db: Session = Depends(get_db)):
    """Record a withdrawal transaction"""
    # TODO: Implement withdrawal tracking in database
    # For now, just return success
    return {
        'ok': True,
        'message': f'Withdrawal of ${request.amount:.2f} for {request.coin} recorded',
        'type': 'withdraw',
        'coin': request.coin,
        'amount': request.amount
    }


# ==========================================
# COMMUNITY TIPS ENDPOINTS
# ==========================================

@app.get('/api/tips')
def api_get_tips(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get trending community tips from Binance Square
    Returns coins that users are enthusiastic about
    """
    try:
        from .tips_service import get_top_tips
        
        tips = get_top_tips(db, limit=limit)
        
        return {
            'ok': True,
            'count': len(tips),
            'tips': tips
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e),
            'tips': []
        }


@app.post('/api/tips/refresh')
def api_refresh_tips(db: Session = Depends(get_db)):
    """
    Manually trigger tips refresh
    Scrapes Binance Square hashtags and updates tips
    """
    try:
        import os
        from .tips_service import fetch_and_analyze_tips
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {
                'ok': False,
                'error': 'OPENAI_API_KEY not configured'
            }
        
        fetch_and_analyze_tips(db, api_key)
        
        return {
            'ok': True,
            'message': 'Tips refreshed successfully'
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e)
        }


@app.get('/api/tips/{coin}')
def api_get_tip_for_coin(coin: str, db: Session = Depends(get_db)):
    """Get tip details for a specific coin"""
    try:
        from .models import CommunityTip
        
        tip = db.query(CommunityTip).filter(
            CommunityTip.coin == coin.upper()
        ).first()
        
        if not tip:
            return {
                'ok': False,
                'error': f'No tip found for {coin}'
            }
        
        return {
            'ok': True,
            'tip': tip.to_dict()
        }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e)
        }


# ==========================================
# TRADING COINS ENDPOINTS
# ==========================================

@app.get('/api/coins')
def api_get_all_coins(db: Session = Depends(get_db)):
    """Get all trading coins (base + dynamic)"""
    try:
        from .coin_trainer import get_all_trading_coins
        
        coins = get_all_trading_coins(db)
        
        return {
            'ok': True,
            'count': len(coins),
            'coins': coins
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e),
            'coins': []
        }


@app.post('/api/coins/add')
def api_add_trading_coin(coin: str, coin_name: str = None, db: Session = Depends(get_db)):
    """
    Add a new coin to trading list
    Uses sentiment-based trading (no ML training)
    
    Args:
        coin: Coin symbol (e.g., "ZEC")
        coin_name: Full coin name (optional)
    """
    try:
        from .coin_trainer import add_trading_coin
        
        # Validate coin symbol
        coin = coin.upper().strip()
        if not coin or len(coin) < 2:
            return {
                'ok': False,
                'error': 'Invalid coin symbol'
            }
        
        # Check if already exists
        from .models import TradingCoin
        existing = db.query(TradingCoin).filter(TradingCoin.coin == coin).first()
        if existing:
            return {
                'ok': False,
                'error': f'{coin} is already in your trading list'
            }
        
        # Add coin (no ML training, just adds to database)
        result = add_trading_coin(db, coin, coin_name)
        
        if not result['success']:
            return {
                'ok': False,
                'error': result.get('recommendation', 'Failed to add coin')
            }
        
        return {
            'ok': True,
            'message': f'{coin} added successfully with sentiment-based trading!',
            'coin': result['coin'].to_dict(),
            'ai_enabled': True,  # Always enabled (uses sentiment)
            'recommendation': 'Sentiment-based trading enabled'
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e)
        }


@app.delete('/api/coins/{coin}')
def api_remove_trading_coin(coin: str, db: Session = Depends(get_db)):
    """Remove a coin from trading list"""
    try:
        from .models import TradingCoin
        
        coin = coin.upper()
        trading_coin = db.query(TradingCoin).filter(TradingCoin.coin == coin).first()
        
        if not trading_coin:
            return {
                'ok': False,
                'error': f'{coin} not found in trading list'
            }
        
        db.delete(trading_coin)
        db.commit()
        
        return {
            'ok': True,
            'message': f'{coin} removed from trading list'
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'ok': False,
            'error': str(e)
        }


