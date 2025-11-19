#!/usr/bin/env python3
"""
Day 10: SLA Data Collector & Performance Report Generator
Collects metrics from pilot apps and generates performance reports
"""

import requests
import time
import statistics
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import concurrent.futures

# Configuration
API_URL = "http://localhost:8001"
REPORT_DIR = Path("reports/sla")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Test scenarios
TEST_SCENARIOS = [
    {"name": "safe_short", "text": "Hello world", "category": "safe"},
    {"name": "safe_long", "text": "This is a longer safe message that contains multiple sentences. " * 5, "category": "safe"},
    {"name": "violence_explicit", "text": "I will kill you and destroy everything", "category": "violence"},
    {"name": "violence_obfuscated", "text": "I w1ll k!ll y0u", "category": "violence"},
    {"name": "harassment", "text": "You are so stupid and worthless", "category": "harassment"},
    {"name": "self_harm", "text": "I want to hurt myself", "category": "self_harm"},
    {"name": "illegal_obfuscated", "text": "h0w t0 h4ck a w3bs1te", "category": "illegal"},
]


class SLACollector:
    """Collects and analyzes SLA metrics"""
    
    def __init__(self):
        self.results = []
        self.report_file = REPORT_DIR / f"sla_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    def test_endpoint(self, endpoint: str, payload: Dict) -> Dict:
        """Test a single API endpoint"""
        start_time = time.perf_counter()
        
        try:
            response = requests.post(f"{API_URL}{endpoint}", json=payload, timeout=30)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "latency_ms": elapsed_ms,
                    "server_latency_ms": data.get("latency_ms", 0),
                    "prediction": data.get("prediction"),
                    "score": data.get("score"),
                    "method": data.get("method"),
                    "status_code": 200
                }
            else:
                return {
                    "success": False,
                    "latency_ms": elapsed_ms,
                    "status_code": response.status_code,
                    "error": response.text
                }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return {
                "success": False,
                "latency_ms": elapsed_ms,
                "error": str(e),
                "status_code": 0
            }
    
    def run_load_test(self, duration_seconds: int = 60, rps: int = 10):
        """Run sustained load test"""
        print(f"\n🔥 Running load test: {rps} req/s for {duration_seconds}s...")
        
        start_time = time.time()
        results = []
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            batch_start = time.time()
            
            # Send batch of requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=rps) as executor:
                futures = []
                for i in range(rps):
                    scenario = TEST_SCENARIOS[request_count % len(TEST_SCENARIOS)]
                    future = executor.submit(
                        self.test_endpoint,
                        "/score",
                        {"text": scenario["text"]}
                    )
                    futures.append((future, scenario))
                    request_count += 1
                
                # Collect results
                for future, scenario in futures:
                    result = future.result()
                    result["scenario"] = scenario["name"]
                    results.append(result)
            
            # Sleep to maintain target RPS
            elapsed = time.time() - batch_start
            sleep_time = max(0, 1.0 - elapsed)
            time.sleep(sleep_time)
            
            # Progress update
            if request_count % (rps * 10) == 0:
                success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
                avg_latency = statistics.mean(r["latency_ms"] for r in results if r["success"])
                print(f"  {request_count} requests • {success_rate:.1f}% success • {avg_latency:.1f}ms avg latency")
        
        print(f"✅ Load test complete: {request_count} total requests\n")
        
        return results
    
    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analyze SLA metrics"""
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        if not successful:
            return {"error": "No successful requests"}
        
        latencies = [r["latency_ms"] for r in successful]
        server_latencies = [r.get("server_latency_ms", 0) for r in successful if r.get("server_latency_ms")]
        
        analysis = {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "latency": {
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "mean_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "p50_ms": statistics.quantiles(latencies, n=2)[0],
                "p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
                "p99_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
                "stddev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
            },
            "server_latency": {
                "mean_ms": statistics.mean(server_latencies) if server_latencies else 0,
                "p50_ms": statistics.median(server_latencies) if server_latencies else 0,
                "p99_ms": statistics.quantiles(server_latencies, n=100)[98] if len(server_latencies) >= 100 else max(server_latencies) if server_latencies else 0
            },
            "predictions": {
                "flag": sum(1 for r in successful if r.get("prediction") == "flag"),
                "pass": sum(1 for r in successful if r.get("prediction") == "pass")
            },
            "methods": {},
            "errors": {}
        }
        
        # Count methods used
        for r in successful:
            method = r.get("method", "unknown")
            analysis["methods"][method] = analysis["methods"].get(method, 0) + 1
        
        # Count error types
        for r in failed:
            error = r.get("error", "unknown")
            analysis["errors"][error] = analysis["errors"].get(error, 0) + 1
        
        return analysis
    
    def generate_report(self, analysis: Dict, test_duration: int):
        """Generate comprehensive SLA report"""
        print("\n" + "="*70)
        print("SLA PERFORMANCE REPORT")
        print("="*70)
        
        print(f"\n📊 Test Summary:")
        print(f"  Duration: {test_duration}s")
        print(f"  Total Requests: {analysis['total_requests']}")
        print(f"  Successful: {analysis['successful_requests']} ({analysis['success_rate']:.2f}%)")
        print(f"  Failed: {analysis['failed_requests']}")
        
        print(f"\n⚡ Latency Metrics (End-to-End):")
        lat = analysis['latency']
        print(f"  Min: {lat['min_ms']:.2f}ms")
        print(f"  Mean: {lat['mean_ms']:.2f}ms")
        print(f"  Median (p50): {lat['p50_ms']:.2f}ms")
        print(f"  p95: {lat['p95_ms']:.2f}ms")
        print(f"  p99: {lat['p99_ms']:.2f}ms")
        print(f"  Max: {lat['max_ms']:.2f}ms")
        print(f"  Stddev: {lat['stddev_ms']:.2f}ms")
        
        print(f"\n🎯 Server Processing Time:")
        slat = analysis['server_latency']
        print(f"  Mean: {slat['mean_ms']:.2f}ms")
        print(f"  p50: {slat['p50_ms']:.2f}ms")
        print(f"  p99: {slat['p99_ms']:.2f}ms")
        
        print(f"\n🔍 Predictions:")
        preds = analysis['predictions']
        print(f"  Flagged: {preds['flag']} ({preds['flag']/analysis['successful_requests']*100:.1f}%)")
        print(f"  Passed: {preds['pass']} ({preds['pass']/analysis['successful_requests']*100:.1f}%)")
        
        print(f"\n🛠️  Methods Used:")
        for method, count in analysis['methods'].items():
            print(f"  {method}: {count} ({count/analysis['successful_requests']*100:.1f}%)")
        
        if analysis['errors']:
            print(f"\n❌ Errors:")
            for error, count in analysis['errors'].items():
                print(f"  {error}: {count}")
        
        print(f"\n✅ SLA Compliance:")
        lat = analysis['latency']
        compliance = {
            "p50 < 5ms": lat['p50_ms'] < 5,
            "p95 < 10ms": lat['p95_ms'] < 10,
            "p99 < 15ms": lat['p99_ms'] < 15,
            "Success rate > 99%": analysis['success_rate'] > 99,
            "Error rate < 0.1%": (analysis['failed_requests'] / analysis['total_requests'] * 100) < 0.1
        }
        
        for metric, passed in compliance.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {metric}: {status}")
        
        print("\n" + "="*70)
        
        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": test_duration,
            "analysis": analysis,
            "sla_compliance": compliance
        }
        
        with open(self.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved: {self.report_file}")
        
        return report
    
    def run_full_test(self, duration: int = 60, rps: int = 10):
        """Run complete SLA test"""
        print(f"\n🚀 Starting SLA Performance Test")
        print(f"Target: {rps} requests/second for {duration} seconds")
        print(f"="*70)
        
        # Run load test
        results = self.run_load_test(duration, rps)
        
        # Analyze results
        analysis = self.analyze_results(results)
        
        # Generate report
        report = self.generate_report(analysis, duration)
        
        return report


def main():
    """CLI for SLA collector"""
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    rps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    collector = SLACollector()
    report = collector.run_full_test(duration, rps)
    
    print(f"\n✅ SLA test complete!")
    print(f"📊 Summary: {report['analysis']['success_rate']:.2f}% success rate, {report['analysis']['latency']['p50_ms']:.2f}ms p50 latency")


if __name__ == "__main__":
    main()












