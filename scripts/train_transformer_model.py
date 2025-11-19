#!/usr/bin/env python3
"""
Train a lightweight transformer model for toxicity detection.

This script provides a realistic alternative to DeBERTa-v3-base that:
1. Runs on Apple Silicon MPS or CPU
2. Trains in reasonable time (~2-4 hours on M1/M2)
3. Stays within memory budget (8GB RAM)
4. Produces a model small enough to deploy (<100MB)

Usage:
    python scripts/train_transformer_model.py --model distilbert --epochs 2 --output models/transformer_toxicity.pkl
"""

import argparse
import logging
import os
import pickle
import time
from typing import Dict, Any, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, matthews_corrcoef

# --- Configuration ---
SUPPORTED_MODELS = {
    "distilbert": "distilbert-base-uncased",  # 66M params, ~250MB
    "tiny-bert": "prajjwal1/bert-tiny",       # 4M params, ~17MB (RECOMMENDED)
    "mini-bert": "prajjwal1/bert-mini",       # 11M params, ~42MB
}

DEFAULT_MODEL = "tiny-bert"
DEFAULT_MAX_LENGTH = 128  # Shorter for speed
DEFAULT_BATCH_SIZE = 32
DEFAULT_EPOCHS = 2
DEFAULT_LR = 2e-5

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# --- Lightweight Dataset (uses existing Jigsaw data) ---
class ToxicityDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = float(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'labels': torch.tensor(label, dtype=torch.float)
        }


def load_jigsaw_data(dataset_path: str, sample_size: Optional[int] = None):
    """Load and prepare Jigsaw dataset for transformer training."""
    import pandas as pd
    
    logger.info(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    
    if sample_size:
        logger.info(f"Sampling {sample_size} examples...")
        df = df.sample(n=min(sample_size, len(df)), random_state=42)
    
    # Binary label: any toxicity > 0 is toxic
    df['toxic_any'] = (
        (df['toxic'] > 0) | 
        (df['severe_toxic'] > 0) | 
        (df['obscene'] > 0) | 
        (df['threat'] > 0) | 
        (df['insult'] > 0) | 
        (df['identity_hate'] > 0)
    ).astype(int)
    
    texts = df['comment_text'].values
    labels = df['toxic_any'].values
    
    # Train/val split
    split_idx = int(0.9 * len(texts))
    train_texts, val_texts = texts[:split_idx], texts[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]
    
    logger.info(f"Loaded {len(train_texts)} training, {len(val_texts)} validation examples")
    logger.info(f"Toxic: {train_labels.sum()} ({train_labels.mean()*100:.1f}%)")
    
    return (train_texts, train_labels), (val_texts, val_labels)


def train_epoch(model, dataloader, optimizer, scheduler, device, pos_weight):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    
    for batch_idx, batch in enumerate(dataloader):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)
        
        optimizer.zero_grad()
        
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits.squeeze(-1)
        loss = loss_fn(logits, labels)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        
        total_loss += loss.item()
        
        if (batch_idx + 1) % 100 == 0:
            logger.info(f"  Batch {batch_idx+1}/{len(dataloader)}, Loss: {loss.item():.4f}")
    
    return total_loss / len(dataloader)


def evaluate(model, dataloader, device):
    """Evaluate model."""
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].cpu().numpy()
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits.squeeze(-1).cpu().numpy()
            probs = 1 / (1 + np.exp(-logits))
            
            all_preds.extend(probs)
            all_labels.extend(labels)
    
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    # Metrics
    roc_auc = roc_auc_score(all_labels, all_preds)
    pr_auc = average_precision_score(all_labels, all_preds)
    
    preds_binary = (all_preds >= 0.5).astype(int)
    f1 = f1_score(all_labels, preds_binary)
    mcc = matthews_corrcoef(all_labels, preds_binary)
    
    return {
        'roc_auc': roc_auc,
        'pr_auc': pr_auc,
        'f1': f1,
        'mcc': mcc,
    }


