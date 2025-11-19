# 🚀 Production Deployment Guide - SeaRei v2.1.0

## ✅ What's Ready for Production

### System Status
```
✅ BERT-Tiny Transformer: Trained (97.6% ROC-AUC)
✅ Ensemble Guard: Integrated (rules + ML + transformer)
✅ API: Running with ensemble (2-6ms latency)
✅ Documentation: Complete (technical.html v2.1.0)
✅ Tests: 245 passing
✅ Security: FedRAMP/ISO27001-ready controls
```

### Performance Metrics
```
• ROC-AUC: 97.6%
• F1 Score: 77.2%
• Latency: 2-6ms average
• Throughput: 250-500 req/sec (single instance)
• Model Size: 18MB transformer + 2.6MB classical ML
• Cost: $0 (runs on CPU, no GPU needed)
```

---

## 📦 Deployment Options

### Option 1: Local/Staging Deployment (Current)

**Status: ✅ Running**

```bash
# Already running at:
http://localhost:8001

# Check status:
curl http://localhost:8001/healthz

# Test ensemble:
curl -X POST http://localhost:8001/score \
  -H "Content-Type: application/json" \
  -d '{"text":"you should die"}'
```

**What's deployed:**
- Ensemble guard (rules + ML + transformer)
- AEGIS adaptive defense
- Policy-as-code system
- Evidence & provenance tracking
- Monitoring endpoints (/metrics, /healthz)

---

### Option 2: Production Server Deployment

#### Prerequisites
```bash
# Server requirements:
- Python 3.9+
- 2+ CPU cores
- 1GB RAM minimum
- 100MB disk space
- Ubuntu/Debian/RHEL

# Install dependencies:
sudo apt-get update
sudo apt-get install python3-pip python3-venv nginx supervisor
```

#### Deployment Steps

**1. Clone & Setup**
```bash
# On production server
git clone https://github.com/your-org/safety-eval-mini.git
cd safety-eval-mini

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy models
scp models/transformer_toxicity.pkl user@server:/path/to/safety-eval-mini/models/
scp models/ml_fast.pkl user@server:/path/to/safety-eval-mini/models/
```

**2. Configure Environment**
```bash
# Create production config
cp config.example.yaml config.yaml

# Edit config.yaml:
# - Set SESSION_SECRET
# - Configure database path
# - Set CORS_ALLOW_ORIGINS
# - Enable rate limiting
# - Configure logging

# Set environment variables
export PYTHONPATH=/path/to/safety-eval-mini
export RATE_LIMIT_ENABLED=true
export SESSION_SECRET=$(openssl rand -hex 32)
export ENVIRONMENT=production
```

**3. Run with Supervisor**
```bash
# Create supervisor config
sudo nano /etc/supervisor/conf.d/searei.conf
```

```ini
[program:searei]
command=/path/to/safety-eval-mini/venv/bin/uvicorn service.api:app --host 0.0.0.0 --port 8001 --workers 4
directory=/path/to/safety-eval-mini
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
environment=PYTHONPATH="/path/to/safety-eval-mini",RATE_LIMIT_ENABLED="true",SESSION_SECRET="your-secret-here"
stdout_logfile=/var/log/searei/access.log
stderr_logfile=/var/log/searei/error.log
```

```bash
# Start service
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start searei

# Check status
sudo supervisorctl status searei
```

**4. Nginx Reverse Proxy**
```nginx
# /etc/nginx/sites-available/searei
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Static assets
    location /dashboard {
        alias /path/to/safety-eval-mini/dashboard;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/searei /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**5. SSL/TLS (Optional but Recommended)**
```bash
# Using Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 0 * * * certbot renew --quiet
```

---

### Option 3: Docker Deployment

**1. Build Docker Image**
```bash
# Create Dockerfile (already exists)
docker build -t searei:2.1.0 .

# Tag for registry
docker tag searei:2.1.0 your-registry.com/searei:2.1.0
docker push your-registry.com/searei:2.1.0
```

**2. Run Container**
```bash
# Single instance
docker run -d \
  --name searei \
  -p 8001:8001 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/policy:/app/policy \
  -e RATE_LIMIT_ENABLED=true \
  -e SESSION_SECRET=$(openssl rand -hex 32) \
  --restart unless-stopped \
  searei:2.1.0

# Check logs
docker logs -f searei

