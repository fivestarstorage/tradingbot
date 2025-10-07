"""
AI Sentiment Tracker
Tracks all AI analysis results for dashboard display
"""
import json
import os
from datetime import datetime
from collections import defaultdict

class AISentimentTracker:
    """Tracks AI analysis and recommendations for dashboard"""
    
    def __init__(self, storage_file='ai_sentiment_data.json'):
        self.storage_file = storage_file
        self.data = {
            'recent_analyses': [],
            'sentiment_stats': {'Positive': 0, 'Negative': 0, 'Neutral': 0},
            'recommendations': [],
            'trade_decisions': [],
            'last_update': None
        }
        self.max_analyses = 100  # Keep last 100 analyses
        self.max_recommendations = 20
        self.max_decisions = 50
        self._load_data()
    
    def _load_data(self):
        """Load existing data from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.data = json.load(f)
        except Exception as e:
            print(f"Error loading sentiment data: {e}")
    
    def _save_data(self):
        """Save data to file"""
        try:
            self.data['last_update'] = datetime.now().isoformat()
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving sentiment data: {e}")
    
    def add_analysis(self, article_title, analysis, mentioned_symbols):
        """
        Add an AI analysis result
        
        Args:
            article_title: News article title
            analysis: AI analysis dict (signal, confidence, sentiment, etc.)
            mentioned_symbols: List of symbols mentioned
        """
        analysis_entry = {
            'timestamp': datetime.now().isoformat(),
            'article': article_title,
            'signal': analysis.get('signal', 'HOLD'),
            'confidence': analysis.get('confidence', 0),
            'sentiment': analysis.get('sentiment', 'Neutral'),
            'impact': analysis.get('impact', 'low'),
            'urgency': analysis.get('urgency', 'long-term'),
            'reasoning': analysis.get('reasoning', ''),
            'symbols': mentioned_symbols[:5],  # Top 5 symbols
        }
        
        # Add to recent analyses
        self.data['recent_analyses'].insert(0, analysis_entry)
        self.data['recent_analyses'] = self.data['recent_analyses'][:self.max_analyses]
        
        # Update sentiment stats
        sentiment = analysis.get('sentiment', 'Neutral')
        if sentiment in self.data['sentiment_stats']:
            self.data['sentiment_stats'][sentiment] += 1
        
        # Add recommendations if strong signal
        if analysis.get('signal') in ['BUY', 'SELL'] and analysis.get('confidence', 0) >= 75:
            recommendation = {
                'timestamp': datetime.now().isoformat(),
                'signal': analysis['signal'],
                'symbols': mentioned_symbols[:3],
                'confidence': analysis['confidence'],
                'reasoning': analysis.get('reasoning', '')[:200],  # First 200 chars
                'sentiment': sentiment
            }
            self.data['recommendations'].insert(0, recommendation)
            self.data['recommendations'] = self.data['recommendations'][:self.max_recommendations]
        
        self._save_data()
    
    def add_trade_decision(self, decision_type, symbol, price, reasoning, result='pending'):
        """
        Add a trade decision (buy/sell)
        
        Args:
            decision_type: 'BUY' or 'SELL'
            symbol: Trading symbol
            price: Entry/exit price
            reasoning: Why this decision was made
            result: 'pending', 'profit', 'loss'
        """
        decision = {
            'timestamp': datetime.now().isoformat(),
            'type': decision_type,
            'symbol': symbol,
            'price': price,
            'reasoning': reasoning[:200],
            'result': result
        }
        
        self.data['trade_decisions'].insert(0, decision)
        self.data['trade_decisions'] = self.data['trade_decisions'][:self.max_decisions]
        self._save_data()
    
    def update_trade_result(self, symbol, result, profit_pct=0):
        """Update the result of the most recent trade for a symbol"""
        for decision in self.data['trade_decisions']:
            if decision['symbol'] == symbol and decision['result'] == 'pending':
                decision['result'] = result
                decision['profit_pct'] = profit_pct
                decision['closed_at'] = datetime.now().isoformat()
                self._save_data()
                break
    
    def get_sentiment_summary(self):
        """Get sentiment statistics"""
        total = sum(self.data['sentiment_stats'].values())
        if total == 0:
            return {
                'Positive': 0,
                'Negative': 0,
                'Neutral': 0,
                'total': 0
            }
        
        return {
            'Positive': self.data['sentiment_stats']['Positive'],
            'Negative': self.data['sentiment_stats']['Negative'],
            'Neutral': self.data['sentiment_stats']['Neutral'],
            'Positive_pct': round(self.data['sentiment_stats']['Positive'] / total * 100, 1),
            'Negative_pct': round(self.data['sentiment_stats']['Negative'] / total * 100, 1),
            'Neutral_pct': round(self.data['sentiment_stats']['Neutral'] / total * 100, 1),
            'total': total
        }
    
    def get_recent_analyses(self, limit=20):
        """Get recent AI analyses"""
        return self.data['recent_analyses'][:limit]
    
    def get_recommendations(self, limit=10):
        """Get top recommendations"""
        return self.data['recommendations'][:limit]
    
    def get_trade_decisions(self, limit=20):
        """Get recent trade decisions"""
        return self.data['trade_decisions'][:limit]
    
    def get_dashboard_data(self):
        """Get all data for dashboard display"""
        return {
            'sentiment_summary': self.get_sentiment_summary(),
            'recent_analyses': self.get_recent_analyses(20),
            'recommendations': self.get_recommendations(10),
            'trade_decisions': self.get_trade_decisions(20),
            'last_update': self.data.get('last_update')
        }
    
    def reset_stats(self):
        """Reset sentiment statistics (for new day)"""
        self.data['sentiment_stats'] = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
        self._save_data()
