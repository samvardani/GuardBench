#!/usr/bin/env python3
"""
CLIP-based Image Safety Guard
Uses OpenAI CLIP (ViT-L/14) for semantic understanding + lightweight MLP classifier
"""
import os
import pickle
import time
from typing import Any, Dict, Optional, Tuple, List
import base64
from io import BytesIO

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# --- Configuration ---
MODEL_PATH = "models/clip_image_classifier.pkl"
CLIP_MODEL_NAME = "ViT-L/14"  # OpenAI CLIP large model
IMAGE_CATEGORIES = ["nsfw", "violence", "hate_symbols"]
THRESHOLD = 0.5  # Classification threshold
MAX_IMAGE_SIZE = (512, 512)  # Resize large images for efficiency

# Global model cache
_clip_model = None
_clip_preprocess = None
_classifier = None
_device = None
_last_model_mtime: float = 0


class ImageClassifier(nn.Module):
    """Multi-label CNN classifier on top of CLIP embeddings
    
    Architecture:
    - Reshape CLIP embedding (768,) → (1, 768, 1) for 1D convolutions
    - 3 Conv1D layers with batch norm + ReLU + dropout
    - Global average pooling
    - 2 FC layers for multi-label classification
    
    Benefits over MLP:
    - Better feature extraction via convolutions
    - Spatial invariance (even for 1D embeddings)
    - Batch normalization for training stability
    - Better generalization on limited data
    """
    def __init__(self, input_dim: int = 768, num_classes: int = 3):
        super().__init__()
        
        # Convolutional layers (1D convolutions over embedding dimension)
        self.conv_layers = nn.Sequential(
            # Conv block 1: 768 → 512
            nn.Conv1d(1, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.MaxPool1d(2),  # 768 → 384
            
            # Conv block 2: 384 → 192
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.MaxPool1d(2),  # 384 → 192
            
            # Conv block 3: 192 → 96
            nn.Conv1d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.MaxPool1d(2),  # 192 → 96
        )
        
        # Global average pooling (256 channels → 256 features)
        self.global_avg_pool = nn.AdaptiveAvgPool1d(1)
        
        # Fully connected layers for multi-label classification
        self.fc_layers = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        # x shape: (batch, 768) - CLIP embedding
        # Reshape for 1D convolution: (batch, 1, 768)
        x = x.unsqueeze(1)
        
        # Convolutional feature extraction
        x = self.conv_layers(x)  # (batch, 256, 96)
        
        # Global average pooling
        x = self.global_avg_pool(x)  # (batch, 256, 1)
        x = x.squeeze(-1)  # (batch, 256)
        
        # Fully connected classification
        x = self.fc_layers(x)  # (batch, num_classes)
        
        return x


def _get_device() -> torch.device:
    """Get the best available device (MPS > CUDA > CPU)"""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")


def _load_clip_model():
    """Load CLIP model and classifier"""
    global _clip_model, _clip_preprocess, _classifier, _device, _last_model_mtime
    
    try:
        # Initialize device
        if _device is None:
            _device = _get_device()
            print(f"Image guard using device: {_device}")
        
        # Load CLIP model (always needed)
        if _clip_model is None:
            try:
                import clip
                _clip_model, _clip_preprocess = clip.load(CLIP_MODEL_NAME, device=_device)
                _clip_model.eval()
                print(f"✓ CLIP model loaded: {CLIP_MODEL_NAME}")
            except ImportError:
                print("⚠ CLIP not installed. Install with: pip install git+https://github.com/openai/CLIP.git")
                return None, None, None
            except Exception as e:
                print(f"❌ Error loading CLIP: {e}")
                return None, None, None
        
        # Load classifier if available
        if os.path.exists(MODEL_PATH):
            current_mtime = os.path.getmtime(MODEL_PATH)
            if _classifier is None or current_mtime > _last_model_mtime:
                with open(MODEL_PATH, 'rb') as f:
                    model_data = pickle.load(f)
                
                _classifier = ImageClassifier(
                    input_dim=model_data.get('input_dim', 768),
                    num_classes=len(IMAGE_CATEGORIES)
                )
                _classifier.load_state_dict(model_data['model_state'])
                _classifier.to(_device)
                _classifier.eval()
                _last_model_mtime = current_mtime
                print(f"✓ Image classifier loaded from {MODEL_PATH}")
        else:
            print(f"⚠ Image classifier not found at {MODEL_PATH}. Using zero-shot CLIP only.")
            _classifier = None
        
        return _clip_model, _clip_preprocess, _classifier
    
    except Exception as e:
        print(f"❌ Error loading image models: {e}")
        return None, None, None


def _preprocess_image(image_data: bytes) -> Optional[Image.Image]:
    """Load and preprocess image from bytes"""
    try:
        img = Image.open(BytesIO(image_data))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (for efficiency)
        if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        return img
    except Exception as e:
        print(f"❌ Error preprocessing image: {e}")
        return None


def _zero_shot_clip_classification(clip_model, image_tensor: torch.Tensor) -> Dict[str, float]:
    """
    Zero-shot classification using CLIP text prompts
    Fallback when trained classifier is unavailable
    """
    # Define text prompts for each category
    prompts = {
        "nsfw": [
            "explicit sexual content",
            "nudity",
            "pornographic image",
            "NSFW content"
        ],
        "violence": [
            "graphic violence",
            "blood and gore",
            "weapons",
            "violent scene"
        ],
        "hate_symbols": [
            "hate symbol",
            "swastika",
            "racist imagery",
            "extremist symbol"
        ]
    }
    
    try:
        import clip
        
        scores = {}
        for category, texts in prompts.items():
            # Tokenize prompts
            text_tokens = clip.tokenize(texts).to(image_tensor.device)
            
            # Get embeddings
            with torch.no_grad():
                image_features = clip_model.encode_image(image_tensor)
                text_features = clip_model.encode_text(text_tokens)
                
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity (cosine similarity)
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                
                # Take max similarity across all prompts for this category
                scores[category] = float(similarity.max().cpu())
        
        return scores
    
    except Exception as e:
        print(f"❌ Error in zero-shot classification: {e}")
        return {cat: 0.0 for cat in IMAGE_CATEGORIES}


async def predict_image(
    image_data: bytes,
    use_zero_shot: bool = False
) -> Dict[str, Any]:
    """
    Predict safety categories for an image
    
    Args:
        image_data: Raw image bytes (JPEG, PNG, etc.)
        use_zero_shot: Force zero-shot CLIP (ignore trained classifier)
    
    Returns:
        Dict with prediction results
    """
    start_time = time.perf_counter()
    
    # Load models
    clip_model, clip_preprocess, classifier = _load_clip_model()
    
    if clip_model is None:
        return {
            "prediction": "error",
            "scores": {cat: 0.0 for cat in IMAGE_CATEGORIES},
            "flagged_categories": [],
            "rationale": "CLIP model unavailable",
            "method": "unavailable",
            "latency_ms": 0
        }
    
    # Preprocess image
    img = _preprocess_image(image_data)
    if img is None:
        return {
            "prediction": "error",
            "scores": {cat: 0.0 for cat in IMAGE_CATEGORIES},
            "flagged_categories": [],
            "rationale": "Invalid image format",
            "method": "error",
            "latency_ms": int((time.perf_counter() - start_time) * 1000)
        }
    
    # Convert to tensor
    image_tensor = clip_preprocess(img).unsqueeze(0).to(_device)
    
    # Get CLIP embedding
    with torch.no_grad():
        clip_embedding = clip_model.encode_image(image_tensor)
        clip_embedding = clip_embedding / clip_embedding.norm(dim=-1, keepdim=True)
    
    # Classify using trained classifier or zero-shot
    if classifier is not None and not use_zero_shot:
        # Use trained classifier
        with torch.no_grad():
            logits = classifier(clip_embedding)
            probs = torch.sigmoid(logits).cpu().numpy()[0]
        
        scores = {cat: float(probs[i]) for i, cat in enumerate(IMAGE_CATEGORIES)}
        method = "clip_trained_classifier"
    else:
        # Use zero-shot CLIP
        scores = _zero_shot_clip_classification(clip_model, image_tensor)
        method = "clip_zero_shot"
    
    # Determine flagged categories
    flagged = [cat for cat, score in scores.items() if score >= THRESHOLD]
    
    # Overall prediction
    prediction = "flag" if len(flagged) > 0 else "pass"
    
    # Rationale
    if flagged:
        rationale = f"Image flagged for: {', '.join(flagged)}"
    else:
        rationale = "Image appears safe"
    
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    return {
        "prediction": prediction,
        "scores": scores,
        "flagged_categories": flagged,
        "rationale": rationale,
        "method": method,
        "latency_ms": latency_ms,
        "model": CLIP_MODEL_NAME
    }


# Convenience functions for different input formats
async def predict_image_from_file(file_path: str) -> Dict[str, Any]:
    """Predict safety for image file"""
    try:
        with open(file_path, 'rb') as f:
            image_data = f.read()
        return await predict_image(image_data)
    except Exception as e:
        return {
            "prediction": "error",
            "scores": {cat: 0.0 for cat in IMAGE_CATEGORIES},
            "flagged_categories": [],
            "rationale": f"Error reading file: {e}",
            "method": "error",
            "latency_ms": 0
        }


async def predict_image_from_base64(base64_str: str) -> Dict[str, Any]:
    """Predict safety for base64-encoded image"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',', 1)[1]
        
        image_data = base64.b64decode(base64_str)
        return await predict_image(image_data)
    except Exception as e:
        return {
            "prediction": "error",
            "scores": {cat: 0.0 for cat in IMAGE_CATEGORIES},
            "flagged_categories": [],
            "rationale": f"Error decoding base64: {e}",
            "method": "error",
            "latency_ms": 0
        }


async def predict_image_from_url(url: str) -> Dict[str, Any]:
    """Predict safety for image URL"""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            image_data = response.content
        
        return await predict_image(image_data)
    except Exception as e:
        return {
            "prediction": "error",
            "scores": {cat: 0.0 for cat in IMAGE_CATEGORIES},
            "flagged_categories": [],
            "rationale": f"Error fetching URL: {e}",
            "method": "error",
            "latency_ms": 0
        }


# Demo / Testing
if __name__ == "__main__":
    import asyncio
    
    async def test_image_guard():
        print("\n🖼️  CLIP Image Safety Guard Test\n")
        
        # Test with a sample image (you'd need actual test images)
        test_cases = [
            ("Test safe image", "test_images/safe.jpg"),
            ("Test NSFW image", "test_images/nsfw.jpg"),
            ("Test violence image", "test_images/violence.jpg"),
        ]
        
        for description, image_path in test_cases:
            if os.path.exists(image_path):
                print(f"\n{description}: {image_path}")
                result = await predict_image_from_file(image_path)
                print(f"  Prediction: {result['prediction']}")
                print(f"  Scores: {result['scores']}")
                print(f"  Flagged: {result['flagged_categories']}")
                print(f"  Latency: {result['latency_ms']}ms")
                print(f"  Method: {result['method']}")
            else:
                print(f"\n⚠ {description}: File not found: {image_path}")
        
        print("\n✅ Image guard test complete")
    
    asyncio.run(test_image_guard())

