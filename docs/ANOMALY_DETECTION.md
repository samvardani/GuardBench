# Anomaly Detection for Safety Metrics

This document describes the automated anomaly detection system that monitors safety metrics and triggers alerts for unusual patterns, enabling early detection of issues like model drift, abuse, or system failures.

## Overview

The anomaly detection system continuously monitors key safety metrics and uses statistical methods to identify deviations from normal behavior. When anomalies are detected, alerts are automatically triggered through configured channels (logs, Slack, email).

## Features

✅ **Multiple Anomaly Types**: Volume spikes/drops, flag rate changes, latency spikes, error rate spikes  
✅ **Statistical Detection**: Z-score, moving average, threshold-based methods  
✅ **Sliding Window**: Configurable time windows for baseline calculation  
✅ **Severity Levels**: Low, medium, high, critical based on deviation magnitude  
✅ **Alert System**: Slack, email, and log-based notifications  
✅ **Cooldown Period**: Prevents alert fatigue with configurable cooldown  
✅ **Multi-Tenant Support**: Per-tenant metric tracking and alerting  
✅ **Background Monitoring**: Async loop with configurable check intervals  
✅ **Warm-up Period**: Minimum samples requirement before detection  

## Anomaly Types

### Volume Anomalies

**Volume Spike**: Unusual increase in request volume
```python
# Example: Normal ~100 requests/min, suddenly 600
# Threshold: 5x multiplier (configurable)
```

**Volume Drop**: Significant decrease in request volume
```python
# Example: Normal ~100 requests/min, suddenly 10
# Threshold: <20% of baseline when baseline >10
```

### Flag Rate Anomalies

**Flag Rate Spike**: Sudden increase in flagged content percentage
```python
# Example: Normally 5% flagged, suddenly 35%
# Threshold: 15% absolute change (configurable)
# Possible causes: Model drift, new attack patterns
```

**Flag Rate Drop**: Sudden decrease in flagged content percentage
```python
# Example: Normally 30% flagged, suddenly 5%
# Threshold: 15% absolute change
# Possible causes: Model misconfiguration, filtering failure
```

### Latency Anomalies

**Latency Spike**: Response time significantly higher than baseline
```python
# Example: Normally 150ms, suddenly 600ms
# Threshold: 3x multiplier (configurable)
```

### Error Rate Anomalies

**Error Spike**: Increase in error rate
```python
# Example: Normally 1% errors, suddenly 15%
# Threshold: 5% absolute change (configurable)
```

## Architecture

```
Metrics → Track in Sliding Window → Statistical Analysis
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

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMALY_WINDOW_SIZE` | `60` | Sliding window size (samples) |
| `ANOMALY_Z_THRESHOLD` | `3.0` | Z-score threshold for detection |
| `ANOMALY_CHECK_INTERVAL` | `60.0` | Check interval (seconds) |
| `SLACK_WEBHOOK_URL` | None | Slack webhook for alerts |
| `EMAIL_ALERTS_ENABLED` | `0` | Enable email alerts |
| `LOG_ALERTS_ENABLED` | `1` | Enable log alerts |

### Example Configuration

```bash
# Enable anomaly detection with Slack alerts
export ANOMALY_WINDOW_SIZE=60
export ANOMALY_Z_THRESHOLD=3.0
export ANOMALY_CHECK_INTERVAL=60
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
export LOG_ALERTS_ENABLED=1

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

## Usage

### Automatic Monitoring

Anomaly detection starts automatically on service startup:

```python
# In service/api.py (automatic)
from analytics import get_anomaly_detector, create_alert_system

detector = get_anomaly_detector()
alert_system = create_alert_system()

# Register alert callback
detector.register_alert_callback(alert_system.send_alert)

# Start monitoring
await detector.start_monitoring()
```

### Manual Tracking

Track metrics manually:

```python
from analytics import get_anomaly_detector

detector = get_anomaly_detector()

# Track volume
detector.track_metric("requests_volume", 150.0)

# Track flag rate
detector.track_metric("flag_rate", 0.05)

# Track latency
detector.track_metric("latency_avg", 200.0)

# Track with tenant ID
detector.track_metric("requests_volume", 100.0, tenant_id="tenant-123")
```

### Manual Anomaly Check

```python
# Check for anomalies
anomalies = detector.check_anomalies()

for anomaly in anomalies:
    print(f"Detected: {anomaly}")
    print(f"  Type: {anomaly.type.value}")
    print(f"  Severity: {anomaly.severity.value}")
    print(f"  Current: {anomaly.current_value}")
    print(f"  Expected: {anomaly.expected_value}")
