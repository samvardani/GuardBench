"""
Transformer-based guard using BERT-Tiny for toxicity detection.

This module provides transformer inference that can be used standalone
or as part of an ensemble with rules and ML guards.
"""

import math
import os
import pickle
import time
from typing import Any, Dict, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --- Configuration ---
DEFAULT_MODEL_PATH = "models/transformer_toxicity.pkl"
DEFAULT_THRESHOLD = 0.5
DEVICE = None  # Will be auto-detected

# --- Global Model State ---
_model = None
_tokenizer = None
_model_config = None
_last_model_mtime = 0


def _get_device():
    """Auto-detect best available device."""
    global DEVICE
    if DEVICE is None:
        if torch.cuda.is_available():
            DEVICE = torch.device('cuda')
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            DEVICE = torch.device('mps')
        else:
            DEVICE = torch.device('cpu')
    return DEVICE


def load_transformer_model(model_path: str = DEFAULT_MODEL_PATH):
    """Load transformer model from pickle file."""
    global _model, _tokenizer, _model_config, _last_model_mtime
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    current_mtime = os.path.getmtime(model_path)
    
    # Hot reload if model file changed
    if _model is None or current_mtime > _last_model_mtime:
        print(f"Loading transformer model from {model_path}...")
        
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        _tokenizer = data['tokenizer']
        model_name = data['model_name']
        max_length = data.get('max_length', 128)
        metadata = data.get('metadata', {})
        
        # Load model architecture and weights
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=1,
            problem_type="regression"
        )
        model.load_state_dict(data['model'])
        model.eval()
        model.to(_get_device())
        
        _model = model
        _model_config = {
            'max_length': max_length,
            'model_name': model_name,
            'metadata': metadata,
        }
        _last_model_mtime = current_mtime
        
        print(f"✓ Transformer model loaded: {model_name}")
        print(f"  Device: {_get_device()}")
        print(f"  Max length: {max_length}")
        if metadata:
            print(f"  ROC-AUC: {metadata.get('best_roc_auc', 'N/A')}")
    
    return _model, _tokenizer, _model_config


def predict_transformer(
    text: str,
    model_path: str = DEFAULT_MODEL_PATH,
    threshold: float = DEFAULT_THRESHOLD
) -> Dict[str, Any]:
    """
    Predict toxicity using transformer model.
    
    Args:
        text: Input text to classify
        model_path: Path to trained model
        threshold: Classification threshold (default 0.5)
    
    Returns:
        Dictionary with prediction, score, and metadata
    """
    start_time = time.perf_counter()
    
    # Load model if not already loaded
    if _model is None:
        load_transformer_model(model_path)
    
    # Tokenize
    max_length = _model_config['max_length']
    inputs = _tokenizer(
        text,
        truncation=True,
        max_length=max_length,
        padding='max_length',
        return_tensors='pt'
    )
    
    # Move to device
    inputs = {k: v.to(_get_device()) for k, v in inputs.items()}
    
    # Inference
    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits.squeeze().item()
    
    # Convert logit to probability
    prob = 1 / (1 + math.exp(-logits))
    
    # Classification
    prediction = "flag" if prob >= threshold else "pass"
    
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    return {
        'prediction': prediction,
        'score': prob,
        'threshold': threshold,
        'method': 'transformer',
        'model': _model_config['model_name'],
        'latency_ms': latency_ms,
    }


# --- Standalone Test ---
if __name__ == "__main__":
    test_cases = [
        "I will kill you",
        "you should die",
        "have a great day",
        "my head hurts",
        "how to make a bomb",
        "everyone would be better without you",
        "h0w t0 h4ck",  # obfuscated
    ]
    
    print("\n🤖 Transformer Guard Test\n")
    
    for text in test_cases:
        result = predict_transformer(text)
        icon = "🔴" if result['prediction'] == 'flag' else "🟢"
        score = result['score']
        latency = result['latency_ms']
        print(f"{icon} {score:.3f} ({latency}ms)  '{text}'")
    
    print(f"\n✓ Model: {_model_config['model_name']}")
    print(f"✓ Device: {_get_device()}")












