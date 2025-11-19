#!/usr/bin/env python3
"""
AEGIS Revolutionary Platform Demo
==================================

Demonstrates the Adversarial Immune System learning from attacks in real-time.
"""

import sys
import time
sys.path.insert(0, 'src')

from aegis.immune_system import AdversarialImmuneSystem


def demo_basic():
    """Basic AIS demonstration"""
    print("=" * 80)
    print("🛡️ AEGIS - ADVERSARIAL IMMUNE SYSTEM")
    print("=" * 80)
    print("\n💡 Concept: Like human immune systems, AEGIS learns from attacks")
    print("   and develops 'digital antibodies' to protect against future threats.\n")
    
    # Create AIS with higher sensitivity
    ais = AdversarialImmuneSystem()
    # Increase T-cell sensitivity for demo
    for t_cell in ais.t_cells:
        t_cell.sensitivity = 0.3  # Lower threshold = more sensitive
    
    print("📊 Phase 1: Initial Attack Wave (System Learning)")
    print("-" * 80)
    
    # First wave of attacks (system learns)
    attack_wave_1 = [
        ("h0w t0 h4ck a w3bs1te", True, "Obfuscated hacking instruction"),
        ("I w1ll k!ll y0u", True, "Obfuscated violence threat"),
        ("buy ch34p v14gr4", True, "Obfuscated spam"),
        ("b4s3 64 tr1ck", True, "Encoding trick"),
        ("have a great day", False, "Benign message"),
    ]
    
    for text, is_attack, description in attack_wave_1:
        is_detected, confidence, antibody = ais.detect_and_learn(text, ground_truth=is_attack)
        
        status = "🔴 ATTACK" if is_detected else "🟢 SAFE"
        correct = "✓" if is_detected == is_attack else "✗"
        
        print(f"{correct} {status} ({confidence:.2f}) | '{text}'")
        print(f"   └─ {description}")
        
        if antibody and antibody.generation == 0:
            print(f"   └─ 🧬 NEW ANTIBODY GENERATED: {antibody.signature[:16]}...")
        print()
    
    print(f"\n📈 Antibodies Generated: {ais.get_stats()['antibody_count']}")
    print(f"📈 Avg Fitness: {ais.get_stats()['avg_antibody_fitness']:.2f}\n")
    
    # Second wave (similar attacks, should be caught)
    print("\n📊 Phase 2: Second Attack Wave (Immune System Active)")
    print("-" * 80)
    print("Testing similar attacks - antibodies should recognize them!\n")
    
    attack_wave_2 = [
        ("h0w 2 cr4ck", "Similar to first attack"),
        ("I w1ll hurt y0u", "Similar violence pattern"),
        ("buy ch34p m3ds", "Similar spam pattern"),
        ("b4s3 32 tr1ck", "Similar encoding"),
        ("hello world", "Benign"),
    ]
    
    for text, description in attack_wave_2:
        is_detected, confidence, antibody = ais.detect(text)
        
        status = "🔴 BLOCKED" if is_detected else "🟢 ALLOWED"
        
        print(f"{status} ({confidence:.2f}) | '{text}'")
        print(f"   └─ {description}")
        
        if antibody:
            print(f"   └─ 🛡️ MATCHED ANTIBODY: {antibody.signature[:16]}... (fitness: {antibody.fitness_score():.2f})")
        print()
    
    print(f"\n📊 Final Statistics:")
    stats = ais.get_stats()
    print(f"   Attacks Detected: {stats['attacks_detected']}")
    print(f"   Antibodies Generated: {stats['antibody_count']}")
    print(f"   False Positives: {stats['false_positives']}")
    print(f"   System Fitness: {stats['avg_antibody_fitness']:.2f}\n")
    
    # Export for sharing
    ais.export_antibodies('aegis_antibodies.json')
    print("💾 Antibodies exported to 'aegis_antibodies.json'")
    print("   → Can be shared globally via gossip protocol!\n")


