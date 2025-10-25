#!/usr/bin/env python3
"""
Test ML Training with Long Timeframe (2 years)
"""
import os
from dotenv import load_dotenv
from core.binance_client import BinanceClient
from app.ml_service import CoinMLService

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print("=" * 80)
print("🤖 ML Training Test - BTCUSDT (2 YEARS)")
print("=" * 80)

# Initialize clients
binance = BinanceClient(api_key, api_secret, testnet=False)
ml_service = CoinMLService(binance)

# Train model on 2 years of data
print("\n🎯 Training model on BTCUSDT with 730 days (2 years)...")
print("This will take ~2 minutes\n")

result = ml_service.train_model('BTCUSDT', days=730)

print("\n" + "=" * 80)
print("📊 TRAINING RESULTS")
print("=" * 80)

if result.get('success'):
    print(f"✅ Training successful!")
    print(f"\n📈 Model Stats:")
    print(f"  - Symbol: {result['symbol']}")
    print(f"  - Training samples: {result['samples']:,}")
    print(f"  - Train accuracy: {result['train_accuracy']:.2%}")
    print(f"  - Test accuracy: {result['test_accuracy']:.2%}")
    print(f"  - Positive rate: {result['positive_rate']:.2%}")
    
    print(f"\n🎯 Top 5 Most Important Features:")
    sorted_features = sorted(result['feature_importance'].items(), key=lambda x: x[1], reverse=True)
    for feature, importance in sorted_features[:5]:
        bar = "█" * int(importance * 50)
        print(f"  {feature:20s} {importance:5.1%} {bar}")
    
    # Test prediction
    print("\n" + "=" * 80)
    print("🔮 TESTING PREDICTION")
    print("=" * 80)
    
    prediction = ml_service.predict('BTCUSDT')
    
    if prediction.get('error'):
        print(f"❌ {prediction['error']}")
    else:
        print(f"📊 Prediction: {prediction['prediction']}")
        print(f"💯 Confidence: {prediction['confidence']:.1%}")
        print(f"💭 {prediction['reasoning']}")
else:
    print(f"❌ Training failed: {result.get('error')}")

print("\n" + "=" * 80)

