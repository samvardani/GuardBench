# Tenant Usage Statistics

This document describes the tenant usage statistics system for monitoring API consumption and capacity planning.

## Overview

The usage statistics system tracks per-tenant API usage metrics, including request counts, flagged content, category breakdown, guard usage, and performance metrics. This enables administrators and users to monitor consumption patterns, identify trends, and plan capacity.

## Features

✅ **Per-Tenant Tracking**: Isolated statistics for each tenant  
✅ **Daily/Hourly Granularity**: Time-series data for trend analysis  
✅ **Category Breakdown**: Track which categories are most flagged  
✅ **Guard Usage**: Monitor which guards are used most  
✅ **Performance Metrics**: Latency tracking (avg, p50, p90, p99)  
✅ **Beautiful Dashboard**: Interactive charts and visualizations  
✅ **Quota Monitoring**: Track usage against free tier limits  
✅ **Real-Time Updates**: Auto-refresh every 60 seconds  

## Data Model

### Daily Usage (tenant_usage_daily)

```sql
CREATE TABLE tenant_usage_daily (
    id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    
    -- Request counts
    total_requests INTEGER DEFAULT 0,
    flagged_requests INTEGER DEFAULT 0,
    safe_requests INTEGER DEFAULT 0,
    
    -- Category breakdown (JSON)
    category_counts TEXT,  -- {"violence": 10, "hate": 5}
    
    -- Guard breakdown (JSON)
    guard_counts TEXT,  -- {"internal": 100, "openai": 50}
    
    -- Latency stats
    avg_latency_ms INTEGER DEFAULT 0,
    
    -- Errors
    error_count INTEGER DEFAULT 0,
    
    UNIQUE(tenant_id, date)
);
```

### Hourly Usage (tenant_usage_hourly)

```sql
CREATE TABLE tenant_usage_hourly (
    id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    hour TEXT NOT NULL,  -- YYYY-MM-DD HH:00
    
    total_requests INTEGER DEFAULT 0,
    flagged_requests INTEGER DEFAULT 0,
    
    UNIQUE(tenant_id, hour)
);
```

## Tracking Usage

### Automatic Tracking

Usage is tracked automatically on each request (when integrated):

```python
from analytics import get_usage_tracker

tracker = get_usage_tracker()

# Track a request
tracker.track_request(
    tenant_id="tenant-123",
    flagged=True,
    category="violence",
    guard="internal",
    latency_ms=150,
    error=False
)
```

### Manual Tracking

```python
# Track multiple requests
for request in requests:
    tracker.track_request(
        tenant_id=request.tenant_id,
        flagged=request.is_flagged,
        category=request.category,
        guard=request.guard_name,
        latency_ms=request.latency
    )
```

## API Endpoints

### GET /analytics/usage

Get usage statistics for a tenant.

**Query Parameters**:
- `tenant_id` (str): Tenant identifier (default: "public")
- `days` (int): Number of days to retrieve (default: 30, max: 365)
- `start_date` (str, optional): Start date (YYYY-MM-DD)
- `end_date` (str, optional): End date (YYYY-MM-DD)

**Response**:

```json
{
  "tenant_id": "tenant-123",
  "days": 30,
  "total_requests": 5000,
  "flagged_requests": 250,
  "safe_requests": 4750,
  "flagged_rate": 0.05,
  "avg_latency_ms": 145,
  "top_categories": [
    {"name": "violence", "count": 100},
    {"name": "hate", "count": 80},
    {"name": "self-harm", "count": 50}
  ],
  "top_guards": [
    {"name": "internal", "count": 4000},
    {"name": "openai", "count": 1000}
  ],
  "daily_stats": [
    {
      "date": "2025-01-01",
      "total_requests": 150,
      "flagged_requests": 10,
      "safe_requests": 140,
      "category_counts": {"violence": 5, "hate": 5},
      "guard_counts": {"internal": 150},
      "avg_latency_ms": 140
    },
    ...
  ]
}
```

**Example**:

```bash
curl "http://localhost:8001/analytics/usage?tenant_id=public&days=30"
```

### GET /analytics/usage/current-month

Get total usage for the current month.

**Query Parameters**:
- `tenant_id` (str): Tenant identifier

**Response**:

```json
{
  "tenant_id": "tenant-123",
  "current_month_requests": 8000
}
```

**Example**:

```bash
curl "http://localhost:8001/analytics/usage/current-month?tenant_id=public"
```

