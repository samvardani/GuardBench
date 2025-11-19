# ML Training System Documentation

## Overview

The ML Training System provides **automatic, continuous training** for the content moderation ML model. It monitors for new data, downloads from live sources, trains models, validates them, and deploys automatically.

## Components

### 1. `train_ml_model.py`
**Manual training script**

Trains a Naive Bayes + Logistic Regression model on Jigsaw dataset.

```bash
# Basic training
python scripts/train_ml_model.py

# With validation
python scripts/train_ml_model.py --validate

# Custom dataset
python scripts/train_ml_model.py --dataset datasets_raw/my_data.csv

# Custom output
python scripts/train_ml_model.py --output models/ml_v2.pkl
```

**Training time:** ~25 seconds on laptop CPU  
**Model size:** ~2 MB  
**Training data:** 159,571 examples

### 2. `download_datasets.py`
**Dataset downloader**

Downloads datasets from live sources (Kaggle, GitHub, etc.).

```bash
# Download Jigsaw (default)
python scripts/download_datasets.py

# Download all datasets
python scripts/download_datasets.py --dataset all

# Only check if new data is needed
python scripts/download_datasets.py --check-only
```

**Supported datasets:**
- Jigsaw Toxic Comments (159K examples) - Kaggle
- Davidson Hate Speech (25K examples) - GitHub
- ToxiGen (274K examples) - GitHub

### 3. `ml_training_daemon.py`
**Continuous training daemon**

Automatically monitors for new data and trains models on a schedule.

```bash
# Run once (check + train if needed)
python scripts/ml_training_daemon.py --once

# Run continuously (check every hour)
python scripts/ml_training_daemon.py --interval 3600

# Run as background daemon
nohup python scripts/ml_training_daemon.py --interval 3600 > logs/ml_daemon.log 2>&1 &

# Daily retraining
python scripts/ml_training_daemon.py --schedule daily

# Disable auto-download
python scripts/ml_training_daemon.py --no-download
```

## Quick Start

### Option 1: Manual Training

```bash
# 1. Download data (if not already available)
python scripts/download_datasets.py

# 2. Train model
python scripts/train_ml_model.py --validate

# 3. API will auto-reload with new model
```

### Option 2: Automatic Continuous Training

```bash
# Start daemon (runs forever, checks hourly, retrains weekly)
python scripts/ml_training_daemon.py --interval 3600 --schedule weekly
```

### Option 3: Scheduled Cron Job

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/safety-eval-mini && python3 scripts/ml_training_daemon.py --once --schedule daily
```

## Training Workflow

### Automatic Training Cycle

1. **Check for updates**
   - Is model missing? → Train
   - Is data newer than model? → Train
   - Is scheduled retrain due? → Train
   - Otherwise → Skip

2. **Download new data** (if enabled)
   - Check Kaggle for new datasets
   - Download if available
   - Skip if downloaded recently (<24h)

3. **Train model**
   - Load dataset (159K examples)
   - TF-IDF vectorization (~15s)
   - Train 6 classifiers (~8s)
   - Save model (~2 MB)

4. **Validate model**
   - Load model
   - Run test cases
   - Check accuracy threshold (>60%)
   - Verify model integrity

5. **Deploy model**
   - Replace old model
   - API auto-reloads (if using `--reload`)
   - Update state file

6. **Sleep and repeat**
   - Wait for next check interval
   - Go to step 1

## Configuration

### Daemon Settings

```python
# In ml_training_daemon.py (or set via CLI)

check_interval = 3600  # Check every hour
retrain_schedule = "weekly"  # daily, weekly, monthly, never
auto_download = True  # Auto-download new data
auto_deploy = True  # Auto-deploy trained model
min_accuracy = 0.60  # Minimum validation accuracy
```

### Training Parameters

```python
# In train_ml_model.py (or set via CLI)

max_features = 15000  # TF-IDF features
ngram_range = (1, 2)  # Unigrams + bigrams
min_df = 3  # Min document frequency
max_df = 0.9  # Max document frequency
C = 4.0  # LogReg regularization
max_iter = 100  # Max training iterations
```

## Monitoring

### Check Daemon Status

```bash
# Check if daemon is running
ps aux | grep ml_training_daemon

# View daemon logs
tail -f logs/ml_daemon.log

# Check last training time
cat data/ml_daemon_state.txt
```

### View Training Stats

```bash
# Model metadata
python3 << 'EOF'
import pickle
with open('models/ml_fast.pkl', 'rb') as f:
    model = pickle.load(f)
    print(model['metadata'])
