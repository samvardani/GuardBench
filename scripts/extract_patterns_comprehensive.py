#!/usr/bin/env python3
"""
Comprehensive Pattern Extraction from Multiple Datasets

This script extracts high-quality patterns from:
1. Davidson Hate Speech (24K examples)
2. ToxiGen (274K examples)  
3. Jigsaw (159K examples)

Goal: Expand from 100+ to 500+ patterns while maintaining low FPR.

Strategy:
1. Extract frequent toxic n-grams (1-3 words)
2. Filter by toxicity ratio (toxic/total)
3. Remove common safe words
4. Generate regex patterns
5. Validate against safe corpus
"""

import re
import sys
import json
import pickle
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

# --- Configuration ---
DATASETS_DIR = Path("datasets_raw")
OUTPUT_DIR = Path("extracted_patterns")
MIN_TOXICITY_RATIO = 0.7  # Pattern must appear in 70%+ toxic contexts
MIN_OCCURRENCES = 5  # Pattern must appear at least 5 times
MAX_PATTERNS_PER_CATEGORY = 150  # Cap per category
SAFE_WORD_THRESHOLD = 0.3  # Words appearing in >30% safe text are excluded

# Categories
CATEGORIES = {
    "violence": ["kill", "murder", "shoot", "stab", "attack", "harm", "hurt", "destroy"],
    "harassment": ["hate", "stupid", "idiot", "loser", "scum", "trash", "worthless"],
    "sexual": ["rape", "sex", "fuck", "porn", "molest", "abuse"],
    "self_harm": ["suicide", "kill myself", "end my life", "want to die"],
    "threat": ["will kill", "going to", "i'll get you", "watch out"],
}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def clean_text(text: str) -> str:
    """Clean and normalize text."""
    text = str(text).lower()
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'@\w+', '', text)  # Remove mentions
    text = re.sub(r'[^a-z\s]', ' ', text)  # Keep only letters and spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_ngrams(text: str, n: int) -> List[str]:
    """Extract n-grams from text."""
    words = text.split()
    return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

def is_safe_word(word: str) -> bool:
    """Check if word is a common safe word."""
    safe_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may',
        'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
        'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
        'me', 'him', 'us', 'them', 'what', 'which', 'who', 'when', 'where', 'why',
        'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'just', 'about', 'like', 'from', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'well',
        'also', 'even', 'still', 'get', 'got', 'getting', 'go', 'going', 'gone',
        'make', 'made', 'making', 'take', 'took', 'taking', 'see', 'saw', 'seeing',
        'know', 'knew', 'knowing', 'think', 'thought', 'thinking', 'want', 'wanted',
        'wanting', 'need', 'needed', 'needing', 'feel', 'felt', 'feeling', 'work',
        'worked', 'working', 'say', 'said', 'saying', 'tell', 'told', 'telling',
        'use', 'used', 'using', 'find', 'found', 'finding', 'give', 'gave', 'giving',
        'take', 'took', 'taking', 'come', 'came', 'coming', 'look', 'looked', 'looking',
    }
    return word in safe_words

def categorize_pattern(pattern: str) -> str:
    """Categorize pattern based on keywords."""
    pattern_lower = pattern.lower()
    
    # Check each category
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in pattern_lower:
                return category
    
    # Default to harassment if contains common insults
    insult_indicators = ['you', 'your', 'are', 'is', 'people', 'all', 'should']
    if any(ind in pattern_lower for ind in insult_indicators):
        return "harassment"
    
    return "general"

# --- Dataset Loaders ---
def load_davidson() -> Tuple[List[str], List[str]]:
    """Load Davidson hate speech dataset."""
    logger.info("Loading Davidson dataset...")
    try:
        df = pd.read_csv(DATASETS_DIR / "hate_speech_davidson.csv")
        # class: 0 = hate speech, 1 = offensive, 2 = neither
        toxic = df[df['class'].isin([0, 1])]['tweet'].tolist()
        safe = df[df['class'] == 2]['tweet'].tolist()
        logger.info(f"  Davidson: {len(toxic)} toxic, {len(safe)} safe")
        return toxic, safe
    except Exception as e:
        logger.warning(f"  Failed to load Davidson: {e}")
        return [], []

