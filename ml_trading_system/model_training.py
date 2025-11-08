"""
Model Training Module

Trains ML models (XGBoost, LightGBM, LSTM) on prepared features
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
import yaml
import json
import pickle
from datetime import datetime
from pathlib import Path

import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns


class ModelTrainer:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize model trainer with config"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.model = None
        self.feature_columns = None
        self.model_type = self.config['model']['type']
        
        # Create models directory
        Path("models").mkdir(exist_ok=True)
        Path("models/metrics").mkdir(exist_ok=True)
    
    def prepare_data(self, df: pd.DataFrame, feature_columns: List[str]) -> Tuple:
        """
        Prepare data for training with proper time-series split
        
        Returns:
            X_train, X_test, y_train, y_test
        """
        # Sort by time
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Split features and labels
        X = df[feature_columns].values
        y = df['label'].values
        timestamps = df['timestamp'].values
        
        # Time-series split (no shuffling!)
        train_size = int(len(X) * self.config['model']['train_test_split'])
        
        X_train = X[:train_size]
        X_test = X[train_size:]
        y_train = y[:train_size]
        y_test = y[train_size:]
        
        print(f"📊 Data Split:")
        print(f"   Train: {len(X_train)} samples ({len(X_train)/len(X)*100:.1f}%)")
        print(f"   Test:  {len(X_test)} samples ({len(X_test)/len(X)*100:.1f}%)")
        print(f"   Features: {X_train.shape[1]}")
        print(f"   Train date range: {timestamps[0]} to {timestamps[train_size-1]}")
        print(f"   Test date range: {timestamps[train_size]} to {timestamps[-1]}")
        print(f"   Positive labels (train): {y_train.sum()} ({y_train.mean()*100:.1f}%)")
        print(f"   Positive labels (test): {y_test.sum()} ({y_test.mean()*100:.1f}%)")
        
        return X_train, X_test, y_train, y_test
    
    def train_xgboost(self, X_train, y_train, X_val=None, y_val=None) -> xgb.Booster:
        """Train XGBoost model"""
        print("\n🚀 Training XGBoost model...")
        
        # Calculate class weights to handle imbalance
        pos_count = y_train.sum()
        neg_count = len(y_train) - pos_count
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        
        print(f"   Class imbalance: {pos_count} positive / {neg_count} negative")
        print(f"   Scale pos weight: {scale_pos_weight:.2f}")
        
        params = {
            'objective': 'binary:logistic',
            'max_depth': self.config['model']['hyperparameters']['max_depth'],
            'learning_rate': self.config['model']['hyperparameters']['learning_rate'],
            'n_estimators': self.config['model']['hyperparameters']['n_estimators'],
            'subsample': self.config['model']['hyperparameters']['subsample'],
            'colsample_bytree': self.config['model']['hyperparameters']['colsample_bytree'],
            'scale_pos_weight': scale_pos_weight,  # Handle class imbalance
            'eval_metric': 'logloss',
            'tree_method': 'hist',
            'random_state': 42
        }
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        evals = [(dtrain, 'train')]
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val)
            evals.append((dval, 'val'))
        
        # Train
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=params['n_estimators'],
            evals=evals,
            early_stopping_rounds=20,
            verbose_eval=50
        )
        
        print("✅ XGBoost training complete")
        return model
    
    def train_lightgbm(self, X_train, y_train, X_val=None, y_val=None):
        """Train LightGBM model"""
        print("\n🚀 Training LightGBM model...")
        
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'max_depth': self.config['model']['hyperparameters']['max_depth'],
            'learning_rate': self.config['model']['hyperparameters']['learning_rate'],
            'n_estimators': self.config['model']['hyperparameters']['n_estimators'],
            'subsample': self.config['model']['hyperparameters']['subsample'],
            'colsample_bytree': self.config['model']['hyperparameters']['colsample_bytree'],
            'random_state': 42,
            'verbose': -1
        }
        
        model = lgb.LGBMClassifier(**params)
        
        # Validation set for early stopping
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))
        
        model.fit(
            X_train, y_train,
            eval_set=eval_set,
            callbacks=[lgb.early_stopping(20), lgb.log_evaluation(50)]
        )
        
        print("✅ LightGBM training complete")
        return model
    
    def train(self, df: pd.DataFrame, feature_columns: List[str]):
        """Main training method"""
        print("\n" + "="*80)
        print("🧠 TRAINING ML MODEL")
        print("="*80)
        
        self.feature_columns = feature_columns
        
        # Prepare data
        X_train, X_test, y_train, y_test = self.prepare_data(df, feature_columns)
        
        # Validation split from training data
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, 
            test_size=self.config['model']['validation_split'],
            shuffle=False  # Keep time order
        )
        
        # Train based on model type
        if self.model_type == 'xgboost':
            self.model = self.train_xgboost(X_train, y_train, X_val, y_val)
        elif self.model_type == 'lightgbm':
            self.model = self.train_lightgbm(X_train, y_train, X_val, y_val)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        # Evaluate
        metrics = self.evaluate(X_test, y_test)
        
        # Save model
        self.save_model(metrics)
        
        print("\n" + "="*80)
        print("✅ TRAINING COMPLETE")
        print("="*80)
        
        return metrics
    
    def predict_proba(self, X) -> np.ndarray:
        """Predict probabilities"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        if self.model_type == 'xgboost':
            dmatrix = xgb.DMatrix(X)
            return self.model.predict(dmatrix)
        elif self.model_type == 'lightgbm':
            return self.model.predict_proba(X)[:, 1]
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def predict(self, X, threshold: Optional[float] = None) -> np.ndarray:
        """Predict class labels"""
        if threshold is None:
            threshold = self.config['model']['probability_threshold']
        
        probas = self.predict_proba(X)
        return (probas >= threshold).astype(int)
    
    def evaluate(self, X_test, y_test) -> Dict:
        """Evaluate model performance"""
        print("\n📊 EVALUATING MODEL...")
        
        # Predictions
        y_proba = self.predict_proba(X_test)
        y_pred = self.predict(X_test)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_proba),
            'test_samples': len(y_test),
            'positive_rate': y_test.mean(),
            'threshold': self.config['model']['probability_threshold']
        }
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        print(f"\n✅ Model Performance:")
        print(f"   Accuracy:  {metrics['accuracy']:.3f}")
        print(f"   Precision: {metrics['precision']:.3f}")
        print(f"   Recall:    {metrics['recall']:.3f}")
        print(f"   F1 Score:  {metrics['f1']:.3f}")
        print(f"   ROC-AUC:   {metrics['roc_auc']:.3f}")
        print(f"\n   Confusion Matrix:")
        print(f"   TN: {cm[0,0]:4d}  FP: {cm[0,1]:4d}")
        print(f"   FN: {cm[1,0]:4d}  TP: {cm[1,1]:4d}")
        
        # Plot confusion matrix
        self._plot_confusion_matrix(cm)
        
        # Feature importance
        self._plot_feature_importance()
        
        return metrics
    
    def _plot_confusion_matrix(self, cm):
        """Plot confusion matrix"""
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.savefig('models/metrics/confusion_matrix.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   📊 Confusion matrix saved to models/metrics/confusion_matrix.png")
    
    def _plot_feature_importance(self, top_n: int = 20):
        """Plot feature importance"""
        if self.model_type == 'xgboost':
            importance = self.model.get_score(importance_type='gain')
            importance_df = pd.DataFrame([
                {'feature': k, 'importance': v} 
                for k, v in importance.items()
            ]).sort_values('importance', ascending=False).head(top_n)
        elif self.model_type == 'lightgbm':
            importance = self.model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': importance
            }).sort_values('importance', ascending=False).head(top_n)
        
        plt.figure(figsize=(10, 8))
        plt.barh(importance_df['feature'], importance_df['importance'])
        plt.xlabel('Importance')
        plt.title(f'Top {top_n} Feature Importances')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig('models/metrics/feature_importance.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   📊 Feature importance saved to models/metrics/feature_importance.png")
    
    def save_model(self, metrics: Dict):
        """Save trained model and metadata"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_name = f"{self.model_type}_{timestamp}"
        
        # Save model
        if self.model_type == 'xgboost':
            model_path = f"models/{model_name}.json"
            self.model.save_model(model_path)
        elif self.model_type == 'lightgbm':
            model_path = f"models/{model_name}.txt"
            self.model.booster_.save_model(model_path)
        
        # Save metadata
        metadata = {
            'model_name': model_name,
            'model_type': self.model_type,
            'timestamp': timestamp,
            'feature_columns': self.feature_columns,
            'metrics': metrics,
            'config': self.config['model']
        }
        
        metadata_path = f"models/{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Model saved:")
        print(f"   Model: {model_path}")
        print(f"   Metadata: {metadata_path}")
    
    def load_model(self, model_path: str):
        """Load a saved model"""
        if 'xgboost' in model_path:
            self.model = xgb.Booster()
            self.model.load_model(model_path)
            self.model_type = 'xgboost'
        elif 'lightgbm' in model_path:
            self.model = lgb.Booster(model_file=model_path)
            self.model_type = 'lightgbm'
        
        # Load metadata
        metadata_path = model_path.replace('.json', '_metadata.json').replace('.txt', '_metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.feature_columns = metadata['feature_columns']
        print(f"✅ Model loaded: {model_path}")
        return metadata


def main():
    """Test model training"""
    from data_ingestion import DataIngestion
    from feature_engineering import FeatureEngineering
    
    print("="*80)
    print("🧪 TESTING MODEL TRAINING")
    print("="*80)
    
    # Load data
    print("\n1️⃣  Loading data...")
    ingestion = DataIngestion()
    df = ingestion.load_ohlcv('BTC/USDT', '1m')
    
    if df.empty:
        print("❌ No data found. Run data_ingestion.py first.")
        return
    
    print(f"✅ Loaded {len(df)} candles")
    
    # Create features
    print("\n2️⃣  Creating features...")
    fe = FeatureEngineering()
    df_features = fe.create_all_features(df)
    feature_columns = fe.get_feature_columns(df_features)
    print(f"✅ {len(feature_columns)} features created")
    
    # Train model
    print("\n3️⃣  Training model...")
    trainer = ModelTrainer()
    metrics = trainer.train(df_features, feature_columns)
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