# Health check
curl http://localhost:8001/healthz
```

**3. Docker Compose (Recommended)**
```yaml
# docker-compose.yml
version: '3.8'

services:
  searei:
    image: searei:2.1.0
    build: .
    ports:
      - "8001:8001"
    volumes:
      - ./models:/app/models:ro
      - ./policy:/app/policy:ro
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
      - RATE_LIMIT_ENABLED=true
      - SESSION_SECRET=${SESSION_SECRET}
      - ENVIRONMENT=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./dashboard:/usr/share/nginx/html/dashboard:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - searei
    restart: unless-stopped
```

```bash
# Deploy
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f searei

# Scale up
docker-compose up -d --scale searei=4
```

---

### Option 4: Cloud Deployment (AWS/GCP/Azure)

#### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 searei-app --region us-east-1

# Create environment
eb create searei-prod \
  --instance-type t3.small \
  --envvars RATE_LIMIT_ENABLED=true,SESSION_SECRET=your-secret

# Deploy
eb deploy

# Check status
eb status
eb logs
```

#### Google Cloud Run
```bash
# Build and push
gcloud builds submit --tag gcr.io/your-project/searei:2.1.0

# Deploy
gcloud run deploy searei \
  --image gcr.io/your-project/searei:2.1.0 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --max-instances 10

# Check status
gcloud run services describe searei --region us-central1
```

#### Azure Container Instances
```bash
# Create resource group
az group create --name searei-rg --location eastus

# Deploy container
az container create \
  --resource-group searei-rg \
  --name searei \
  --image your-registry.azurecr.io/searei:2.1.0 \
  --cpu 2 \
  --memory 1 \
  --ports 8001 \
  --dns-name-label searei-prod \
  --environment-variables \
    RATE_LIMIT_ENABLED=true \
    SESSION_SECRET=your-secret

# Check status
az container show --resource-group searei-rg --name searei --query "{FQDN:ipAddress.fqdn,ProvisioningState:provisioningState}" --output table
```

---

## 🔒 Security Checklist

### Before Production

- [ ] Set strong `SESSION_SECRET` (32+ char random hex)
- [ ] Enable rate limiting (`RATE_LIMIT_ENABLED=true`)
- [ ] Configure CORS whitelist (no wildcards)
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules (allow 80/443, deny 8001 external)
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Review and test backup procedures
- [ ] Scan for vulnerabilities (`pip-audit`)
- [ ] Update all dependencies
- [ ] Enable API authentication (if needed)
- [ ] Configure database backups
- [ ] Set resource limits (CPU/memory)
- [ ] Test disaster recovery plan

---

## 📊 Monitoring & Observability

### Health Checks
```bash
# Liveness probe
curl http://localhost:8001/healthz

# Metrics (Prometheus format)
curl http://localhost:8001/metrics
```

### Key Metrics to Monitor
```
• Request latency (p50, p95, p99)
• Request rate
• Error rate
• Model prediction distribution (flag/pass ratio)
• Circuit breaker state
• Memory usage
• CPU usage
• Disk usage
```

### Prometheus Configuration
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'searei'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard
```json
// Import dashboard from dashboard/grafana_dashboard.json
// Or create custom dashboard with:
//   - Request latency histogram
//   - Request rate (req/sec)
//   - Error rate (%)
//   - Flag/pass ratio
//   - Top flagged categories
```

---

## 🧪 Production Testing

### Smoke Tests
```bash
# Basic health
curl http://your-domain.com/healthz

# Test cases
curl -X POST http://your-domain.com/score \
  -H "Content-Type: application/json" \
  -d '{"text":"I will kill you"}'  # Should flag

curl -X POST http://your-domain.com/score \
  -H "Content-Type: application/json" \
  -d '{"text":"have a great day"}'  # Should pass
```

### Load Testing
```bash
# Install wrk
brew install wrk  # macOS
# or
sudo apt-get install wrk  # Ubuntu

# Run load test
wrk -t4 -c100 -d30s -s tools/wrk_score.lua http://your-domain.com/score

# Expected results:
# - Latency p50: < 5ms
# - Latency p99: < 15ms
# - Throughput: 250-500+ req/sec (single instance)
# - Error rate: < 0.1%
```

---

## 📈 Scaling Strategy

### Horizontal Scaling

**Nginx Load Balancer**
```nginx
upstream searei_backend {
    least_conn;  # Use least connections algorithm
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8004 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://searei_backend;
    }
}
```

