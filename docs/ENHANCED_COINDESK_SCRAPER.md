# Enhanced CoinDesk Scraper with AI Analysis

## 🎯 Overview

The CoinDesk scraper has been upgraded to provide **full article analysis** using OpenAI:

### What's New

✅ **Full Article Content** - Fetches and reads the complete article  
✅ **AI Sentiment Analysis** - Uses GPT-4o-mini to determine sentiment  
✅ **Automatic Ticker Extraction** - AI identifies mentioned cryptocurrencies  
✅ **Accurate Published Time** - Extracts actual publication date from article  
✅ **Open Graph Images** - Gets proper article images from metadata  

## 🔄 How It Works

### Step 1: Fetch Article List
Scrapes the CoinDesk latest news page for article URLs

### Step 2: Process Each Article (Limited to 10)
For each article:
1. **Fetch Full Page** - Downloads the complete article
2. **Extract Content** - Parses article text from `<article>` tags
3. **Extract Date** - Finds `<time datetime>` tag for published time
4. **Extract Image** - Gets image from Open Graph meta tags
5. **AI Analysis** - Sends to OpenAI for sentiment and ticker extraction

### Step 3: Store with Complete Data
Articles are stored with:
- **Proper datetime** (not "5 minutes ago")
- **Sentiment** ("Positive", "Negative", or "Neutral")
- **Tickers** (e.g., ["BTC", "ETH", "XRP"])
- **Full content** (first 500 chars as description)

## 📊 Example Output

```python
{
    'news_url': 'https://www.coindesk.com/markets/2025/10/25/xrp-leads-gains...',
    'title': 'XRP Leads Gains on Ripple Moves, Bitcoin Holds $111K...',
    'text': 'October has been defined by forced selling and false starts...',
    'image_url': 'https://cdn.sanity.io/images/...',
    'source_name': 'CoinDesk',
    'date': datetime(2025, 10, 25, 6, 30, 0),  # Proper datetime object in UTC
    'type': 'Article',
    'sentiment': 'Positive',  # AI-determined
    'tickers': ['XRP', 'BTC']  # AI-extracted
}
```

## 🤖 AI Analysis Details

### Sentiment Analysis
The AI reads the article and determines:
- **Positive** - Bullish news, price increases, adoption, partnerships
- **Negative** - Bearish news, price drops, regulations, hacks
- **Neutral** - Informational, balanced reporting

### Ticker Extraction
The AI identifies cryptocurrency symbols mentioned in the article:
- Extracts common formats: BTC, BTCUSDT, Bitcoin
- Normalizes to standard symbols: Bitcoin → BTC
- Returns as list: ["BTC", "ETH", "XRP"]

### Model Used
- **GPT-4o-mini** - Fast and cost-effective
- **Temperature: 0.3** - Balanced consistency
- **JSON mode** - Structured output

## 💰 Cost Considerations

### OpenAI API Usage
Each CoinDesk article requires:
- 1 API call to GPT-4o-mini
- ~500-1000 tokens per analysis
- Cost: ~$0.0001 per article

### Limits
- **10 articles per run** (to control costs)
- Runs every **5 minutes** (automatic scheduler)
- ~1,440 articles/day max
- Estimated cost: **$0.14/day** or **$4.20/month**

## 🚀 Usage

### Automatic (Recommended)
The scraper runs automatically every 5 minutes via the scheduler:
```python
# No action needed - it just works!
```

### Manual Testing
Test the enhanced scraper:
```bash
cd /Users/rileymartin/tradingbot
python3 test_enhanced_coindesk.py
```

### Check Backend Logs
Monitor scraping progress:
```
Found 10 CoinDesk articles to process...
  [1/10] Processing: XRP Leads Gains on Ripple Moves...
    ✓ Sentiment: Positive, Tickers: XRP, BTC
  [2/10] Processing: Dogecoin Hits $0.20 as Breakout...
    ✓ Sentiment: Positive, Tickers: DOGE
✓ Scraped 10 CoinDesk articles with AI analysis
```