### GET /analytics/usage/dashboard

Serve the interactive usage dashboard UI.

**Example**:

```bash
# Open in browser
open http://localhost:8001/analytics/usage/dashboard
```

## Dashboard UI

### Features

📊 **Summary Cards**:
- Total requests (with quota bar)
- Flagged content count and rate
- Safe content count and rate
- Average latency

📈 **Charts**:
- **Requests Over Time**: Line chart showing total and flagged requests by day
- **Top Categories**: Bar chart of most flagged categories
- **Guards Used**: Doughnut chart of guard distribution

🔄 **Auto-Refresh**: Updates every 60 seconds

### Screenshots

**Summary Cards**:
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  Total Requests │ Flagged Content │  Safe Content   │  Avg Latency    │
│      5,000      │      250        │     4,750       │     145ms       │
│  ═══════════    │   5.0% flagged  │   95.0% safe    │                 │
│  50.0% of 10k   │                 │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

**Requests Over Time**:
```
200 │                         ╭─╮
    │                    ╭────╯ ╰╮
150 │          ╭────────╯        ╰╮
    │     ╭────╯                  ╰╮
100 │╭────╯                        ╰─╮
    │                                 ╰─
 50 │
    └─────────────────────────────────────►
      1/1  1/5  1/10  1/15  1/20  1/25  1/30
```

## Programmatic Usage

### UsageTracker

```python
from analytics import UsageTracker

tracker = UsageTracker()

# Track a request
tracker.track_request(
    tenant_id="tenant-123",
    flagged=True,
    category="violence",
    guard="internal",
    latency_ms=150
)

# Get daily stats
stats = tracker.get_daily_stats(
    tenant_id="tenant-123",
    limit=30
)

for stat in stats:
    print(f"{stat.date}: {stat.total_requests} requests")

# Get summary
summary = tracker.get_summary("tenant-123", days=30)

print(f"Total: {summary['total_requests']}")
print(f"Flagged: {summary['flagged_requests']} ({summary['flagged_rate']:.1%})")
print(f"Top category: {summary['top_categories'][0]['name']}")
```

### UsageStats

```python
from analytics import UsageStats

# Create stats manually
stats = UsageStats(
    tenant_id="tenant-123",
    date="2025-01-15",
    total_requests=100,
    flagged_requests=5,
    safe_requests=95,
    category_counts={"violence": 3, "hate": 2},
    guard_counts={"internal": 100},
    avg_latency_ms=140
)

# Convert to dict
data = stats.to_dict()
```

## Integration Examples

### FastAPI Middleware

Track all requests automatically:

```python
from fastapi import FastAPI, Request
from analytics import get_usage_tracker
import time

app = FastAPI()
tracker = get_usage_tracker()

@app.middleware("http")
async def track_usage(request: Request, call_next):
    start = time.time()
    
    response = await call_next(request)
    
    latency_ms = int((time.time() - start) * 1000)
    
    # Track request
    tracker.track_request(
        tenant_id=request.state.tenant_id,
        flagged=response.headers.get("X-Content-Flagged") == "true",
        category=response.headers.get("X-Flagged-Category"),
        guard=response.headers.get("X-Guard-Name"),
        latency_ms=latency_ms,
        error=(response.status_code >= 500)
    )
    
    return response
```

### Batch Processing

Track batch results:

```python
from analytics import get_usage_tracker

tracker = get_usage_tracker()

# Process batch
for item in batch:
    result = evaluate(item)
    
    tracker.track_request(
        tenant_id=item.tenant_id,
        flagged=result.is_flagged,
        category=result.category,
        guard=result.guard,
        latency_ms=result.latency_ms
    )
```

## Quota Monitoring

### Free Tier Example

```python
from analytics import get_usage_tracker

tracker = get_usage_tracker()

# Check usage against quota
FREE_TIER_LIMIT = 10000

current_usage = tracker.get_current_month_total("tenant-123")

if current_usage >= FREE_TIER_LIMIT:
    print("❌ Free tier quota exceeded!")
    print(f"Usage: {current_usage}/{FREE_TIER_LIMIT}")
elif current_usage >= FREE_TIER_LIMIT * 0.8:
    print("⚠️  Approaching quota limit")
    print(f"Usage: {current_usage}/{FREE_TIER_LIMIT} ({current_usage/FREE_TIER_LIMIT:.0%})")
else:
    print("✅ Within quota")
    remaining = FREE_TIER_LIMIT - current_usage
    print(f"Remaining: {remaining:,} requests")
```

