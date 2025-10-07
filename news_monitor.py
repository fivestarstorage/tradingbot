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
    
    def fetch_crypto_news(self, symbols=['BTC', 'ETH', 'crypto', 'bitcoin', 'ethereum'], hours_back=1):
        """
        Fetch recent crypto news
        
        Args:
            symbols: List of keywords to search for
            hours_back: How many hours of news to fetch
            
        Returns:
            List of news articles with metadata
        """
        if not self.newsapi_key:
            logger.warning("No NewsAPI key provided")
            return []
        
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
            
            logger.info(f"Fetched {len(articles)} new articles")
            return articles
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
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
    from config import Config
    
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
