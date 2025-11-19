#!/usr/bin/env python3
"""
AEGIS Pattern Generator v0
Automatically generates regex patterns from novel attacks detected by T-cells
"""

import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import Counter

# Configuration
QUARANTINE_FILE = Path("data/quarantine.yaml")
POLICY_FILE = Path("policy/policy.yaml")
MIN_CONFIDENCE = 0.75
AUTO_PROMOTE_COUNT = 10


class PatternGenerator:
    """Generates regex patterns from obfuscated/novel text"""
    
    # Common character substitutions (leetspeak)
    SUBSTITUTIONS = {
        'a': '[a4@]',
        'e': '[e3]',
        'i': '[i1!l]',
        'o': '[o0]',
        's': '[s5$]',
        't': '[t7+]',
        'l': '[l1!i]',
        'g': '[g9]',
        'b': '[b8]',
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text by removing obfuscation"""
        text = text.lower()
        # Replace common substitutions
        text = re.sub(r'[4@]', 'a', text)
        text = re.sub(r'[3€]', 'e', text)
        text = re.sub(r'[1!]', 'i', text)
        text = re.sub(r'[0]', 'o', text)
        text = re.sub(r'[5$]', 's', text)
        text = re.sub(r'[7+]', 't', text)
        return text
    
    @staticmethod
    def extract_core_pattern(text: str) -> str:
        """Extract core pattern from text with obfuscation"""
        text = text.lower()
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    @classmethod
    def generate_regex(cls, text: str) -> str:
        """Generate flexible regex pattern from text"""
        normalized = cls.normalize_text(text)
        words = normalized.split()
        
        pattern_parts = []
        for word in words:
            word_pattern = ''
            for char in word:
                if char in cls.SUBSTITUTIONS:
                    word_pattern += cls.SUBSTITUTIONS[char]
                elif char.isalnum():
                    word_pattern += char
                else:
                    word_pattern += re.escape(char)
            pattern_parts.append(word_pattern)
        
        # Join with flexible whitespace
        pattern = r'\s+'.join(pattern_parts)
        # Add word boundaries
        pattern = r'\b' + pattern + r'\b'
        return pattern
    
    @staticmethod
    def calculate_confidence(text: str, seen_count: int) -> float:
        """Calculate confidence score for pattern"""
        base_confidence = 0.6
        
        # Boost if seen multiple times
        frequency_boost = min(seen_count * 0.05, 0.2)
        
        # Boost if has obfuscation markers
        obfuscation_markers = sum([
            bool(re.search(r'[0-9]', text)),  # Numbers as letters
            bool(re.search(r'[!@#$%^&*]', text)),  # Special chars
            bool(re.search(r'[A-Z]{2,}', text)),  # Mixed case
        ])
        obfuscation_boost = obfuscation_markers * 0.05
        
        # Boost if contains known harmful keywords
        harmful_keywords = ['kill', 'hack', 'hurt', 'attack', 'threat', 'bomb', 'weapon']
        keyword_boost = 0
        text_lower = text.lower()
        for keyword in harmful_keywords:
            if keyword in text_lower:
                keyword_boost = 0.1
                break
        
        confidence = min(base_confidence + frequency_boost + obfuscation_boost + keyword_boost, 0.95)
        return round(confidence, 2)
    
    @staticmethod
    def categorize_pattern(text: str) -> str:
        """Categorize pattern based on content"""
        text_lower = text.lower()
        
        # Violence keywords
        if any(kw in text_lower for kw in ['kill', 'murder', 'shoot', 'stab', 'attack', 'hurt', 'weapon', 'bomb']):
            return 'violence'
        
        # Harassment keywords
        if any(kw in text_lower for kw in ['hate', 'stupid', 'idiot', 'loser', 'worthless', 'ugly']):
            return 'harassment'
        
        # Self-harm keywords
        if any(kw in text_lower for kw in ['suicide', 'self harm', 'cut myself', 'end it', 'die']):
            return 'self_harm'
        
        # Illegal/hacking keywords
        if any(kw in text_lower for kw in ['hack', 'crack', 'steal', 'phish', 'malware', 'exploit']):
            return 'illegal'
        
        # Sexual keywords
        if any(kw in text_lower for kw in ['sex', 'porn', 'nude', 'rape', 'molest']):
            return 'sexual'
        
        # Spam keywords
        if any(kw in text_lower for kw in ['buy', 'cheap', 'discount', 'offer', 'click here']):
            return 'spam'
        
        return 'unknown'


class QuarantineManager:
    """Manages quarantine list and promotions"""
    
    def __init__(self, quarantine_file: Path = QUARANTINE_FILE):
        self.quarantine_file = quarantine_file
        self.data = self.load()
    
    def load(self) -> Dict:
        """Load quarantine list"""
        if not self.quarantine_file.exists():
            return {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'quarantine_rules': [],
                'statistics': {
                    'total_quarantined': 0,
                    'promoted_to_policy': 0,
                    'rejected': 0,
                    'pending_review': 0
                },
                'auto_promote_threshold': AUTO_PROMOTE_COUNT,
                'auto_reject_threshold': 5,
                'confidence_threshold': MIN_CONFIDENCE
            }
        
        with open(self.quarantine_file, 'r') as f:
            return yaml.safe_load(f)
    
    def save(self):
        """Save quarantine list"""
        self.data['last_updated'] = datetime.now().isoformat()
        with open(self.quarantine_file, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)
    
    def add_pattern(self, text: str, category: Optional[str] = None) -> Dict:
        """Add new pattern to quarantine"""
        generator = PatternGenerator()
        
        pattern = generator.generate_regex(text)
        normalized = generator.normalize_text(text)
        
        # Check if pattern already exists
        for rule in self.data['quarantine_rules']:
            if rule['pattern'] == pattern:
                rule['seen_count'] += 1
                rule['confidence'] = generator.calculate_confidence(text, rule['seen_count'])
                self.save()
                return rule
        
        # Create new rule
        if not category:
            category = generator.categorize_pattern(text)
        
        confidence = generator.calculate_confidence(text, 1)
        
        new_rule = {
            'pattern': pattern,
            'confidence': confidence,
            'category': category,
            'first_seen': datetime.now().isoformat(),
            'seen_count': 1,
            'notes': f"Auto-generated from: '{text[:50]}...'",
            'status': 'pending_review',
            'normalized_example': normalized
        }
        
        self.data['quarantine_rules'].append(new_rule)
        self.data['statistics']['total_quarantined'] += 1
        self.data['statistics']['pending_review'] += 1
        self.save()
        
        return new_rule
    
    def get_promotable_patterns(self) -> List[Dict]:
        """Get patterns ready for promotion to policy"""
        threshold = self.data.get('auto_promote_threshold', AUTO_PROMOTE_COUNT)
        confidence_min = self.data.get('confidence_threshold', MIN_CONFIDENCE)
        
        promotable = []
        for rule in self.data['quarantine_rules']:
            if (rule['status'] == 'pending_review' and 
                rule['seen_count'] >= threshold and 
                rule['confidence'] >= confidence_min):
                promotable.append(rule)
        
        return promotable
    
    def promote_to_policy(self, pattern: str) -> bool:
        """Promote pattern from quarantine to main policy"""
        # Find rule in quarantine
        rule_to_promote = None
        for i, rule in enumerate(self.data['quarantine_rules']):
            if rule['pattern'] == pattern:
                rule_to_promote = rule
                rule_index = i
                break
        
        if not rule_to_promote:
            return False
        
        # Load policy
        with open(POLICY_FILE, 'r') as f:
            policy = yaml.safe_load(f)
        
        # Find appropriate category slice
        category = rule_to_promote['category']
        found_slice = False
        
        for slice_def in policy.get('slices', []):
            if slice_def.get('category') == category:
                # Add pattern to rules
                new_rule = {
                    'pattern': rule_to_promote['pattern'],
                    'severity': 'high' if rule_to_promote['confidence'] > 0.85 else 'medium',
                    'description': rule_to_promote['notes']
                }
                slice_def.setdefault('rules', []).append(new_rule)
                found_slice = True
                break
        
        if not found_slice:
            print(f"⚠️  Category '{category}' not found in policy, skipping promotion")
            return False
        
        # Save updated policy
        with open(POLICY_FILE, 'w') as f:
            yaml.dump(policy, f, default_flow_style=False, sort_keys=False)
        
        # Update quarantine
        self.data['quarantine_rules'][rule_index]['status'] = 'promoted'
        self.data['statistics']['promoted_to_policy'] += 1
        self.data['statistics']['pending_review'] -= 1
        self.save()
        
        print(f"✅ Promoted pattern to policy: {pattern}")
        return True
    
    def list_quarantine(self):
        """List all quarantined patterns"""
        print("\n🔒 AEGIS Quarantine List\n")
        print(f"Total: {self.data['statistics']['total_quarantined']}")
        print(f"Pending Review: {self.data['statistics']['pending_review']}")
        print(f"Promoted: {self.data['statistics']['promoted_to_policy']}")
        print(f"Rejected: {self.data['statistics']['rejected']}\n")
        
        for i, rule in enumerate(self.data['quarantine_rules']):
            status_icon = {
                'pending_review': '⏳',
                'promoted': '✅',
                'rejected': '❌'
            }.get(rule['status'], '❓')
            
            print(f"{i+1}. {status_icon} [{rule['category']}] Confidence: {rule['confidence']:.2f}")
            print(f"   Pattern: {rule['pattern']}")
            print(f"   Seen: {rule['seen_count']} times | First: {rule['first_seen'][:10]}")
            print(f"   Notes: {rule['notes'][:80]}")
            print()


def main():
    """CLI for AEGIS pattern generator"""
    import sys
    
    manager = QuarantineManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python aegis_pattern_generator.py list")
        print("  python aegis_pattern_generator.py add 'h0w t0 h4ck'")
        print("  python aegis_pattern_generator.py promote")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        manager.list_quarantine()
    
    elif command == 'add':
        if len(sys.argv) < 3:
            print("Error: Provide text to add")
            sys.exit(1)
        
        text = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else None
        
        rule = manager.add_pattern(text, category)
        print(f"✅ Added to quarantine:")
        print(f"   Pattern: {rule['pattern']}")
        print(f"   Category: {rule['category']}")
        print(f"   Confidence: {rule['confidence']}")
        print(f"   Seen: {rule['seen_count']} times")
    
    elif command == 'promote':
        promotable = manager.get_promotable_patterns()
        
        if not promotable:
            print("No patterns ready for promotion")
            print(f"(Need {manager.data.get('auto_promote_threshold', 10)} confirmations)")
            sys.exit(0)
        
        print(f"Found {len(promotable)} patterns ready for promotion:\n")
        for rule in promotable:
            print(f"  • [{rule['category']}] {rule['pattern']}")
            print(f"    Confidence: {rule['confidence']}, Seen: {rule['seen_count']} times")
        
        print("\nPromoting patterns...")
        for rule in promotable:
            manager.promote_to_policy(rule['pattern'])
    
    elif command == 'test':
        # Test pattern generation
        test_texts = [
            "h0w t0 h4ck a w3bs1te",
            "I w1ll k!ll y0u",
            "buy ch34p v14gr4",
            "th1s 1s 4 t3st"
        ]
        
        generator = PatternGenerator()
        print("\n🧪 Testing Pattern Generation\n")
        
        for text in test_texts:
            pattern = generator.generate_regex(text)
            category = generator.categorize_pattern(text)
            confidence = generator.calculate_confidence(text, 1)
            normalized = generator.normalize_text(text)
            
            print(f"Input: '{text}'")
            print(f"  Normalized: '{normalized}'")
            print(f"  Pattern: {pattern}")
            print(f"  Category: {category}")
            print(f"  Confidence: {confidence}")
            print()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()












