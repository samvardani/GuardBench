# Usage Quota Enforcement

This document describes the usage quota enforcement system for SaaS monetization of the Safety-Eval-Mini service.

## Overview

The usage quota system tracks API usage per tenant and enforces monthly limits based on subscription plans. This enables a freemium model with a free tier (10k evaluations/month) and paid plans for higher usage.

## Architecture

### Components

1. **Database Schema** (`src/seval/quotas/schema.py`)
   - `tenant_usage`: Tracks usage count per tenant per month
   - `tenant_plans`: Stores plan type and quota limits per tenant

2. **Quota Enforcer** (`src/seval/quotas/enforcer.py`)
   - Atomic usage increment with SQLite transactions
   - Soft and hard limit enforcement
   - Plan-based quota management

3. **Middleware** (`src/seval/quotas/middleware.py`)
   - Tracks usage for API endpoints
   - Adds usage headers to responses
   - Blocks requests when quota exceeded (if hard limit enabled)

4. **Reset Logic** (`src/seval/quotas/reset.py`)
   - Monthly usage reset
   - Can be called from cron job or scheduler

## Plan Types

| Plan       | Monthly Quota | Description                     |
|------------|---------------|----------------------------------|
| free       | 10,000        | Free tier for testing/small use |
| starter    | 100,000       | Starter plan                    |
| pro        | 1,000,000     | Professional plan               |
| enterprise | Unlimited     | Enterprise plan (no limits)     |

## Configuration

### Environment Variables

```bash
# Enable hard limit (block requests over quota)
export ENFORCE_USAGE_QUOTA=1

# If not set, soft limit is used (warning headers only)
# export ENFORCE_USAGE_QUOTA=0
```

### Custom Quotas

You can customize quotas programmatically:

```python
from seval.quotas import QuotaEnforcer

enforcer = QuotaEnforcer(
    enforce_hard_limit=True,
    quotas={
        "free": 5_000,
        "pro": 500_000,
        "enterprise": None,
    }
)
```

## Usage Tracking

### Tracked Endpoints

The following endpoints count toward usage:

- `/score` - Single evaluation
- `/score-image` - Image evaluation
- `/batch-score` - Batch evaluation

### Usage Headers

Responses include usage information in headers:

```http
X-Usage-Count: 245
X-Usage-Period: 2024-10
X-Usage-Limit: 10000
X-Usage-Remaining: 9755
X-Usage-Warning: Approaching quota limit (9500/10000)
```

## Soft vs Hard Limits

### Soft Limit (Default)

- Allows requests beyond quota
- Adds warning header when approaching limit
- Adds exceeded header when over quota
- Useful for graceful degradation and upsell opportunities

```http
X-Usage-Exceeded: Quota exceeded (10100/10000). Upgrade to continue.
```

### Hard Limit

Enable with `ENFORCE_USAGE_QUOTA=1`

- Blocks requests that would exceed quota
- Returns HTTP 402 Payment Required
- Includes usage details in error response

```json
{
  "error": "quota_exceeded",
  "message": "Monthly quota of 10000 evaluations exceeded",
  "usage": 10001,
  "limit": 10000,
  "period": "2024-10",
  "action": "Upgrade your plan to continue using the API"
}
```

## Monthly Reset

### Automatic Reset

Usage counts are automatically reset when entering a new billing period (month). The enforcer checks the period on each request and creates new period entries as needed.

### Manual Reset

Reset all tenants:

```python
from seval.quotas.reset import UsageResetter

resetter = UsageResetter()
stats = resetter.check_and_reset_all()
print(f"Reset {stats['reset_count']} tenants")
```

Reset specific tenant:

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()
enforcer.reset_usage("tenant-123")
```

### Cron Job

Schedule monthly resets (optional, since automatic reset is built-in):

```bash
# Reset at midnight on 1st of each month
0 0 1 * * cd /app && python -c "from seval.quotas.reset import reset_usage_for_new_month; reset_usage_for_new_month()"
```

## Managing Plans

### Set Tenant Plan

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()

# Upgrade to pro
enforcer.set_tenant_plan("tenant-123", "pro")

# Custom quota
enforcer.set_tenant_plan("tenant-456", "custom", monthly_quota=50_000)

# Unlimited (enterprise)
enforcer.set_tenant_plan("tenant-789", "enterprise")
```

### Query Usage

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()
usage = enforcer.get_usage("tenant-123")

print(f"Plan: {usage.plan_type}")
print(f"Usage: {usage.usage_count}/{usage.monthly_quota}")
print(f"Period: {usage.period}")
print(f"Exceeded: {usage.quota_exceeded}")
print(f"Warning: {usage.quota_warning}")
```

## Database Schema

### `tenant_usage`

```sql
CREATE TABLE tenant_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    period TEXT NOT NULL,          -- Format: YYYY-MM
    usage_count INTEGER DEFAULT 0,
    last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, period)
);

