#!/usr/bin/env python3
"""
Test ML Training Locally
"""
import os
from dotenv import load_dotenv
from core.binance_client import BinanceClient
from app.ml_service import CoinMLService

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print("=" * 80)
print("🤖 ML Training Test - VIRTUALUSDT")
print("=" * 80)

# Initialize clients
binance = BinanceClient(api_key, api_secret, testnet=False)
ml_service = CoinMLService(binance)

# Train model
print("\n🎯 Training model on VIRTUALUSDT...")
print("This will take ~30 seconds\n")

result = ml_service.train_model('VIRTUALUSDT', days=365)

print("\n" + "=" * 80)
print("📊 TRAINING RESULTS")
print("=" * 80)

if result.get('success'):
    print(f"✅ Training successful!")
    print(f"\n📈 Model Stats:")
    print(f"  - Symbol: {result['symbol']}")
    print(f"  - Training samples: {result['samples']}")
    print(f"  - Train accuracy: {result['train_accuracy']:.2%}")
    print(f"  - Test accuracy: {result['test_accuracy']:.2%}")
    print(f"  - Positive rate: {result['positive_rate']:.2%} (% of time price increased >2%)")
    print(f"  - Trained at: {result['trained_at']}")
    
    print(f"\n🎯 Feature Importance (what the model learned):")
    for feature, importance in sorted(result['feature_importance'].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(importance * 50)
        print(f"  {feature:20s} {importance:5.1%} {bar}")
    
    # Now test prediction
    print("\n" + "=" * 80)
    print("🔮 TESTING PREDICTION")
    print("=" * 80)
    
    prediction = ml_service.predict('VIRTUALUSDT')
    
    if prediction.get('error'):
        print(f"❌ Prediction error: {prediction['error']}")
    else:
        print(f"🎯 Symbol: {prediction['symbol']}")
        print(f"📊 Prediction: {prediction['prediction']}")
        print(f"💯 Confidence: {prediction['confidence']:.1%}")
        print(f"💭 Reasoning: {prediction['reasoning']}")
        
        print(f"\n📈 Current Indicators:")
        for key, val in prediction['current_indicators'].items():
            print(f"  - {key}: {val:.2f}")
        
        print(f"\n🤖 Model Info:")
        print(f"  - Trained: {prediction['model_info']['trained_at']}")
        print(f"  - Test Accuracy: {prediction['model_info']['test_accuracy']:.2%}")
else:
    print(f"❌ Training failed: {result.get('error')}")

print("\n" + "=" * 80)
print("✅ Test Complete!")
print("=" * 80)

