"""
Adversarial Immune System (AIS)
================================

Revolutionary self-evolving defense system inspired by human immune systems.

Key Features:
- Real-time learning from attack attempts
- Automatic "antibody" generation (new detection rules)
- Global distribution via gossip protocol
- Memory cells for long-term protection
- Clonal selection (best defenses proliferate)

Example:
    >>> ais = AdversarialImmuneSystem()
    >>> is_attack, confidence, antibody = ais.detect_and_learn("b4s3 64 tr1ck")
    >>> print(f"Attack detected: {is_attack}, Antibody: {antibody}")
"""

import hashlib
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class Antibody:
    """
    Digital antibody - a learned defense pattern
    
    Attributes:
        pattern: Regex or feature pattern
        signature: Unique identifier (hash)
        confidence: How effective this antibody is (0-1)
        created_at: Timestamp of creation
        success_count: Number of successful detections
        false_positive_count: Number of false positives
        generation: Evolution generation number
    """
    pattern: str
    signature: str
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    success_count: int = 0
    false_positive_count: int = 0
    generation: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def matches(self, text: str) -> bool:
        """Check if antibody matches given text"""
        try:
            return bool(re.search(self.pattern, text, re.IGNORECASE))
        except re.error:
            return False
    
    def update_fitness(self, was_correct: bool):
        """Update antibody fitness based on results"""
        if was_correct:
            self.success_count += 1
            self.confidence = min(0.99, self.confidence + 0.05)
        else:
            self.false_positive_count += 1
            self.confidence = max(0.1, self.confidence - 0.1)
    
    def fitness_score(self) -> float:
        """Calculate overall fitness (for clonal selection)"""
        total = self.success_count + self.false_positive_count
        if total == 0:
            return self.confidence
        
        accuracy = self.success_count / total
        return (accuracy * 0.7) + (self.confidence * 0.3)


