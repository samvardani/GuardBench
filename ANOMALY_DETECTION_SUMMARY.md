# Anomaly Detection System - Implementation Summary

## Overview

Implemented a comprehensive automated anomaly detection system that monitors safety metrics in real-time, using statistical methods to identify unusual patterns and trigger alerts for early detection of model drift, abuse, or system failures.

## Problem Solved

**Before**: Blind to issues
- No automated monitoring of metrics
- Manual detection of anomalies
- Reactive to problems (after damage)
- No early warning system
- Unknown model drift
- Undetected abuse patterns

**After**: Proactive anomaly detection
- Real-time monitoring of key metrics
- Statistical detection (z-score, thresholds)
- Multiple anomaly types detected
- Automated alerts (Slack, logs)
- Early warning for model drift
- **28 comprehensive tests** (100% pass rate)

## Implementation

### Core Components

1. **AnomalyDetector**: Main detection engine
2. **MetricWindow**: Sliding window for baseline calculation
3. **Anomaly**: Data model for detected anomalies
4. **AlertSystem**: Multi-channel alerting (Slack, email, logs)
5. **Background Monitor**: Async monitoring loop

### Architecture

```
Metrics → Sliding Window → Statistical Analysis
                                    ↓
                          Anomaly Detection
                                    ↓
                          Severity Calculation
                                    ↓
                            Cooldown Check
                                    ↓
                            Alert System
                                    ↓
                    Slack / Email / Logs
```

## Features Implemented

### Anomaly Types

**Volume Anomalies**:
```python
# Spike: 5x increase
# Normal: 100 req/min → Spike: 600 req/min
AnomalyType.VOLUME_SPIKE

# Drop: <20% of baseline
# Normal: 100 req/min → Drop: 10 req/min
AnomalyType.VOLUME_DROP
```

**Flag Rate Anomalies**:
```python
# Spike: >15% absolute change
# Normal: 5% flagged → Spike: 35% flagged
AnomalyType.FLAG_RATE_SPIKE

# Drop: >15% absolute change
# Normal: 30% flagged → Drop: 5% flagged
AnomalyType.FLAG_RATE_DROP
```

**Performance Anomalies**:
```python
# Latency: 3x increase
# Normal: 150ms → Spike: 600ms
AnomalyType.LATENCY_SPIKE

# Errors: >5% absolute change
# Normal: 1% errors → Spike: 15% errors
AnomalyType.ERROR_SPIKE
```

### Statistical Methods

**Z-Score Detection**:
```python
z_score = (current_value - mean) / std_dev

if z_score > 3.0:  # Configurable threshold
    anomaly_detected()

# Severity based on z-score:
# z > 5: Critical
# z > 4: High
# z > 3: Medium
```

**Threshold-Based Detection**:
```python
# Volume spike: >5x baseline
if current > baseline * 5:
    volume_spike()

# Flag rate: >15% absolute change
if abs(current - baseline) > 0.15:
    flag_rate_anomaly()
```

**Sliding Window**:
```python
window_size = 60  # 60 samples (1 hour at 1 min/sample)
min_samples = 10  # Warm-up period

# FIFO queue for recent values
values = deque(maxlen=window_size)
```

### Alert System

**Slack Integration**:
```json
{
  "attachments": [{
    "color": "#ff0000",
    "title": "🚨 Anomaly Detected: volume_spike",
    "text": "[HIGH] requests_volume=600 (expected ~100, +500% change)",
    "fields": [
      {"title": "Metric", "value": "requests_volume"},
      {"title": "Severity", "value": "HIGH"},
      {"title": "Current Value", "value": "600.00"},
      {"title": "Expected Value", "value": "100.00"}
    ]
  }]
}
```

**Log Alerts**:
```
WARNING - 🚨 ANOMALY ALERT: [HIGH] volume_spike: 
requests_volume=600.00 (expected ~100.00, +500.0% change, 5.00σ deviation)
```