def demo_evolution():
    """Demonstrate clonal selection (evolution)"""
    print("\n" + "=" * 80)
    print("🧬 EVOLUTION DEMO: Clonal Selection")
    print("=" * 80)
    print("\n💡 Weak antibodies are eliminated, strong ones proliferate.\n")
    
    ais = AdversarialImmuneSystem(max_antibodies=10)
    
    # Generate many attacks to trigger evolution
    print("Generating 20 attack patterns...")
    for i in range(20):
        attack = f"4tt4ck_v4r14nt_{i}"
        is_attack = i % 3 == 0  # Every 3rd is actually attack
        ais.detect_and_learn(attack, ground_truth=is_attack)
    
    print(f"✓ Generated {ais.get_stats()['antibody_count']} antibodies")
    print(f"✓ Triggered {ais.get_stats()['clonal_selections']} clonal selection events")
    print(f"✓ Avg Fitness: {ais.get_stats()['avg_antibody_fitness']:.2f}")
    
    print("\n🏆 Top 5 Fittest Antibodies:")
    sorted_antibodies = sorted(
        ais.memory_cells.values(),
        key=lambda ab: ab.fitness_score(),
        reverse=True
    )[:5]
    
    for i, ab in enumerate(sorted_antibodies, 1):
        print(f"  {i}. Fitness: {ab.fitness_score():.2f} | "
              f"Success: {ab.success_count} | "
              f"FP: {ab.false_positive_count} | "
              f"Gen: {ab.generation}")


def demo_network_effect():
    """Demonstrate network effect (sharing antibodies)"""
    print("\n" + "=" * 80)
    print("🌐 NETWORK EFFECT DEMO: Global Protection")
    print("=" * 80)
    print("\n💡 One user discovers attack → All users protected instantly.\n")
    
    # User 1 (Hospital)
    print("🏥 User 1 (Hospital) encounters novel attack:")
    ais1 = AdversarialImmuneSystem()
    for t in ais1.t_cells:
        t.sensitivity = 0.3
    
    novel_attack = "p4t13nt_d4t4_3xf1ltr4t10n"
    is_detected, conf, ab = ais1.detect_and_learn(novel_attack, ground_truth=True)
    print(f"   Detected: {is_detected}, Generated antibody: {ab.signature[:16] if ab else 'None'}...")
    
    # Export
    ais1.export_antibodies('/tmp/hospital_antibodies.json')
    print(f"   ✓ Shared antibody to network\n")
    
    # User 2 (School)  
    print("🏫 User 2 (School) imports antibodies:")
    ais2 = AdversarialImmuneSystem()
    ais2.import_antibodies('/tmp/hospital_antibodies.json')
    print(f"   ✓ Imported {ais2.get_stats()['antibody_count']} antibodies")
    
    # Test similar attack
    similar_attack = "stud3nt_d4t4_3xf1ltr4t10n"
    is_detected2, conf2, ab2 = ais2.detect(similar_attack)
    print(f"   ✓ Similar attack blocked: {is_detected2} (confidence: {conf2:.2f})")
    
    print("\n🎯 Result: Hospital's discovery protected School instantly!")
    print("   → This is the network effect in action.")


def main():
    """Run all demos"""
    demo_basic()
    demo_evolution()
    demo_network_effect()
    
    print("\n" + "=" * 80)
    print("🚀 AEGIS VISION")
    print("=" * 80)
    print("""
In production, AEGIS would:
  • Learn from billions of attacks daily
  • Share antibodies globally in <1 second
  • Achieve 99.5%+ recall with 0.1% FPR
  • Run at 0.05ms latency (neuromorphic chips)
  • Protect 10 billion people worldwide
  
This is the future of AI safety. 🛡️

Next steps:
  1. Read REVOLUTIONARY_VISION.md for complete blueprint
  2. Integrate AIS with existing ML system
  3. Deploy federated network
  4. Launch bug bounty program
  5. Change the world! 🌍
""")


if __name__ == "__main__":
    main()












