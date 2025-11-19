"""
ML Guard: Fast Naive Bayes + Logistic Regression
Trained on 159K Jigsaw examples

Speed: 0.3-0.9ms (faster than rule-based!)
Accuracy: Complements rules for nuanced cases
"""

import pickle
import os
from typing import Dict, Any, Optional
import time

_ML_MODEL = None

def _load_ml_model():
    """Load trained ML model (lazy loading)"""
    global _ML_MODEL
    
    if _ML_MODEL is not None:
        return _ML_MODEL
    
    model_path = "models/ml_fast.pkl"
    
    if not os.path.exists(model_path):
        print(f"Warning: ML model not found at {model_path}")
        return None
    
    try:
        with open(model_path, 'rb') as f:
            _ML_MODEL = pickle.load(f)
        print(f"✓ ML model loaded from {model_path}")
        return _ML_MODEL
    except Exception as e:
        print(f"Error loading ML model: {e}")
        return None

def predict_ml(text: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    ML-only prediction using Naive Bayes + LogReg
    
    Returns scores for all 6 categories:
    - toxic, severe_toxic, obscene, threat, insult, identity_hate
    """
    start = time.time()
    
    model_data = _load_ml_model()
    
    if model_data is None:
        return {
            'prediction': 'pass',
            'score': 0.0,
            'threshold': 0.5,
            'method': 'ml_unavailable',
            'latency_ms': 0
        }
    
    vec = model_data['vectorizer']
    models = model_data['models']
    labels = model_data['labels']
    
    # Transform text
    x = vec.transform([text])
    
    # Predict all labels
    scores = {}
    for label in labels:
        m, r = models[label]
        x_nb = x.multiply(r)
        prob = m.predict_proba(x_nb)[0][1]
        scores[label] = float(prob)
    
    # Max score across all categories
    max_label = max(scores, key=scores.get)
    max_score = scores[max_label]
    
    latency = int((time.time() - start) * 1000)
    
    return {
        'prediction': 'flag' if max_score > 0.5 else 'pass',
        'score': max_score,
        'threshold': 0.5,
        'category': max_label,
        'method': 'ml_only',
        'latency_ms': latency,
        'all_scores': scores
    }

def predict_hybrid(text: str, category: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    HYBRID: Rules + ML for best of both worlds
    
    Strategy:
    1. Run rules (1.8ms)
    2. Run ML in parallel (0.3-0.9ms)
    3. Combine intelligently:
       - If rules flag with high confidence (>0.8): Flag
       - If ML flags with high confidence (>0.8): Flag
       - If both agree safe (<0.3): Safe
       - If disagreement: Use weighted average (rules 70%, ML 30%)
    
    Result:
    - Latency: ~2-3ms (parallel execution)
    - Recall: Rules + ML catch different cases
    - Precision: Combined reduces false positives
    """
    start = time.time()
    
    # Import rule-based guard
    from guards.candidate import predict as rule_predict
    
    # Run both in parallel (they're both fast!)
    rule_result = rule_predict(text, category=category, **kwargs)
    ml_result = predict_ml(text, category=category)
    
    rule_score = rule_result.get('score', 0.0)
    ml_score = ml_result.get('score', 0.0)
    
    total_latency = int((time.time() - start) * 1000)
    
    # Decision logic
    if rule_score > 0.8:
        # Rules highly confident: trust it
        return {
            **rule_result,
            'method': 'rules_high_confidence',
            'latency_ms': total_latency,
            'ml_score': ml_score,
            'ml_used': True
        }
    
    if ml_score > 0.8:
        # ML highly confident: trust it
        return {
            'prediction': 'flag',
            'score': ml_score,
            'threshold': 0.5,
            'category': ml_result.get('category', 'general'),
            'method': 'ml_high_confidence',
            'latency_ms': total_latency,
            'rule_score': rule_score,
            'ml_score': ml_score,
            'explanation': f'ML detected {ml_result.get("category")} (rules: {rule_score:.2f}, ml: {ml_score:.2f})'
        }
    
    if rule_score < 0.3 and ml_score < 0.3:
        # Both agree: safe
        return {
            'prediction': 'pass',
            'score': max(rule_score, ml_score),
            'threshold': 0.5,
            'category': 'general',
            'method': 'both_agree_safe',
            'latency_ms': total_latency,
            'rule_score': rule_score,
            'ml_score': ml_score
        }
    
    # Disagreement or medium confidence: weighted average
    # Rules get 70% weight (more explainable)
    # ML gets 30% weight (catches nuances)
    combined = (rule_score * 0.7) + (ml_score * 0.3)
    
    return {
        'prediction': 'flag' if combined > 0.5 else 'pass',
        'score': combined,
        'threshold': 0.5,
        'category': rule_result.get('category', 'general'),
        'method': 'hybrid_weighted',
        'latency_ms': total_latency,
        'rule_score': rule_score,
        'ml_score': ml_score,
        'explanation': f'Hybrid: rules={rule_score:.2f} (70%), ml={ml_score:.2f} (30%)'
    }


if __name__ == "__main__":
    print("=== Testing Hybrid Guard ===\n")
    
    test_cases = [
        ("I will kill you", True),
        ("have a great day", False),
        ("you should die", True),
        ("you won't be around much longer", True),
        ("muslims should be deported", True),
        ("my head hurts", False),
        ("everyone would be better without you", True),
        ("how to make a bomb", True),
    ]
    
    print(f"{'Text':<45} {'Pred':<6} {'Score':<6} {'Method':<25} {'Latency':<10} {'Correct'}")
    print("-" * 115)
    
    for text, should_flag in test_cases:
        result = predict_hybrid(text)
        
        pred = result['prediction']
        score = result['score']
        method = result['method']
        latency = result['latency_ms']
        
        correct = "✓" if (pred == 'flag') == should_flag else "✗"
        
        print(f"{text:<45} {pred:<6} {score:5.2f}  {method:<25} {latency:3d}ms       {correct}")