### Background Monitoring

```python
async def _monitor_loop(self):
    while self._running:
        await asyncio.sleep(check_interval_seconds)
        
        # Check for anomalies
        anomalies = self.check_anomalies()
        
        # Alert
        for anomaly in anomalies:
            self._alert(anomaly)
```

## Testing

**28 comprehensive tests** (100% pass rate):

```bash
pytest tests/test_anomaly_detection.py -v
# ================ 28 passed in 1.57s ================
```

### Test Coverage

✅ **MetricWindow** (6 tests):
- Creation
- Adding values
- Window overflow (FIFO)
- Mean calculation
- Standard deviation
- Ready check (minimum samples)

✅ **Anomaly** (3 tests):
- Creation
- to_dict() serialization
- String representation

✅ **AnomalyDetector** (13 tests):
- Detector creation
- Track metrics
- Track with tenant ID
- Volume spike detection
- Volume drop detection
- Flag rate spike detection
- Flag rate drop detection
- Latency spike detection
- Error rate spike detection
- No false positives with normal variation
- Cooldown period
- Minimum samples requirement
- Alert callbacks
- Background monitoring loop

✅ **AlertSystem** (3 tests):
- Creation
- Log alerts
- Color mapping

✅ **Integration** (2 tests):
- End-to-end detection and alert
- Multiple metric types

### Test Examples

**Volume Spike Detection**:
```python
def test_volume_spike_detection(detector):
    # Establish baseline: 100 requests
    for _ in range(10):
        detector.track_metric("requests_volume", 100.0)
    
    # Spike to 600 (6x)
    detector.track_metric("requests_volume", 600.0)
    
    # Check
    anomalies = detector.check_anomalies()
    
    assert len(anomalies) == 1
    assert anomalies[0].type == AnomalyType.VOLUME_SPIKE
    assert anomalies[0].current_value == 600.0
```

## Usage

### Automatic Monitoring

```python
# Starts automatically on service startup
from analytics import get_anomaly_detector, create_alert_system

detector = get_anomaly_detector()
alert_system = create_alert_system()

# Register callback
detector.register_alert_callback(alert_system.send_alert)

# Start monitoring
await detector.start_monitoring()
```

### Manual Tracking

```python
from analytics import get_anomaly_detector

detector = get_anomaly_detector()

# Track metrics
detector.track_metric("requests_volume", 150.0)
detector.track_metric("flag_rate", 0.05)
detector.track_metric("latency_avg", 200.0)

# With tenant ID
detector.track_metric("requests_volume", 100.0, tenant_id="tenant-123")

# Check for anomalies
anomalies = detector.check_anomalies()

for anomaly in anomalies:
    print(f"Detected: {anomaly}")
```

### Custom Alert Callbacks

```python
def custom_handler(anomaly):
    if anomaly.severity == AnomalySeverity.CRITICAL:
        page_on_call_engineer()
    
    log_to_datadog(anomaly)

detector.register_alert_callback(custom_handler)
```

## Configuration

### Environment Variables