```

### Custom Alert Callback

Register custom alert handlers:

```python
def my_alert_handler(anomaly):
    print(f"ALERT: {anomaly}")
    
    # Send to custom system
    if anomaly.severity == AnomalySeverity.CRITICAL:
        page_on_call_engineer()

detector.register_alert_callback(my_alert_handler)
```

## Statistical Methods

### Z-Score Detection

Detects deviations based on standard deviations:

```python
z_score = (current_value - mean) / std_dev

if z_score > threshold:  # Default: 3.0
    # Anomaly detected
```

**Severity Calculation**:
- `z > 5`: Critical
- `z > 4`: High
- `z > 3`: Medium
- `z ≤ 3`: Low

### Threshold-Based Detection

Direct comparison with baseline:

```python
# Volume spike
if current > baseline * 5:
    # Anomaly detected

# Flag rate spike
if abs(current - baseline) > 0.15:
    # Anomaly detected
```

### Sliding Window

Maintains recent history for baseline:

```python
window_size = 60  # 60 samples (e.g., 1 hour at 1 min/sample)
min_samples = 10  # Minimum before detection starts

# FIFO queue
values = deque(maxlen=window_size)
```

## Alert System

### Slack Alerts

**Format**:
```json
{
  "attachments": [
    {
      "color": "#ff0000",
      "title": "🚨 Anomaly Detected: volume_spike",
      "text": "[HIGH] volume_spike: requests_volume=600.00 (expected ~100.00, +500% change, 5.00σ deviation)",
      "fields": [
        {"title": "Metric", "value": "requests_volume"},
        {"title": "Severity", "value": "HIGH"},
        {"title": "Current Value", "value": "600.00"},
        {"title": "Expected Value", "value": "100.00"}
      ]
    }
  ]
}
```

**Color Codes**:
- Low: Green (`#36a64f`)
- Medium: Orange (`#ff9900`)
- High: Red (`#ff0000`)
- Critical: Dark Red (`#8b0000`)

### Log Alerts

```
WARNING - 🚨 ANOMALY ALERT: [HIGH] volume_spike: requests_volume=600.00 (expected ~100.00, +500.0% change, 5.00σ deviation)
```

### Email Alerts

Placeholder for SMTP or SendGrid integration:

```python
def _send_email_alert(self, anomaly):
    # TODO: Implement via SMTP or service
    pass
```

## Examples

### Example 1: Volume Spike Detection

```python
from analytics import AnomalyDetector

detector = AnomalyDetector(
    window_size=60,
    min_samples=10,
    volume_threshold_multiplier=5.0
)

# Establish baseline: 100 requests/minute
for _ in range(20):
    detector.track_metric("requests_volume", 100.0)

# Sudden spike: 600 requests/minute (6x)
detector.track_metric("requests_volume", 600.0)

# Check
anomalies = detector.check_anomalies()

assert len(anomalies) == 1
assert anomalies[0].type == AnomalyType.VOLUME_SPIKE
# Output: [HIGH] volume_spike: requests_volume=600.00 (expected ~100.00, +500.0% change)
```

### Example 2: Flag Rate Spike Detection

```python
# Establish baseline: 5% flag rate
for _ in range(20):
    detector.track_metric("flag_rate", 0.05)

# Sudden spike: 35% flag rate
detector.track_metric("flag_rate", 0.35)

# Check
anomalies = detector.check_anomalies()

assert anomalies[0].type == AnomalyType.FLAG_RATE_SPIKE
# Possible cause: Model drift or new attack pattern
```

### Example 3: Multi-Metric Monitoring

```python
# Monitor multiple metrics
for i in range(30):
    detector.track_metric("requests_volume", 100.0)
    detector.track_metric("flag_rate", 0.05)
    detector.track_metric("latency_avg", 150.0)
    detector.track_metric("error_rate", 0.01)

# Trigger anomalies
detector.track_metric("requests_volume", 600.0)  # Volume spike
detector.track_metric("flag_rate", 0.35)  # Flag rate spike
detector.track_metric("latency_avg", 600.0)  # Latency spike

# Check
anomalies = detector.check_anomalies()

# Detects all three
assert len(anomalies) == 3
```

### Example 4: Per-Tenant Monitoring

```python
# Track for multiple tenants
detector.track_metric("requests_volume", 100.0, tenant_id="tenant-a")
detector.track_metric("requests_volume", 200.0, tenant_id="tenant-b")

# Spike for tenant-a only
detector.track_metric("requests_volume", 600.0, tenant_id="tenant-a")

# Check
anomalies = detector.check_anomalies()

# Only tenant-a anomaly detected
assert anomalies[0].tenant_id == "tenant-a"
```

