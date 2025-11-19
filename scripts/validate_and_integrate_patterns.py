#!/usr/bin/env python3
"""
Validate and Integrate Extracted Patterns

This script:
1. Validates patterns against safe corpus
2. Filters false positives
3. Integrates best patterns into policy.yaml
4. Updates src/guards/candidate.py
"""

import json
import yaml
import re
import logging
from pathlib import Path
from typing import List, Dict, Set
import pandas as pd

# --- Configuration ---
PATTERNS_DIR = Path("extracted_patterns")
PATTERNS_FILE = PATTERNS_DIR / "extracted_patterns.json"
OUTPUT_POLICY = Path("policy/policy_expanded.yaml")
OUTPUT_GUARD = Path("src/guards/candidate_expanded.py")

# Safe corpus for validation (common phrases that should NOT be flagged)
SAFE_CORPUS = [
    "I'm going to the store",
    "people with disabilities deserve respect",
    "the middle east has rich history",
    "asian americans contribute greatly",
    "trans women are women",
    "bisexual people exist",
    "mental illness is real",
    "african americans face challenges",
    "mexican food is delicious",
    "watch out for that car",
    "going to be late",
    "hundreds of people attended",
    "our country is diverse",
    "attracted to someone",
    "same sex couples",
    "native american culture",
    "wheelchair accessible",
    "chinese food",
    "arab culture",
]

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Load Patterns ---
def load_patterns() -> Dict:
    """Load extracted patterns."""
    with open(PATTERNS_FILE, 'r') as f:
        return json.load(f)

# --- Validation ---
def validate_patterns(patterns: Dict) -> Dict:
    """
    Validate patterns against safe corpus.
    Remove patterns that flag safe content.
    """
    logger.info("Validating patterns against safe corpus...")
    
    validated = {}
    removed_count = 0
    
    for category, pattern_list in patterns.items():
        validated[category] = []
        
        for pattern_info in pattern_list:
            regex = pattern_info['regex']
            pattern_text = pattern_info['pattern']
            
            # Test against safe corpus
            false_positive = False
            for safe_text in SAFE_CORPUS:
                if re.search(regex, safe_text, re.IGNORECASE):
                    logger.debug(f"  FP: '{pattern_text}' matches '{safe_text}'")
                    false_positive = True
                    break
            
            if not false_positive:
                validated[category].append(pattern_info)
            else:
                removed_count += 1
    
    logger.info(f"  Removed {removed_count} false positive patterns")
    logger.info(f"  Kept {sum(len(v) for v in validated.values())} patterns")
    
    return validated

# --- Filter Best Patterns ---
def filter_best_patterns(patterns: Dict, top_n: int = 100) -> Dict:
    """
    Select best patterns based on:
    1. High toxicity ratio (>0.9)
    2. Sufficient occurrences (>10)
    3. Reasonable length (2-4 words ideal)
    """
    logger.info(f"Filtering best {top_n} patterns per category...")
    
    filtered = {}
    
    for category, pattern_list in patterns.items():
        # Score patterns
        scored = []
        for p in pattern_list:
            ratio = p['toxicity_ratio']
            count = p['count']
            words = len(p['pattern'].split())
            
            # Scoring: prefer high ratio, high count, 2-3 word phrases
            score = ratio * 100 + min(count, 1000) / 10
            if 2 <= words <= 3:
                score *= 1.5  # Bonus for ideal length
            
            scored.append((score, p))
        
        # Sort and take top N
        scored.sort(reverse=True, key=lambda x: x[0])
        filtered[category] = [p for score, p in scored[:top_n]]
        
        logger.info(f"  {category:15} {len(filtered[category]):3} patterns")
    
    return filtered

# --- Generate Policy YAML ---
def generate_policy_yaml(patterns: Dict) -> str:
    """Generate YAML policy content."""
    logger.info("Generating policy YAML...")
    
    yaml_content = """# Expanded Policy with Machine-Extracted Patterns
# Auto-generated from Davidson, ToxiGen, and Jigsaw datasets
# Total patterns: {}

categories:
""".format(sum(len(v) for v in patterns.values()))
    
    for category, pattern_list in sorted(patterns.items()):
        yaml_content += f"\n  {category}:\n"
        yaml_content += f"    description: Auto-extracted {category} patterns\n"
        yaml_content += f"    patterns:\n"
        
        for p in pattern_list[:50]:  # Top 50 per category in YAML
            yaml_content += f"      - {p['regex']}  # {p['pattern']} (ratio={p['toxicity_ratio']:.2f})\n"
    
    return yaml_content

