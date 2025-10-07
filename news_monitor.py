"""
News Monitor - Fetches Live Crypto News
Integrates with NewsAPI and other sources
"""
import requests
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class NewsMonitor:
    """Monitors crypto news from multiple sources"""
    
    def __init__(self, newsapi_key=None):
        self.newsapi_key = newsapi_key
        self.newsapi_url = "https://newsapi.org/v2/everything"
        
        # Track seen articles to avoid duplicates
        self.seen_articles = set()
        
        # CACHING to reduce API calls
        self.cached_articles = []
        self.cache_time = None
        self.cache_duration = 600  # Cache for 10 minutes (600 seconds)
        
        # Rate limiting
        self.last_api_call = None
        self.min_call_interval = 60  # Minimum 60 seconds between API calls
    
    def fetch_crypto_news(self, symbols=['BTC', 'ETH', 'crypto', 'bitcoin', 'ethereum'], hours_back=1):
        """
        Fetch recent crypto news (WITH CACHING to avoid rate limits)
        
        Args:
            symbols: List of keywords to search for
            hours_back: How many hours of news to fetch
            
        Returns:
            List of news articles with metadata
        """
        if not self.newsapi_key:
            logger.warning("No NewsAPI key provided")
            return []
        
        # CHECK CACHE FIRST
        if self.cache_time and self.cached_articles:
            time_since_cache = (datetime.now() - self.cache_time).total_seconds()
            if time_since_cache < self.cache_duration:
                logger.info(f"📦 Using cached articles ({len(self.cached_articles)} articles, {int(self.cache_duration - time_since_cache)}s until refresh)")
                return self.cached_articles
        
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
            
            # Update rate limiting tracker
            self.last_api_call = datetime.now()
            
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
        (WITH RATE LIMITING)
        """
        if not self.newsapi_key:
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
        """Extract crypto symbols mentioned in text"""
        # Common crypto symbols
        symbols = {
            'BTC': 'BTCUSDT',
            'BITCOIN': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'ETHEREUM': 'ETHUSDT',
            'BNB': 'BNBUSDT',
            'BINANCE': 'BNBUSDT',
            'SOL': 'SOLUSDT',
            'SOLANA': 'SOLUSDT',
            'XRP': 'XRPUSDT',
            'RIPPLE': 'XRPUSDT',
            'ADA': 'ADAUSDT',
            'CARDANO': 'ADAUSDT',
            'DOGE': 'DOGEUSDT',
            'DOGECOIN': 'DOGEUSDT',
            'AVAX': 'AVAXUSDT',
            'AVALANCHE': 'AVAXUSDT',
            'DOT': 'DOTUSDT',
            'POLKADOT': 'DOTUSDT',
            'MATIC': 'MATICUSDT',
            'POLYGON': 'MATICUSDT'
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
