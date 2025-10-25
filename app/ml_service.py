"""
Machine Learning Service for Per-Coin Prediction Models
========================================================

Trains dedicated ML models for individual coins using historical data.
Models can predict:
- Price direction (up/down)
- Optimal buy/sell timing  
- Risk assessment
"""
import os
import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class CoinMLService:
    """Machine learning service for individual coin prediction"""
    
    def __init__(self, binance_client, models_dir='/tmp/ml_models'):
        self.binance = binance_client
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
    
    def fetch_historical_data(self, symbol: str, days: int = 365) -> List[Dict]:
        """
        Fetch historical candle data from Binance
        
        Args:
            symbol: Trading pair (e.g. 'BTCUSDT')
            days: Number of days of history to fetch
        
        Returns:
            List of candles with OHLCV data
        """
        print(f"[ML] Fetching {days} days of {symbol} data...")
        
        import time
        
        candles = []
        interval = '1h'  # 1-hour candles
        limit = 1000  # Max per request
        
        # Calculate how many requests needed
        candles_needed = days * 24  # 24 candles per day
        requests_needed = (candles_needed // limit) + 1
        
        print(f"[ML] Need {requests_needed} API requests to fetch {days} days")
        
        end_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(requests_needed):
            try:
                raw_candles = self.binance.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                    endTime=end_time
                )
                
                if not raw_candles:
                    break
                
                # Format candles
                for candle in raw_candles:
                    candles.append({
                        'timestamp': candle[0],
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
                
                # Move end_time back
                end_time = raw_candles[0][0] - 1
                
                # Progress indicator
                if (i + 1) % 5 == 0:
                    print(f"[ML] Progress: {i + 1}/{requests_needed} requests ({len(candles)} candles)")
                
                # Small delay to respect rate limits (1200 requests/minute = ~50ms per request)
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[ML] Error fetching candles: {e}")
                break
        
        candles.reverse()  # Oldest first
        print(f"[ML] Fetched {len(candles)} candles ({len(candles)/24:.1f} days)")
        
        return candles
    
    def engineer_features(self, candles: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create features and labels from candle data
        
        Features:
        - Price changes (1h, 4h, 24h)
        - Volume ratios
        - RSI (14 period)
        - MACD
        - Bollinger bands
        - High/Low ratios
        
        Labels:
        - 1 if price increased >2% in next 24h
        - 0 otherwise
        """
        print(f"[ML] Engineering features from {len(candles)} candles...")
        
        features_list = []
        labels_list = []
        
        for i in range(50, len(candles) - 24):  # Need 50 for indicators, 24 for future
            # Extract recent candles
            recent = candles[i-50:i+1]
            closes = np.array([c['close'] for c in recent])
            volumes = np.array([c['volume'] for c in recent])
            highs = np.array([c['high'] for c in recent])
            lows = np.array([c['low'] for c in recent])
            
            # Current price
            current_price = closes[-1]
            
            # Price changes
            price_change_1h = (closes[-1] - closes[-2]) / closes[-2] * 100
            price_change_4h = (closes[-1] - closes[-5]) / closes[-5] * 100
            price_change_24h = (closes[-1] - closes[-25]) / closes[-25] * 100
            
            # Volume ratio
            vol_ratio = volumes[-1] / np.mean(volumes[-24:]) if np.mean(volumes[-24:]) > 0 else 1
            
            # RSI
            rsi = self._calculate_rsi(closes, period=14)
            
            # MACD
            macd, signal = self._calculate_macd(closes)
            
            # Bollinger Bands
            bb_middle = np.mean(closes[-20:])
            bb_std = np.std(closes[-20:])
            bb_upper = bb_middle + (2 * bb_std)
            bb_lower = bb_middle - (2 * bb_std)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
            
            # High/Low ratios
            hl_ratio = (highs[-1] - lows[-1]) / lows[-1] * 100 if lows[-1] > 0 else 0
            
            # Trend (EMA comparison)
            ema_20 = np.mean(closes[-20:])
            ema_50 = np.mean(closes[-50:])
            ema_trend = 1 if ema_20 > ema_50 else 0
            
            # Create feature vector
            features = [
                price_change_1h,
                price_change_4h,
                price_change_24h,
                vol_ratio,
                rsi,
                macd - signal,  # MACD histogram
                bb_position,
                hl_ratio,
                ema_trend
            ]
            
            # Label: Did price increase >2% in next 24 hours?
            future_price = candles[i + 24]['close']
            price_increase_pct = (future_price - current_price) / current_price * 100
            label = 1 if price_increase_pct > 2 else 0
            
            features_list.append(features)
            labels_list.append(label)
        
        X = np.array(features_list)
        y = np.array(labels_list)
        
        print(f"[ML] Created {len(X)} samples")
        print(f"[ML] Positive samples (price increased): {sum(y)}/{len(y)} ({sum(y)/len(y)*100:.1f}%)")
        
        return X, y
    
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator"""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_macd(self, closes: np.ndarray) -> Tuple[float, float]:
        """Calculate MACD indicator"""
        ema_12 = np.mean(closes[-12:])
        ema_26 = np.mean(closes[-26:])
        macd = ema_12 - ema_26
        signal = macd  # Simplified
        return float(macd), float(signal)
    
    def train_model(self, symbol: str, days: int = 365) -> Dict:
        """
        Train a Random Forest model for a specific coin
        
        Returns:
            Training metrics and model info
        """
        print(f"\n[ML] 🤖 Training model for {symbol}...")
        
        # Fetch historical data
        candles = self.fetch_historical_data(symbol, days=days)
        
        if len(candles) < 100:
            return {
                'success': False,
                'error': f'Not enough data (got {len(candles)} candles, need 100+)'
            }
        
        # Engineer features
        X, y = self.engineer_features(candles)
        
        if len(X) < 50:
            return {
                'success': False,
                'error': f'Not enough samples for training (got {len(X)}, need 50+)'
            }
        
        # Split train/test (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Random Forest
        print(f"[ML] Training Random Forest with {len(X_train)} samples...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = model.score(X_train_scaled, y_train)
        test_score = model.score(X_test_scaled, y_test)
        
        # Feature importance
        feature_names = [
            'price_change_1h', 'price_change_4h', 'price_change_24h',
            'vol_ratio', 'rsi', 'macd_hist', 'bb_position', 'hl_ratio', 'ema_trend'
        ]
        importance = dict(zip(feature_names, model.feature_importances_))
        
        print(f"[ML] Train accuracy: {train_score:.2%}")
        print(f"[ML] Test accuracy: {test_score:.2%}")
        
        # Save model
        model_path = os.path.join(self.models_dir, f'{symbol}_model.pkl')
        scaler_path = os.path.join(self.models_dir, f'{symbol}_scaler.pkl')
        info_path = os.path.join(self.models_dir, f'{symbol}_info.json')
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        info = {
            'symbol': symbol,
            'trained_at': datetime.now().isoformat(),
            'samples': len(X),
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'feature_importance': {k: float(v) for k, v in importance.items()},
            'positive_rate': float(sum(y) / len(y))
        }
        
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        print(f"[ML] ✅ Model saved to {model_path}")
        
        return {
            'success': True,
            **info
        }
    
    def predict(self, symbol: str) -> Dict:
        """
        Make prediction for a symbol using its trained model
        
        Returns:
            {
                'prediction': 'BUY' | 'HOLD',
                'confidence': float,
                'reasoning': str
            }
        """
        model_path = os.path.join(self.models_dir, f'{symbol}_model.pkl')
        scaler_path = os.path.join(self.models_dir, f'{symbol}_scaler.pkl')
        info_path = os.path.join(self.models_dir, f'{symbol}_info.json')
        
        # Check if model exists
        if not os.path.exists(model_path):
            return {
                'error': f'No trained model found for {symbol}. Train one first!'
            }
        
        # Load model
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        
        with open(info_path, 'r') as f:
            info = json.load(f)
        
        # Fetch recent data
        candles = self.fetch_historical_data(symbol, days=3)
        
        if len(candles) < 50:
            return {'error': 'Not enough recent data for prediction'}
        
        # Engineer features for current state
        recent = candles[-51:]
        closes = np.array([c['close'] for c in recent])
        volumes = np.array([c['volume'] for c in recent])
        highs = np.array([c['high'] for c in recent])
        lows = np.array([c['low'] for c in recent])
        
        current_price = closes[-1]
        
        # Calculate features (same as training)
        price_change_1h = (closes[-1] - closes[-2]) / closes[-2] * 100
        price_change_4h = (closes[-1] - closes[-5]) / closes[-5] * 100
        price_change_24h = (closes[-1] - closes[-25]) / closes[-25] * 100
        vol_ratio = volumes[-1] / np.mean(volumes[-24:]) if np.mean(volumes[-24:]) > 0 else 1
        rsi = self._calculate_rsi(closes, period=14)
        macd, signal = self._calculate_macd(closes)
        
        bb_middle = np.mean(closes[-20:])
        bb_std = np.std(closes[-20:])
        bb_upper = bb_middle + (2 * bb_std)
        bb_lower = bb_middle - (2 * bb_std)
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
        
        hl_ratio = (highs[-1] - lows[-1]) / lows[-1] * 100 if lows[-1] > 0 else 0
        
        ema_20 = np.mean(closes[-20:])
        ema_50 = np.mean(closes[-50:])
        ema_trend = 1 if ema_20 > ema_50 else 0
        
        features = np.array([[
            price_change_1h,
            price_change_4h,
            price_change_24h,
            vol_ratio,
            rsi,
            macd - signal,
            bb_position,
            hl_ratio,
            ema_trend
        ]])
        
        # Scale and predict
        features_scaled = scaler.transform(features)
        prediction_proba = model.predict_proba(features_scaled)[0]
        prediction = model.predict(features_scaled)[0]
        
        confidence = float(prediction_proba[1])  # Probability of price increase
        
        # Generate reasoning
        if prediction == 1 and confidence > 0.65:
            action = 'BUY'
            reasoning = f"Model predicts {confidence:.0%} chance of >2% increase in next 24h"
        elif confidence > 0.5:
            action = 'HOLD'
            reasoning = f"Model shows {confidence:.0%} confidence but below buy threshold (65%)"
        else:
            action = 'HOLD'
            reasoning = f"Model predicts {confidence:.0%} chance of increase (low confidence)"
        
        return {
            'symbol': symbol,
            'prediction': action,
            'confidence': confidence,
            'reasoning': reasoning,
            'model_info': {
                'trained_at': info['trained_at'],
                'test_accuracy': info['test_accuracy']
            },
            'current_indicators': {
                'rsi': float(rsi),
                'price_change_24h': float(price_change_24h),
                'volume_ratio': float(vol_ratio)
            }
        }