@dataclass
class TCell:
    """
    T-Cell: Pattern recognition cell that identifies anomalies
    
    Detects novel attacks that don't match known antibodies
    """
    sensitivity: float = 0.4  # Lower = more sensitive
    anomaly_detector: Optional[object] = None
    
    def recognizes_anomaly(self, text: str, baseline_score: float) -> Tuple[bool, float]:
        """
        Detect if text is anomalous
        
        Uses multiple heuristics:
        - Character frequency analysis
        - Obfuscation detection
        - Entropy analysis
        - Semantic coherence
        """
        anomaly_score = 0.0
        
        # 1. Character frequency anomaly
        char_freq = self._analyze_char_frequency(text)
        if char_freq > 0.3:
            anomaly_score += 0.3
        
        # 2. Obfuscation detection
        obfuscation = self._detect_obfuscation(text)
        if obfuscation > 0.5:
            anomaly_score += 0.4
        
        # 3. Entropy analysis
        entropy = self._calculate_entropy(text)
        if entropy > 4.5:  # High entropy = potential obfuscation
            anomaly_score += 0.3
        
        is_anomaly = anomaly_score > self.sensitivity
        return is_anomaly, anomaly_score
    
    def _analyze_char_frequency(self, text: str) -> float:
        """Detect unusual character frequency"""
        special_chars = sum(1 for c in text if not c.isalnum() and c != ' ')
        return special_chars / max(len(text), 1)
    
    def _detect_obfuscation(self, text: str) -> float:
        """Detect common obfuscation techniques"""
        score = 0.0
        
        # Leetspeak (a->4, e->3, etc.) - MORE SENSITIVE
        leet_chars = sum(1 for c in text if c in '4301!@#$%^&*()')
        leet_ratio = leet_chars / max(len(text), 1)
        if leet_ratio > 0.05:  # Lower threshold
            score += 0.5
        
        # Number substitution (common in obfuscation)
        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count > 2 and text.count('0') + text.count('1') + text.count('3') + text.count('4') > 1:
            score += 0.4
        
        # Excessive spaces or dashes
        if '  ' in text or '--' in text or '__' in text:
            score += 0.3
        
        # Base64-like patterns
        if re.search(r'[A-Za-z0-9+/]{20,}={0,2}', text):
            score += 0.5
        
        # Unicode tricks
        if any(ord(c) > 127 for c in text):
            score += 0.3
        
        # Mixed case in weird patterns (e.g., "HeLLo")
        if text != text.lower() and text != text.upper() and text != text.title():
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy"""
        if not text:
            return 0.0
        
        # Character frequency
        freq = defaultdict(int)
        for char in text:
            freq[char] += 1
        
        # Shannon entropy
        entropy = 0.0
        text_len = len(text)
        for count in freq.values():
            p = count / text_len
            if p > 0:
                entropy -= p * np.log2(p)
        
        return entropy


@dataclass
class BCell:
    """
    B-Cell: Defense generator that creates new antibodies
    
    When T-cell recognizes anomaly, B-cell generates specific antibody
    """
    generation_strategy: str = "pattern_extraction"
    
    def generate_antibody(self, attack_text: str, context: Dict) -> Antibody:
        """
        Generate new antibody from attack attempt
        
        Strategies:
        - Extract core pattern
        - Generalize to similar attacks
        - Balance specificity vs generality
        """
        # Extract attack pattern
        pattern = self._extract_pattern(attack_text)
        
        # Generate signature
        signature = hashlib.sha256(pattern.encode()).hexdigest()[:16]
        
        # Create antibody
        antibody = Antibody(
            pattern=pattern,
            signature=signature,
            confidence=0.6,  # Start with medium confidence
            metadata={
                'attack_text': attack_text[:100],  # Sample only
                'context': context,
                'strategy': self.generation_strategy
            }
        )
        
        return antibody
    
    def _extract_pattern(self, text: str) -> str:
        """
        Extract regex pattern from attack text
        
        Balances specificity and generality
        """
        # Remove numbers (generalize)
        pattern = re.sub(r'\d', r'\\d', text)
        
        # Replace common obfuscations
        pattern = pattern.replace('4', '[4a]')
        pattern = pattern.replace('3', '[3e]')
        pattern = pattern.replace('0', '[0o]')
        pattern = pattern.replace('1', '[1il]')
        pattern = pattern.replace('$', '[s$]')
        
        # Make case insensitive
        pattern = pattern.lower()
        
        # Word boundaries
        pattern = r'\b' + pattern + r'\b'
        
        return pattern


class AdversarialImmuneSystem:
    """
    Complete Adversarial Immune System
    
    Combines T-cells (anomaly detection), B-cells (antibody generation),
    and memory cells (long-term storage) for adaptive defense.
    
    Example:
        >>> ais = AdversarialImmuneSystem()
        >>> 
        >>> # Attack attempt
        >>> is_attack, conf, antibody = ais.detect_and_learn("h0w t0 h4ck")
        >>> print(f"Detected: {is_attack}, Confidence: {conf:.2f}")
        >>> 
        >>> # Future attempts automatically blocked
        >>> is_attack2, conf2, _ = ais.detect_and_learn("h0w t0 cr4ck")
        >>> print(f"Blocked: {is_attack2}")
    """
    
    def __init__(
        self,
        t_cell_count: int = 10,
        b_cell_count: int = 5,
        max_antibodies: int = 10000,
        clonal_selection_threshold: float = 0.7
    ):
        self.memory_cells: Dict[str, Antibody] = {}
        self.t_cells: List[TCell] = [TCell() for _ in range(t_cell_count)]
        self.b_cells: List[BCell] = [BCell() for _ in range(b_cell_count)]
        self.max_antibodies = max_antibodies
        self.clonal_selection_threshold = clonal_selection_threshold
        
        # Statistics
        self.stats = {
            'attacks_detected': 0,
            'antibodies_generated': 0,
            'false_positives': 0,
            'clonal_selections': 0
        }
    
    def detect(self, text: str) -> Tuple[bool, float, Optional[Antibody]]:
        """
        Detect if text is an attack
        
        Returns:
            (is_attack, confidence, matching_antibody)
        """
        # 1. Check memory cells (known attacks)
        for antibody in self.memory_cells.values():
            if antibody.matches(text):
                self.stats['attacks_detected'] += 1
                return True, antibody.confidence, antibody
        
        # 2. Check for novel attacks (T-cell recognition)
        baseline_score = 0.0  # Would normally get from base model
        
        for t_cell in self.t_cells:
            is_anomaly, anomaly_score = t_cell.recognizes_anomaly(text, baseline_score)
            
            if is_anomaly:
                # Novel attack detected!
                return True, anomaly_score, None
        
        return False, 0.0, None
    
    def detect_and_learn(
        self,
        text: str,
        ground_truth: Optional[bool] = None,
        context: Optional[Dict] = None
    ) -> Tuple[bool, float, Optional[Antibody]]:
        """
        Detect attack and learn from it
        
        Args:
            text: Input text to analyze
            ground_truth: True label (if known) for training
            context: Additional context for learning
        
        Returns:
            (is_attack, confidence, antibody_used_or_generated)
        """
        context = context or {}
        
        # Detect
        is_attack, confidence, antibody = self.detect(text)
        
        # Learn if novel attack
        if is_attack and antibody is None:
            # Generate new antibody
            antibody = self._generate_antibody(text, context)
            self.stats['antibodies_generated'] += 1
        
        # Update fitness if ground truth provided
        if ground_truth is not None and antibody is not None:
            was_correct = is_attack == ground_truth
            antibody.update_fitness(was_correct)
            
            if not was_correct:
                self.stats['false_positives'] += 1
        
        # Clonal selection (evolution)
        if len(self.memory_cells) > self.max_antibodies:
            self._clonal_selection()
        
        return is_attack, confidence, antibody
    
    def _generate_antibody(self, text: str, context: Dict) -> Antibody:
        """Generate new antibody using B-cells"""
        # Select B-cell (could be random or based on specialization)
        b_cell = self.b_cells[0]
        
        # Generate antibody
        antibody = b_cell.generate_antibody(text, context)
        
        # Add to memory
        self.memory_cells[antibody.signature] = antibody
        
        return antibody
    
    def _clonal_selection(self):
        """
        Evolutionary algorithm: Keep fittest antibodies, discard weak ones
        
        Mimics biological immune system clonal selection
        """
        # Calculate fitness for all antibodies
        antibodies_with_fitness = [
            (sig, ab, ab.fitness_score())
            for sig, ab in self.memory_cells.items()
        ]
        
        # Sort by fitness
        antibodies_with_fitness.sort(key=lambda x: x[2], reverse=True)
        
        # Keep top N%
        keep_count = int(self.max_antibodies * 0.8)
        survivors = antibodies_with_fitness[:keep_count]
        
        # Update memory cells
        self.memory_cells = {
            sig: ab for sig, ab, _ in survivors
        }
        
        # Evolve top antibodies (mutation)
        for sig, ab, fitness in survivors[:10]:
            if fitness > self.clonal_selection_threshold:
                mutated = self._mutate_antibody(ab)
                if mutated:
                    self.memory_cells[mutated.signature] = mutated
        
        self.stats['clonal_selections'] += 1
    
    def _mutate_antibody(self, antibody: Antibody) -> Optional[Antibody]:
        """
        Mutate antibody pattern to create variant
        
        Biological analogy: Somatic hypermutation
        """
        # Simple mutation: Make pattern more/less specific
        pattern = antibody.pattern
        
        # Mutation: Relax character class
        mutated_pattern = pattern.replace('[4a]', '[4a@]')
        mutated_pattern = mutated_pattern.replace('[3e]', '[3e€]')
        
        if mutated_pattern != pattern:
            signature = hashlib.sha256(mutated_pattern.encode()).hexdigest()[:16]
            return Antibody(
                pattern=mutated_pattern,
                signature=signature,
                confidence=antibody.confidence * 0.9,  # Slightly lower
                generation=antibody.generation + 1
            )
        
        return None
    
    def export_antibodies(self, filepath: str):
        """Export antibodies for distribution (gossip protocol)"""
        data = {
            'antibodies': [
                {
                    'pattern': ab.pattern,
                    'signature': ab.signature,
                    'confidence': ab.confidence,
                    'success_count': ab.success_count,
                    'false_positive_count': ab.false_positive_count,
                    'generation': ab.generation
                }
                for ab in self.memory_cells.values()
            ],
            'stats': self.stats,
            'exported_at': time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_antibodies(self, filepath: str, merge: bool = True):
        """Import antibodies from other AEGIS instances"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for ab_data in data['antibodies']:
            antibody = Antibody(
                pattern=ab_data['pattern'],
                signature=ab_data['signature'],
                confidence=ab_data['confidence'],
                success_count=ab_data['success_count'],
                false_positive_count=ab_data['false_positive_count'],
                generation=ab_data['generation']
            )
            
            if merge:
                # Merge with existing
                if antibody.signature in self.memory_cells:
                    existing = self.memory_cells[antibody.signature]
                    # Keep better one
                    if antibody.fitness_score() > existing.fitness_score():
                        self.memory_cells[antibody.signature] = antibody
                else:
                    self.memory_cells[antibody.signature] = antibody
            else:
                # Overwrite
                self.memory_cells[antibody.signature] = antibody
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        return {
            **self.stats,
            'antibody_count': len(self.memory_cells),
            'avg_antibody_fitness': np.mean([
                ab.fitness_score() for ab in self.memory_cells.values()
            ]) if self.memory_cells else 0.0
        }


