#!/usr/bin/env python3
"""
AEGIS Federation Network
Gossip protocol for antibody sharing across deployments

Privacy-preserving antibody exchange with reputation system.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yaml

# Configuration
FEDERATION_DB = Path("data/federation.yaml")
ANTIBODY_CACHE = Path("data/antibody_cache.yaml")
MAX_ANTIBODY_AGE_DAYS = 30
MIN_REPUTATION_SCORE = 0.6


@dataclass
class Antibody:
    """Shared antibody pattern"""
    pattern: str
    confidence: float
    category: str
    seen_count: int
    false_positive_count: int
    false_negative_count: int
    created_at: str
    source_node: str
    antibody_id: str
    reputation_score: float = 1.0
    upvotes: int = 0
    downvotes: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Antibody':
        return cls(**data)
    
    def calculate_reputation(self) -> float:
        """Calculate reputation score based on accuracy"""
        total_predictions = self.seen_count
        if total_predictions == 0:
            return 1.0
        
        # Base score from accuracy
        accuracy = 1.0 - (self.false_positive_count / total_predictions)
        
        # Boost from community votes
        vote_score = 1.0
        total_votes = self.upvotes + self.downvotes
        if total_votes > 0:
            vote_score = (self.upvotes / total_votes)
        
        # Weighted combination
        reputation = (accuracy * 0.7) + (vote_score * 0.3)
        
        # Penalty for high FP rate
        if self.false_positive_count > (total_predictions * 0.1):
            reputation *= 0.5
        
        return round(reputation, 3)
    
    def is_expired(self) -> bool:
        """Check if antibody is too old"""
        created = datetime.fromisoformat(self.created_at)
        age = datetime.now() - created
        return age.days > MAX_ANTIBODY_AGE_DAYS


class FederationNetwork:
    """Manages antibody sharing across deployments"""
    
    def __init__(self, node_id: str = "local"):
        self.node_id = node_id
        self.federation_db = FEDERATION_DB
        self.antibody_cache = ANTIBODY_CACHE
        self.load()
    
    def load(self):
        """Load federation database"""
        if self.federation_db.exists():
            with open(self.federation_db, 'r') as f:
                data = yaml.safe_load(f)
                self.nodes = data.get('nodes', {})
                self.antibodies = {
                    ab_id: Antibody.from_dict(ab_data)
                    for ab_id, ab_data in data.get('antibodies', {}).items()
                }
        else:
            self.nodes = {}
            self.antibodies = {}
        
        # Register self
        if self.node_id not in self.nodes:
            self.nodes[self.node_id] = {
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'antibodies_shared': 0,
                'antibodies_received': 0,
                'reputation': 1.0
            }
    
    def save(self):
        """Save federation database"""
        self.federation_db.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'nodes': self.nodes,
            'antibodies': {
                ab_id: ab.to_dict()
                for ab_id, ab in self.antibodies.items()
            },
            'statistics': {
                'total_nodes': len(self.nodes),
                'total_antibodies': len(self.antibodies),
                'active_antibodies': sum(1 for ab in self.antibodies.values() if not ab.is_expired()),
                'avg_reputation': round(sum(ab.reputation_score for ab in self.antibodies.values()) / len(self.antibodies), 3) if self.antibodies else 0.0
            }
        }
        
        with open(self.federation_db, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def generate_antibody_id(self, pattern: str, category: str) -> str:
        """Generate unique ID for antibody"""
        content = f"{pattern}:{category}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def submit_antibody(
        self,
        pattern: str,
        confidence: float,
        category: str,
        seen_count: int = 1,
        false_positive_count: int = 0,
        false_negative_count: int = 0
    ) -> Dict[str, Any]:
        """Submit new antibody to federation"""
        
        # Check if antibody already exists
        for ab_id, ab in self.antibodies.items():
            if ab.pattern == pattern and ab.category == category:
                # Update existing antibody
                ab.seen_count += seen_count
                ab.false_positive_count += false_positive_count
                ab.false_negative_count += false_negative_count
                ab.confidence = max(ab.confidence, confidence)
                ab.reputation_score = ab.calculate_reputation()
                
                self.save()
                return {
                    'status': 'updated',
                    'antibody_id': ab_id,
                    'reputation': ab.reputation_score,
                    'message': 'Antibody updated with new data'
                }
        
        # Create new antibody
        antibody_id = self.generate_antibody_id(pattern, category)
        
        antibody = Antibody(
            pattern=pattern,
            confidence=confidence,
            category=category,
            seen_count=seen_count,
            false_positive_count=false_positive_count,
            false_negative_count=false_negative_count,
            created_at=datetime.now().isoformat(),
            source_node=self.node_id,
            antibody_id=antibody_id
        )
        
        antibody.reputation_score = antibody.calculate_reputation()
        
        self.antibodies[antibody_id] = antibody
        self.nodes[self.node_id]['antibodies_shared'] += 1
        self.nodes[self.node_id]['last_seen'] = datetime.now().isoformat()
        
        self.save()
        
        return {
            'status': 'created',
            'antibody_id': antibody_id,
            'reputation': antibody.reputation_score,
            'message': 'New antibody shared with federation'
        }
    
    def upvote_antibody(self, antibody_id: str) -> Dict[str, Any]:
        """Upvote an antibody (worked well)"""
        if antibody_id not in self.antibodies:
            return {'status': 'error', 'message': 'Antibody not found'}
        
        ab = self.antibodies[antibody_id]
        ab.upvotes += 1
        ab.reputation_score = ab.calculate_reputation()
        
        self.save()
        
        return {
            'status': 'success',
            'antibody_id': antibody_id,
            'upvotes': ab.upvotes,
            'reputation': ab.reputation_score
        }
    
    def downvote_antibody(self, antibody_id: str, reason: str = "false_positive") -> Dict[str, Any]:
        """Downvote an antibody (false positive or ineffective)"""
        if antibody_id not in self.antibodies:
            return {'status': 'error', 'message': 'Antibody not found'}
        
        ab = self.antibodies[antibody_id]
        ab.downvotes += 1
        
        if reason == "false_positive":
            ab.false_positive_count += 1
        elif reason == "false_negative":
            ab.false_negative_count += 1
        
        ab.reputation_score = ab.calculate_reputation()
        
        self.save()
        
        return {
            'status': 'success',
            'antibody_id': antibody_id,
            'downvotes': ab.downvotes,
            'reputation': ab.reputation_score,
            'reason': reason
        }
    
    def get_validated_antibodies(
        self,
        min_reputation: float = MIN_REPUTATION_SCORE,
        category: Optional[str] = None,
        include_expired: bool = False
    ) -> List[Antibody]:
        """Get antibodies above reputation threshold"""
        validated = []
        
        for antibody in self.antibodies.values():
            # Skip expired
            if not include_expired and antibody.is_expired():
                continue
            
            # Check reputation
            if antibody.reputation_score < min_reputation:
                continue
            
            # Filter by category
            if category and antibody.category != category:
                continue
            
            validated.append(antibody)
        
        # Sort by reputation (highest first)
        validated.sort(key=lambda x: x.reputation_score, reverse=True)
        
        return validated
    
    def sync_with_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync antibodies from another node (gossip protocol)"""
        node_id = node_data.get('node_id')
        node_antibodies = node_data.get('antibodies', [])
        
        if not node_id:
            return {'status': 'error', 'message': 'No node_id provided'}
        
        # Register node if new
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'antibodies_shared': 0,
                'antibodies_received': 0,
                'reputation': 1.0
            }
        
        self.nodes[node_id]['last_seen'] = datetime.now().isoformat()
        
        # Import antibodies
        imported = 0
        updated = 0
        rejected = 0
        
        for ab_data in node_antibodies:
            ab = Antibody.from_dict(ab_data)
            
            # Validate reputation
            if ab.reputation_score < MIN_REPUTATION_SCORE:
                rejected += 1
                continue
            
            # Check if exists
            if ab.antibody_id in self.antibodies:
                # Update if newer/better data
                existing = self.antibodies[ab.antibody_id]
                if ab.seen_count > existing.seen_count:
                    self.antibodies[ab.antibody_id] = ab
                    updated += 1
            else:
                # Import new antibody
                self.antibodies[ab.antibody_id] = ab
                imported += 1
        
        self.nodes[node_id]['antibodies_received'] += imported
        self.nodes[self.node_id]['antibodies_received'] += imported
        
        self.save()
        
        return {
            'status': 'success',
            'node_id': node_id,
            'imported': imported,
            'updated': updated,
            'rejected': rejected,
            'message': f'Synced {imported + updated} antibodies from {node_id}'
        }
    
    def export_antibodies_for_sync(
        self,
        min_reputation: float = MIN_REPUTATION_SCORE
    ) -> Dict[str, Any]:
        """Export antibodies for sharing with other nodes"""
        validated = self.get_validated_antibodies(min_reputation=min_reputation)
        
        return {
            'node_id': self.node_id,
            'timestamp': datetime.now().isoformat(),
            'antibodies': [ab.to_dict() for ab in validated],
            'node_stats': self.nodes.get(self.node_id, {})
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get federation statistics"""
        active_antibodies = [ab for ab in self.antibodies.values() if not ab.is_expired()]
        
        return {
            'total_nodes': len(self.nodes),
            'total_antibodies': len(self.antibodies),
            'active_antibodies': len(active_antibodies),
            'expired_antibodies': len(self.antibodies) - len(active_antibodies),
            'avg_reputation': round(
                sum(ab.reputation_score for ab in active_antibodies) / len(active_antibodies), 3
            ) if active_antibodies else 0.0,
            'categories': {
                category: sum(1 for ab in active_antibodies if ab.category == category)
                for category in set(ab.category for ab in active_antibodies)
            },
            'node_id': self.node_id,
            'node_stats': self.nodes.get(self.node_id, {})
        }
    
    def prune_expired_antibodies(self) -> int:
        """Remove expired antibodies"""
        expired = [ab_id for ab_id, ab in self.antibodies.items() if ab.is_expired()]
        
        for ab_id in expired:
            del self.antibodies[ab_id]
        
        if expired:
            self.save()
        
        return len(expired)
    
    def prune_low_reputation_antibodies(self, threshold: float = 0.3) -> int:
        """Remove antibodies with very low reputation"""
        low_rep = [
            ab_id for ab_id, ab in self.antibodies.items()
            if ab.reputation_score < threshold and ab.seen_count > 10
        ]
        
        for ab_id in low_rep:
            del self.antibodies[ab_id]
        
        if low_rep:
            self.save()
        
        return len(low_rep)


def main():
    """CLI for federation management"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python federation.py stats")
        print("  python federation.py submit <pattern> <category> <confidence>")
        print("  python federation.py list [category]")
        print("  python federation.py upvote <antibody_id>")
        print("  python federation.py downvote <antibody_id> [reason]")
        print("  python federation.py export")
        print("  python federation.py prune")
        sys.exit(1)
    
    federation = FederationNetwork()
    command = sys.argv[1]
    
    if command == 'stats':
        stats = federation.get_statistics()
        print("\n🔗 AEGIS Federation Statistics\n")
        print(f"Total Nodes: {stats['total_nodes']}")
        print(f"Total Antibodies: {stats['total_antibodies']}")
        print(f"Active Antibodies: {stats['active_antibodies']}")
        print(f"Expired Antibodies: {stats['expired_antibodies']}")
        print(f"Average Reputation: {stats['avg_reputation']:.3f}")
        print(f"\nCategories:")
        for cat, count in stats['categories'].items():
            print(f"  • {cat}: {count}")
        print(f"\nNode ID: {stats['node_id']}")
    
    elif command == 'submit':
        if len(sys.argv) < 5:
            print("Error: python federation.py submit <pattern> <category> <confidence>")
            sys.exit(1)
        
        pattern = sys.argv[2]
        category = sys.argv[3]
        confidence = float(sys.argv[4])
        
        result = federation.submit_antibody(pattern, confidence, category)
        print(f"\n✅ {result['message']}")
        print(f"Antibody ID: {result['antibody_id']}")
        print(f"Reputation: {result['reputation']:.3f}")
    
    elif command == 'list':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        antibodies = federation.get_validated_antibodies(category=category)
        
        print(f"\n🛡️  Validated Antibodies ({len(antibodies)})\n")
        for ab in antibodies[:20]:  # Show top 20
            print(f"ID: {ab.antibody_id}")
            print(f"  Pattern: {ab.pattern}")
            print(f"  Category: {ab.category}")
            print(f"  Confidence: {ab.confidence:.2f}")
            print(f"  Reputation: {ab.reputation_score:.3f} ({ab.upvotes}↑ {ab.downvotes}↓)")
            print(f"  Seen: {ab.seen_count} times | FP: {ab.false_positive_count}")
            print()
    
    elif command == 'upvote':
        if len(sys.argv) < 3:
            print("Error: python federation.py upvote <antibody_id>")
            sys.exit(1)
        
        ab_id = sys.argv[2]
        result = federation.upvote_antibody(ab_id)
        print(f"✅ {result.get('message', 'Upvoted')}")
        print(f"Reputation: {result.get('reputation', 0):.3f}")
    
    elif command == 'downvote':
        if len(sys.argv) < 3:
            print("Error: python federation.py downvote <antibody_id> [reason]")
            sys.exit(1)
        
        ab_id = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else "false_positive"
        result = federation.downvote_antibody(ab_id, reason)
        print(f"✅ Downvoted ({reason})")
        print(f"Reputation: {result.get('reputation', 0):.3f}")
    
    elif command == 'export':
        export = federation.export_antibodies_for_sync()
        print(json.dumps(export, indent=2))
    
    elif command == 'prune':
        expired = federation.prune_expired_antibodies()
        low_rep = federation.prune_low_reputation_antibodies()
        print(f"\n🗑️  Pruned {expired} expired antibodies")
        print(f"🗑️  Pruned {low_rep} low-reputation antibodies")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()












