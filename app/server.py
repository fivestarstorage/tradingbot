import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from .db import Base, engine, get_db
from .models import NewsArticle, Signal, Position, Trade
from .news_service import fetch_and_store_news
from .ai_decider import AIDecider
from .trading_service import TradingService
from core.binance_client import BinanceClient

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

# Load environment from .env if present (project root)
load_dotenv()

app = FastAPI(title="TradingBot v2")

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


@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    latest_news = db.query(NewsArticle).order_by(NewsArticle.created_at.desc()).limit(20).all()
    latest_signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
    open_positions = db.query(Position).filter(Position.status == 'OPEN').all()
    recent_trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(20).all()
    return templates.TemplateResponse('advanced_dashboard.html', {
        'request': request,
        'news': latest_news,
        'signals': latest_signals,
        'positions': open_positions,
        'trades': recent_trades
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
            'date': n.date.isoformat() if n.date else None
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


def scheduled_job():
    from .db import SessionLocal
    db = SessionLocal()
    try:
        api_key = os.getenv('CRYPTONEWS_API_KEY', '')
        if api_key:
            fetch_and_store_news(db, api_key)
        # decide on a default watchlist
        symbols = os.getenv('WATCHLIST', 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT').split(',')
        ai_decider.decide(db, [s.strip().upper() for s in symbols])
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'interval', minutes=5, id='news_and_decision')
scheduler.start()