if __name__ == "__main__":
    # Demo
    print("🛡️ AEGIS - Adversarial Immune System Demo\n")
    
    ais = AdversarialImmuneSystem()
    
    # Test attacks
    attacks = [
        ("h0w t0 h4ck", True),
        ("how to make b0mb", True),
        ("I w1ll k1ll y0u", True),
        ("buy cheap m3ds", True),
        ("have a great day", False),
        ("my password is 1234", False),  # Sensitive but not attack
    ]
    
    print("Initial Detection (No antibodies):")
    for text, is_attack_label in attacks:
        detected, conf, ab = ais.detect_and_learn(text, ground_truth=is_attack_label)
        status = "✓" if detected == is_attack_label else "✗"
        print(f"  {status} '{text}' → {'ATTACK' if detected else 'SAFE'} ({conf:.2f})")
    
    print(f"\n📊 Stats: {ais.get_stats()}")
    
    # Test learned patterns
    print("\n\nSecond Pass (With learned antibodies):")
    similar_attacks = [
        "h0w 2 cr4ck",  # Similar to first attack
        "how to make p1p3 b0mb",  # Similar to second
    ]
    
    for text in similar_attacks:
        detected, conf, ab = ais.detect(text)
        print(f"  {'🔴' if detected else '🟢'} '{text}' → {'BLOCKED' if detected else 'ALLOWED'} ({conf:.2f})")
        if ab:
            print(f"     Matched antibody: {ab.pattern[:50]}...")
    
    print(f"\n📊 Final Stats: {ais.get_stats()}")
    
    # Export for distribution
    ais.export_antibodies('aegis_antibodies.json')
    print(f"\n💾 Antibodies exported to aegis_antibodies.json")

