# Anomaly Detection Tuning

This document describes the anomaly detection system with noise reduction through minimum sample requirements and per-metric cooldown.

## Overview

The anomaly detection system provides statistical anomaly detection with intelligent tuning to reduce false positives and alert storms:

✅ **Minimum Sample Requirement**: No alerts until sufficient baseline data  
✅ **Per-Metric Cooldown**: Prevents alert storms during sustained anomalies  
✅ **Z-Score Detection**: Statistically robust outlier detection  
✅ **Configurable**: Tune via environment variables  

## Problem Solved

**Before**: Noisy anomaly detection
- Alerts triggered with insufficient baseline data
- Alert storms during sustained anomalies
- High false positive rate
- No cooldown mechanism

**After**: Tuned anomaly detection
- Requires minimum N samples (default: 12)
- Per-metric cooldown (default: 10 minutes)
- **19 comprehensive tests** (100% pass rate)
- Reduced noise, actionable alerts

## Features

### 🎯 Minimum Sample Requirement

**Prevents false positives from insufficient data**:

\`\`\`python
from analytics.anomaly_detector import AnomalyDetector, AnomalyConfig

config = AnomalyConfig(min_samples=12)  # Require 12 samples
detector = AnomalyDetector(config)

# Add 11 samples
for i in range(11):
    detector.record("latency", 100.0)

# Check outlier (NO alert - insufficient samples)
anomaly = detector.check("latency", 1000.0)  # → None

# Add 1 more sample (now have 12)
detector.record("latency", 100.0)

# Check outlier (now alerts - sufficient samples)
anomaly = detector.check("latency", 1000.0)  # → Anomaly detected!
\`\`\`

### ⏱️ Per-Metric Cooldown

**Prevents alert storms**:

\`\`\`python
config = AnomalyConfig(
    min_samples=10,
    cooldown_seconds=600  # 10 minute cooldown
)
detector = AnomalyDetector(config)

# Build baseline
for i in range(20):
    detector.record("error_rate", 0.01)

# First spike (alerts)
anomaly = detector.check("error_rate", 0.5, timestamp=1000.0)
# → Anomaly detected!

# Second spike within cooldown (NO alert)
anomaly = detector.check("error_rate", 0.6, timestamp=1100.0)  # 100s later
# → None (in cooldown)

# Third spike after cooldown (alerts again)
anomaly = detector.check("error_rate", 0.7, timestamp=1700.0)  # 700s later
# → Anomaly detected!
\`\`\`

### 📊 Z-Score Detection

**Statistical anomaly detection**:

\`\`\`python
config = AnomalyConfig(
    min_samples=10,
    z_threshold=3.0  # 3 standard deviations
)
detector = AnomalyDetector(config)

# Build baseline (mean=100, std≈5)
baseline = [95, 100, 105, 100, 98, 102, 97, 103, 100, 101]
for v in baseline:
    detector.record("latency", v)

# Normal value (within 3σ) → No alert
detector.check("latency", 105.0)  # → None

# Outlier (> 3σ) → Alert
detector.check("latency", 300.0)  # → Anomaly!
\`\`\`

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ANOMALY_MIN_SAMPLES` | int | 12 | Minimum samples before alerting |
| `ANOMALY_COOLDOWN_SEC` | int | 600 | Cooldown seconds (10 minutes) |
| `ANOMALY_Z_THRESHOLD` | float | 3.0 | Z-score threshold (std devs) |
| `ANOMALY_WINDOW_SIZE` | int | 100 | Rolling window size |

### Usage

