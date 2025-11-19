#!/usr/bin/env python3
"""
AEGIS Federation Demo
Demonstrates antibody sharing across multiple nodes using gossip protocol
"""

import requests
import time
import json
from typing import Dict, List

API_BASE = "http://localhost:8001"


class FederationClient:
    """Client for interacting with federation API"""
    
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
    
    def submit_antibody(self, pattern: str, confidence: float, category: str, **kwargs) -> Dict:
        """Submit new antibody to federation"""
        payload = {
            "pattern": pattern,
            "confidence": confidence,
            "category": category,
            **kwargs
        }
        
        response = requests.post(f"{self.base_url}/federation/intel-exchange", json=payload)
        return response.json()
    
    def upvote(self, antibody_id: str) -> Dict:
        """Upvote an antibody"""
        response = requests.post(
            f"{self.base_url}/federation/upvote",
            json={"antibody_id": antibody_id}
        )
        return response.json()
    
    def downvote(self, antibody_id: str, reason: str = "false_positive") -> Dict:
        """Downvote an antibody"""
        response = requests.post(
            f"{self.base_url}/federation/downvote",
            json={"antibody_id": antibody_id, "reason": reason}
        )
        return response.json()
    
    def get_antibodies(self, category: str = None, min_reputation: float = 0.6) -> Dict:
        """Get validated antibodies"""
        params = {"min_reputation": min_reputation}
        if category:
            params["category"] = category
        
        response = requests.get(f"{self.base_url}/federation/antibodies", params=params)
        return response.json()
    
    def get_antibody(self, antibody_id: str) -> Dict:
        """Get specific antibody details"""
        response = requests.get(f"{self.base_url}/federation/antibodies/{antibody_id}")
        return response.json()
    
    def get_statistics(self) -> Dict:
        """Get federation statistics"""
        response = requests.get(f"{self.base_url}/federation/statistics")
        return response.json()
    
    def export_antibodies(self, min_reputation: float = 0.6) -> Dict:
        """Export antibodies for sharing"""
        response = requests.get(
            f"{self.base_url}/federation/export",
            params={"min_reputation": min_reputation}
        )
        return response.json()
    
    def sync_with_node(self, node_data: Dict) -> Dict:
        """Sync antibodies from another node"""
        response = requests.post(f"{self.base_url}/federation/sync", json=node_data)
        return response.json()
    
    def prune(self) -> Dict:
        """Prune expired/low-reputation antibodies"""
        response = requests.post(f"{self.base_url}/federation/prune")
        return response.json()


def demo_basic_submission():
    """Demo 1: Submit antibodies"""
    print("\n" + "="*70)
    print("DEMO 1: Basic Antibody Submission")
    print("="*70 + "\n")
    
    client = FederationClient()
    
    # Submit test antibodies
    test_antibodies = [
        ("k[i1!]ll\\s+y[o0]u", 0.85, "violence"),
        ("h[0o]w\\s+t[0o]\\s+h[a4]ck", 0.75, "illegal"),
        ("you\\s+are\\s+st[u\\*]+pid", 0.70, "harassment"),
    ]
    
    antibody_ids = []
    
    for pattern, confidence, category in test_antibodies:
        print(f"📤 Submitting: {pattern} ({category})")
        result = client.submit_antibody(pattern, confidence, category)
        
        if result['success']:
            ab_id = result['data']['antibody_id']
            reputation = result['data']['reputation']
            antibody_ids.append(ab_id)
            print(f"   ✅ {result['data']['status']}: {ab_id}")
            print(f"   Reputation: {reputation:.3f}\n")
        else:
            print(f"   ❌ Error\n")
    
    return antibody_ids


def demo_voting_system(antibody_ids: List[str]):
    """Demo 2: Upvote/Downvote antibodies"""
    print("\n" + "="*70)
    print("DEMO 2: Reputation System (Voting)")
    print("="*70 + "\n")
    
    client = FederationClient()
    
    if not antibody_ids:
        print("⚠️  No antibodies to vote on")
        return
    
    # Upvote first antibody (good detection)
    print(f"👍 Upvoting antibody: {antibody_ids[0]}")
    result = client.upvote(antibody_ids[0])
    if result['success']:
        print(f"   ✅ Upvotes: {result['data']['upvotes']}")
        print(f"   Reputation: {result['data']['reputation']:.3f}\n")
    
    # Upvote again (simulate multiple deployments agreeing)
    print(f"👍 Upvoting again: {antibody_ids[0]}")
    result = client.upvote(antibody_ids[0])
    if result['success']:
        print(f"   ✅ Upvotes: {result['data']['upvotes']}")
        print(f"   Reputation: {result['data']['reputation']:.3f}\n")
    
    # Downvote second antibody (false positive)
    if len(antibody_ids) > 1:
        print(f"👎 Downvoting antibody (false positive): {antibody_ids[1]}")
        result = client.downvote(antibody_ids[1], reason="false_positive")
        if result['success']:
            print(f"   ✅ Downvotes: {result['data']['downvotes']}")
            print(f"   Reputation: {result['data']['reputation']:.3f}\n")