EOF
```

## Live Data Sources

### Currently Supported

1. **Kaggle** (requires API key)
   - Jigsaw Toxic Comments (159K)
   - Civil Comments (2M) - Can be added
   
2. **GitHub** (public repositories)
   - Davidson Hate Speech (25K)
   - ToxiGen (274K)

### Adding New Sources

Edit `download_datasets.py` and add:

```python
def download_my_dataset(output_dir: str, verbose: bool = True):
    """Download from custom source"""
    # Download logic
    pass
```

## Performance

### Training Performance

| Metric | Value |
|--------|-------|
| Training time | ~25 seconds |
| Model size | ~2 MB |
| Dataset size | 159,571 examples |
| CPU usage | 100% (single core) |
| Memory usage | ~2 GB peak |

### Validation Performance

| Metric | Value |
|--------|-------|
| Validation accuracy | 66.7% (on 6 test cases) |
| True positives | 4/6 |
| False negatives | 2/6 |
| Inference latency | 0.9ms |

## Troubleshooting

### Model not loading

```bash
# Check model file exists
ls -lh models/ml_fast.pkl

# Verify model integrity
python3 -c "import pickle; pickle.load(open('models/ml_fast.pkl', 'rb'))"
```

### Training fails

```bash
# Check dataset exists
ls -lh datasets_raw/train.csv

# Check Python dependencies
pip install pandas numpy scikit-learn

# Run with verbose output
python scripts/train_ml_model.py --validate
```

### Daemon not starting

```bash
# Check Python version (needs 3.9+)
python3 --version

# Run once to see errors
python scripts/ml_training_daemon.py --once

# Check logs
cat logs/ml_daemon.log
```

### Kaggle download fails

```bash
# Install Kaggle CLI
pip install kaggle

# Set up credentials
# 1. Go to https://www.kaggle.com/settings
# 2. Create new API token
# 3. Place kaggle.json in ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# Test
kaggle datasets list
```

## Production Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/system/ml-training-daemon.service
[Unit]
Description=ML Training Daemon
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/safety-eval-mini
ExecStart=/usr/bin/python3 scripts/ml_training_daemon.py --interval 3600 --schedule weekly
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable ml-training-daemon
sudo systemctl start ml-training-daemon
sudo systemctl status ml-training-daemon
```

### Docker

```dockerfile
# Dockerfile.training-daemon
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY datasets_raw/ ./datasets_raw/
COPY models/ ./models/

CMD ["python", "scripts/ml_training_daemon.py", "--interval", "3600", "--schedule", "weekly"]
```

```bash
# Build and run
docker build -f Dockerfile.training-daemon -t ml-training-daemon .
docker run -d --name ml-daemon ml-training-daemon
```

## Best Practices

### 1. Regular Backups

```bash
# Backup models before retraining
cp models/ml_fast.pkl models/ml_fast_backup_$(date +%Y%m%d).pkl
```

### 2. Version Control

```bash
# Track model versions in git
git add models/ml_fast.pkl
git commit -m "Retrained model - $(date)"
```

### 3. A/B Testing

```bash
# Train to different file
python scripts/train_ml_model.py --output models/ml_candidate.pkl

# Compare performance
python scripts/compare_models.py --old models/ml_fast.pkl --new models/ml_candidate.pkl

# Deploy if better
mv models/ml_candidate.pkl models/ml_fast.pkl
```

### 4. Monitoring Alerts

```bash
# Check if model is stale (>7 days)
find models/ml_fast.pkl -mtime +7 -exec echo "Model is stale!" \;

# Alert on low accuracy
python scripts/validate_model.py | grep -q "accuracy.*0\.[0-5]" && echo "Low accuracy alert!"
```

## FAQ

**Q: How often should I retrain?**  
A: Weekly is recommended for most use cases. Daily if you have rapidly evolving threats. Monthly for stable environments.

**Q: Can I train on multiple datasets?**  
A: Yes! Concatenate datasets before training:
```bash
cat datasets_raw/train.csv datasets_raw/extra_data.csv > datasets_raw/combined.csv
python scripts/train_ml_model.py --dataset datasets_raw/combined.csv
```

**Q: Does retraining require downtime?**  
A: No! The daemon trains to the same file, and the API auto-reloads on file change. There may be a brief moment (< 1s) where the old model is still in memory.

**Q: What if training fails mid-way?**  
A: The old model remains intact. Training is atomic - either completes fully or doesn't deploy.

**Q: Can I train on custom data?**  
A: Yes! Format your data as CSV with columns: `comment_text`, `toxic`, `threat`, `insult`, etc. Then train:
```bash
python scripts/train_ml_model.py --dataset my_data.csv
```

## Support

For issues or questions:
1. Check logs: `logs/ml_daemon.log`
2. Run validation: `python scripts/train_ml_model.py --validate`
3. Check model metadata: See "View Training Stats" above
4. Restart daemon: `pkill -f ml_training_daemon && python scripts/ml_training_daemon.py &`

## License

MIT License - See LICENSE file












