# Usage Quotas - Quick Start

Get started with usage quota enforcement in 5 minutes.

## Installation

The quota system is included in the main codebase. Just ensure you have the latest version:

```bash
git pull origin main
pip install -e .
```

## Enable Quota Tracking

### 1. Start Service

The quota tables are automatically created on startup:

```bash
PYTHONPATH=src uvicorn service.api:app --port 8001
```

You should see:
```
INFO: Usage quota tracking enabled
INFO: Usage quota tables initialized
```

### 2. Choose Limit Mode

**Soft Limit (Default)** - Allows overage with warnings:
```bash
# No configuration needed - this is the default
```

**Hard Limit** - Blocks requests over quota:
```bash
export ENFORCE_USAGE_QUOTA=1
PYTHONPATH=src uvicorn service.api:app --port 8001
```

## Basic Usage

### Make API Requests

All `/score` endpoints are automatically tracked:

```bash
curl -X POST http://localhost:8001/score \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "test message", "guards": ["default"]}'
```

### Check Usage Headers

Every response includes usage information:

```http
HTTP/1.1 200 OK
X-Usage-Count: 1
X-Usage-Period: 2024-10
X-Usage-Limit: 10000
X-Usage-Remaining: 9999
```

## CLI Management

### Check Tenant Usage

```bash
python -m seval.quotas.cli usage tenant-123
```

Output:
```
Tenant: tenant-123
Period: 2024-10
Plan: free
Usage: 5,432
Quota: 10,000
Percentage: 54.3%
```

### Upgrade Tenant Plan

```bash
# Upgrade to pro
python -m seval.quotas.cli set-plan tenant-123 pro

# Custom quota
python -m seval.quotas.cli set-plan tenant-123 custom --quota 50000
```

### List All Tenants

```bash
python -m seval.quotas.cli list
```

Output:
```
Tenant ID                      Period     Plan         Usage     Quota      %
------------------------------------------------------------------------------------------
tenant-123                     2024-10    free         8,432    10,000   84.3%
tenant-456                     2024-10    pro        125,000 1,000,000   12.5%
tenant-789                     2024-10    enterprise 500,000         ∞      -
```

### Reset Usage

```bash
# Reset specific tenant
python -m seval.quotas.cli reset --tenant-id tenant-123

# Reset all tenants (for new billing period)
python -m seval.quotas.cli reset --all
```

## Plan Types

| Plan       | Quota/Month | Cost Example |
|------------|-------------|--------------|
| Free       | 10,000      | $0           |
| Starter    | 100,000     | $29/mo       |
| Pro        | 1,000,000   | $199/mo      |
| Enterprise | Unlimited   | Custom       |

## Testing Quotas

### Simulate Free Tier Limit

```bash
# Use quota tracking endpoint multiple times
for i in {1..10001}; do
  curl -X POST http://localhost:8001/score \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text": "test", "guards": ["default"]}' \
    -w "\nStatus: %{http_code}\n"
done
```

With **soft limit**: All requests succeed, but after 10,000:
```http
HTTP/1.1 200 OK
X-Usage-Exceeded: Quota exceeded (10001/10000). Upgrade to continue.
```

With **hard limit** (`ENFORCE_USAGE_QUOTA=1`): Request 10,001 fails:
```http
HTTP/1.1 402 Payment Required
{
  "error": "quota_exceeded",
  "message": "Monthly quota of 10000 evaluations exceeded",
  "usage": 10001,
  "limit": 10000,
  "period": "2024-10",
  "action": "Upgrade your plan to continue using the API"
}
```

## Programmatic Usage

### Check Usage in Code

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()
usage = enforcer.get_usage("tenant-123")

if usage.quota_warning:
    print(f"⚠️  Warning: {usage.usage_count}/{usage.monthly_quota}")

if usage.quota_exceeded:
    print(f"🚫 Quota exceeded!")
```

### Set Plan Programmatically

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()

# Upgrade to pro
enforcer.set_tenant_plan("tenant-123", "pro")

# Enterprise (unlimited)
enforcer.set_tenant_plan("tenant-789", "enterprise")
```

### Track Custom Events

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()

# Track a batch of evaluations
enforcer.increment_usage("tenant-123", amount=50)
```

## Automation

### Cron Job for Monthly Reset

Although usage auto-resets on first request of new month, you can proactively reset all tenants:

```bash
# Add to crontab
0 0 1 * * cd /app && python -m seval.quotas.cli reset --all
```

### Alert on High Usage

```python
from seval.quotas import get_quota_enforcer

enforcer = get_quota_enforcer()

for tenant_id in get_all_tenant_ids():
    usage = enforcer.get_usage(tenant_id)
    
    if usage.quota_warning and not usage.quota_exceeded:
        send_email(
            to=tenant_email,
            subject="Usage Alert: 90% Quota Used",
            body=f"You've used {usage.usage_count:,} of your "
                 f"{usage.monthly_quota:,} monthly evaluations."
        )
```

## Troubleshooting

### Quotas Not Tracking

Check logs for initialization:
```bash
grep "Usage quota" /var/log/service.log
```

Should see:
```
INFO: Usage quota tracking enabled
INFO: Usage quota tables initialized
```

### Usage Headers Missing

1. Verify endpoint is tracked (see `UsageTrackingMiddleware.TRACKED_ENDPOINTS`)
2. Ensure middleware is registered before route handlers
3. Check authentication provides `tenant_id`

### Wrong Count

Verify atomic increments are working:
```sql
sqlite3 history.db "SELECT * FROM tenant_usage;"
```

## Next Steps

- Read full documentation: [docs/USAGE_QUOTAS.md](USAGE_QUOTAS.md)
- Implement usage dashboard UI
- Add webhook notifications for quota events
- Configure alerts for sales team on high-usage tenants
- Set up Stripe integration for paid plans

## Support

For issues or questions:
- Check full docs: `docs/USAGE_QUOTAS.md`
- Run tests: `pytest tests/test_usage_quotas.py -v`
- File issue on GitHub