```bash
# Detection parameters
export ANOMALY_WINDOW_SIZE=60        # Sliding window (samples)
export ANOMALY_Z_THRESHOLD=3.0       # Z-score threshold
export ANOMALY_CHECK_INTERVAL=60     # Check interval (seconds)

# Alert channels
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export EMAIL_ALERTS_ENABLED=0
export LOG_ALERTS_ENABLED=1

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### Tuning Sensitivity

**High Sensitivity** (more alerts):
```python
detector = AnomalyDetector(
    z_threshold=2.0,
    volume_threshold_multiplier=3.0,
    flag_rate_threshold=0.10
)
```

**Low Sensitivity** (fewer alerts):
```python
detector = AnomalyDetector(
    z_threshold=4.0,
    volume_threshold_multiplier=10.0,
    flag_rate_threshold=0.25
)
```

## Files Added/Modified

**6 files, 2,000+ lines**

### New Files (5)

**Analytics Module** (2):
- src/analytics/anomaly_detector.py (550 lines) - Detection engine
- src/analytics/alerts.py (150 lines) - Alert system

**Tests** (1):
- tests/test_anomaly_detection.py (550 lines) - 28 comprehensive tests

**Documentation** (2):
- docs/ANOMALY_DETECTION.md (600+ lines) - Complete guide
- ANOMALY_DETECTION_SUMMARY.md - This summary

### Modified Files (2)
- src/analytics/__init__.py - Module exports
- src/service/api.py - Background monitoring startup

## Acceptance Criteria

✅ Multiple anomaly types (volume, flag rate, latency, error)  
✅ Statistical detection (z-score, thresholds)  
✅ Sliding window for baseline calculation  
✅ Severity levels (low, medium, high, critical)  
✅ Alert system (Slack, email, logs)  
✅ Background monitoring service  
✅ Cooldown period to prevent alert fatigue  
✅ Multi-tenant support  
✅ Configurable thresholds and sensitivity  
✅ Minimum samples requirement (warm-up)  
✅ 28 comprehensive tests (all passing)  
✅ Complete documentation with examples  

## Benefits

### For Operations

- ✅ **Early Warning**: Detect issues before they escalate
- ✅ **Proactive Monitoring**: No manual checking required
- ✅ **Reduced MTTR**: Faster issue identification and resolution
- ✅ **Automated Alerts**: Immediate notification via Slack/email

### For Security

- ✅ **Abuse Detection**: Identify unusual traffic patterns
- ✅ **Attack Prevention**: Detect coordinated abuse early
- ✅ **Model Drift**: Catch changes in flag rate (model issues)

### For Reliability

- ✅ **System Health**: Monitor latency and error rates
- ✅ **Performance**: Detect degradation early
- ✅ **Capacity Planning**: Identify traffic growth

## Use Cases

### Model Drift Detection

```python
# Normal: 5% flag rate
# Drift: Suddenly 35% flagged
# Alert: FLAG_RATE_SPIKE detected
# Action: Review model, retrain if needed
```

### Abuse Detection

```python
# Normal: 100 req/min
# Abuse: Suddenly 600 req/min (6x)
# Alert: VOLUME_SPIKE detected
# Action: Rate limit, investigate source
```

### System Degradation

```python
# Normal: 150ms latency
# Degradation: Suddenly 600ms
# Alert: LATENCY_SPIKE detected
# Action: Check infrastructure, scale up
```

### Filter Failure

```python
# Normal: 30% flagged
# Failure: Suddenly 5% flagged
# Alert: FLAG_RATE_DROP detected
# Action: Check filter configuration
```

## Performance

**Efficient**:
- O(1) metric tracking (deque append)
- O(n) anomaly check (where n = window_size)
- Async background monitoring (non-blocking)
- Cooldown prevents excessive checks

**Scalable**:
- Per-tenant metric tracking
- Configurable window sizes
- Background task doesn't block main thread

## Security

- **Multi-Tenant Isolation**: Separate metrics per tenant
- **No Sensitive Data**: Only aggregated metrics
- **Secure Webhooks**: HTTPS for Slack integration
- **Rate Limiting**: Cooldown prevents alert spam

## Future Enhancements

- [ ] Machine learning-based detection
- [ ] Seasonal/trend analysis
- [ ] Predictive anomalies
- [ ] Custom metric definitions
- [ ] Dashboard for anomaly history
- [ ] Auto-remediation actions
- [ ] Integration with PagerDuty
- [ ] Email alert templates

## Related

- Complements usage statistics
- Enables proactive monitoring
- Supports SRE best practices
- Foundation for auto-remediation

---

**Implementation Complete** ✅

Anomaly detection ready for production with comprehensive testing, multi-channel alerting, and statistical rigor.

