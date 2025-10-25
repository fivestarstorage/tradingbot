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
from .models import NewsArticle, Signal, Position, Trade, SchedulerRun, BotLog
from datetime import timezone
import datetime
from .news_service import fetch_and_store_news
from .ai_decider import AIDecider
from .trading_service import TradingService
from .trending_service import compute_trending
from .chat_service import ChatService
from core.binance_client import BinanceClient
import subprocess
from typing import Optional, Dict, Any
import json

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

# Init services
binance = BinanceClient(
    api_key=os.getenv('BINANCE_API_KEY', ''),
    api_secret=os.getenv('BINANCE_API_SECRET', ''),
    testnet=os.getenv('USE_TESTNET', 'true').lower() == 'true'
)
trade_service = TradingService(binance)
ai_decider = AIDecider()
chat_service = ChatService(binance, trade_service)

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
    recent_trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(20).all()
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
            # Dates are stored as naive UTC in DB, add Z suffix to indicate UTC
            'date': (
                (n.date.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'))
                if n.date else None
            ),
            'ingested_at': (
                (n.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'))
                if n.created_at else None
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


@app.get('/api/logs')
def api_logs(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    sigs = db.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
    trs = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
    bl = db.query(BotLog).order_by(BotLog.created_at.desc()).limit(limit).all()
    sig_entries = [{
        'type': 'signal',
        'created_at': s.created_at.isoformat(),
        'message': f"{s.symbol} {s.action} ({s.confidence}%) - {s.reasoning[:120] if s.reasoning else ''}"
    } for s in sigs]
    tr_entries = [{
        'type': 'trade',
        'created_at': t.created_at.isoformat(),
        'message': f"{t.side} {t.symbol} qty={t.quantity:.6f} @ {t.price:.4f} (${t.notional:.2f})"
    } for t in trs]
    ai_entries = [{
        'type': l.category.lower(),
        'created_at': l.created_at.isoformat(),
        'message': l.message
    } for l in bl]
    # Merge and sort by time desc
    merged = sig_entries + tr_entries + ai_entries
    merged.sort(key=lambda x: x['created_at'], reverse=True)
    return merged[:limit]


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
    trs = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
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
    
    # top symbols by signals
    sym_counts = db.query(Signal.symbol, func.count(Signal.id)).group_by(Signal.symbol).order_by(func.count(Signal.id).desc()).limit(5).all()
    top_symbols = [[s, c] for s, c in sym_counts]
    # hourly signals for last 24h
    import datetime
    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(hours=24)
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
            'watchlist': os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT')
        }
    }


@app.get('/api/ai/summary')
def api_ai_summary(window_minutes: int = 90, db: Session = Depends(get_db)):
    now = datetime.datetime.utcnow()
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
def api_deploy_webhook(x_deploy_token: str | None = Header(None)):
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


def scheduled_job():
    from .db import SessionLocal
    from .portfolio_manager import PortfolioManager
    import openai
    
    db = SessionLocal()
    try:
        run = SchedulerRun()
        api_key = os.getenv('CRYPTONEWS_API_KEY', '')
        if api_key:
            stats = fetch_and_store_news(db, api_key)
            run.inserted = stats.get('inserted', 0)
            run.notes = f"updated={stats.get('updated',0)}"
            run.skipped = stats.get('skipped', 0)
            run.total = stats.get('total', 0)
        
        # Decide on watchlist (new coins to potentially buy)
        symbols = [s.strip().upper() for s in os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT').split(',')]
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
        portfolio_auto = os.getenv('PORTFOLIO_AUTO_MANAGE', 'false').lower() == 'true'
        portfolio_recommendations = portfolio_mgr.manage_portfolio(db, auto_execute=portfolio_auto)
        
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
        except Exception:
            pass
        db.add(run)
        db.commit()
    finally:
        db.close()


def momentum_scanner_job():
    """
    Continuous momentum scanner - runs every minute to detect rapid price movements
    """
    from .db import SessionLocal
    
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


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'interval', minutes=15, id='news_and_decision')
scheduler.add_job(momentum_scanner_job, 'interval', minutes=1, id='momentum_scanner')  # Runs every minute
scheduler.start()


@app.post('/api/runs/refresh')
def api_runs_refresh():
    # Force a news fetch + decision run now
    scheduled_job()
    return {'ok': True}


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
    """Manually trigger momentum signal scan"""
    from .momentum_service import MomentumTradingService
    
    momentum_service = MomentumTradingService(binance)
    signals = momentum_service.scan_for_signals(db)
    
    return {
        'ok': True,
        'signals_found': len(signals),
        'signals': [{
            'symbol': s.symbol,
            'price_change_pct': s.price_change_pct,
            'ai_confidence': s.ai_confidence,
        } for s in signals]
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
    """Get momentum bot status and config"""
    config_file = '/tmp/momentum_config.json'
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            enabled = config.get('enabled', False)
    except:
        enabled = False
        config = {}
    
    return {
        'enabled': enabled,
        'config': {
            'min_price_change': config.get('min_price_change', os.getenv('MOMENTUM_MIN_PRICE_CHANGE', '20')),
            'min_volume': config.get('min_volume', os.getenv('MOMENTUM_MIN_VOLUME', '1000000')),
            'ai_threshold': config.get('ai_threshold', os.getenv('MOMENTUM_AI_THRESHOLD', '0.8')),
            'max_position_pct': config.get('max_position_pct', os.getenv('MOMENTUM_MAX_POSITION', '10')),
            'stop_loss_pct': config.get('stop_loss_pct', os.getenv('MOMENTUM_STOP_LOSS', '5')),
            'check_frequency': config.get('check_frequency', '60'),  # seconds between scans
        }
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
    from datetime import timedelta
    from sqlalchemy import func
    
    now = datetime.datetime.utcnow()
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
    from datetime import timedelta
    
    cutoff = datetime.datetime.utcnow() - timedelta(days=older_than_days)
    
    deleted = db.query(BotLog).filter(BotLog.created_at < cutoff).delete()
    db.commit()
    
    return {
        'ok': True,
        'deleted': deleted,
        'message': f'Cleared logs older than {older_than_days} days'
    }


