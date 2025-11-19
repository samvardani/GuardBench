#!/usr/bin/env python3
"""
Comprehensive Health Check System
Checks API, database, models, policy, and dependencies
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from . import metrics


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details
        }


@dataclass
class HealthReport:
    """Overall health report"""
    status: HealthStatus
    timestamp: float
    uptime_seconds: float
    checks: List[HealthCheck]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "checks": [check.to_dict() for check in self.checks],
            "summary": {
                "total": len(self.checks),
                "healthy": sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY),
            }
        }


_start_time = time.time()


def check_database() -> HealthCheck:
    """Check database connectivity"""
    start = time.perf_counter()
    try:
        from service import db
        
        # Try a simple query
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        if result and result[0] == 1:
            latency = (time.perf_counter() - start) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Database connection successful",
                details={"query": "SELECT 1"}
            )
        else:
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Database query returned unexpected result"
            )
    
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=f"Database check failed: {str(e)}",
            details={"error": type(e).__name__}
        )


def check_policy() -> HealthCheck:
    """Check policy loading"""
    start = time.perf_counter()
    try:
        from policy.loader import load_policy, validate_policy
        
        policy, checksum = load_policy()
        is_valid, error = validate_policy(policy)
        
        latency = (time.perf_counter() - start) * 1000
        
        if is_valid:
            return HealthCheck(
                name="policy",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Policy loaded and validated",
                details={
                    "version": policy.get("version", "unknown"),
                    "checksum": checksum[:16],
                    "total_slices": len(policy.get("slices", [])),
                }
            )
        else:
            return HealthCheck(
                name="policy",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Policy validation failed: {error}"
            )
    
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="policy",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=f"Policy check failed: {str(e)}",
            details={"error": type(e).__name__}
        )


def check_ml_model() -> HealthCheck:
    """Check ML model availability"""
    start = time.perf_counter()
    try:
        from guards.ml_guard import predict_ml
        
        # Try a simple prediction
        test_scores = predict_ml("test")
        
        latency = (time.perf_counter() - start) * 1000
        
        if test_scores and isinstance(test_scores, dict):
            return HealthCheck(
                name="ml_model",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="ML model loaded and functional",
                details={
                    "labels": list(test_scores.keys()),
                    "inference_latency_ms": round(latency, 2)
                }
            )
        else:
            return HealthCheck(
                name="ml_model",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message="ML model returned unexpected output"
            )
    
    except ImportError:
        return HealthCheck(
            name="ml_model",
            status=HealthStatus.DEGRADED,
            message="ML model not available (using rules-only fallback)"
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="ml_model",
            status=HealthStatus.DEGRADED,
            latency_ms=latency,
            message=f"ML model check failed: {str(e)}",
            details={"error": type(e).__name__}
        )


def check_transformer() -> HealthCheck:
    """Check transformer model availability"""
    start = time.perf_counter()
    try:
        from guards.transformer_guard import predict_transformer
        import asyncio
        
        # Try a simple prediction
        result = asyncio.run(predict_transformer("test"))
        
        latency = (time.perf_counter() - start) * 1000
        
        if result and isinstance(result, dict) and "prediction" in result:
            return HealthCheck(
                name="transformer",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Transformer model loaded and functional",
                details={
                    "model": "BERT-Tiny",
                    "inference_latency_ms": round(latency, 2)
                }
            )
        else:
            return HealthCheck(
                name="transformer",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message="Transformer model returned unexpected output"
            )
    
    except ImportError:
        return HealthCheck(
            name="transformer",
            status=HealthStatus.DEGRADED,
            message="Transformer model not available (using ML+rules fallback)"
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="transformer",
            status=HealthStatus.DEGRADED,
            latency_ms=latency,
            message=f"Transformer check failed: {str(e)}",
            details={"error": type(e).__name__}
        )


def check_rules_guard() -> HealthCheck:
    """Check rules guard availability"""
    start = time.perf_counter()
    try:
        from guards.candidate import predict as rules_predict
        import asyncio
        
        # Try a simple prediction
        result = asyncio.run(rules_predict("test violence"))
        
        latency = (time.perf_counter() - start) * 1000
        
        if result and isinstance(result, dict) and "prediction" in result:
            return HealthCheck(
                name="rules_guard",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Rules guard functional",
                details={"inference_latency_ms": round(latency, 2)}
            )
        else:
            return HealthCheck(
                name="rules_guard",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message="Rules guard returned unexpected output"
            )
    
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="rules_guard",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=f"Rules guard check failed: {str(e)}",
            details={"error": type(e).__name__}
        )


async def perform_health_check(detailed: bool = False) -> HealthReport:
    """
    Perform comprehensive health check
    
    Args:
        detailed: Include optional/slower checks (ML models, transformer)
    
    Returns:
        HealthReport with status and check results
    """
    checks: List[HealthCheck] = []
    
    # Critical checks (always run)
    checks.append(check_database())
    checks.append(check_policy())
    checks.append(check_rules_guard())
    
    # Optional checks (only if detailed=True)
    if detailed:
        checks.append(check_ml_model())
        checks.append(check_transformer())
    
    # Determine overall status
    unhealthy_count = sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY)
    degraded_count = sum(1 for c in checks if c.status == HealthStatus.DEGRADED)
    
    if unhealthy_count > 0:
        overall_status = HealthStatus.UNHEALTHY
    elif degraded_count > 0:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY
    
    # Update Prometheus metrics
    metrics.update_health_status(overall_status == HealthStatus.HEALTHY)
    for check in checks:
        metrics.update_dependency_status(
            check.name,
            check.status == HealthStatus.HEALTHY
        )
    metrics.update_uptime()
    
    report = HealthReport(
        status=overall_status,
        timestamp=time.time(),
        uptime_seconds=time.time() - _start_time,
        checks=checks
    )
    
    return report


def is_ready() -> bool:
    """
    Quick readiness check (for k8s readiness probes)
    Returns True if critical components are healthy
    """
    try:
        # Check critical components only
        db_check = check_database()
        policy_check = check_policy()
        rules_check = check_rules_guard()
        
        critical_checks = [db_check, policy_check, rules_check]
        return all(c.status == HealthStatus.HEALTHY for c in critical_checks)
    except Exception:
        return False


def is_alive() -> bool:
    """
    Quick liveness check (for k8s liveness probes)
    Returns True if service is running
    """
    return True  # If this function runs, the service is alive


if __name__ == "__main__":
    import asyncio
    
    print("\n🔧 Health Check System Test\n")
    
    print("1. Running quick health check...")
    report = asyncio.run(perform_health_check(detailed=False))
    print(f"   Status: {report.status.value}")
    print(f"   Checks: {len(report.checks)}")
    for check in report.checks:
        status_icon = "✓" if check.status == HealthStatus.HEALTHY else ("⚠" if check.status == HealthStatus.DEGRADED else "✗")
        print(f"   {status_icon} {check.name}: {check.status.value} ({check.latency_ms:.2f}ms)")
    
    print("\n2. Running detailed health check...")
    report_detailed = asyncio.run(perform_health_check(detailed=True))
    print(f"   Status: {report_detailed.status.value}")
    print(f"   Checks: {len(report_detailed.checks)}")
    for check in report_detailed.checks:
        status_icon = "✓" if check.status == HealthStatus.HEALTHY else ("⚠" if check.status == HealthStatus.DEGRADED else "✗")
        print(f"   {status_icon} {check.name}: {check.status.value} ({check.latency_ms:.2f}ms)")
    
    print("\n3. Testing readiness check...")
    is_ready_result = is_ready()
    print(f"   Ready: {is_ready_result}")
    
    print("\n4. Testing liveness check...")
    is_alive_result = is_alive()
    print(f"   Alive: {is_alive_result}")
    
    print("\n5. JSON output example:")
    import json
    print(json.dumps(report_detailed.to_dict(), indent=2))
    
    print("\n✅ Health check test complete")