## Tuning

### Sensitivity

Adjust detection sensitivity via thresholds:

**High Sensitivity** (more alerts):
```python
detector = AnomalyDetector(
    z_threshold=2.0,  # Lower (detect smaller deviations)
    volume_threshold_multiplier=3.0,  # Lower
    flag_rate_threshold=0.10  # Lower
)
```

**Low Sensitivity** (fewer alerts):
```python
detector = AnomalyDetector(
    z_threshold=4.0,  # Higher
    volume_threshold_multiplier=10.0,  # Higher
    flag_rate_threshold=0.25  # Higher
)
```

### Cooldown

Prevent alert fatigue:

```python
detector = AnomalyDetector(
    cooldown_seconds=300.0  # 5 minutes
)

# After alert, same metric won't alert for 5 minutes
```

### Window Size

Balance responsiveness vs stability:

```python
# Short window (more responsive, less stable)
detector = AnomalyDetector(window_size=30)  # 30 minutes

# Long window (more stable, less responsive)
detector = AnomalyDetector(window_size=120)  # 2 hours
```

## Integration with Usage Statistics

Combine with usage tracking:

```python
from analytics import get_usage_tracker, get_anomaly_detector

tracker = get_usage_tracker()
detector = get_anomaly_detector()

# Track request
tracker.track_request("tenant-123", flagged=True)

# Calculate metrics
stats = tracker.get_daily_stats("tenant-123", limit=1)[0]

# Track for anomaly detection
detector.track_metric("requests_volume", stats.total_requests)
detector.track_metric("flag_rate", stats.flagged_requests / stats.total_requests)
```

## Testing

Run anomaly detection tests:

```bash
pytest tests/test_anomaly_detection.py -v
```

**28 comprehensive tests** covering:
- ✅ MetricWindow (6 tests)
- ✅ Anomaly model (3 tests)
- ✅ AnomalyDetector (13 tests)
  - Volume spikes/drops
  - Flag rate spikes/drops
  - Latency spikes
  - Error rate spikes
  - No false positives
  - Cooldown periods
  - Minimum samples
  - Alert callbacks
  - Background monitoring
- ✅ AlertSystem (3 tests)
- ✅ Integration (2 tests)

## Troubleshooting

### No Alerts Being Triggered

**Check configuration**:
```bash
echo $ANOMALY_WINDOW_SIZE
echo $ANOMALY_Z_THRESHOLD
echo $SLACK_WEBHOOK_URL
```

**Check if monitoring is running**:
```bash
# Look for log message
grep "Anomaly detection monitoring started" /var/log/service.log
```

**Lower sensitivity for testing**:
```python
detector = AnomalyDetector(z_threshold=2.0)
```

### Too Many False Positives

**Increase thresholds**:
```python
detector = AnomalyDetector(
    z_threshold=4.0,
    volume_threshold_multiplier=10.0
)
```

**Increase minimum samples**:
```python
detector = AnomalyDetector(min_samples=20)
```

**Increase cooldown**:
```python
detector = AnomalyDetector(cooldown_seconds=600)  # 10 minutes
```

### Alerts Not Reaching Slack

**Verify webhook URL**:
```bash
curl -X POST $SLACK_WEBHOOK_URL \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Test message"}'
```

**Check httpx is installed**:
```bash
pip show httpx
```

**Check logs for errors**:
```bash
grep "Failed to send Slack alert" /var/log/service.log
```

## Best Practices

1. **Start Conservative**: Begin with high thresholds, lower gradually
2. **Monitor Alerts**: Review alert frequency and tune accordingly
3. **Set Cooldowns**: Prevent alert fatigue with appropriate cooldowns
4. **Use Multiple Channels**: Log + Slack for redundancy
5. **Test Regularly**: Simulate anomalies to verify detection
6. **Document Thresholds**: Record why specific values were chosen
7. **Review Alerts**: Investigate all alerts, tune false positives
8. **Combine with Dashboards**: Use dashboards for visual confirmation

## Related Documentation

- [Usage Statistics](USAGE_STATISTICS.md)
- [Monitoring](MONITORING.md)
- [Alerts](ALERTS.md)
- [Configuration](CONFIG.md)

## Support

For anomaly detection issues:
1. Check logs for "Anomaly detection monitoring started"
2. Verify configuration (window size, thresholds)
3. Test with simulated anomalies
4. Review Slack webhook configuration
5. Check alert callback registration

