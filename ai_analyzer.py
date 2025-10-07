"""
AI News Analyzer - Uses OpenAI to Analyze News Sentiment
Generates trading signals based on news analysis
"""
import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class AINewsAnalyzer:
    """Analyzes news using OpenAI GPT-4 to generate trading signals"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided")
    
    def analyze_news(self, article, symbol=None):
        """
        Analyze news article and generate trading signal
        
        Args:
            article: Dict with 'title', 'description', 'content'
            symbol: Optional specific symbol to analyze for
            
        Returns:
            Dict with analysis results:
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0-100,
                'sentiment': 'bullish' | 'bearish' | 'neutral',
                'impact': 'high' | 'medium' | 'low',
                'reasoning': str,
                'symbols': [list of affected symbols],
                'urgency': 'immediate' | 'short-term' | 'long-term'
            }
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return self._default_analysis()
        
        try:
            # Prepare text for analysis
            text = f"""
Title: {article.get('title', '')}
Description: {article.get('description', '')}
Content: {article.get('content', '')[:500]}
"""
            
            # Create prompt
            prompt = f"""Analyze this cryptocurrency news article and provide a trading recommendation.

{text}

Provide your analysis in the following JSON format:
{{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0-100 (how confident you are),
    "sentiment": "bullish" or "bearish" or "neutral",
    "impact": "high" or "medium" or "low",
    "reasoning": "brief explanation of your analysis",
    "symbols": ["BTCUSDT", "ETHUSDT", etc. - ONLY coins directly mentioned or affected],
    "urgency": "immediate" or "short-term" or "long-term",
    "key_points": ["key", "point", "1", "key", "point", "2"],
    "primary_coin": "The MAIN coin this news affects (e.g. BTCUSDT)"
}}

Consider:
- Is this news significant enough to move markets?
- What's the sentiment (positive/negative/neutral)?
- Which cryptocurrencies are affected?
- Is this breaking news or old information?
- What's the credibility of the source?

Only recommend BUY/SELL if you're >70% confident. Otherwise say HOLD."""

            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper model, still very good
                messages=[
                    {"role": "system", "content": "You are an expert cryptocurrency trader and news analyst. You analyze ALL types of news (tech, business, finance) and determine if they impact cryptocurrency markets. You provide actionable trading signals only for crypto-relevant news. If news is not crypto-related, return HOLD with low confidence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=500
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON
            try:
                # Find JSON in response
                start = analysis_text.find('{')
                end = analysis_text.rfind('}') + 1
                json_str = analysis_text[start:end]
                
                analysis = json.loads(json_str)
                
                # Validate and normalize
                analysis['signal'] = analysis.get('signal', 'HOLD').upper()
                analysis['confidence'] = min(100, max(0, int(analysis.get('confidence', 50))))
                analysis['sentiment'] = analysis.get('sentiment', 'neutral').lower()
                analysis['impact'] = analysis.get('impact', 'low').lower()
                analysis['urgency'] = analysis.get('urgency', 'long-term').lower()
                analysis['symbols'] = analysis.get('symbols', [])
                analysis['reasoning'] = analysis.get('reasoning', 'No reasoning provided')
                analysis['key_points'] = analysis.get('key_points', [])
                
                logger.info(f"Analysis: {analysis['signal']} ({analysis['confidence']}%) - {analysis['sentiment']}")
                
                return analysis
            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from GPT response: {e}")
                logger.debug(f"Response was: {analysis_text}")
                return self._default_analysis()
        
        except Exception as e:
            logger.error(f"Error analyzing news with AI: {e}")
            return self._default_analysis()
    
    def _default_analysis(self):
        """Return default safe analysis when AI fails"""
        return {
            'signal': 'HOLD',
            'confidence': 0,
            'sentiment': 'neutral',
            'impact': 'low',
            'reasoning': 'AI analysis unavailable',
            'symbols': [],
            'urgency': 'long-term',
            'key_points': []
        }
    
    def batch_analyze_comprehensive(self, articles, max_articles=5):
        """
        Analyze ALL articles in ONE OpenAI call for comprehensive trading decision
        Much more efficient and provides better context to AI
        
        Args:
            articles: List of article dicts with title, description, content, url
            max_articles: Max articles to include (default 5)
            
        Returns:
            Dict with comprehensive trading decision
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return self._default_analysis()
        
        if not articles:
            return self._default_analysis()
        
        # Limit articles
        articles_to_analyze = articles[:max_articles]
        
        # Build comprehensive prompt with ALL articles
        articles_text = ""
        for i, article in enumerate(articles_to_analyze, 1):
            articles_text += f"""
---ARTICLE {i}---
Title: {article.get('title', '')}
Source: {article.get('source', 'Unknown')}
Date: {article.get('date', '')}
Content: {article.get('text', article.get('description', ''))}
URL: {article.get('news_url', article.get('url', ''))}
Sentiment (pre-tagged): {article.get('sentiment', 'Unknown')}
Mentioned Tickers: {', '.join(article.get('tickers', []))}

"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert cryptocurrency trader analyzing multiple news articles to make ONE trading decision.

Analyze ALL articles together, considering:
1. Overall market sentiment across all news
2. Which coins are most mentioned
3. Correlation between articles
4. Urgency and impact of news
5. Conflicting signals

Return JSON with:
{
    "signal": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "recommended_coin": "BTCUSDT" | "ETHUSDT" | "XRPUSDT",
    "sentiment": "bullish" | "bearish" | "neutral",
    "impact": "high" | "medium" | "low",
    "urgency": "immediate" | "short-term" | "long-term",
    "reasoning": "Brief explanation of why this decision based on all articles",
    "key_articles": [1, 2] (indices of most important articles),
    "risk_level": "high" | "medium" | "low"
}

IMPORTANT:
- Consider ALL articles together, not individually
- Pick the SINGLE best trading opportunity
- If news is mixed or unclear, return HOLD
- Focus on BTC, ETH, XRP only"""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze these {len(articles_to_analyze)} crypto news articles and provide ONE trading decision:

{articles_text}

What should I do? Provide comprehensive analysis in JSON format."""
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(result_text)
            
            # Ensure required fields
            return {
                'signal': analysis.get('signal', 'HOLD'),
                'confidence': analysis.get('confidence', 50),
                'recommended_symbol': analysis.get('recommended_coin', 'BTCUSDT'),
                'sentiment': analysis.get('sentiment', 'neutral'),
                'impact': analysis.get('impact', 'medium'),
                'urgency': analysis.get('urgency', 'long-term'),
                'reasoning': analysis.get('reasoning', 'Comprehensive analysis complete'),
                'risk_level': analysis.get('risk_level', 'medium'),
                'key_articles': analysis.get('key_articles', []),
                'articles_analyzed': len(articles_to_analyze),
                'symbols': [analysis.get('recommended_coin', 'BTCUSDT')]
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response was: {result_text}")
            return self._default_analysis()
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return self._default_analysis()
    
    def batch_analyze(self, articles, max_articles=10):
        """
        OLD METHOD: Analyze multiple articles individually
        DEPRECATED: Use batch_analyze_comprehensive instead for efficiency
        """
        if not articles:
            return self._default_analysis()
        
        # Limit number of articles
        articles_to_analyze = articles[:max_articles]
        
        results = []
        for article in articles_to_analyze:
            analysis = self.analyze_news(article)
            results.append(analysis)
        
        # Aggregate results
        buy_count = sum(1 for r in results if r['signal'] == 'BUY')
        sell_count = sum(1 for r in results if r['signal'] == 'SELL')
        
        avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
        
        # Determine overall signal
        if buy_count > sell_count and avg_confidence > 60:
            signal = 'BUY'
        elif sell_count > buy_count and avg_confidence > 60:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        # Collect all mentioned symbols
        all_symbols = set()
        for r in results:
            all_symbols.update(r['symbols'])
        
        return {
            'signal': signal,
            'confidence': avg_confidence,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': len(results) - buy_count - sell_count,
            'symbols': list(all_symbols),
            'articles_analyzed': len(results),
            'individual_results': results
        }


def test_analyzer():
    """Test the AI analyzer"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 70)
    print("🤖 TESTING AI NEWS ANALYZER")
    print("=" * 70)
    print()
    
    # Test article
    test_article = {
        'title': 'Bitcoin ETF Approved by SEC - Major Milestone for Crypto',
        'description': 'The SEC has approved the first spot Bitcoin ETF, marking a historic moment for cryptocurrency adoption.',
        'content': 'In a groundbreaking decision, the Securities and Exchange Commission has approved multiple spot Bitcoin ETFs...'
    }
    
    analyzer = AINewsAnalyzer()
    
    if not analyzer.client:
        print("❌ No OpenAI API key found")
        print("Set OPENAI_API_KEY environment variable")
        return
    
    print("Analyzing test article...")
    print(f"Title: {test_article['title']}")
    print()
    
    analysis = analyzer.analyze_news(test_article)
    
    print("=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    print(f"Signal: {analysis['signal']}")
    print(f"Confidence: {analysis['confidence']}%")
    print(f"Sentiment: {analysis['sentiment']}")
    print(f"Impact: {analysis['impact']}")
    print(f"Urgency: {analysis['urgency']}")
    print(f"Symbols: {', '.join(analysis['symbols']) if analysis['symbols'] else 'None'}")
    print(f"\nReasoning: {analysis['reasoning']}")
    
    if analysis['key_points']:
        print(f"\nKey Points:")
        for point in analysis['key_points']:
            print(f"  • {point}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_analyzer()
