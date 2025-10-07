"""
News Monitor - Fetches Live Crypto News
Integrates with NewsAPI and other sources
"""
import requests
import time
import os
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class NewsMonitor:
    """Monitors crypto news from multiple sources"""
    
    def __init__(self, newsapi_key=None, cryptonews_key=None):
        # Legacy NewsAPI (kept for fallback)
        self.newsapi_key = newsapi_key
        self.newsapi_url = "https://newsapi.org/v2/everything"
        
        # NEW: CryptoNews API (UNLIMITED crypto news!)
        self.cryptonews_key = cryptonews_key or os.getenv('CRYPTONEWS_API_KEY')
        self.cryptonews_url = "https://cryptonews-api.com/api/v1"
        
        # Track seen articles to avoid duplicates
        self.seen_articles = set()
        
        # CACHING to reduce API calls (CRITICAL for 3 calls/day limit!)
        self.cached_articles = []
        self.cache_time = None
        self.cache_duration = 28800  # Cache for 8 HOURS (28800 seconds) for 3 calls/day
        
        # Rate limiting
        self.last_api_call = None
        self.min_call_interval = 60  # Minimum 60 seconds between API calls
        
        # DAILY LIMIT TRACKING
        self.newsapi_daily_limit = 100
        self.newsapi_calls_today = 0
        
        # CryptoNews API STRICT LIMIT: 3 calls/day!
        self.cryptonews_daily_limit = 3
        self.cryptonews_calls_today = 0
        self.calls_reset_date = None
        
        self._load_daily_stats()
    
    def _load_daily_stats(self):
        """Load daily API call stats from file"""
        try:
            if os.path.exists('newsapi_stats.json'):
                with open('newsapi_stats.json', 'r') as f:
                    stats = json.load(f)
                    self.newsapi_calls_today = stats.get('newsapi_calls_today', 0)
                    self.cryptonews_calls_today = stats.get('cryptonews_calls_today', 0)
                    reset_date_str = stats.get('reset_date')
                    if reset_date_str:
                        self.calls_reset_date = datetime.fromisoformat(reset_date_str).date()
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            self.newsapi_calls_today = 0
            self.cryptonews_calls_today = 0
            self.calls_reset_date = None
    
    def _save_daily_stats(self):
        """Save daily API call stats to file"""
        try:
            stats = {
                'newsapi_calls_today': self.newsapi_calls_today,
                'cryptonews_calls_today': self.cryptonews_calls_today,
                'reset_date': datetime.now().date().isoformat()
            }
            with open('newsapi_stats.json', 'w') as f:
                json.dump(stats, f)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")
    
    def _check_cryptonews_limit(self):
        """Check CryptoNews API daily limit (3 calls/day!)"""
        today = datetime.now().date()
        
        # Reset counter if it's a new day
        if self.calls_reset_date is None or today > self.calls_reset_date:
            self.cryptonews_calls_today = 0
            self.newsapi_calls_today = 0
            self.calls_reset_date = today
            self._save_daily_stats()
            logger.info(f"📅 New day! Reset API counters")
        
        # Check CryptoNews limit
        if self.cryptonews_calls_today >= self.cryptonews_daily_limit:
            logger.warning(f"⚠️ CryptoNews daily limit reached! ({self.cryptonews_calls_today}/{self.cryptonews_daily_limit} calls)")
            return False
        
        return True
    
    def _increment_cryptonews_counter(self):
        """Increment CryptoNews call counter"""
        self.cryptonews_calls_today += 1
        self._save_daily_stats()
        remaining = self.cryptonews_daily_limit - self.cryptonews_calls_today
        logger.info(f"📊 CryptoNews calls today: {self.cryptonews_calls_today}/{self.cryptonews_daily_limit} (⏳ {remaining} remaining)")
        logger.warning(f"⚠️ CACHING for 8 hours to preserve remaining calls!")
    
    def _check_newsapi_limit(self):
        """Check NewsAPI daily limit"""
        today = datetime.now().date()
        
        if self.calls_reset_date is None or today > self.calls_reset_date:
            self.cryptonews_calls_today = 0
            self.newsapi_calls_today = 0
            self.calls_reset_date = today
            self._save_daily_stats()
        
        if self.newsapi_calls_today >= self.newsapi_daily_limit:
            logger.warning(f"⚠️ NewsAPI limit reached! ({self.newsapi_calls_today}/{self.newsapi_daily_limit})")
            return False
        
        return True
    
    def _increment_newsapi_counter(self):
        """Increment NewsAPI call counter"""
        self.newsapi_calls_today += 1
        self._save_daily_stats()
        remaining = self.newsapi_daily_limit - self.newsapi_calls_today
        logger.info(f"📊 NewsAPI calls today: {self.newsapi_calls_today}/{self.newsapi_daily_limit} (⏳ {remaining} remaining)")
    
    def fetch_cryptonews_api(self, items=50):
        """
        Fetch crypto news from CryptoNews API (PRIMARY SOURCE)
        CRITICAL: Only 3 calls per day! Must cache aggressively!
        """
        if not self.cryptonews_key:
            logger.warning("No CryptoNews API key provided, falling back to other sources")
            return []
        
        # CHECK DAILY LIMIT FIRST
        if not self._check_cryptonews_limit():
            logger.error(f"❌ CryptoNews API limit exhausted! Using cache or fallback sources")
            return []
        
        try:
            # Use the correct CryptoNews API endpoint
            # According to docs: https://cryptonews-api.com/documentation
            # Endpoint: /api/v1/category?section=general&items=50&page=1&token=XXX
            params = {
                'section': 'general',  # General crypto news
                'items': items,
                'page': 1,
                'token': self.cryptonews_key  # Use 'token' not 'auth_token'
            }
            
            # Use /category endpoint
            response = requests.get(f"{self.cryptonews_url}/category", params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # CryptoNews API returns data directly in 'data' field
            articles = []
            news_data = data.get('data', [])
            
            if not news_data:
                logger.warning("CryptoNews API returned no articles")
                return []
            
            for article in news_data:
                article_id = f"cryptonews_{article.get('news_url', '')}"
                
                if article_id in self.seen_articles:
                    continue
                
                self.seen_articles.add(article_id)
                
                # Parse date
                date_str = article.get('date', '')
                try:
                    timestamp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z') if date_str else datetime.now()
                except:
                    timestamp = datetime.now()
                
                articles.append({
                    'id': article_id,
                    'title': article.get('title', ''),
                    'description': article.get('text', '')[:500],  # First 500 chars
                    'content': article.get('text', ''),
                    'source': article.get('source_name', 'CryptoNews'),
                    'url': article.get('news_url', ''),
                    'published_at': date_str,
                    'timestamp': timestamp,
                    'tickers': article.get('tickers', []),  # Mentioned coins!
                    'sentiment': article.get('sentiment', 'Neutral')
                })
            
            logger.info(f"📰 Fetched {len(articles)} articles from CryptoNews API")
            self._increment_cryptonews_counter()
            return articles
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from CryptoNews API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error with CryptoNews API: {e}")
            return []
    
    def fetch_crypto_news(self, symbols=['BTC', 'ETH', 'crypto', 'bitcoin', 'ethereum'], hours_back=1, force_fresh=False):
        """
        Fetch recent crypto news (PRIMARY: CryptoNews API, FALLBACK: others)
        
        Args:
            symbols: List of keywords to search for (used for fallback sources)
            hours_back: How many hours of news to fetch
            force_fresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of news articles with metadata
        """
        # CHECK CACHE FIRST (unless force_fresh)
        if not force_fresh and self.cache_time and self.cached_articles:
            time_since_cache = (datetime.now() - self.cache_time).total_seconds()
            if time_since_cache < self.cache_duration:
                logger.info(f"📦 Using cached articles ({len(self.cached_articles)} articles, {int(self.cache_duration - time_since_cache)}s until refresh)")
                return self.cached_articles
        
        if force_fresh:
            logger.info("🔄 FORCE FRESH FETCH - Bypassing cache for startup")
        
        # PRIORITY 1: Try CryptoNews API (UNLIMITED, best crypto coverage)
        if self.cryptonews_key:
            articles = self.fetch_cryptonews_api(items=50)
            if articles:
                self.cached_articles = articles
                self.cache_time = datetime.now()
                logger.info(f"💾 Cached {len(articles)} CryptoNews articles")
                return articles
        
        # PRIORITY 2: Try CoinDesk RSS (FREE, no limits)
        articles = self.fetch_coindesk_news()
        if articles:
            self.cached_articles = articles
            self.cache_time = datetime.now()
            return articles
        
        # PRIORITY 3: Fall back to NewsAPI (rate limited)
        if not self.newsapi_key:
            logger.warning("No news sources available!")
            return []
        
        # CHECK DAILY LIMIT
        if not self._check_newsapi_limit():
            logger.warning("All news sources exhausted or rate limited")
            return []
        
        # RATE LIMITING - wait if called too recently
        if self.last_api_call:
            time_since_last = (datetime.now() - self.last_api_call).total_seconds()
            if time_since_last < self.min_call_interval:
                wait_time = self.min_call_interval - time_since_last
                logger.info(f"⏳ Rate limit: waiting {int(wait_time)}s before next API call...")
                time.sleep(wait_time)
        
        # Build query
        query = ' OR '.join(symbols)
        
        # Time range
        from_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        try:
            params = {
                'q': query,
                'from': from_time,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.newsapi_key
            }
            
            response = requests.get(self.newsapi_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'ok':
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = []
            
            for article in data.get('articles', []):
                # Create unique ID
                article_id = f"{article['source']['name']}_{article['publishedAt']}"
                
                # Skip if already seen
                if article_id in self.seen_articles:
                    continue
                
                self.seen_articles.add(article_id)
                
                articles.append({
                    'id': article_id,
                    'title': article['title'],
                    'description': article['description'] or '',
                    'content': article['content'] or '',
                    'source': article['source']['name'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'timestamp': datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                })
            
            logger.info(f"Fetched {len(articles)} crypto-specific articles")
            
            # Update rate limiting tracker and increment counter
            self.last_api_call = datetime.now()
            self._increment_newsapi_counter()
            
            # If we got very few articles, expand to general tech/business news
            if len(articles) < 5:
                logger.info(f"Only {len(articles)} crypto articles, expanding to tech/business news...")
                tech_articles = self.fetch_tech_news(hours_back)
                articles.extend(tech_articles)
                logger.info(f"Total: {len(articles)} articles (AI will filter for crypto relevance)")
            
            # UPDATE CACHE
            self.cached_articles = articles
            self.cache_time = datetime.now()
            logger.info(f"💾 Cached {len(articles)} articles for {self.cache_duration}s")
            
            return articles
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if '429' in error_msg:
                logger.warning(f"⚠️ NewsAPI rate limit hit!")
                # Try cache first
                if self.cached_articles:
                    logger.info(f"📦 Returning {len(self.cached_articles)} cached articles")
                    return self.cached_articles
                # Otherwise use FREE CoinDesk RSS
                logger.info(f"📰 Falling back to FREE CoinDesk RSS feed...")
                return self.fetch_coindesk_news()
            else:
                logger.error(f"Error fetching news: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Return cache if available
            if self.cached_articles:
                return self.cached_articles
            return []
    
    def fetch_tech_news(self, hours_back=2):
        """
        Fetch general tech and business news
        AI will filter for crypto/blockchain relevance
        (WITH RATE LIMITING AND DAILY LIMIT)
        """
        if not self.newsapi_key:
            return []
        
        # CHECK DAILY LIMIT
        if not self._check_newsapi_limit():
            logger.info(f"⏳ Daily limit reached, skipping tech news fetch")
            return []
        
        # RATE LIMITING - avoid double API calls
        if self.last_api_call:
            time_since_last = (datetime.now() - self.last_api_call).total_seconds()
            if time_since_last < 10:  # Wait at least 10 seconds between calls
                logger.info(f"⏳ Skipping tech news fetch (too soon after last call)")
                return []
        
        from_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        try:
            # Get top tech headlines
            params = {
                'category': 'technology',
                'from': from_time,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.newsapi_key,
                'pageSize': 50  # Get more articles
            }
            
            response = requests.get('https://newsapi.org/v2/top-headlines', params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message')}")
                return []
            
            articles = []
            for article in data.get('articles', []):
                # Skip if no title or description
                if not article.get('title') or not article.get('description'):
                    continue
                
                article_id = f"{article['source']['name']}_{article['publishedAt']}"
                
                if article_id in self.seen_articles:
                    continue
                
                self.seen_articles.add(article_id)
                
                articles.append({
                    'id': article_id,
                    'title': article['title'],
                    'description': article['description'] or '',
                    'content': article['content'] or '',
                    'source': article['source']['name'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'timestamp': datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                })
            
            logger.info(f"Fetched {len(articles)} tech news articles")
            self._increment_newsapi_counter()
            return articles
        
        except Exception as e:
            logger.error(f"Error fetching tech news: {e}")
            return []
    
    def fetch_coindesk_news(self):
        """
        Fetch crypto news from CoinDesk RSS (FREE, no API key needed!)
        Alternative to NewsAPI when rate limited
        """
        try:
            import feedparser
            
            url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
            feed = feedparser.parse(url)
            
            articles = []
            for entry in feed.entries[:20]:  # Get latest 20
                article_id = f"coindesk_{entry.published}"
                
                if article_id in self.seen_articles:
                    continue
                
                self.seen_articles.add(article_id)
                
                articles.append({
                    'id': article_id,
                    'title': entry.title,
                    'description': entry.summary if hasattr(entry, 'summary') else '',
                    'content': entry.summary if hasattr(entry, 'summary') else '',
                    'source': 'CoinDesk',
                    'url': entry.link,
                    'published_at': entry.published,
                    'timestamp': datetime.now()
                })
            
            logger.info(f"📰 Fetched {len(articles)} articles from CoinDesk RSS (FREE!)")
            return articles
        
        except Exception as e:
            logger.error(f"Error fetching CoinDesk news: {e}")
            return []
    
    def fetch_coingecko_trending(self):
        """Fetch trending coins from CoinGecko (no API key needed)"""
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            trending = []
            for coin in data.get('coins', [])[:10]:  # Top 10
                item = coin['item']
                trending.append({
                    'symbol': item['symbol'].upper(),
                    'name': item['name'],
                    'rank': item['market_cap_rank'],
                    'price_btc': item['price_btc'],
                    'score': item['score']
                })
            
            logger.info(f"Fetched {len(trending)} trending coins")
            return trending
        
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")
            return []
    
    def extract_mentioned_symbols(self, text):
        """Extract crypto symbols mentioned in text (EXPANDED!)"""
        # All supported crypto symbols and their common names
        symbols = {
            # Major coins
            'BTC': 'BTCUSDT',
            'BITCOIN': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'ETHEREUM': 'ETHUSDT',
            'BNB': 'BNBUSDT',
            'BINANCE': 'BNBUSDT',
            
            # Layer 1s
            'SOL': 'SOLUSDT',
            'SOLANA': 'SOLUSDT',
            'XRP': 'XRPUSDT',
            'RIPPLE': 'XRPUSDT',
            'ADA': 'ADAUSDT',
            'CARDANO': 'ADAUSDT',
            'AVAX': 'AVAXUSDT',
            'AVALANCHE': 'AVAXUSDT',
            'DOT': 'DOTUSDT',
            'POLKADOT': 'DOTUSDT',
            'TRX': 'TRXUSDT',
            'TRON': 'TRXUSDT',
            'TON': 'TONUSDT',
            'TELEGRAM': 'TONUSDT',
            'NEAR': 'NEARUSDT',
            'ATOM': 'ATOMUSDT',
            'COSMOS': 'ATOMUSDT',
            'SUI': 'SUIUSDT',
            'APT': 'APTUSDT',
            'APTOS': 'APTUSDT',
            'ICP': 'ICPUSDT',
            'INTERNET COMPUTER': 'ICPUSDT',
            'FIL': 'FILUSDT',
            'FILECOIN': 'FILUSDT',
            'VET': 'VETUSDT',
            'VECHAIN': 'VETUSDT',
            'ALGO': 'ALGOUSDT',
            'ALGORAND': 'ALGOUSDT',
            'HBAR': 'HBARUSDT',
            'HEDERA': 'HBARUSDT',
            'STX': 'STXUSDT',
            'STACKS': 'STXUSDT',
            'INJ': 'INJUSDT',
            'INJECTIVE': 'INJUSDT',
            
            # Layer 2s
            'MATIC': 'MATICUSDT',
            'POLYGON': 'MATICUSDT',
            'ARB': 'ARBUSDT',
            'ARBITRUM': 'ARBUSDT',
            'OP': 'OPUSDT',
            'OPTIMISM': 'OPUSDT',
            
            # DeFi
            'LINK': 'LINKUSDT',
            'CHAINLINK': 'LINKUSDT',
            'UNI': 'UNIUSDT',
            'UNISWAP': 'UNIUSDT',
            'AAVE': 'AAVEUSDT',
            'MKR': 'MKRUSDT',
            'MAKER': 'MKRUSDT',
            'LDO': 'LDOUSDT',
            'LIDO': 'LDOUSDT',
            'RNDR': 'RNDRUSDT',
            'RENDER': 'RNDRUSDT',
            
            # Memecoins
            'DOGE': 'DOGEUSDT',
            'DOGECOIN': 'DOGEUSDT',
            'SHIB': 'SHIBUSDT',
            'SHIBA': 'SHIBUSDT',
            'SHIBA INU': 'SHIBUSDT',
            'PEPE': 'PEPEUSDT',
            
            # Others
            'LTC': 'LTCUSDT',
            'LITECOIN': 'LTCUSDT',
            'ETC': 'ETCUSDT',
            'ETHEREUM CLASSIC': 'ETCUSDT',
        }
        
        text_upper = text.upper()
        found = []
        
        for keyword, symbol in symbols.items():
            if keyword in text_upper:
                if symbol not in found:
                    found.append(symbol)
        
        return found


def test_news_monitor():
    """Test the news monitor"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 70)
    print("📰 TESTING NEWS MONITOR")
    print("=" * 70)
    print()
    
    # Get API key
    newsapi_key = os.getenv('NEWSAPI_KEY')
    if not newsapi_key:
        print("❌ No NEWSAPI_KEY found in environment")
        print("Get free key at: https://newsapi.org/")
        return
    
    monitor = NewsMonitor(newsapi_key=newsapi_key)
    
    print("Fetching crypto news...")
    articles = monitor.fetch_crypto_news(hours_back=24)
    
    print(f"\n✅ Found {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   Time: {article['published_at']}")
        symbols = monitor.extract_mentioned_symbols(article['title'] + ' ' + article['description'])
        if symbols:
            print(f"   Symbols: {', '.join(symbols)}")
        print()
    
    print("\nFetching trending coins...")
    trending = monitor.fetch_coingecko_trending()
    
    print(f"\n✅ Top {len(trending)} trending coins:\n")
    for coin in trending[:5]:
        print(f"  {coin['symbol']} - {coin['name']} (Rank: {coin['rank']})")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_news_monitor()