### Dashboard Display

The dashboard automatically shows quota usage:

```html
<div class="quota-bar">
    <div class="quota-fill" style="width: 80%"></div>
</div>
<div class="quota-text">
    8,000 of 10,000 (80.0%)
</div>
```

## Multi-Tenant Security

### Isolation

Each tenant's data is fully isolated:

```python
# Tenant A
stats_a = tracker.get_daily_stats("tenant-a")
# Only sees tenant-a data

# Tenant B
stats_b = tracker.get_daily_stats("tenant-b")
# Only sees tenant-b data
```

### API Security

In production, enforce tenant context from authentication:

```python
@app.get("/analytics/usage")
async def get_usage(
    auth: AuthContext = Depends(get_auth_context)
):
    # Use authenticated tenant ID
    tenant_id = auth.tenant_id
    
    tracker = get_usage_tracker()
    summary = tracker.get_summary(tenant_id, days=30)
    
    return summary
```

## Performance

### Efficient Updates

Usage tracking uses `ON CONFLICT ... DO UPDATE` for efficient increments:

```sql
INSERT INTO tenant_usage_daily (tenant_id, date, total_requests)
VALUES ('tenant-123', '2025-01-15', 1)
ON CONFLICT(tenant_id, date) DO UPDATE SET
    total_requests = total_requests + 1
```

### Indexing

Queries are optimized with indexes:

```sql
CREATE INDEX idx_usage_daily_tenant 
ON tenant_usage_daily(tenant_id, date DESC);
```

### Aggregation Performance

For large datasets:
- Daily stats are pre-aggregated
- Hourly stats for fine-grained analysis
- Limit queries to recent periods (30-90 days)

## Testing

Run usage statistics tests:

```bash
pytest tests/test_usage_statistics.py -v
```

**20 comprehensive tests** covering:
- ✅ UsageStats data model (2 tests)
- ✅ UsageTracker operations (14 tests)
  - Single/multiple requests
  - Category/guard breakdown
  - Latency tracking
  - Multi-tenant isolation
  - Error tracking
  - Summaries
- ✅ API endpoints (4 tests)
  - GET /analytics/usage
  - GET /analytics/usage/current-month
  - GET /analytics/usage/dashboard

## Troubleshooting

### No Data Showing

**Check database**:
```bash
sqlite3 history.db "SELECT COUNT(*) FROM tenant_usage_daily;"
```

**Track test request**:
```python
from analytics import get_usage_tracker

tracker = get_usage_tracker()
tracker.track_request("test-tenant")

stats = tracker.get_daily_stats("test-tenant")
print(stats)  # Should have 1 entry
```

### Dashboard Not Loading

**Check template path**:
```bash
ls -la templates/analytics/usage.html
```

**Check route**:
```bash
curl http://localhost:8001/analytics/usage/dashboard
```

### Latency Calculation Issues

Average latency is calculated incrementally:

```python
new_avg = ((prev_avg * prev_count) + new_latency) / (prev_count + 1)
```

Ensure latency values are in milliseconds.

## Best Practices

1. **Regular Monitoring**: Check usage dashboard daily
2. **Quota Alerts**: Set up alerts at 80% and 95% of quota
3. **Trend Analysis**: Review weekly/monthly trends
4. **Category Breakdown**: Identify which categories need improvement
5. **Performance**: Monitor latency trends for degradation
6. **Error Tracking**: Investigate error rate spikes

## Future Enhancements

- [ ] Weekly/monthly aggregation tables
- [ ] Export to CSV/JSON
- [ ] Email alerts for quota approaching
- [ ] Comparison vs previous period
- [ ] Custom date ranges
- [ ] Tenant-level dashboards
- [ ] Admin global view (all tenants)
- [ ] Cost estimation based on usage
- [ ] Predictive usage forecasting

## Related Documentation

- [Configuration Guide](CONFIG.md)
- [Multi-Tenancy](MULTITENANCY.md)
- [Rate Limiting](RATE_LIMITING.md)
- [Quota Enforcement](QUOTA.md)

## Support

For usage statistics issues:
1. Check database tables exist: `tenant_usage_daily`, `tenant_usage_hourly`
2. Verify API endpoints respond: `/analytics/usage`
3. Check logs for errors
4. Review multi-tenant isolation
5. Test with curl/API client