\`\`\`bash
# Set configuration
export ANOMALY_MIN_SAMPLES=20
export ANOMALY_COOLDOWN_SEC=300
export ANOMALY_Z_THRESHOLD=2.5

# Create detector
python -c "
from analytics.anomaly_detector import create_detector_from_env
detector = create_detector_from_env()
print(f'Min samples: {detector.config.min_samples}')
print(f'Cooldown: {detector.config.cooldown_seconds}s')
"
\`\`\`

## API

### AnomalyDetector

\`\`\`python
from analytics.anomaly_detector import AnomalyDetector, AnomalyConfig

# Create detector
config = AnomalyConfig(
    min_samples=12,
    cooldown_seconds=600,
    z_threshold=3.0,
    window_size=100
)
detector = AnomalyDetector(config)

# Record metrics
detector.record("latency_ms", 100.0)
detector.record("error_rate", 0.01)

# Check for anomalies
anomaly = detector.check("latency_ms", 500.0)

if anomaly:
    print(f"Anomaly: {anomaly.metric_name}={anomaly.value}")
    print(f"Z-score: {anomaly.z_score:.2f}")
    print(f"Mean: {anomaly.mean:.2f}, Std: {anomaly.std:.2f}")
\`\`\`

### Anomaly Object

\`\`\`python
@dataclass
class Anomaly:
    metric_name: str      # Metric that triggered
    value: float          # Anomalous value
    mean: float           # Baseline mean
    std: float            # Baseline std dev
    z_score: float        # Number of std devs from mean
    timestamp: float      # When detected
    sample_count: int     # Number of samples in baseline
\`\`\`

## Testing

**19 comprehensive tests** (100% pass rate):

\`\`\`bash
pytest tests/test_anomaly_tuning.py -v
# ================ 19 passed in 0.03s ================
\`\`\`

### Test Coverage

✅ **MetricTimeSeries** (4 tests):
  - Creation
  - Adding values
  - Computing statistics
  - Z-score calculation

✅ **AnomalyDetector** (3 tests):
  - Creation
  - Custom configuration
  - Recording metrics

✅ **Min Samples** (3 tests):
  - No alert before minimum samples
  - Alert after minimum samples
  - Gradual baseline building

✅ **Cooldown** (3 tests):
  - Two spikes (only first alerts)
  - Different metrics independent
  - Prevents alert storm

✅ **Z-Score** (3 tests):
  - Normal values (no alert)
  - Outliers trigger alerts
  - Z-score calculation accuracy

✅ **Configuration** (2 tests):
  - Create from environment
  - Default values

✅ **Integration** (1 test):
  - Realistic scenario

### Key Test Results

**Minimum samples**:
\`\`\`python
# 11 samples → No alert (insufficient)
for i in range(10):
    detector.record("latency", 100.0)

anomaly = detector.check("latency", 1000.0)
assert anomaly is None  # Below min_samples=12

# 12 samples → Alert (sufficient)
detector.record("latency", 100.0)
anomaly = detector.check("latency", 1000.0)
assert anomaly is not None  # ✅
\`\`\`

**Cooldown**:
\`\`\`python
# First spike → Alert
anomaly1 = detector.check("latency", 500.0, timestamp=1000.0)
assert anomaly1 is not None  # ✅

# Second spike (5s later) → No alert (cooldown)
anomaly2 = detector.check("latency", 600.0, timestamp=1005.0)
assert anomaly2 is None  # In cooldown ✅

# Third spike (after cooldown) → Alert
anomaly3 = detector.check("latency", 700.0, timestamp=1700.0)
assert anomaly3 is not None  # ✅
\`\`\`

## Use Cases

### 1. Latency Monitoring

\`\`\`python
detector = create_detector_from_env()

# Record latency for each request
for request in requests:
    latency_ms = measure_latency(request)
    
    anomaly = detector.check("latency_ms", latency_ms)
    
    if anomaly:
        alert(f"High latency: {latency_ms}ms (baseline: {anomaly.mean:.0f}ms)")
\`\`\`

### 2. Error Rate Monitoring

\`\`\`python
detector = AnomalyDetector(AnomalyConfig(
    min_samples=50,  # Need more samples for error rates
    cooldown_seconds=300,  # 5 minute cooldown
    z_threshold=2.5  # More sensitive
))

# Check error rate every minute
error_rate = errors / total_requests

anomaly = detector.check("error_rate", error_rate)

if anomaly:
    page_oncall(f"Error rate spike: {error_rate:.2%}")
\`\`\`

### 3. Multiple Metrics

\`\`\`python
detector = create_detector_from_env()

# Independent cooldowns per metric
metrics = {
    "latency_p99": measure_p99_latency(),
    "error_rate": calculate_error_rate(),
    "throughput": measure_throughput()
}

for metric_name, value in metrics.items():
    anomaly = detector.check(metric_name, value)
    
    if anomaly:
        log_anomaly(anomaly)
\`\`\`

## Tuning Guide

### Minimum Samples

**Too low** (< 10):
- ❌ High false positive rate
- ❌ Unstable baseline statistics
- ✅ Faster anomaly detection

**Recommended** (12-30):
- ✅ Stable baseline
- ✅ Low false positive rate
- ✅ Reasonable detection delay

**Too high** (> 50):
- ✅ Very stable baseline
- ❌ Slow to detect anomalies
- ❌ May miss short-lived issues

### Cooldown Period

**Too short** (< 1 minute):
- ❌ Alert storms possible
- ✅ Catch multiple anomalies quickly

**Recommended** (5-10 minutes):
- ✅ Prevents alert storms
- ✅ Allows time for remediation
- ✅ Reduces alert fatigue

**Too long** (> 30 minutes):
- ✅ Very few alerts
- ❌ May miss repeated anomalies
- ❌ Slow feedback loop

### Z-Score Threshold

**Low** (< 2.0):
- ✅ Sensitive to small changes
- ❌ More false positives
- Use for critical metrics

**Medium** (2.5-3.0):
- ✅ Balanced sensitivity
- ✅ Standard statistical significance
- Recommended for most metrics

**High** (> 3.5):
- ✅ Very few false positives
- ❌ May miss real anomalies
- Use for noisy metrics

## Best Practices

1. **Start with defaults**: Min 12 samples, 10 min cooldown, 3.0 z-score
2. **Tune per metric**: Different metrics may need different thresholds
3. **Monitor false positives**: Adjust if too many false alerts
4. **Independent cooldowns**: Each metric has its own cooldown
5. **Combine with static thresholds**: Use anomaly detection AND absolute limits

## Troubleshooting

### No Alerts Triggered

**Issue**: Detector never alerts

**Causes**:
1. Not enough samples collected
2. Z-threshold too high
3. Metric variance too high (all values seem normal)

**Fix**:
\`\`\`python
# Check stats
stats = detector.get_metric_stats("my_metric")
print(f"Samples: {stats['sample_count']}")  # Need min_samples
print(f"Mean: {stats['mean']:.2f}")
print(f"Std: {stats['std']:.2f}")

# Lower threshold if needed
config = AnomalyConfig(z_threshold=2.0)
\`\`\`

### Too Many Alerts

**Issue**: Alert storm

**Causes**:
1. Cooldown too short
2. Z-threshold too low
3. Metric naturally noisy

**Fix**:
\`\`\`python
# Increase cooldown
config = AnomalyConfig(cooldown_seconds=1200)  # 20 minutes

# Or raise threshold
config = AnomalyConfig(z_threshold=4.0)  # More strict
\`\`\`

### Delayed Detection

**Issue**: Anomalies detected too late

**Causes**:
1. min_samples too high
2. Window size too large

**Fix**:
\`\`\`python
# Reduce minimum samples
config = AnomalyConfig(
    min_samples=8,  # Faster baseline
    window_size=50  # Smaller window
)
\`\`\`

## Related Documentation

- [Monitoring Best Practices](./MONITORING.md)
- [Alerting Guidelines](./ALERTING.md)
- [Metrics Collection](./METRICS.md)

## Summary

The anomaly detection system with tuning provides:

✅ **Noise Reduction**: Min samples requirement  
✅ **Alert Storm Prevention**: Per-metric cooldown  
✅ **Statistical Robustness**: Z-score detection  
✅ **Configurable**: Environment-based settings  
✅ **Tested**: 19 comprehensive tests (100% pass)  

This ensures actionable, low-noise anomaly alerts for production monitoring.

