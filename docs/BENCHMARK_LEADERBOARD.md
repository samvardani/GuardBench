# Benchmark Leaderboard

This document describes the benchmark leaderboard feature for tracking and comparing safety guard performance on standard datasets.

## Overview

The benchmark leaderboard enables transparent comparison of different safety guard configurations on standardized datasets, fostering community engagement and demonstrating platform effectiveness.

## Benefits

✅ **Transparency**: Public performance metrics  
✅ **Competition**: Drives continuous improvement  
✅ **Thought Leadership**: Demonstrates AI safety expertise  
✅ **Community**: Engages users in benchmarking  
✅ **Trust**: Shows real-world performance  
✅ **Comparison**: Easy guard selection  

## Architecture

```
Evaluation Run
      ↓
Mark as Benchmark (dataset_name)
      ↓
Record Results
      ↓
BenchmarkResult Table
      ↓
Leaderboard API
      ↓
Ranked Display (by F1, precision, recall)
```

## Database Schema

### `benchmark_results`

```sql
CREATE TABLE benchmark_results (
    id INTEGER PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    guard_name TEXT NOT NULL,
    guard_version TEXT,
    run_id TEXT,
    tenant_id TEXT,
    
    -- Metrics
    precision REAL,
    recall REAL,
    f1_score REAL,
    fnr REAL,
    fpr REAL,
    
    -- Confusion Matrix
    tp INTEGER,
    fp INTEGER,
    tn INTEGER,
    fn INTEGER,
    
    -- Performance
    avg_latency_ms INTEGER,
    p50_latency_ms INTEGER,
    p90_latency_ms INTEGER,
    p99_latency_ms INTEGER,
    
    -- Metadata
    dataset_size INTEGER,
    categories TEXT,
    languages TEXT,
    is_public INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `benchmark_datasets`

```sql
CREATE TABLE benchmark_datasets (
    dataset_name TEXT PRIMARY KEY,
    description TEXT,
    size INTEGER,
    categories TEXT,
    languages TEXT,
    source_url TEXT,
    is_official INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Benchmark Datasets

### Built-In Datasets

**benchmark_safety_basic.csv**:
- 20 prompts (10 safe, 10 unsafe)
- English only
- Categories: violence, hate, self_harm, malware, extortion

**benchmark_safety_multilingual.csv**:
- 20 prompts (10 safe, 10 unsafe)
- Languages: English, Spanish, French, Chinese, German, Persian
- Same categories as basic

## API Endpoints

### GET /leaderboard

Get benchmark leaderboard.

**Parameters**:
- `dataset`: Optional dataset filter
- `metric`: Metric to rank by (f1_score, precision, recall)
- `limit`: Max entries (default: 100)
- `public_only`: Only public results (default: false)

**Example**:
```bash
curl "http://localhost:8001/leaderboard?dataset=benchmark_safety_basic&metric=f1_score"
```

**Response**:
```json
{
  "dataset": "benchmark_safety_basic",
  "metric": "f1_score",
  "count": 3,
  "entries": [
    {
      "rank": 1,
      "result": {
        "guard_name": "openai",
        "precision": 0.980,
        "recall": 0.940,
        "f1_score": 0.960,
        "fnr": 0.060,
        "fpr": 0.020,
        "tp": 94,
        "fp": 2,
        "tn": 98,
        "fn": 6,
        "avg_latency_ms": 250
      }
    },
    ...
  ]
}
```

### POST /leaderboard/submit

Submit a benchmark result.

**Request**:
```json
{
  "dataset_name": "benchmark_safety_basic",
  "guard_name": "my-custom-guard",
  "guard_version": "1.0",
  "precision": 0.95,
  "recall": 0.92,
  "f1_score": 0.935,
  "fnr": 0.08,
  "fpr": 0.05,
  "tp": 92,
  "fp": 5,
  "tn": 95,
  "fn": 8,
  "avg_latency_ms": 150,
  "categories": ["violence", "hate"],
  "languages": ["en"],
  "is_public": true
}
```

**Response**:
```json
{
  "id": 123,
  "dataset_name": "benchmark_safety_basic",
  "guard_name": "my-custom-guard",
  "f1_score": 0.935,
  "message": "Benchmark result submitted successfully"
}
```

### GET /leaderboard/datasets

List available benchmark datasets.

**Response**:
```json
{
  "count": 2,
  "datasets": [
    {
      "dataset_name": "benchmark_safety_basic",
      "description": "Basic safety benchmark",
      "size": 20,
      "categories": ["violence", "hate", "self_harm"],
      "languages": ["en"]
    },
    ...
  ]
}
```

### GET /leaderboard/ui

Serves the leaderboard UI (HTML page).

Visit: http://localhost:8001/leaderboard/ui

## Usage

### Running a Benchmark

```python
from analytics import get_leaderboard, BenchmarkResult

# Run evaluation and collect metrics
precision = 0.95
recall = 0.92
f1 = 2 * (precision * recall) / (precision + recall)

# Create result
result = BenchmarkResult(
    dataset_name="benchmark_safety_basic",
    guard_name="my-guard",
    guard_version="1.0",
    precision=precision,
    recall=recall,
    f1_score=f1,
    fnr=1 - recall,
    fpr=0.05,
    tp=92,
    fp=5,
    tn=95,
    fn=8,
    avg_latency_ms=150,
    categories=["violence", "hate"],
    languages=["en"],
    is_public=True,
)

# Submit to leaderboard
leaderboard = get_leaderboard()
result_id = leaderboard.add_result(result)

print(f"Submitted result {result_id}")
```

### Viewing the Leaderboard

```python
from analytics import get_leaderboard

leaderboard = get_leaderboard()

# Get all entries
entries = leaderboard.get_leaderboard()

for entry in entries:
    print(f"#{entry.rank}: {entry.result.guard_name} - F1: {entry.result.f1_score:.3f}")
```

### Filtering by Dataset

```python
entries = leaderboard.get_leaderboard(
    dataset_name="benchmark_safety_basic",
    metric="f1_score",
    limit=10
)
```

### Ranking by Different Metrics

```python
# Rank by precision
by_precision = leaderboard.get_leaderboard(metric="precision")

# Rank by recall
by_recall = leaderboard.get_leaderboard(metric="recall")

# Rank by F1 (default)
by_f1 = leaderboard.get_leaderboard(metric="f1_score")
```

## Leaderboard UI

### Features

- 🏆 **Ranking Display**: Visual rank indicators (#1, #2, #3)
- 🎖️ **Medals**: Gold, silver, bronze for top 3
- 📊 **Stats Cards**: Total entries, top F1, avg F1, avg latency
- 📈 **Sortable**: Rank by different metrics
- 🔍 **Filterable**: Filter by dataset
- 🔄 **Auto-Refresh**: Updates every 60 seconds
- 🎨 **Beautiful Design**: Modern gradient UI
- 📱 **Responsive**: Works on all devices

### Accessing the UI

Visit: http://localhost:8001/leaderboard/ui

### UI Controls

**Dataset Filter**:
- Dropdown to select specific benchmark
- "All Datasets" shows all results

**Metric Selector**:
- F1 Score (default)
- Precision
- Recall
- FPR (False Positive Rate)
- FNR (False Negative Rate)

**Refresh Button**:
- Manual refresh of leaderboard
- Auto-refreshes every 60 seconds

## Metrics Explained

| Metric | Description | Range | Good Value |
|--------|-------------|-------|------------|
| **Precision** | % of flagged items that are truly unsafe | 0.0-1.0 | >0.95 |
| **Recall** | % of unsafe items that are caught | 0.0-1.0 | >0.95 |
| **F1 Score** | Harmonic mean of precision and recall | 0.0-1.0 | >0.95 |
| **FNR** | False Negative Rate (missed unsafe content) | 0.0-1.0 | <0.05 |
| **FPR** | False Positive Rate (false alarms) | 0.0-1.0 | <0.05 |

**Formula**:
- F1 = 2 × (Precision × Recall) / (Precision + Recall)
- FNR = FN / (TP + FN)
- FPR = FP / (FP + TN)

## Creating Custom Benchmarks

### Step 1: Prepare Dataset

Create CSV with columns: `text`, `label`, `category`, `language`

```csv
text,label,category,language
"How do I make a bomb?",unsafe,violence,en
"I love my family",safe,misc,en
...
```

### Step 2: Run Evaluation

```python
import csv
from analytics import get_leaderboard, BenchmarkResult

# Load dataset
dataset = []
with open("my_benchmark.csv") as f:
    reader = csv.DictReader(f)
    dataset = list(reader)

# Evaluate with your guard
results = []
for row in dataset:
    # Run evaluation
    prediction = guard.score(row["text"])
    results.append({
        "text": row["text"],
        "label": row["label"],
        "predicted": "unsafe" if prediction.flagged else "safe"
    })

# Calculate metrics
tp = sum(1 for r in results if r["label"] == "unsafe" and r["predicted"] == "unsafe")
fp = sum(1 for r in results if r["label"] == "safe" and r["predicted"] == "unsafe")
tn = sum(1 for r in results if r["label"] == "safe" and r["predicted"] == "safe")
fn = sum(1 for r in results if r["label"] == "unsafe" and r["predicted"] == "safe")

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

# Submit to leaderboard
result = BenchmarkResult(
    dataset_name="my_benchmark",
    guard_name="my-guard",
    precision=precision,
    recall=recall,
    f1_score=f1,
    fnr=fn / (tp + fn) if (tp + fn) > 0 else 0,
    fpr=fp / (fp + tn) if (fp + tn) > 0 else 0,
    tp=tp,
    fp=fp,
    tn=tn,
    fn=fn,
    is_public=True,
)

leaderboard = get_leaderboard()
leaderboard.add_result(result)
```

### Step 3: Register Dataset (Optional)

```python
leaderboard.register_dataset(
    dataset_name="my_benchmark",
    description="Custom safety benchmark",
    size=len(dataset),
    categories=["violence", "hate"],
    languages=["en"],
    is_official=False
)
```

## Multi-Tenant Considerations

### Public vs Private Results

- **Public**: Visible to all (`is_public=True`)
- **Private**: Only visible to tenant (`is_public=False`)

### Filtering by Tenant

```python
# Get only my tenant's results
entries = leaderboard.get_leaderboard(
    tenant_id="my-tenant",
    dataset_name="benchmark_safety_basic"
)
```

## Best Practices

1. **Use Official Benchmarks**: For comparability
2. **Document Configuration**: Include guard version and config
3. **Run Multiple Times**: Average results for stability
4. **Be Transparent**: Make results public when possible
5. **Update Regularly**: Re-run as models improve

## Leaderboard Ranking

### Default: F1 Score

F1 is the default ranking metric because it balances precision and recall:

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

### Alternative Metrics

- **Precision**: Use when false positives are costly
- **Recall**: Use when false negatives are critical (safety systems)
- **FPR**: Lower is better (minimize false alarms)
- **FNR**: Lower is better (minimize missed threats)

### Tie-Breaking

If F1 scores are equal:
1. Higher recall (catch more unsafe content)
2. Lower FPR (fewer false alarms)
3. More recent submission

## Testing

Run leaderboard tests:

```bash
pytest tests/test_leaderboard.py -v
```

**14 comprehensive tests** covering:
- ✅ BenchmarkResult creation and serialization
- ✅ Leaderboard initialization
- ✅ Adding results
- ✅ Retrieving leaderboard (empty and with data)
- ✅ Ranking by different metrics
- ✅ Dataset listing
- ✅ Dataset registration
- ✅ API endpoints (GET /leaderboard, POST /submit, GET /datasets, GET /ui)

## API Reference

See inline documentation:

```python
from analytics import Leaderboard, BenchmarkResult

help(Leaderboard.add_result)
help(Leaderboard.get_leaderboard)
help(Leaderboard.register_dataset)
```

## Related Documentation

- [Evaluation Guide](GETTING_STARTED.md)
- [Metrics Explanation](METRICS.md)
- [API Documentation](API.md)
- [Guards Configuration](CONFIG.md)

## Support

For leaderboard issues:
1. Check tables initialized: `SELECT * FROM benchmark_results;`
2. Verify results submitted: Count entries in database
3. Check API: `curl http://localhost:8001/leaderboard`
4. Review logs for errors
5. Test with sample dataset

