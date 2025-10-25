# CoinDesk News Scraping

## Overview

The trading bot now fetches crypto news from **two sources**:

1. **Crypto News API** (existing) - Provides structured news data with sentiment analysis and ticker tags
2. **CoinDesk** (new) - Web scraping of the latest crypto news from CoinDesk.com

## How It Works

### News Sources

The news service (`app/news_service.py`) automatically fetches from both sources when you trigger a news update:

- **Crypto News API**: `https://cryptonews-api.com/api/v1/category?section=alltickers&items=100&page=1`
- **CoinDesk**: `https://www.coindesk.com/latest-crypto-news`

### What Gets Scraped from CoinDesk

For each article on the CoinDesk latest news page, the scraper extracts:

- **Title**: Article headline
- **URL**: Full article link
- **Description**: Article summary/preview text
- **Image**: Article featured image
- **Date**: Publication time (e.g., "5 minutes ago", "2 hours ago")
- **Source**: "CoinDesk"

### How Articles Are Stored

All articles (from both sources) are stored in the SQLite database with:

- Automatic deduplication by URL
- UTC date normalization for consistent timezone handling
- Full article metadata (title, text, image, source, tickers, sentiment)

### Features

✅ **Automatic scraping** - Runs every time news is fetched (every 5 minutes by the scheduler)
✅ **Smart deduplication** - Prevents duplicate articles based on URL
✅ **Error handling** - Gracefully handles scraping failures without breaking the news service
✅ **Image URL extraction** - Properly handles Next.js image optimization URLs
✅ **No API key required** - CoinDesk scraping is completely free

## Technical Details

### Dependencies

The scraper requires:
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - Fast XML/HTML parser

These are included in `requirements.txt` and automatically installed.

### Scraping Strategy

The scraper targets CoinDesk's HTML structure:

```python
# Find article links
article_links = soup.find_all('a', class_='content-card-title')

# For each article:
# - Extract title from <h2> within the link
# - Find parent container to get description
# - Extract time from metadata span
# - Extract image from sibling img element
```

### Date Handling

**Note**: CoinDesk provides relative times like "5 minutes ago" rather than absolute timestamps. These are stored as-is in the database. The `parse_date()` function attempts to convert them but may fallback to storing the relative time string.

## Testing

To test the CoinDesk scraper independently:

```python
from app.news_service import scrape_coindesk_news

articles = scrape_coindesk_news()
print(f"Scraped {len(articles)} articles")

for article in articles[:3]:
    print(f"Title: {article['title']}")
    print(f"URL: {article['news_url']}")
    print(f"Date: {article['date']}")
    print()
```

## Troubleshooting

### No Articles Scraped

If CoinDesk scraping returns 0 articles:

1. **Page structure changed** - CoinDesk may have updated their HTML structure
2. **Network issues** - Check your internet connection
3. **Rate limiting** - CoinDesk might be blocking excessive requests

### Relative Dates

CoinDesk provides times like "5 minutes ago" instead of absolute timestamps. The frontend will display these as-is. For accurate timestamps, the Crypto News API articles include proper ISO date strings.

## Benefits

🎯 **More news sources** = Better market coverage  
📰 **CoinDesk quality** = Trusted, professional crypto journalism  
🆓 **Free** = No additional API costs  
⚡ **Real-time** = Latest news within minutes

## Limitations

- **No sentiment analysis** - CoinDesk articles don't include sentiment scores
- **No ticker tags** - Articles aren't automatically tagged with relevant crypto tickers
- **Relative timestamps** - Uses "X minutes ago" format instead of absolute dates
- **Web scraping risks** - May break if CoinDesk changes their page structure

## Future Improvements

Potential enhancements:

- [ ] Convert relative dates to absolute timestamps
- [ ] Extract ticker symbols from article titles/content using NLP
- [ ] Add sentiment analysis for CoinDesk articles using OpenAI
- [ ] Scrape additional crypto news sites (CoinTelegraph, Decrypt, etc.)
- [ ] Implement browser-based scraping for JavaScript-rendered content

