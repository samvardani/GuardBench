# Database Stability: SQLite WAL + Postgres Option

This document describes database stability improvements that eliminate "database is locked" errors under concurrency and provide an optional Postgres backend for high-scale deployments.

## Overview

The database engine supports two backends with a unified `CounterStore` interface:
- **SQLite with WAL mode**: Optimized for concurrency (default)
- **Postgres**: For high-scale production deployments

## SQLite Optimizations

### WAL Mode (Write-Ahead Logging)

**Benefits**:
- Readers don't block writers
- Writers don't block readers
- Better concurrency performance
- Crash recovery

**Configuration** (automatic):
```sql
PRAGMA journal_mode=WAL;           -- Enable WAL
PRAGMA synchronous=NORMAL;          -- Good balance
PRAGMA busy_timeout=5000;           -- 5 second timeout
PRAGMA journal_size_limit=33554432; -- 32MB limit
PRAGMA foreign_keys=ON;             -- Enforce constraints
```

**Verified**: ✅ 50 threads × 1,000 increments = 50,000 exact count

### Retry Logic

Exponential backoff with jitter:

```python
# Automatic retry on "database is locked"
result = retry_on_locked(
    func,
    max_retries=5,
    base_delay=0.1
)

# Delay calculation
delay = base_delay × (2 ^ attempt) + random_jitter
# Attempt 1: ~0.1s
# Attempt 2: ~0.2s
# Attempt 3: ~0.4s
# ...
```

## CounterStore Interface

Abstract interface for usage counters:

```python
from db.engine import CounterStore

class CounterStore(ABC):
    def increment(self, period_key: str, tenant_id: str, count: int = 1) -> int:
        """Increment counter, return new value."""
        pass
    
    def get(self, period_key: str, tenant_id: str) -> int:
        """Get current counter value."""
        pass
    
    def close(self) -> None:
        """Close connection."""
        pass
```

## SQLite Backend

### Usage

```python
from db.engine import SQLiteCounterStore

store = SQLiteCounterStore(db_path=Path("history.db"))

# Increment
new_value = store.increment("2025-01", "tenant-1", count=1)
# Returns: 1

# Get
value = store.get("2025-01", "tenant-1")
# Returns: 1
```

### Performance

**Concurrency Test Results**:
- 50 threads × 1,000 increments
- Total: 50,000 operations
- Result: ✅ Exact count (50,000)
- Latency: p50=0.13ms, p95=12.14ms

## Postgres Backend

### Setup

```bash
# Install driver
pip install psycopg2-binary

# Set DATABASE_URL
export DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Start service (auto-detects Postgres)
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### Usage

```python
from db.engine import PostgresCounterStore

store = PostgresCounterStore(
    database_url="postgres://user:pass@localhost/dbname"
)

# Same interface as SQLite
new_value = store.increment("2025-01", "tenant-1", count=1)
value = store.get("2025-01", "tenant-1")
```

### Schema

```sql
CREATE TABLE usage_counters (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    period_key TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, period_key)
);

CREATE INDEX idx_counters_tenant_period
ON usage_counters(tenant_id, period_key);
```

## Auto-Detection

The system automatically chooses the backend:

```python
from db.engine import get_counter_store

# Auto-detect from DATABASE_URL
store = get_counter_store()

# If DATABASE_URL starts with postgres:// → PostgresCounterStore
# Otherwise → SQLiteCounterStore
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `""` | Database URL (empty = SQLite) |

### SQLite (Default)

```bash
# Use default SQLite
# No configuration needed

# Or specify path
export DATABASE_URL=/path/to/history.db

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### Postgres

```bash
# Set Postgres URL
export DATABASE_URL=postgres://user:password@localhost:5432/safety_eval

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

## Kubernetes/Helm

### values.yaml

```yaml
database:
  # Use SQLite (default)
  type: sqlite
  
  # Or use Postgres
  # type: postgres
  # url: postgres://user:password@postgres-service:5432/safety_eval
  
  # Or use secret
  # existingSecret: postgres-credentials
  # secretKeys:
  #   url: database-url
```

### Postgres Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
type: Opaque
stringData:
  database-url: postgres://user:password@postgres-service:5432/safety_eval
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-credentials
                  key: database-url
```

## Testing

Run database stability tests:

```bash
pytest tests/test_db_stability.py -v
```

**16 comprehensive tests** covering:
- ✅ SQLite WAL configuration (2 tests)
- ✅ Retry logic (3 tests)
- ✅ SQLiteCounterStore (6 tests)
- ✅ Concurrency (2 tests)
  - 50 threads × 1,000 = 50,000 exact
  - p95 latency < 100ms
- ✅ Counter store factory (3 tests)

### Concurrency Test Results

```
50 threads × 1,000 increments each
Total operations: 50,000
Final count: 50,000 ✅ (exact)

Latency stats:
- p50: 0.13ms
- p95: 12.14ms
- max: 68.52ms
```

## Migration to Postgres

### Step 1: Setup Postgres

```bash
# Docker
docker run -d \\
  -e POSTGRES_USER=safety \\
  -e POSTGRES_PASSWORD=password \\
  -e POSTGRES_DB=safety_eval \\
  -p 5432:5432 \\
  postgres:15
```

### Step 2: Install Driver

```bash
pip install psycopg2-binary
```

### Step 3: Set DATABASE_URL

```bash
export DATABASE_URL=postgres://safety:password@localhost:5432/safety_eval
```

### Step 4: Restart Service

```bash
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### Step 5: Verify

```bash
# Check logs
# "Using PostgresCounterStore"
```

## Troubleshooting

### Database Locked Errors

**Issue**: `sqlite3.OperationalError: database is locked`

**Fix**:
1. Verify WAL mode is enabled:
   ```sql
   sqlite3 history.db "PRAGMA journal_mode"
   -- Should return: wal
   ```

2. Check busy timeout:
   ```sql
   sqlite3 history.db "PRAGMA busy_timeout"
   -- Should return: 5000
   ```

3. Reduce concurrency or migrate to Postgres

### Postgres Connection Fails

**Issue**: `psycopg2.OperationalError: could not connect`

**Fix**:
1. Verify Postgres is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Test connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

3. Check credentials and firewall rules

### Performance Issues

**Slow Increments**:
- SQLite: Check WAL checkpoint frequency
- Postgres: Check connection pool size
- Both: Monitor disk I/O

**High p95 Latency**:
- SQLite: Consider Postgres for >1000 req/s
- Postgres: Add read replicas for heavy read workloads

## Best Practices

1. **Use WAL**: Always enable for SQLite (automatic)
2. **Set Timeouts**: 5 seconds prevents most locks
3. **Retry Logic**: Handle transient locked errors
4. **Postgres for Scale**: Use for >1000 concurrent connections
5. **Monitor Metrics**: Track p95 latency and lock frequency
6. **Connection Pooling**: Use pgbouncer for Postgres
7. **Read Replicas**: For read-heavy workloads

## Performance Targets

- **p95 Latency**: < 10ms (local), < 50ms (production)
- **Concurrency**: 50+ simultaneous writers
- **Accuracy**: Exact counts (no lost increments)
- **Availability**: >99.9% uptime

## Related Documentation

- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Postgres Performance](https://www.postgresql.org/docs/current/performance-tips.html)
- [Deployment Guide](DEPLOYMENT.md)

## Support

For database stability issues:
1. Check WAL mode: `PRAGMA journal_mode`
2. Verify busy timeout: `PRAGMA busy_timeout`
3. Review error logs for "locked" messages
4. Consider Postgres for high concurrency
5. Monitor p95 latency metrics