CREATE INDEX idx_tenant_usage_lookup ON tenant_usage(tenant_id, period);
```

### `tenant_plans`

```sql
CREATE TABLE tenant_plans (
    tenant_id TEXT PRIMARY KEY,
    plan_type TEXT NOT NULL DEFAULT 'free',
    monthly_quota INTEGER,         -- NULL = unlimited
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);
```

## Concurrency Safety

The quota enforcer uses atomic SQLite operations to handle concurrent requests safely:

```sql
INSERT INTO tenant_usage (tenant_id, period, usage_count, updated_at)
VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(tenant_id, period) DO UPDATE SET
    usage_count = usage_count + ?,
    updated_at = CURRENT_TIMESTAMP
```

This ensures accurate counting even under high concurrent load.

## Testing

Run quota enforcement tests:

```bash
pytest tests/test_usage_quotas.py -v
```

### Test Scenarios Covered

- ✅ Basic usage increment and tracking
- ✅ Quota warning at 90% threshold
- ✅ Soft limit allows overage
- ✅ Hard limit blocks overage
- ✅ Plan upgrades and downgrades
- ✅ Unlimited (enterprise) plans
- ✅ Custom quotas
- ✅ Monthly reset
- ✅ Concurrent increments (atomic)
- ✅ Quota boundary race conditions
- ✅ Usage headers in responses
- ✅ HTTP 402 error on quota exceeded

### Load Testing

Test concurrent usage tracking:

```bash
# Generate concurrent requests
ab -n 10000 -c 100 -H "Authorization: Bearer YOUR_TOKEN" \
   -H "Content-Type: application/json" \
   -p score_payload.json \
   http://localhost:8001/score
```

## Monitoring

### Prometheus Metrics (Optional)

Add custom metrics for quota monitoring:

```python
from prometheus_client import Gauge

quota_usage = Gauge(
    'tenant_quota_usage',
    'Current usage count per tenant',
    ['tenant_id', 'plan_type']
)

# Update periodically
quota_usage.labels(tenant_id="tenant-123", plan_type="free").set(5000)
```

### Alerting

Set up alerts for tenants approaching limits:

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()

for tenant_id in get_all_tenant_ids():
    usage = enforcer.get_usage(tenant_id)
    
    if usage.quota_warning:
        # Send email/Slack notification
        notify_sales(
            f"Tenant {tenant_id} at {usage.usage_count}/{usage.monthly_quota} "
            f"- upgrade opportunity!"
        )
```

## Migration

Initialize usage tables in existing database:

```python
from seval.quotas import init_usage_tables
import sqlite3

conn = sqlite3.connect("history.db")
init_usage_tables(conn)
conn.close()
```

The tables are automatically created on service startup.

## Best Practices

1. **Start with Soft Limits**
   - Use soft limits initially to avoid disrupting users
   - Monitor usage patterns and adjust quotas
   - Enable hard limits after establishing baseline

2. **Upsell Opportunities**
   - Monitor tenants approaching limits
   - Send proactive upgrade offers
   - Provide usage dashboards to tenants

3. **Graceful Degradation**
   - Return clear error messages
   - Include upgrade instructions in responses
   - Provide self-service upgrade path

4. **Usage Analytics**
   - Track usage trends per tenant
   - Identify power users for custom plans
   - Monitor quota effectiveness

## Troubleshooting

### Usage Not Tracking

1. Check middleware is enabled:
   ```bash
   # Look for "Usage quota tracking enabled" in logs
   grep "Usage quota tracking" /var/log/service.log
   ```

2. Verify tables exist:
   ```sql
   SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%usage%';
   ```

3. Check endpoint is tracked:
   ```python
   from seval.quotas.middleware import UsageTrackingMiddleware
   print(UsageTrackingMiddleware.TRACKED_ENDPOINTS)
   ```

### Race Conditions

If you see inconsistent counts under load:

1. Verify SQLite is using UPSERT correctly
2. Check for database locking issues
3. Consider connection pooling

### Reset Not Working

1. Check current period logic:
   ```python
   from seval.quotas import get_quota_enforcer
   enforcer = get_quota_enforcer()
   print(enforcer._get_current_period())
   ```

2. Verify reset was called:
   ```sql
   SELECT tenant_id, period, last_reset_at FROM tenant_usage;
   ```

## API Reference

See inline documentation:

```python
from seval.quotas import QuotaEnforcer

help(QuotaEnforcer.increment_usage)
help(QuotaEnforcer.get_usage)
help(QuotaEnforcer.set_tenant_plan)
```

## Related Documents

- [SaaS Pricing Strategy](docs/PRICING.md) (if available)
- [Multi-Tenant Auth](docs/AUTH.md)
- [Database Schema](docs/DATABASE.md)
- [API Documentation](docs/API.md)

## Future Enhancements

- [ ] Rate limiting per plan tier (requests/second)
- [ ] Usage analytics dashboard
- [ ] Webhook notifications on quota events
- [ ] Self-service plan management UI
- [ ] Usage prediction and forecasting
- [ ] Overages with pay-per-use pricing
- [ ] Annual billing with monthly quotas
- [ ] Team member seat-based pricing