def load_toxigen() -> Tuple[List[str], List[str]]:
    """Load ToxiGen dataset."""
    logger.info("Loading ToxiGen dataset...")
    try:
        toxic, safe = [], []
        # ToxiGen is in various formats, try to load text files
        toxigen_dir = DATASETS_DIR / "ToxiGen"
        if toxigen_dir.exists():
            for file in toxigen_dir.glob("*.txt"):
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Assume all are toxic for now
                    toxic.extend([line.strip() for line in lines if line.strip()])
        
        # Also try the main file
        main_file = DATASETS_DIR / "toxigen_all.txt"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                toxic.extend([line.strip() for line in lines if line.strip()])
        
        logger.info(f"  ToxiGen: {len(toxic)} toxic, {len(safe)} safe")
        return toxic, safe
    except Exception as e:
        logger.warning(f"  Failed to load ToxiGen: {e}")
        return [], []

def load_jigsaw() -> Tuple[List[str], List[str]]:
    """Load Jigsaw dataset."""
    logger.info("Loading Jigsaw dataset...")
    try:
        df = pd.read_csv(DATASETS_DIR / "train.csv")
        # Any toxicity column > 0.5 is toxic
        toxic_mask = (df['toxic'] > 0.5) | (df['severe_toxic'] > 0.5) | \
                     (df['obscene'] > 0.5) | (df['threat'] > 0.5) | \
                     (df['insult'] > 0.5) | (df['identity_hate'] > 0.5)
        toxic = df[toxic_mask]['comment_text'].tolist()
        safe = df[~toxic_mask]['comment_text'].sample(n=min(10000, len(df[~toxic_mask])), random_state=42)['comment_text'].tolist()
        logger.info(f"  Jigsaw: {len(toxic)} toxic, {len(safe)} safe")
        return toxic, safe
    except Exception as e:
        logger.warning(f"  Failed to load Jigsaw: {e}")
        return [], []

# --- Pattern Extraction ---
def extract_patterns_from_datasets() -> Dict[str, List[Tuple[str, float, int]]]:
    """
    Extract patterns from all datasets.
    
    Returns:
        Dict mapping category to list of (pattern, toxicity_ratio, count) tuples
    """
    logger.info("="*80)
    logger.info("EXTRACTING PATTERNS FROM DATASETS")
    logger.info("="*80)
    
    # Load all datasets
    davidson_toxic, davidson_safe = load_davidson()
    toxigen_toxic, toxigen_safe = load_toxigen()
    jigsaw_toxic, jigsaw_safe = load_jigsaw()
    
    # Combine
    all_toxic = davidson_toxic + toxigen_toxic + jigsaw_toxic
    all_safe = davidson_safe + toxigen_safe + jigsaw_safe
    
    logger.info(f"\nTotal: {len(all_toxic)} toxic, {len(all_safe)} safe examples")
    
    # Clean texts
    logger.info("\nCleaning texts...")
    toxic_texts = [clean_text(t) for t in all_toxic if t]
    safe_texts = [clean_text(s) for s in all_safe if s]
    
    # Extract n-grams
    logger.info("\nExtracting n-grams...")
    toxic_ngrams = Counter()
    safe_ngrams = Counter()
    
    for text in toxic_texts:
        for n in [1, 2, 3]:  # 1-gram, 2-gram, 3-gram
            for ngram in extract_ngrams(text, n):
                if not is_safe_word(ngram):
                    toxic_ngrams[ngram] += 1
    
    for text in safe_texts:
        for n in [1, 2, 3]:
            for ngram in extract_ngrams(text, n):
                if not is_safe_word(ngram):
                    safe_ngrams[ngram] += 1
    
    logger.info(f"  Found {len(toxic_ngrams)} unique toxic n-grams")
    logger.info(f"  Found {len(safe_ngrams)} unique safe n-grams")
    
    # Calculate toxicity ratios
    logger.info("\nCalculating toxicity ratios...")
    pattern_scores = []
    
    for ngram, toxic_count in toxic_ngrams.items():
        if toxic_count < MIN_OCCURRENCES:
            continue
        
        safe_count = safe_ngrams.get(ngram, 0)
        total_count = toxic_count + safe_count
        toxicity_ratio = toxic_count / total_count if total_count > 0 else 0
        
        if toxicity_ratio >= MIN_TOXICITY_RATIO:
            # Filter out very common safe words in toxic contexts
            if safe_count / max(len(safe_texts), 1) < SAFE_WORD_THRESHOLD:
                pattern_scores.append((ngram, toxicity_ratio, toxic_count))
    
    # Sort by toxicity ratio, then by count
    pattern_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    logger.info(f"  Found {len(pattern_scores)} high-quality patterns")
    
    # Categorize patterns
    logger.info("\nCategorizing patterns...")
    categorized_patterns = defaultdict(list)
    
    for pattern, ratio, count in pattern_scores:
        category = categorize_pattern(pattern)
        if len(categorized_patterns[category]) < MAX_PATTERNS_PER_CATEGORY:
            categorized_patterns[category].append((pattern, ratio, count))
    
    # Print summary
    logger.info("\nPattern Distribution:")
    for category, patterns in sorted(categorized_patterns.items()):
        logger.info(f"  {category:15} {len(patterns):4} patterns")
    
    total_patterns = sum(len(p) for p in categorized_patterns.values())
    logger.info(f"\nTotal extracted: {total_patterns} patterns")
    
    return dict(categorized_patterns)