def demo_get_validated_antibodies():
    """Demo 3: Retrieve validated antibodies"""
    print("\n" + "="*70)
    print("DEMO 3: Get Validated Antibodies")
    print("="*70 + "\n")
    
    client = FederationClient()
    
    result = client.get_antibodies(min_reputation=0.5)
    
    if result['success']:
        print(f"Found {result['count']} validated antibodies:\n")
        
        for ab in result['antibodies'][:5]:  # Show top 5
            print(f"  🛡️  {ab['antibody_id'][:12]}...")
            print(f"     Pattern: {ab['pattern']}")
            print(f"     Category: {ab['category']}")
            print(f"     Confidence: {ab['confidence']:.2f}")
            print(f"     Reputation: {ab['reputation_score']:.3f}")
            print(f"     Votes: {ab['upvotes']}↑ {ab['downvotes']}↓")
            print(f"     Seen: {ab['seen_count']} times")
            print()


def demo_gossip_protocol():
    """Demo 4: Simulate gossip protocol between nodes"""
    print("\n" + "="*70)
    print("DEMO 4: Gossip Protocol (Node Synchronization)")
    print("="*70 + "\n")
    
    client = FederationClient()
    
    # Node A exports its antibodies
    print("📤 Node A: Exporting antibodies for sharing...")
    export_result = client.export_antibodies(min_reputation=0.6)
    
    if export_result['success']:
        export_data = export_result['data']
        antibody_count = len(export_data['antibodies'])
        print(f"   ✅ Exported {antibody_count} antibodies")
        print(f"   Node ID: {export_data['node_id']}\n")
        
        # Simulate Node B receiving and syncing
        print("📥 Node B: Syncing with Node A's antibodies...")
        
        # In real gossip protocol, this would be automated
        # For demo, we show the manual sync
        sync_result = client.sync_with_node({
            "node_id": "node_b_demo",
            "antibodies": export_data['antibodies']
        })
        
        if sync_result['success']:
            data = sync_result['data']
            print(f"   ✅ Sync complete:")
            print(f"      Imported: {data['imported']}")
            print(f"      Updated: {data['updated']}")
            print(f"      Rejected: {data['rejected']}")
            print(f"      {data['message']}\n")


def demo_statistics():
    """Demo 5: Federation statistics"""
    print("\n" + "="*70)
    print("DEMO 5: Federation Statistics")
    print("="*70 + "\n")
    
    client = FederationClient()
    
    result = client.get_statistics()
    
    if result['success']:
        stats = result['statistics']
        
        print(f"Total Nodes: {stats['total_nodes']}")
        print(f"Total Antibodies: {stats['total_antibodies']}")
        print(f"Active Antibodies: {stats['active_antibodies']}")
        print(f"Expired Antibodies: {stats['expired_antibodies']}")
        print(f"Average Reputation: {stats['avg_reputation']:.3f}")
        print(f"\nCategories:")
        for category, count in stats.get('categories', {}).items():
            print(f"  • {category}: {count}")
        print(f"\nNode ID: {stats['node_id']}")


def demo_privacy_features():
    """Demo 6: Privacy-preserving features"""
    print("\n" + "="*70)
    print("DEMO 6: Privacy-Preserving Features")
    print("="*70 + "\n")
    
    print("🔒 Privacy Guarantees:")
    print("   1. Only regex patterns are shared (no raw text)")
    print("   2. No user data leaves your deployment")
    print("   3. Patterns are anonymized (source node ID only)")
    print("   4. Reputation scores prevent spam/malicious patterns")
    print()
    
    client = FederationClient()
    
    # Show example of what gets shared
    result = client.get_antibodies(min_reputation=0.7)
    
    if result['success'] and result['antibodies']:
        ab = result['antibodies'][0]
        print("Example of shared data:")
        print(f"  Pattern: {ab['pattern']}")
        print(f"  Category: {ab['category']}")
        print(f"  Confidence: {ab['confidence']}")
        print(f"  Source: {ab['source_node']} (anonymized node ID)")
        print()
        print("❌ NOT shared: Raw text, user IDs, URLs, IP addresses")
        print()


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("AEGIS FEDERATION NETWORK DEMO")
    print("Gossip Protocol for Antibody Sharing")
    print("="*70)
    
    try:
        # Check if API is running
        response = requests.get(f"{API_BASE}/federation/health")
        if response.status_code != 200:
            print("\n❌ Error: API not responding")
            print(f"   Make sure the API is running on {API_BASE}")
            print(f"   Command: uvicorn src.service.api:app --reload --port 8001\n")
            return
        
        print("✅ API is running\n")
        
        # Run demos
        antibody_ids = demo_basic_submission()
        time.sleep(0.5)
        
        demo_voting_system(antibody_ids)
        time.sleep(0.5)
        
        demo_get_validated_antibodies()
        time.sleep(0.5)
        
        demo_gossip_protocol()
        time.sleep(0.5)
        
        demo_statistics()
        time.sleep(0.5)
        
        demo_privacy_features()
        
        print("\n" + "="*70)
        print("✅ All demos complete!")
        print("="*70 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API")
        print(f"   Make sure the API is running on {API_BASE}")
        print(f"   Command: uvicorn src.service.api:app --reload --port 8001\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()