def train_transformer_model(
    model_name: str = DEFAULT_MODEL,
    dataset_path: str = "datasets_raw/train.csv",
    output_path: str = "models/transformer_toxicity.pkl",
    max_length: int = DEFAULT_MAX_LENGTH,
    batch_size: int = DEFAULT_BATCH_SIZE,
    epochs: int = DEFAULT_EPOCHS,
    lr: float = DEFAULT_LR,
    sample_size: Optional[int] = None,
):
    """Train a lightweight transformer model for toxicity detection."""
    
    logger.info("="*80)
    logger.info("🤖 TRAINING TRANSFORMER MODEL")
    logger.info("="*80)
    logger.info(f"Model: {model_name} ({SUPPORTED_MODELS.get(model_name, model_name)})")
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Batch size: {batch_size}, Epochs: {epochs}, LR: {lr}")
    
    # Device
    if torch.cuda.is_available():
        device = torch.device('cuda')
        logger.info("✓ Using CUDA GPU")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
        logger.info("✓ Using Apple Silicon MPS")
    else:
        device = torch.device('cpu')
        logger.info("⚠ Using CPU (training will be slow)")
    
    # Load data
    (train_texts, train_labels), (val_texts, val_labels) = load_jigsaw_data(
        dataset_path, sample_size=sample_size
    )
    
    # Tokenizer
    model_id = SUPPORTED_MODELS.get(model_name, model_name)
    logger.info(f"\n📥 Loading tokenizer: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Datasets
    train_dataset = ToxicityDataset(train_texts, train_labels, tokenizer, max_length)
    val_dataset = ToxicityDataset(val_texts, val_labels, tokenizer, max_length)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size * 2, shuffle=False)
    
    # Model
    logger.info(f"\n🤖 Loading model: {model_id}")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_id,
        num_labels=1,
        problem_type="regression"
    )
    model.to(device)
    
    # Optimizer & scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps
    )
    
    # Class weight for imbalance
    pos_count = train_labels.sum()
    neg_count = len(train_labels) - pos_count
    pos_weight = torch.tensor([neg_count / pos_count], dtype=torch.float).to(device)
    logger.info(f"Positive weight: {pos_weight.item():.2f}")
    
    # Training loop
    logger.info("\n🎓 Training...")
    start_time = time.time()
    best_roc_auc = 0
    
    for epoch in range(epochs):
        logger.info(f"\nEpoch {epoch+1}/{epochs}")
        
        # Train
        train_loss = train_epoch(model, train_loader, optimizer, scheduler, device, pos_weight)
        logger.info(f"  Train Loss: {train_loss:.4f}")
        
        # Evaluate
        metrics = evaluate(model, val_loader, device)
        logger.info(f"  Val ROC-AUC: {metrics['roc_auc']:.4f}, PR-AUC: {metrics['pr_auc']:.4f}, F1: {metrics['f1']:.4f}, MCC: {metrics['mcc']:.4f}")
        
        # Save best
        if metrics['roc_auc'] > best_roc_auc:
            best_roc_auc = metrics['roc_auc']
            logger.info(f"  ✓ New best ROC-AUC: {best_roc_auc:.4f}")
    
    training_time = time.time() - start_time
    logger.info(f"\n⏱️  Total training time: {training_time:.1f}s ({training_time/60:.1f}min)")
    
    # Save model
    logger.info(f"\n💾 Saving model to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save as pickle (compatible with existing pipeline)
    model_data = {
        'model': model.cpu().state_dict(),
        'tokenizer': tokenizer,
        'model_name': model_id,
        'max_length': max_length,
        'metadata': {
            'trained_on': time.strftime("%Y-%m-%d %H:%M:%S"),
            'training_time_s': training_time,
            'dataset': dataset_path,
            'num_examples': len(train_texts),
            'best_roc_auc': best_roc_auc,
            'model_type': 'transformer',
        }
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    model_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"  ✓ Model saved ({model_size_mb:.1f} MB)")
    
    logger.info("\n✅ Training complete!")
    logger.info("="*80)
    
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train lightweight transformer for toxicity")
    parser.add_argument("--model", choices=list(SUPPORTED_MODELS.keys()), default=DEFAULT_MODEL,
                        help=f"Model to train (default: {DEFAULT_MODEL})")
    parser.add_argument("--dataset", default="datasets_raw/train.csv",
                        help="Path to training dataset")
    parser.add_argument("--output", default="models/transformer_toxicity.pkl",
                        help="Path to save trained model")
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH,
                        help="Max sequence length")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="Training batch size")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=DEFAULT_LR,
                        help="Learning rate")
    parser.add_argument("--sample", type=int, default=None,
                        help="Sample N examples for quick testing")
    
    args = parser.parse_args()
    
    train_transformer_model(
        model_name=args.model,
        dataset_path=args.dataset,
        output_path=args.output,
        max_length=args.max_length,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        sample_size=args.sample,
    )












