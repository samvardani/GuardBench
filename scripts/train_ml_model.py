#!/usr/bin/env python3
"""
Train ML Model: Naive Bayes + Logistic Regression

Usage:
    python scripts/train_ml_model.py
    python scripts/train_ml_model.py --dataset datasets_raw/train.csv
    python scripts/train_ml_model.py --output models/ml_fast_v2.pkl
"""

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


def train_ml_model(
    dataset_path: str = "datasets_raw/train.csv",
    output_path: str = "models/ml_fast.pkl",
    max_features: int = 15000,
    ngram_range: tuple = (1, 2),
    min_df: int = 3,
    max_df: float = 0.9,
    C: float = 4.0,
    max_iter: int = 100,
    verbose: bool = True
):
    """
    Train ML model on Jigsaw dataset
    
    Args:
        dataset_path: Path to training CSV
        output_path: Path to save model
        max_features: Max TF-IDF features
        ngram_range: N-gram range for TF-IDF
        min_df: Minimum document frequency
        max_df: Maximum document frequency
        C: Logistic regression regularization
        max_iter: Max iterations for training
        verbose: Print progress
    
    Returns:
        dict: Model metadata (training time, accuracy, etc.)
    """
    start_time = time.time()
    
    if verbose:
        print("=" * 70)
        print("🤖 TRAINING ML MODEL")
        print("=" * 70)
        print(f"\nDataset: {dataset_path}")
        print(f"Output: {output_path}")
        print(f"Features: {max_features}, N-grams: {ngram_range}")
        print()
    
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        print(f"❌ Error: Dataset not found at {dataset_path}")
        print(f"   Run: python scripts/download_datasets.py")
        sys.exit(1)
    
    # Load dataset
    if verbose:
        print("📥 Loading dataset...")
    
    try:
        train = pd.read_csv(dataset_path)
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        sys.exit(1)
    
    if verbose:
        print(f"   ✓ Loaded {len(train):,} examples")
    
    # Define labels
    labels = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
    
    # Check if labels exist
    missing_labels = [l for l in labels if l not in train.columns]
    if missing_labels:
        print(f"❌ Error: Missing labels in dataset: {missing_labels}")
        sys.exit(1)
    
    # Clean data
    if verbose:
        print("\n🧹 Cleaning data...")
    
    train = train.copy()
    train['comment_text'] = train['comment_text'].fillna("unknown")
    
    # Remove empty rows
    before = len(train)
    train = train[train['comment_text'].str.len() > 0]
    after = len(train)
    
    if verbose:
        print(f"   ✓ Removed {before - after} empty rows")
        print(f"\n📊 Label Distribution:")
        for label in labels:
            count = train[label].sum()
            pct = count / len(train) * 100
            print(f"   {label:15} {count:6,} ({pct:5.2f}%)")
    
    # TF-IDF Vectorization
    if verbose:
        print(f"\n🔢 TF-IDF Vectorization...")
        print(f"   Max features: {max_features}")
        print(f"   N-gram range: {ngram_range}")
    
    vec_start = time.time()
    vec = TfidfVectorizer(
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        strip_accents='unicode',
        use_idf=True,
        smooth_idf=True,
        sublinear_tf=True,
        token_pattern=r'\b\w+\b'
    )
    
    X_train = vec.fit_transform(train['comment_text'])
    vec_time = time.time() - vec_start
    
    if verbose:
        print(f"   ✓ Vectorization complete in {vec_time:.1f}s")
        print(f"   Shape: {X_train.shape}")
        print(f"   Sparsity: {(1.0 - X_train.nnz / (X_train.shape[0] * X_train.shape[1])) * 100:.2f}%")
    
    # Train models
    if verbose:
        print(f"\n🎓 Training {len(labels)} classifiers...")
    
    def pr(x, y_i, y):
        """Naive Bayes probability ratio"""
        p = x[y==y_i].sum(0)
        return (p+1) / ((y==y_i).sum()+1)
    
    models = {}
    training_stats = {}
    
    for i, label in enumerate(labels):
        if verbose:
            print(f"   [{i+1}/{len(labels)}] Training '{label}'...", end=' ', flush=True)
        
        model_start = time.time()
        y = train[label].values
        
        # Naive Bayes feature weights
        r = np.log(pr(X_train, 1, y) / pr(X_train, 0, y))
        
        # Weighted features
        X_nb = X_train.multiply(r)
        
        # Logistic Regression
        m = LogisticRegression(
            C=C,
            dual=False,
            max_iter=max_iter,
            solver='lbfgs',
            n_jobs=1,
            random_state=42
        )
        m.fit(X_nb, y)
        
        model_time = time.time() - model_start
        
        # Store model and weights
        models[label] = (m, r)
        
        # Training stats
        train_acc = m.score(X_nb, y)
        training_stats[label] = {
            'training_time': model_time,
            'accuracy': train_acc,
            'positive_examples': int(y.sum()),
            'negative_examples': int((1 - y).sum())
        }
        
        if verbose:
            print(f"✓ ({model_time:.1f}s, acc: {train_acc:.3f})")
    
    total_train_time = time.time() - start_time
    
    # Save model
    if verbose:
        print(f"\n💾 Saving model to {output_path}...")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    model_data = {
        'vectorizer': vec,
        'models': models,
        'labels': labels,
        'metadata': {
            'dataset_path': dataset_path,
            'dataset_size': len(train),
            'max_features': max_features,
            'ngram_range': ngram_range,
            'training_time': total_train_time,
            'trained_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'training_stats': training_stats,
            'sklearn_version': '1.3+',
            'python_version': sys.version
        }
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    file_size = os.path.getsize(output_path) / 1024 / 1024
    
    if verbose:
        print(f"   ✓ Model saved ({file_size:.2f} MB)")
        print(f"\n⏱️  Total training time: {total_train_time:.1f}s")
        print(f"\n✅ Training complete!")
        print("=" * 70)
    
    return model_data['metadata']


def validate_model(model_path: str, test_cases: list = None, verbose: bool = True):
    """
    Validate trained model on test cases
    
    Args:
        model_path: Path to trained model
        test_cases: List of (text, expected_flag) tuples
        verbose: Print results
    
    Returns:
        dict: Validation results
    """
    if verbose:
        print("\n🧪 Validating model...")
    
    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    vec = model_data['vectorizer']
    models = model_data['models']
    labels = model_data['labels']
    
    # Default test cases
    if test_cases is None:
        test_cases = [
            ("I will kill you", True),
            ("you should die", True),
            ("have a great day", False),
            ("everyone would be better without you", True),
            ("my head hurts", False),
            ("how to make a bomb", True),
        ]
    
    results = []
    correct = 0
    
    if verbose:
        print(f"\n{'Text':<45} {'Expected':<10} {'Predicted':<10} {'Score':<8} {'Result'}")
        print("-" * 85)
    
    for text, expected_flag in test_cases:
        # Transform
        x = vec.transform([text])
        
        # Get scores for all labels
        scores = {}
        for label in labels:
            m, r = models[label]
            x_nb = x.multiply(r)
            prob = m.predict_proba(x_nb)[0][1]
            scores[label] = prob
        
        # Max score
        max_score = max(scores.values())
        predicted_flag = max_score > 0.5
        
        is_correct = predicted_flag == expected_flag
        if is_correct:
            correct += 1
        
        results.append({
            'text': text,
            'expected': expected_flag,
            'predicted': predicted_flag,
            'score': max_score,
            'correct': is_correct,
            'scores': scores
        })
        
        if verbose:
            exp_str = "FLAG" if expected_flag else "SAFE"
            pred_str = "FLAG" if predicted_flag else "SAFE"
            result_str = "✓" if is_correct else "✗"
            print(f"{text:<45} {exp_str:<10} {pred_str:<10} {max_score:7.3f}  {result_str}")
    
    accuracy = correct / len(test_cases)
    
    if verbose:
        print("-" * 85)
        print(f"Validation Accuracy: {correct}/{len(test_cases)} = {accuracy*100:.1f}%")
    
    return {
        'accuracy': accuracy,
        'correct': correct,
        'total': len(test_cases),
        'results': results
    }


def main():
    parser = argparse.ArgumentParser(description='Train ML model for content moderation')
    parser.add_argument('--dataset', type=str, default='datasets_raw/train.csv',
                        help='Path to training dataset (CSV)')
    parser.add_argument('--output', type=str, default='models/ml_fast.pkl',
                        help='Path to save trained model')
    parser.add_argument('--max-features', type=int, default=15000,
                        help='Max TF-IDF features (default: 15000)')
    parser.add_argument('--validate', action='store_true',
                        help='Validate model after training')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output')
    
    args = parser.parse_args()
    
    # Train model
    metadata = train_ml_model(
        dataset_path=args.dataset,
        output_path=args.output,
        max_features=args.max_features,
        verbose=not args.quiet
    )
    
    # Validate if requested
    if args.validate:
        validate_model(args.output, verbose=not args.quiet)
    
    # Return success
    return 0


if __name__ == '__main__':
    sys.exit(main())