## ⚙️ Configuration

### Required Environment Variables
```bash
# In /Users/rileymartin/tradingbot/.env
OPENAI_API_KEY=sk-proj-...
```

### Optional Settings
You can modify limits in `news_service.py`:
```python
# Line 158: Change number of articles to process
article_links = article_links[:10]  # Change 10 to desired number
```

## 🎨 Frontend Display

Articles now show:
- ✅ **Real timestamps** (not "5 minutes ago")
- ✅ **Sentiment badges** (Positive/Negative/Neutral)
- ✅ **Ticker tags** (BTC, ETH, etc.)
- ✅ **Full article content** (first 500 chars)

## 🔧 Technical Details

### Article Content Extraction
```python
def extract_article_content(article_url: str, headers: dict):
    """
    Fetches and extracts:
    - Article text from <article> or <p> tags
    - Published date from <time datetime> tag
    - Image from Open Graph meta tags
    """
```

### AI Analysis
```python
def analyze_article_with_ai(title: str, content: str):
    """
    Uses OpenAI to determine:
    - Sentiment: Positive/Negative/Neutral
    - Tickers: List of crypto symbols
    """
```

### Main Scraper
```python
def scrape_coindesk_news():
    """
    1. Gets article URLs from main page
    2. Processes first 10 articles
    3. Extracts content and metadata
    4. Analyzes with AI
    5. Returns complete article data
    """
```

## 📈 Benefits

### Before Enhancement
❌ Relative timestamps ("5 minutes ago")  
❌ No sentiment data  
❌ No ticker tags  
❌ Only preview text  
❌ Limited metadata  

### After Enhancement
✅ Absolute timestamps (UTC datetime)  
✅ AI-determined sentiment  
✅ AI-extracted tickers  
✅ Full article content  
✅ Complete metadata  
✅ Better trading signals  

## 🐛 Troubleshooting

### No Articles Scraped
**Problem**: `Scraped 0 CoinDesk articles`

**Solutions**:
1. Check OPENAI_API_KEY is set
2. Verify internet connection
3. Check if CoinDesk changed their HTML structure

### AI Analysis Fails
**Problem**: `Error analyzing article with AI`

**Solutions**:
1. Verify OPENAI_API_KEY is valid
2. Check OpenAI API quota/billing
3. Review backend logs for error details

### Content Extraction Fails
**Problem**: `Could not extract content, skipping`

**Solutions**:
1. CoinDesk may have changed article structure
2. Check individual article URL manually
3. May need to update selectors in `extract_article_content()`

### Rate Limiting
**Problem**: Too many requests to CoinDesk or OpenAI

**Solutions**:
1. Reduce number of articles: Change `[:10]` to `[:5]`
2. Increase delay between requests
3. Check OpenAI rate limits

## 🔒 Privacy & Ethics

### Respectful Scraping
- ✅ Uses proper User-Agent
- ✅ Respects server load (limited articles)
- ✅ Includes delays between requests
- ✅ Only scrapes public content

### Data Usage
- Articles are for **personal trading analysis** only
- Not redistributed or republished
- Complies with fair use for automated trading

## 📚 Related Documentation

- **COINDESK_NEWS.md** - Original scraper documentation
- **COINDESK_QUICKSTART.md** - Setup guide
- **COINDESK_IMPLEMENTATION_SUMMARY.md** - Technical details

## 🎯 Next Steps

### Potential Enhancements
- [ ] Add more news sources (CoinTelegraph, Decrypt)
- [ ] Implement caching to avoid re-analyzing same articles
- [ ] Add confidence scores to sentiment
- [ ] Extract price targets and predictions
- [ ] Summarize articles with AI
- [ ] Category classification (DeFi, NFTs, etc.)

---

**Status**: ✅ **ENHANCED & READY**  
**AI Analysis**: ✅ **ENABLED**  
**Article Limit**: 10 per run  
**Cost**: ~$0.14/day  
**Quality**: ⭐⭐⭐⭐⭐

