import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, Query, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from apscheduler.schedulers.background import BackgroundScheduler
from .db import Base, engine, get_db
from .models import NewsArticle, Signal, Position, Trade, SchedulerRun
from datetime import timezone
from .news_service import fetch_and_store_news
from .ai_decider import AIDecider
from .trading_service import TradingService
from .trending_service import compute_trending
from .chat_service import ChatService
from core.binance_client import BinanceClient
import subprocess
from typing import Optional, Dict, Any

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

# Load environment from .env if present (project root)
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TradingBot v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv('CORS_ORIGIN', 'http://localhost:3000'),
        os.getenv('CORS_ORIGIN_2', ''),
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
            # normalize to explicit UTC (Z) so frontend can convert to local tz reliably
            'date': (
                (n.date.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'))
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
            'created_at': s.created_at.isoformat()
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
    # Merge and sort by time desc
    merged = sig_entries + tr_entries
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
            'created_at': t.created_at.isoformat(),
        } for t in trs
    ]


@app.get('/api/insights')
def api_insights(db: Session = Depends(get_db)):
    # Basic insights: counts, top symbols, hourly signal counts (last 24h)
    total_signals = db.query(func.count(Signal.id)).scalar() or 0
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
    return {'signals_total': total_signals, 'top_symbols': top_symbols, 'signals_hourly': series, 'trades': {'buys': buys, 'sells': sells}}


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


@app.post('/api/trade/buy')
def api_buy(symbol: str, usdt: float, db: Session = Depends(get_db)):
    check = trade_service.verify_buy(symbol.upper(), usdt)
    if not (check['has_funds'] and check['is_tradeable'] and check['symbol_ok']):
        return {'ok': False, 'verify': check}
    trade = trade_service.buy_market(db, symbol.upper(), usdt)
    return {'ok': trade is not None, 'trade_id': trade.id if trade else None}


@app.post('/api/trade/sell')
def api_sell(symbol: str, quantity: float, db: Session = Depends(get_db)):
    check = trade_service.verify_sell(symbol.upper())
    if not check['has_asset']:
        return {'ok': False, 'verify': check}
    trade = trade_service.sell_market(db, symbol.upper(), quantity)
    return {'ok': trade is not None, 'trade_id': trade.id if trade else None}


@app.post('/api/chat')
def api_chat(q: str, db: Session = Depends(get_db)):
    return chat_service.handle(db, q)


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
    db = SessionLocal()
    try:
        run = SchedulerRun()
        api_key = os.getenv('CRYPTONEWS_API_KEY', '')
        if api_key:
            stats = fetch_and_store_news(db, api_key)
            run.inserted = stats.get('inserted', 0)
            run.skipped = stats.get('skipped', 0)
            run.total = stats.get('total', 0)
        # decide on a default watchlist
        symbols = [s.strip().upper() for s in os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT').split(',')]
        signals = ai_decider.decide(db, symbols)
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
                elif s.action == 'SELL':
                    # sell full available asset (simple policy)
                    asset = s.symbol.replace('USDT', '')
                    bal = binance.get_account_balance(asset) or {'free': 0.0}
                    qty = float(bal.get('free', 0.0))
                    if qty > 0:
                        trade_service.sell_market(db, s.symbol, qty)
                        run.sells += 1
        db.add(run)
        db.commit()
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'interval', minutes=5, id='news_and_decision')
scheduler.start()


@app.post('/api/runs/refresh')
def api_runs_refresh():
    # Force a news fetch + decision run now
    scheduled_job()
    return {'ok': True}