# --- Pattern to Regex ---
def pattern_to_regex(pattern: str) -> str:
    """Convert pattern to regex with word boundaries."""
    # Escape special regex characters
    escaped = re.escape(pattern)
    # Add word boundaries
    return r'\b' + escaped + r'\b'

# --- Save Patterns ---
def save_patterns(categorized_patterns: Dict[str, List[Tuple[str, float, int]]]):
    """Save extracted patterns to files."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    logger.info("\nSaving patterns...")
    
    # Save as JSON
    json_output = {}
    for category, patterns in categorized_patterns.items():
        json_output[category] = [
            {
                "pattern": p,
                "regex": pattern_to_regex(p),
                "toxicity_ratio": float(ratio),
                "count": int(count)
            }
            for p, ratio, count in patterns
        ]
    
    json_path = OUTPUT_DIR / "extracted_patterns.json"
    with open(json_path, 'w') as f:
        json.dump(json_output, f, indent=2)
    logger.info(f"  Saved JSON to {json_path}")
    
    # Save as Python dict for easy import
    py_path = OUTPUT_DIR / "extracted_patterns.py"
    with open(py_path, 'w') as f:
        f.write("# Auto-generated pattern file\n")
        f.write("# Generated: " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
        f.write("EXTRACTED_PATTERNS = {\n")
        for category, patterns in categorized_patterns.items():
            f.write(f"    '{category}': [\n")
            for pattern, ratio, count in patterns[:50]:  # Top 50 per category
                regex = pattern_to_regex(pattern)
                f.write(f"        r'{regex}',  # {pattern} (ratio={ratio:.2f}, n={count})\n")
            f.write("    ],\n")
        f.write("}\n")
    logger.info(f"  Saved Python to {py_path}")
    
    # Save detailed CSV for analysis
    csv_path = OUTPUT_DIR / "extracted_patterns.csv"
    rows = []
    for category, patterns in categorized_patterns.items():
        for pattern, ratio, count in patterns:
            rows.append({
                'category': category,
                'pattern': pattern,
                'regex': pattern_to_regex(pattern),
                'toxicity_ratio': ratio,
                'count': count,
            })
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    logger.info(f"  Saved CSV to {csv_path}")
    
    # Print top patterns per category
    logger.info("\nTop 10 patterns per category:")
    for category, patterns in sorted(categorized_patterns.items()):
        logger.info(f"\n  {category.upper()}:")
        for i, (pattern, ratio, count) in enumerate(patterns[:10], 1):
            logger.info(f"    {i:2}. '{pattern}' (ratio={ratio:.2f}, n={count})")

# --- Main ---
def main():
    logger.info("\n" + "="*80)
    logger.info("COMPREHENSIVE PATTERN EXTRACTION")
    logger.info("="*80)
    logger.info("\nGoal: Extract 500+ high-quality patterns from:")
    logger.info("  • Davidson (24K examples)")
    logger.info("  • ToxiGen (274K examples)")
    logger.info("  • Jigsaw (159K examples)")
    logger.info("")
    
    # Extract patterns
    categorized_patterns = extract_patterns_from_datasets()
    
    # Save patterns
    save_patterns(categorized_patterns)
    
    logger.info("\n" + "="*80)
    logger.info("✅ PATTERN EXTRACTION COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nOutput directory: {OUTPUT_DIR}")
    logger.info("Files created:")
    logger.info("  • extracted_patterns.json (all patterns with metadata)")
    logger.info("  • extracted_patterns.py (Python import)")
    logger.info("  • extracted_patterns.csv (analysis)")
    logger.info("\nNext steps:")
    logger.info("  1. Review extracted patterns in CSV")
    logger.info("  2. Validate against safe corpus")
    logger.info("  3. Integrate into policy.yaml")
    logger.info("  4. Test with: pytest tests/ -k pattern")
    logger.info("")

if __name__ == "__main__":
    main()












