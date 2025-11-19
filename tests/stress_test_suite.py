#!/usr/bin/env python3
"""
SeaRei Comprehensive Stress Test Suite
Multi-layer testing framework for production readiness validation

Test Layers:
1. Unit Stress Tests - Individual component limits
2. Integration Stress Tests - Cross-component interactions
3. Concurrency Tests - Race conditions and deadlocks
4. Load Tests - High throughput scenarios
5. Chaos Tests - Failure injection and recovery
6. Memory Leak Tests - Long-running stability
7. Security Tests - Attack scenarios
8. Edge Case Tests - Boundary conditions
"""

import asyncio
import concurrent.futures
import gc
import json
import multiprocessing
import os
import psutil
import random
import string
import sys
import tempfile
import threading
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.guards.candidate import predict as rules_predict
from src.guards.ml_guard import predict_ml, predict_hybrid
from src.guards.ensemble_guard import predict_ensemble


@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    layer: str
    passed: bool
    duration_ms: float
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, float]
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StressTestRunner:
    """Main test runner"""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.results: List[TestResult] = []
        self.process = psutil.Process()
        
    def run_all(self) -> Dict[str, Any]:
        """Run all test layers"""
        print("\n" + "="*80)
        print("SEAREI COMPREHENSIVE STRESS TEST SUITE")
        print("="*80 + "\n")
        
        layers = [
            ("Layer 1", "Unit Stress Tests", self.layer1_unit_stress),
            ("Layer 2", "Integration Stress", self.layer2_integration_stress),
            ("Layer 3", "Concurrency Tests", self.layer3_concurrency),
            ("Layer 4", "Load Tests", self.layer4_load_tests),
            ("Layer 5", "Chaos Tests", self.layer5_chaos),
            ("Layer 6", "Memory Leak Tests", self.layer6_memory_leaks),
            ("Layer 7", "Security Tests", self.layer7_security),
            ("Layer 8", "Edge Case Tests", self.layer8_edge_cases),
        ]
        
        for layer_id, layer_name, layer_func in layers:
            print(f"\n{'='*80}")
            print(f"{layer_id}: {layer_name}")
            print(f"{'='*80}\n")
            
            try:
                layer_func()
            except Exception as e:
                print(f"❌ Layer failed with exception: {e}")
                traceback.print_exc()
        
        return self.generate_report()
    
    # ========================================================================
    # LAYER 1: UNIT STRESS TESTS
    # ========================================================================
    
    def layer1_unit_stress(self):
        """Test individual components under extreme load"""
        
        # Test 1.1: Rules engine with massive pattern set
        print("Test 1.1: Rules Engine Stress (10,000 texts)...")
        start = time.perf_counter()
        errors = []
        latencies = []
        
        for i in range(10000):
            try:
                text = self._generate_random_text(random.randint(10, 500))
                t0 = time.perf_counter()
                result = rules_predict(text)
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
            except Exception as e:
                errors.append(str(e))
        
        duration = (time.perf_counter() - start) * 1000
        
        self.results.append(TestResult(
            test_name="Rules Engine Stress",
            layer="Unit Stress",
            passed=len(errors) == 0,
            duration_ms=duration,
            details={
                "total_tests": 10000,
                "errors": len(errors),
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "p95_latency_ms": self._percentile(latencies, 95) if latencies else 0,
                "p99_latency_ms": self._percentile(latencies, 99) if latencies else 0,
            },
            errors=errors[:10],  # First 10 errors
            warnings=[],
            metrics={"throughput": 10000 / (duration / 1000)}
        ))
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        print(f"    Avg latency: {sum(latencies) / len(latencies):.2f}ms")
        print(f"    Errors: {len(errors)}")
        
        # Test 1.2: ML model stress test
        print("\nTest 1.2: ML Model Stress (5,000 predictions)...")
        start = time.perf_counter()
        errors = []
        latencies = []
        
        for i in range(5000):
            try:
                text = self._generate_random_text(random.randint(10, 300))
                t0 = time.perf_counter()
                result = predict_ml(text)
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
            except Exception as e:
                errors.append(str(e))
        
        duration = (time.perf_counter() - start) * 1000
        
        self.results.append(TestResult(
            test_name="ML Model Stress",
            layer="Unit Stress",
            passed=len(errors) == 0,
            duration_ms=duration,
            details={
                "total_tests": 5000,
                "errors": len(errors),
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            },
            errors=errors[:10],
            warnings=[],
            metrics={"throughput": 5000 / (duration / 1000)}
        ))
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        
        # Test 1.3: Extreme input lengths
        print("\nTest 1.3: Extreme Input Lengths...")
        test_cases = [
            ("empty", ""),
            ("single_char", "a"),
            ("very_long", "a" * 50000),
            ("unicode_heavy", "🔥" * 5000),
            ("mixed", ("Hello " + "世界" * 100) * 10),
        ]
        
        for name, text in test_cases:
            try:
                start = time.perf_counter()
                result = rules_predict(text)
                duration = (time.perf_counter() - start) * 1000
                print(f"  ✓ {name}: {duration:.2f}ms")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
    
    # ========================================================================
    # LAYER 2: INTEGRATION STRESS TESTS
    # ========================================================================
    
    def layer2_integration_stress(self):
        """Test component interactions under stress"""
        
        # Test 2.1: Ensemble guard stress
        print("Test 2.1: Ensemble Guard Stress (1,000 requests)...")
        start = time.perf_counter()
        errors = []
        latencies = []
        methods_used = defaultdict(int)
        
        for i in range(1000):
            try:
                text = self._generate_random_text(random.randint(50, 300))
                t0 = time.perf_counter()
                result = asyncio.run(predict_ensemble(text))
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
                methods_used[result.get('method', 'unknown')] += 1
            except Exception as e:
                errors.append(str(e))
        
        duration = (time.perf_counter() - start) * 1000
        
        self.results.append(TestResult(
            test_name="Ensemble Guard Stress",
            layer="Integration Stress",
            passed=len(errors) == 0,
            duration_ms=duration,
            details={
                "total_tests": 1000,
                "errors": len(errors),
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "methods_distribution": dict(methods_used),
            },
            errors=errors[:10],
            warnings=[],
            metrics={"throughput": 1000 / (duration / 1000)}
        ))
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        print(f"    Methods: {dict(methods_used)}")
        
        # Test 2.2: API endpoint stress (if API is running)
        print("\nTest 2.2: API Endpoint Stress...")
        try:
            response = requests.get(f"{self.api_url}/healthz", timeout=5)
            if response.status_code == 200:
                self._api_stress_test()
            else:
                print("  ⚠️  API not healthy, skipping")
        except:
            print("  ⚠️  API not available, skipping")
    
    def _api_stress_test(self):
        """Stress test API endpoints"""
        errors = []
        latencies = []
        
        for i in range(500):
            try:
                text = self._generate_random_text(random.randint(20, 200))
                t0 = time.perf_counter()
                response = requests.post(
                    f"{self.api_url}/score",
                    json={"text": text},
                    timeout=10
                )
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
                
                if response.status_code != 200:
                    errors.append(f"Status {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        print(f"  ✓ 500 API requests completed")
        print(f"    Avg latency: {sum(latencies) / len(latencies):.2f}ms")
        print(f"    Errors: {len(errors)}")
    
    # ========================================================================
    # LAYER 3: CONCURRENCY TESTS
    # ========================================================================
    
    def layer3_concurrency(self):
        """Test concurrent access and race conditions"""
        
        # Test 3.1: Thread safety
        print("Test 3.1: Thread Safety (100 threads)...")
        
        def worker(thread_id, results_list, errors_list):
            try:
                for i in range(10):
                    text = f"Thread {thread_id} test {i}"
                    result = rules_predict(text)
                    results_list.append(result)
            except Exception as e:
                errors_list.append((thread_id, str(e)))
        
        threads = []
        results_list = []
        errors_list = []
        
        start = time.perf_counter()
        
        for i in range(100):
            t = threading.Thread(target=worker, args=(i, results_list, errors_list))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        duration = (time.perf_counter() - start) * 1000
        
        self.results.append(TestResult(
            test_name="Thread Safety",
            layer="Concurrency",
            passed=len(errors_list) == 0,
            duration_ms=duration,
            details={
                "threads": 100,
                "total_operations": 1000,
                "errors": len(errors_list),
                "results": len(results_list),
            },
            errors=[str(e) for e in errors_list[:10]],
            warnings=[],
            metrics={"ops_per_second": 1000 / (duration / 1000)}
        ))
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        print(f"    Operations: {len(results_list)}, Errors: {len(errors_list)}")
        
        # Test 3.2: Process safety
        print("\nTest 3.2: Process Safety (10 processes)...")
        
        def process_worker(process_id, queue):
            try:
                results = []
                for i in range(20):
                    text = f"Process {process_id} test {i}"
                    result = rules_predict(text)
                    results.append(result['prediction'])
                queue.put(("success", process_id, results))
            except Exception as e:
                queue.put(("error", process_id, str(e)))
        
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        processes = []
        
        start = time.perf_counter()
        
        for i in range(10):
            p = multiprocessing.Process(target=process_worker, args=(i, queue))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()
        
        duration = (time.perf_counter() - start) * 1000
        
        errors = []
        success_count = 0
        while not queue.empty():
            result = queue.get()
            if result[0] == "error":
                errors.append(result[2])
            else:
                success_count += 1
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        print(f"    Processes succeeded: {success_count}/10")
    
    # ========================================================================
    # LAYER 4: LOAD TESTS
    # ========================================================================
    
    def layer4_load_tests(self):
        """Test sustained high load"""
        
        # Test 4.1: Sustained load (30 seconds)
        print("Test 4.1: Sustained Load Test (30 seconds)...")
        
        start_time = time.time()
        end_time = start_time + 30
        
        total_requests = 0
        total_errors = 0
        latencies = []
        
        while time.time() < end_time:
            try:
                text = self._generate_random_text(random.randint(50, 200))
                t0 = time.perf_counter()
                result = rules_predict(text)
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
                total_requests += 1
            except Exception as e:
                total_errors += 1
            
            # Small sleep to avoid CPU saturation
            time.sleep(0.001)
        
        duration = time.time() - start_time
        
        self.results.append(TestResult(
            test_name="Sustained Load",
            layer="Load Tests",
            passed=total_errors < (total_requests * 0.01),  # < 1% error rate
            duration_ms=duration * 1000,
            details={
                "duration_seconds": 30,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "requests_per_second": total_requests / duration,
                "error_rate_percent": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            },
            errors=[],
            warnings=[],
            metrics={
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "p95_latency_ms": self._percentile(latencies, 95) if latencies else 0,
                "p99_latency_ms": self._percentile(latencies, 99) if latencies else 0,
            }
        ))
        
        print(f"  ✓ Completed: {total_requests} requests in {duration:.2f}s")
        print(f"    RPS: {total_requests / duration:.2f}")
        print(f"    Error rate: {(total_errors / total_requests * 100) if total_requests > 0 else 0:.2f}%")
        
        # Test 4.2: Burst load
        print("\nTest 4.2: Burst Load Test (1000 requests in 5 seconds)...")
        
        start = time.perf_counter()
        errors = []
        latencies = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for i in range(1000):
                text = self._generate_random_text(random.randint(50, 200))
                future = executor.submit(self._measure_predict, text)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    latency = future.result()
                    latencies.append(latency)
                except Exception as e:
                    errors.append(str(e))
        
        duration = (time.perf_counter() - start) * 1000
        
        print(f"  ✓ Completed in {duration:.2f}ms")
        print(f"    Avg latency: {sum(latencies) / len(latencies):.2f}ms")
        print(f"    Errors: {len(errors)}")
    
    def _measure_predict(self, text: str) -> float:
        """Measure prediction latency"""
        t0 = time.perf_counter()
        rules_predict(text)
        return (time.perf_counter() - t0) * 1000
    
    # ========================================================================
    # LAYER 5: CHAOS TESTS
    # ========================================================================
    
    def layer5_chaos(self):
        """Test failure scenarios and recovery"""
        
        # Test 5.1: Corrupted input handling
        print("Test 5.1: Corrupted Input Handling...")
        
        chaos_inputs = [
            None,
            123,
            [],
            {},
            {"text": "nested"},
            b"bytes",
            "\x00\x01\x02\x03",  # Binary data
            "null\x00byte",
            "\uffff" * 100,  # Invalid Unicode
        ]
        
        handled = 0
        crashed = 0
        
        for inp in chaos_inputs:
            try:
                result = rules_predict(inp)
                handled += 1
            except (TypeError, ValueError, AttributeError):
                handled += 1  # Expected error, handled gracefully
            except Exception as e:
                crashed += 1
                print(f"  ❌ Unexpected crash: {type(e).__name__}")
        
        print(f"  ✓ Handled: {handled}/{len(chaos_inputs)}")
        print(f"    Crashed: {crashed}")
        
        # Test 5.2: Resource exhaustion
        print("\nTest 5.2: Resource Exhaustion...")
        
        # Memory stress
        print("  Testing memory stress...")
        try:
            large_texts = []
            for i in range(100):
                large_texts.append("x" * 100000)  # 100KB each = 10MB total
                result = rules_predict(large_texts[-1])
            
            print(f"    ✓ Handled 100 large texts")
        except MemoryError:
            print(f"    ❌ Memory exhausted")
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
        finally:
            large_texts = None
            gc.collect()
        
        # Test 5.3: Malformed patterns (if applicable)
        print("\nTest 5.3: Attack Patterns...")
        
        attack_patterns = [
            "a" * 10000,  # ReDoS attempt
            "(((((" * 100,  # Regex bomb
            "<script>alert('xss')</script>",  # XSS
            "'; DROP TABLE users; --",  # SQL injection
            "../../../etc/passwd",  # Path traversal
            "%00%00%00",  # Null byte injection
        ]
        
        for pattern in attack_patterns:
            try:
                t0 = time.perf_counter()
                result = rules_predict(pattern)
                latency = (time.perf_counter() - t0) * 1000
                
                if latency > 1000:  # More than 1 second
                    print(f"  ⚠️  Slow: {latency:.2f}ms")
            except Exception as e:
                print(f"  ❌ Crashed on attack pattern")
    
    # ========================================================================
    # LAYER 6: MEMORY LEAK TESTS
    # ========================================================================
    
    def layer6_memory_leaks(self):
        """Test for memory leaks over time"""
        
        print("Test 6.1: Memory Leak Detection (10,000 iterations)...")
        
        tracemalloc.start()
        
        # Baseline
        gc.collect()
        baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many iterations
        for i in range(10000):
            text = self._generate_random_text(random.randint(50, 200))
            result = rules_predict(text)
            
            if i % 1000 == 0:
                gc.collect()
                current_memory = self.process.memory_info().rss / 1024 / 1024
                print(f"  Iteration {i}: {current_memory:.2f} MB")
        
        # Final measurement
        gc.collect()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - baseline_memory
        
        # Get top memory consumers
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:5]
        
        tracemalloc.stop()
        
        self.results.append(TestResult(
            test_name="Memory Leak Detection",
            layer="Memory Leaks",
            passed=memory_growth < 100,  # Less than 100MB growth
            duration_ms=0,
            details={
                "iterations": 10000,
                "baseline_mb": baseline_memory,
                "final_mb": final_memory,
                "growth_mb": memory_growth,
                "growth_per_1k_requests_mb": (memory_growth / 10) if memory_growth > 0 else 0,
            },
            errors=[],
            warnings=[] if memory_growth < 50 else ["High memory growth detected"],
            metrics={"memory_growth_mb": memory_growth}
        ))
        
        print(f"\n  ✓ Memory growth: {memory_growth:.2f} MB")
    
    # ========================================================================
    # LAYER 7: SECURITY TESTS
    # ========================================================================
    
    def layer7_security(self):
        """Test security vulnerabilities"""
        
        # Test 7.1: Injection attacks
        print("Test 7.1: Injection Attack Resilience...")
        
        injection_tests = [
            ("SQL Injection", "' OR '1'='1"),
            ("Command Injection", "; ls -la; echo"),
            ("LDAP Injection", "*)(&(objectClass=*"),
            ("XML Injection", "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>"),
            ("Template Injection", "{{7*7}}"),
        ]
        
        for name, payload in injection_tests:
            try:
                result = rules_predict(payload)
                # Check if it's detected as unsafe
                if result['prediction'] == 'flag':
                    print(f"  ✓ {name}: Detected as unsafe")
                else:
                    print(f"  ⚠️  {name}: Not detected")
            except Exception as e:
                print(f"  ❌ {name}: Crashed - {e}")
        
        # Test 7.2: Rate limiting bypass attempts (if API available)
        print("\nTest 7.2: Rate Limiting Tests...")
        try:
            response = requests.get(f"{self.api_url}/healthz", timeout=5)
            if response.status_code == 200:
                # Rapid fire requests
                blocked = 0
                for i in range(100):
                    try:
                        resp = requests.post(
                            f"{self.api_url}/score",
                            json={"text": "test"},
                            timeout=1
                        )
                        if resp.status_code == 429:  # Too Many Requests
                            blocked += 1
                    except:
                        pass
                print(f"  Blocked by rate limiter: {blocked}/100 requests")
            else:
                print("  ⚠️  API not available")
        except:
            print("  ⚠️  API not available")
    
    # ========================================================================
    # LAYER 8: EDGE CASE TESTS
    # ========================================================================
    
    def layer8_edge_cases(self):
        """Test boundary conditions and edge cases"""
        
        # Test 8.1: Unicode edge cases
        print("Test 8.1: Unicode Edge Cases...")
        
        unicode_tests = [
            ("Emoji", "🔥💯🎉" * 100),
            ("RTL", "مرحبا بك في العالم" * 50),
            ("Mixed", "Hello 世界 🌍 Привет مرحبا"),
            ("Zero-width", "a\u200b\u200c\u200d" * 100),
            ("Combining", "e\u0301\u0302\u0303" * 100),
            ("Surrogate pairs", "\U0001F600" * 100),
        ]
        
        for name, text in unicode_tests:
            try:
                t0 = time.perf_counter()
                result = rules_predict(text)
                latency = (time.perf_counter() - t0) * 1000
                print(f"  ✓ {name}: {latency:.2f}ms")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        
        # Test 8.2: Boundary values
        print("\nTest 8.2: Boundary Value Tests...")
        
        boundary_tests = [
            ("Empty string", ""),
            ("Single space", " "),
            ("Only newlines", "\n" * 100),
            ("Max length", "a" * 100000),
            ("Repeated char", "a" * 10000),
            ("All punctuation", "!@#$%^&*()" * 100),
        ]
        
        for name, text in boundary_tests:
            try:
                t0 = time.perf_counter()
                result = rules_predict(text)
                latency = (time.perf_counter() - t0) * 1000
                print(f"  ✓ {name}: {latency:.2f}ms")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        
        # Test 8.3: Real-world edge cases
        print("\nTest 8.3: Real-World Edge Cases...")
        
        real_world_tests = [
            "I'm fine, thanks!",  # Safe with potentially flagged words
            "He's such a killer guitarist!",  # Context matters
            "This movie absolutely murdered me (laughing)",  # Metaphorical
            "Fighting cancer with chemotherapy",  # Medical context
            "Killing time before the meeting",  # Idiom
        ]
        
        for text in real_world_tests:
            try:
                result = rules_predict(text)
                print(f"  ✓ '{text[:50]}...': {result['prediction']}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _generate_random_text(self, length: int) -> str:
        """Generate random text for testing"""
        words = ["hello", "world", "test", "sample", "data", "random", "text", 
                 "content", "message", "information", "system", "platform"]
        result = []
        while len(" ".join(result)) < length:
            result.append(random.choice(words))
        return " ".join(result)[:length]
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    # ========================================================================
    # REPORT GENERATION
    # ========================================================================
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80 + "\n")
        
        # Calculate statistics
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total_tests - passed
        
        total_duration = sum(r.duration_ms for r in self.results)
        
        # Group by layer
        by_layer = defaultdict(list)
        for result in self.results:
            by_layer[result.layer].append(result)
        
        # Print summary
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ({passed/total_tests*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
        print(f"Total Duration: {total_duration/1000:.2f}s")
        print()
        
        # Print by layer
        for layer, results in sorted(by_layer.items()):
            layer_passed = sum(1 for r in results if r.passed)
            print(f"{layer}: {layer_passed}/{len(results)} passed")
        
        print("\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80 + "\n")
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} | {result.layer} | {result.test_name}")
            print(f"  Duration: {result.duration_ms:.2f}ms")
            
            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")
            
            if result.errors:
                print(f"  Errors: {len(result.errors)}")
                for error in result.errors[:3]:
                    print(f"    - {error}")
            
            if result.warnings:
                print(f"  Warnings: {', '.join(result.warnings)}")
            
            print()
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total_tests if total_tests > 0 else 0,
                "total_duration_ms": total_duration,
            },
            "by_layer": {
                layer: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r.passed),
                    "failed": sum(1 for r in results if not r.passed),
                }
                for layer, results in by_layer.items()
            },
            "detailed_results": [asdict(r) for r in self.results],
        }
        
        report_path = Path("test_results") / f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Detailed report saved to: {report_path}")
        
        return report


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SeaRei Comprehensive Stress Test Suite")
    parser.add_argument("--api-url", default="http://localhost:8001", help="API base URL")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    runner = StressTestRunner(api_url=args.api_url)
    report = runner.run_all()
    
    # Exit with appropriate code
    if report['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()