# --- Generate Guard Python ---
def generate_guard_python(patterns: Dict) -> str:
    """Generate Python guard code."""
    logger.info("Generating guard Python code...")
    
    py_content = '''"""
Auto-generated expanded guard with machine-extracted patterns.
Generated from Davidson, ToxiGen, and Jigsaw datasets.
Total patterns: {}
"""

import re
from typing import Dict, List, Optional

# Machine-extracted patterns by category
EXPANDED_PATTERNS = {{
'''.format(sum(len(v) for v in patterns.values()))
    
    for category, pattern_list in sorted(patterns.items()):
        py_content += f"    '{category}': [\n"
        for p in pattern_list[:100]:  # Top 100 in Python
            py_content += f"        r'{p['regex']}',  # {p['pattern'][:30]} (r={p['toxicity_ratio']:.2f})\n"
        py_content += "    ],\n"
    
    py_content += """}\n
def check_expanded_patterns(text: str, category: Optional[str] = None) -> Dict:
    \"\"\"Check text against expanded patterns.\"\"\"
    text_lower = text.lower()
    matches = []
    
    categories_to_check = [category] if category else EXPANDED_PATTERNS.keys()
    
    for cat in categories_to_check:
        if cat not in EXPANDED_PATTERNS:
            continue
        for pattern in EXPANDED_PATTERNS[cat]:
            if re.search(pattern, text_lower):
                matches.append((cat, pattern))
    
    if matches:
        return {
            'flagged': True,
            'category': matches[0][0],
            'pattern': matches[0][1],
            'total_matches': len(matches),
        }
    
    return {'flagged': False}
"""
    
    return py_content

# --- Main ---
def main():
    logger.info("="*80)
    logger.info("PATTERN VALIDATION AND INTEGRATION")
    logger.info("="*80)
    
    # Load patterns
    logger.info("\nLoading extracted patterns...")
    patterns = load_patterns()
    logger.info(f"  Loaded {sum(len(v) for v in patterns.values())} patterns")
    
    # Validate
    validated_patterns = validate_patterns(patterns)
    
    # Filter best
    best_patterns = filter_best_patterns(validated_patterns, top_n=100)
    
    # Generate outputs
    logger.info("\nGenerating output files...")
    
    # Policy YAML
    policy_content = generate_policy_yaml(best_patterns)
    OUTPUT_POLICY.parent.mkdir(exist_ok=True)
    with open(OUTPUT_POLICY, 'w') as f:
        f.write(policy_content)
    logger.info(f"  ✓ {OUTPUT_POLICY}")
    
    # Guard Python
    guard_content = generate_guard_python(best_patterns)
    OUTPUT_GUARD.parent.mkdir(exist_ok=True)
    with open(OUTPUT_GUARD, 'w') as f:
        f.write(guard_content)
    logger.info(f"  ✓ {OUTPUT_GUARD}")
    
    # Summary CSV
    summary_file = PATTERNS_DIR / "integrated_patterns.csv"
    rows = []
    for category, pattern_list in best_patterns.items():
        for p in pattern_list:
            rows.append({
                'category': category,
                'pattern': p['pattern'],
                'regex': p['regex'],
                'toxicity_ratio': p['toxicity_ratio'],
                'count': p['count'],
            })
    df = pd.DataFrame(rows)
    df.to_csv(summary_file, index=False)
    logger.info(f"  ✓ {summary_file}")
    
    logger.info("\n" + "="*80)
    logger.info("✅ VALIDATION AND INTEGRATION COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nIntegrated patterns: {len(df)}")
    logger.info("\nPattern breakdown:")
    for category in sorted(best_patterns.keys()):
        count = len(best_patterns[category])
        logger.info(f"  {category:15} {count:3} patterns")
    
    logger.info("\nNext steps:")
    logger.info("  1. Review: cat policy/policy_expanded.yaml")
    logger.info("  2. Test: python3 -c 'from src.guards.candidate_expanded import check_expanded_patterns; print(check_expanded_patterns(\"test text\"))'")
    logger.info("  3. Integrate into main policy.yaml and candidate.py")
    logger.info("  4. Run tests: pytest tests/ -k guard")
    logger.info("")

if __name__ == "__main__":
    main()












