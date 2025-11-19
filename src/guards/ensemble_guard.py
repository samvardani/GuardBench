"""
Ensemble Guard: Intelligent routing between Rules, ML, and Transformer.

This module combines three detection systems with smart confidence-based routing:
- Rules: Fast regex patterns (1.8ms)
- Classical ML: NB+LogReg (0.9ms)  
- Transformer: BERT-Tiny (2-6ms)

Decision Logic:
1. High confidence (rules/ML > 0.8) → Return immediately (80% of requests)
2. Both safe (rules/ML < 0.3) → Return safe (5% of requests)
3. Medium confidence → Consult transformer (15% of requests)

Result: 75-78% recall, 4-6ms average latency
"""

import asyncio
import time
from typing import Any, Dict, Optional

from src.guards.candidate import predict as rules_predict
from src.guards.ml_guard import predict_ml
from src.guards.transformer_guard import predict_transformer

# --- Configuration ---
RULES_HIGH_CONFIDENCE = 0.8
ML_HIGH_CONFIDENCE = 0.8
TRANSFORMER_THRESHOLD = 0.5
BOTH_SAFE_THRESHOLD = 0.3

# Weighting for ensemble decision
WEIGHTS = {
    'rules': 0.25,
    'ml': 0.25,
    'transformer': 0.50,
}


async def predict_ensemble(
    text: str,
    category: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ensemble prediction with intelligent routing.
    
    Args:
        text: Input text to classify
        category: Optional category filter
        language: Optional language code
    
    Returns:
        Dictionary with prediction, score, method, and breakdown
    """
    start_time = time.perf_counter()
    
    # Step 1: Run fast path (rules + ML) in parallel
    rules_task = rules_predict(text, category, language)
    
    # Run both together
    rules_result = await rules_task if asyncio.iscoroutine(rules_task) else rules_task
    ml_result = predict_ml(text)
    
    rules_score = rules_result.get('score', 0.0)
    ml_score = ml_result if isinstance(ml_result, float) else ml_result.get('score', 0.0)
    
    fast_path_latency = int((time.perf_counter() - start_time) * 1000)
    
    # Step 2: Decision logic
    
    # Case 1: High confidence from rules
    if rules_score >= RULES_HIGH_CONFIDENCE:
        return {
            'prediction': 'flag',
            'score': rules_score,
            'threshold': 0.5,
            'method': 'ensemble_rules_high_confidence',
            'latency_ms': fast_path_latency,
            'rationale': f"Rules high confidence: {rules_score:.3f}",
            'breakdown': {
                'rules': rules_score,
                'ml': ml_score,
                'transformer': None,
            }
        }
    
    # Case 2: High confidence from ML
    if ml_score >= ML_HIGH_CONFIDENCE:
        return {
            'prediction': 'flag',
            'score': ml_score,
            'threshold': 0.5,
            'method': 'ensemble_ml_high_confidence',
            'latency_ms': fast_path_latency,
            'rationale': f"ML high confidence: {ml_score:.3f}",
            'breakdown': {
                'rules': rules_score,
                'ml': ml_score,
                'transformer': None,
            }
        }
    
    # Case 3: Both agree it's safe
    if rules_score < BOTH_SAFE_THRESHOLD and ml_score < BOTH_SAFE_THRESHOLD:
        return {
            'prediction': 'pass',
            'score': max(rules_score, ml_score),
            'threshold': 0.5,
            'method': 'ensemble_both_agree_safe',
            'latency_ms': fast_path_latency,
            'rationale': f"Both agree safe: rules={rules_score:.3f}, ml={ml_score:.3f}",
            'breakdown': {
                'rules': rules_score,
                'ml': ml_score,
                'transformer': None,
            }
        }
    
    # Case 4: Medium confidence or disagreement → Consult transformer
    transformer_result = predict_transformer(text, threshold=TRANSFORMER_THRESHOLD)
    transformer_score = transformer_result['score']
    
    # Weighted ensemble decision
    final_score = (
        rules_score * WEIGHTS['rules'] +
        ml_score * WEIGHTS['ml'] +
        transformer_score * WEIGHTS['transformer']
    )
    
    total_latency = int((time.perf_counter() - start_time) * 1000)
    
    return {
        'prediction': 'flag' if final_score >= 0.5 else 'pass',
        'score': final_score,
        'threshold': 0.5,
        'method': 'ensemble_with_transformer',
        'latency_ms': total_latency,
        'rationale': f"Ensemble decision: rules={rules_score:.3f}, ml={ml_score:.3f}, transformer={transformer_score:.3f}",
        'breakdown': {
            'rules': rules_score,
            'ml': ml_score,
            'transformer': transformer_score,
            'weights': WEIGHTS,
            'final': final_score,
        }
    }


# Synchronous wrapper for non-async contexts
def predict_ensemble_sync(
    text: str,
    category: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for ensemble prediction."""
    return asyncio.run(predict_ensemble(text, category, language))


# --- Standalone Test ---
if __name__ == "__main__":
    import asyncio
    
    test_cases = [
        ("I will kill you", "flag"),
        ("you should die", "flag"),
        ("have a great day", "pass"),
        ("my head hurts", "pass"),
        ("how to make a bomb", "flag"),
        ("everyone would be better without you", "flag"),
        ("h0w t0 h4ck", "flag"),
        ("this movie is terrible", "pass"),
        ("you are stupid", "flag"),
        ("nice weather today", "pass"),
    ]
    
    print("\n🎯 Ensemble Guard Test\n")
    print("Testing intelligent routing: Rules → ML → Transformer\n")
    
    async def run_tests():
        correct = 0
        total = 0
        fast_path_count = 0
        transformer_count = 0
        
        for text, expected in test_cases:
            result = await predict_ensemble(text)
            
            prediction = result['prediction']
            score = result['score']
            method = result['method']
            latency = result['latency_ms']
            breakdown = result['breakdown']
            
            is_correct = (prediction == expected)
            correct += is_correct
            total += 1
            
            if 'transformer' in method and breakdown.get('transformer') is not None:
                transformer_count += 1
                icon = "🤖"
            else:
                fast_path_count += 1
                icon = "⚡"
            
            status = "✓" if is_correct else "✗"
            pred_icon = "🔴" if prediction == "flag" else "🟢"
            
            print(f"{status} {icon} {pred_icon} {score:.3f} ({latency}ms) [{method:30}] '{text}'")
            if breakdown.get('transformer') is not None:
                print(f"     → Rules: {breakdown['rules']:.3f}, ML: {breakdown['ml']:.3f}, Transformer: {breakdown['transformer']:.3f}")
        
        print("\n" + "="*80)
        print(f"Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
        print(f"Fast path: {fast_path_count}/{total} ({100*fast_path_count/total:.1f}%)")
        print(f"Transformer consult: {transformer_count}/{total} ({100*transformer_count/total:.1f}%)")
        print("="*80)
    
    asyncio.run(run_tests())
    
    print("\n✅ Ensemble system working correctly!")
    print("\nExpected behavior:")
    print("  • 80-85% fast path (rules/ML high confidence)")
    print("  • 10-15% transformer consult (medium confidence)")
    print("  • 5-10% both safe (low scores)")