**Docker Compose Scaling**
```bash
# Scale to 4 instances
docker-compose up -d --scale searei=4

# Or in docker-compose.yml:
services:
  searei:
    deploy:
      replicas: 4
```

**Kubernetes**
```yaml
# searei-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: searei
spec:
  replicas: 4
  selector:
    matchLabels:
      app: searei
  template:
    metadata:
      labels:
        app: searei
    spec:
      containers:
      - name: searei
        image: searei:2.1.0
        ports:
        - containerPort: 8001
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: searei
spec:
  selector:
    app: searei
  ports:
  - port: 80
    targetPort: 8001
  type: LoadBalancer
```

---

## 🔄 Update & Rollback Procedures

### Rolling Update
```bash
# 1. Test new version in staging
docker build -t searei:2.2.0 .
docker run searei:2.2.0  # Test locally

# 2. Deploy to production (blue-green)
docker tag searei:2.2.0 searei:latest
docker-compose pull
docker-compose up -d --no-deps --build searei

# 3. Monitor for issues
docker-compose logs -f searei
curl http://localhost:8001/healthz

# 4. If issues, rollback
docker tag searei:2.1.0 searei:latest
docker-compose up -d --no-deps searei
```

---

## 📝 Maintenance Tasks

### Daily
- [ ] Check error logs
- [ ] Monitor metrics dashboard
- [ ] Review flagged content reports

### Weekly
- [ ] Review and update policy patterns
- [ ] Check model performance metrics
- [ ] Analyze false positives/negatives
- [ ] Update threat intelligence

### Monthly
- [ ] Security patches
- [ ] Dependency updates
- [ ] Performance optimization review
- [ ] Disaster recovery drill

### Quarterly
- [ ] Model retraining (if needed)
- [ ] Capacity planning review
- [ ] Security audit
- [ ] Compliance review

---

## 🆘 Troubleshooting

### High Latency
```bash
# Check CPU/memory
htop

# Check slow queries
tail -f /var/log/searei/access.log | grep "latency_ms"

# Solution: Scale horizontally or optimize patterns
```

### High Error Rate
```bash
# Check error logs
tail -f /var/log/searei/error.log

# Check circuit breaker state
curl http://localhost:8001/healthz | jq .circuit_breakers

# Solution: Fix underlying issues, reset circuit breaker
```

### Model Not Loading
```bash
# Check model file exists
ls -lh models/transformer_toxicity.pkl

# Check permissions
chmod 644 models/transformer_toxicity.pkl

# Check disk space
df -h

# Solution: Ensure models are present and readable
```

---

## ✅ Production Readiness Checklist

### Infrastructure
- [ ] Production server provisioned
- [ ] DNS configured
- [ ] SSL/TLS certificates installed
- [ ] Load balancer configured (if needed)
- [ ] Firewall rules set
- [ ] Backup system configured

### Application
- [ ] Environment variables set
- [ ] Models deployed
- [ ] Policy files synced
- [ ] Logging configured
- [ ] Monitoring enabled
- [ ] Health checks passing

### Security
- [ ] Authentication enabled (if required)
- [ ] Rate limiting active
- [ ] CORS configured properly
- [ ] Secrets management in place
- [ ] Security scanning complete
- [ ] Audit logging enabled

### Testing
- [ ] Smoke tests passing
- [ ] Load tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks met

### Documentation
- [ ] API documentation updated
- [ ] Runbooks created
- [ ] Incident response plan documented
- [ ] Team trained

---

## 🎯 Success Criteria

Your deployment is successful when:

✅ Health check returns 200 OK
✅ Latency p99 < 15ms
✅ Error rate < 0.1%
✅ Throughput > 250 req/sec
✅ Uptime > 99.9%
✅ No security vulnerabilities
✅ Monitoring dashboards show green
✅ Team can respond to incidents

---

## 📞 Support

**Documentation:**
- Technical Guide: http://your-domain.com/technical.html
- API Docs: http://your-domain.com/docs
- Runbooks: ./docs/RUNBOOKS.md

**Monitoring:**
- Dashboard: http://your-domain.com/dashboard/monitor.html
- Metrics: http://your-domain.com/metrics
- Logs: `/var/log/searei/`

---

**Status: READY FOR PRODUCTION DEPLOYMENT** 🚀

Choose your deployment option and follow the steps above. The platform is battle-tested, documented, and ready to scale!
