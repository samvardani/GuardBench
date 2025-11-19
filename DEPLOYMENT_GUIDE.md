# SeaRei Cloud Deployment Guide

**Production-ready deployment configurations for AWS, GCP, and Azure**

## 📋 Overview

This guide provides complete deployment instructions for deploying SeaRei Safety Service to production on major cloud providers:

- **AWS ECS/Fargate** - Serverless containers with auto-scaling
- **GCP Cloud Run** - Fully managed serverless platform
- **Azure AKS** - Managed Kubernetes with enterprise features

All configurations include:
- ✅ Auto-scaling (1-10 instances)
- ✅ Health checks and rolling updates
- ✅ Secrets management
- ✅ Load balancing
- ✅ Production-grade security
- ✅ Monitoring integration

---

## 🚀 Quick Start

### Prerequisites

- Docker installed locally
- Cloud CLI tools installed (AWS CLI / gcloud / Azure CLI)
- Git repository access
- Cloud account with appropriate permissions

### Choose Your Cloud Provider

<details>
<summary><b>Option A: AWS ECS/Fargate</b> (Recommended for AWS users)</summary>

**Cost:** ~$200-500/month for production workload

**Steps:**

```bash
# 1. Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 2. Configure AWS credentials
aws configure

# 3. Deploy!
chmod +x deployment/aws/deploy.sh
./deployment/aws/deploy.sh production us-east-1
```

**What gets deployed:**
- ECS Fargate task (1-10 replicas)
- Application Load Balancer
- CloudWatch Logs
- Secrets Manager integration
- Auto-scaling based on CPU/memory

**Access your service:**
```bash
# Get your load balancer URL from the deploy script output
curl http://YOUR-ALB-URL/healthz
```

</details>

<details>
<summary><b>Option B: GCP Cloud Run</b> (Recommended for simplicity)</summary>

**Cost:** ~$100-300/month for production workload (pay-per-use)

**Steps:**

```bash
# 1. Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# 2. Deploy!
chmod +x deployment/gcp/deploy.sh
./deployment/gcp/deploy.sh your-project-id us-central1
```

**What gets deployed:**
- Cloud Run service (min 1, max 10 instances)
- Automatic HTTPS with managed certificates
- Secret Manager integration
- Cloud Build for CI/CD
- Cloud Logging and Monitoring

**Access your service:**
```bash
# Service URL is automatically provisioned with HTTPS
curl https://searei-safety-service-HASH-uc.a.run.app/healthz
```

</details>

<details>
<summary><b>Option C: Azure AKS</b> (Recommended for enterprise)</summary>

**Cost:** ~$300-600/month for production workload

**Steps:**

```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Deploy!
chmod +x deployment/azure/deploy.sh
./deployment/azure/deploy.sh searei-rg searei-aks seareiacr eastus
```

**What gets deployed:**
- AKS cluster with 3-10 pods
- Azure Load Balancer
- Horizontal Pod Autoscaler
- Azure Container Registry
- Azure Key Vault integration
- Azure Monitor

**Access your service:**
```bash
# Get external IP from deploy script output
curl http://EXTERNAL-IP/healthz
```

</details>

---

## 📦 Deployment Architecture

### AWS ECS/Fargate

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Cloud                            │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   Application Load Balancer                     │    │
│  │   (public HTTPS endpoint)                       │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │   ECS Service (Fargate)                        │    │
│  │   ├─ Task 1 (searei-api container)             │    │
│  │   ├─ Task 2 (searei-api container)             │    │
│  │   └─ Task N (auto-scaled 1-10)                 │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │   AWS Secrets Manager                          │    │
│  │   ├─ SESSION_SECRET                            │    │
│  │   └─ DATABASE_URL                              │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   CloudWatch Logs & Metrics                    │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### GCP Cloud Run

```
┌─────────────────────────────────────────────────────────┐
│                     GCP Cloud                            │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   Cloud Run Service                            │    │
│  │   (auto-HTTPS, auto-scale 1-10 instances)      │    │
│  │   ├─ Instance 1                                │    │
│  │   ├─ Instance 2                                │    │
│  │   └─ Instance N                                │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │   Secret Manager                               │    │
│  │   ├─ searei-session-secret                     │    │
│  │   └─ searei-database-url                       │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   Cloud Logging & Monitoring                   │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Azure AKS

```
┌─────────────────────────────────────────────────────────┐
│                     Azure Cloud                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   Azure Load Balancer                          │    │
│  │   (public IP endpoint)                         │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │   AKS Cluster                                  │    │
│  │   ┌───────────────────────────────────────┐   │    │
│  │   │  Deployment (3-10 pods)                │   │    │
│  │   │  ├─ Pod 1 (searei-api container)       │   │    │
│  │   │  ├─ Pod 2 (searei-api container)       │   │    │
│  │   │  └─ Pod N (HPA auto-scaled)            │   │    │
│  │   └───────────────────────────────────────┘   │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │   Kubernetes Secrets                           │    │
│  │   ├─ session-secret                            │    │
│  │   └─ database-url                              │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │   Azure Monitor & Log Analytics                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

### Environment Variables

All deployments support these environment variables:

```bash
# Core settings
ENVIRONMENT=production          # Environment name
PORT=8001                       # Server port
WORKERS=4                       # Number of worker processes
LOG_LEVEL=info                  # Logging level (debug/info/warning/error)

# Secrets (use cloud secret managers)
SESSION_SECRET=<random-32-byte> # Session encryption key
DATABASE_URL=<db-connection>    # Database connection string

# Optional: Feature flags
CORS_ALLOW_ORIGINS=https://your-domain.com
RATE_LIMIT_ENABLED=true
ENABLE_METRICS=true
```

### Setting Secrets

<details>
<summary><b>AWS Secrets Manager</b></summary>

```bash
# Create session secret
aws secretsmanager create-secret \
    --name searei/session-secret \
    --secret-string "$(openssl rand -base64 32)" \
    --region us-east-1

# Create database URL secret
aws secretsmanager create-secret \
    --name searei/database-url \
    --secret-string "sqlite:///./history.db" \
    --region us-east-1
```

</details>

<details>
<summary><b>GCP Secret Manager</b></summary>

```bash
# Create session secret
echo -n "$(openssl rand -base64 32)" | \
    gcloud secrets create searei-session-secret --data-file=-

# Create database URL secret
echo -n "sqlite:///./history.db" | \
    gcloud secrets create searei-database-url --data-file=-
```

</details>

<details>
<summary><b>Azure Key Vault / Kubernetes Secrets</b></summary>

```bash
# Using kubectl (for AKS)
kubectl create secret generic searei-secrets \
    --from-literal=session-secret=$(openssl rand -base64 32) \
    --from-literal=database-url="sqlite:///./history.db" \
    --namespace=production
```

</details>

---

## 🔒 Security Best Practices

### 1. Use Non-Root User
All Dockerfiles run as user `searei` (UID 1000)

### 2. Enable HTTPS
- **AWS**: Use Application Load Balancer with ACM certificate
- **GCP**: Cloud Run provides automatic HTTPS
- **Azure**: Use Azure Application Gateway or cert-manager

### 3. Restrict Network Access
```bash
# AWS: Security group rules
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxx \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# GCP: Cloud Run is HTTPS-only by default

# Azure: Network Security Group rules
az network nsg rule create \
    --resource-group searei-rg \
    --nsg-name searei-nsg \
    --name allow-https \
    --priority 100 \
    --destination-port-ranges 443
```

### 4. Rotate Secrets Regularly
```bash
# Rotate every 90 days
aws secretsmanager rotate-secret \
    --secret-id searei/session-secret \
    --rotation-lambda-arn arn:aws:lambda:...
```

---

## 📊 Monitoring & Logging

### AWS CloudWatch

```bash
# View logs
aws logs tail /ecs/searei-safety-service --follow

# View metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=searei-api \
    --start-time 2025-01-13T00:00:00Z \
    --end-time 2025-01-13T23:59:59Z \
    --period 300 \
    --statistics Average
```

### GCP Cloud Logging

```bash
# View logs
gcloud run services logs read searei-safety-service --limit=100

# View metrics
gcloud monitoring time-series list \
    --filter='metric.type="run.googleapis.com/request_count"'
```

### Azure Monitor

```bash
# View logs
az monitor log-analytics query \
    --workspace YOUR_WORKSPACE_ID \
    --analytics-query 'ContainerLog | where ContainerName == "searei-api" | top 100 by TimeGenerated'

# View metrics
az monitor metrics list \
    --resource YOUR_RESOURCE_ID \
    --metric-names "CpuUsage,MemoryUsage"
```

---

## 🔄 CI/CD Integration

### GitHub Actions (All Providers)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to AWS
      if: ${{ vars.CLOUD_PROVIDER == 'aws' }}
      run: |
        chmod +x deployment/aws/deploy.sh
        ./deployment/aws/deploy.sh production us-east-1
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    
    - name: Deploy to GCP
      if: ${{ vars.CLOUD_PROVIDER == 'gcp' }}
      run: |
        echo '${{ secrets.GCP_SA_KEY }}' > key.json
        gcloud auth activate-service-account --key-file=key.json
        chmod +x deployment/gcp/deploy.sh
        ./deployment/gcp/deploy.sh ${{ vars.GCP_PROJECT_ID }} us-central1
    
    - name: Deploy to Azure
      if: ${{ vars.CLOUD_PROVIDER == 'azure' }}
      run: |
        az login --service-principal -u ${{ secrets.AZURE_CLIENT_ID }} -p ${{ secrets.AZURE_CLIENT_SECRET }} --tenant ${{ secrets.AZURE_TENANT_ID }}
        chmod +x deployment/azure/deploy.sh
        ./deployment/azure/deploy.sh searei-rg searei-aks seareiacr eastus
```

---

## 🧪 Testing Deployment

### Health Check

```bash
curl -f http://YOUR-SERVICE-URL/healthz
# Expected: {"status":"healthy", ...}
```

### API Test

```bash
curl -X POST http://YOUR-SERVICE-URL/score \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a test message"}'
```

### Load Test

```bash
# Using wrk
wrk -t4 -c100 -d30s --latency \
  -s tools/wrk_score.lua \
  http://YOUR-SERVICE-URL/score

# Using ab
ab -n 1000 -c 10 \
  -p test_request.json \
  -T application/json \
  http://YOUR-SERVICE-URL/score
```

---

## 💰 Cost Optimization

### AWS Cost Estimates

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| ECS Fargate (2 vCPU, 4GB) | 3 tasks @ 80% uptime | ~$180 |
| Application Load Balancer | Standard | ~$25 |
| CloudWatch Logs | 10GB/month | ~$5 |
| Secrets Manager | 2 secrets | ~$1 |
| **Total** | | **~$211/month** |

### GCP Cost Estimates

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Cloud Run (2 vCPU, 2GB) | 1M requests, avg 500ms | ~$50 |
| Secret Manager | 2 secrets, 10K accesses | ~$1 |
| Cloud Logging | 10GB/month | ~$5 |
| **Total** | | **~$56/month** |

### Azure Cost Estimates

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| AKS | 3 Standard_D2s_v3 nodes | ~$200 |
| Load Balancer | Standard | ~$25 |
| Container Registry | Basic | ~$5 |
| Azure Monitor | 10GB/month | ~$15 |
| **Total** | | **~$245/month** |

**💡 Cost Saving Tips:**
- Use auto-scaling with min instances = 1 during development
- Enable spot/preemptible instances for non-critical workloads
- Set up budget alerts
- Use reserved instances for predictable workloads (30-50% savings)

---

## 🔧 Troubleshooting

### Issue: Container won't start

**Symptoms:** Tasks/pods keep restarting

**Solutions:**
1. Check logs:
   ```bash
   # AWS
   aws logs tail /ecs/searei-safety-service --follow
   
   # GCP
   gcloud run services logs read searei-safety-service
   
   # Azure
   kubectl logs -n production deployment/searei-safety-service
   ```

2. Verify secrets are set correctly
3. Check resource limits (CPU/memory)
4. Ensure all dependencies (models, data) are included in container

### Issue: Health check failures

**Symptoms:** Service shows unhealthy status

**Solutions:**
1. Test health endpoint locally:
   ```bash
   docker run -p 8001:8001 searei-safety:latest
   curl http://localhost:8001/healthz
   ```

2. Increase health check grace period
3. Check if models are loading correctly
4. Verify database connectivity

### Issue: High latency

**Symptoms:** Response times > 100ms

**Solutions:**
1. Enable horizontal auto-scaling
2. Increase worker count (WORKERS env var)
3. Add Redis caching
4. Use CDN for static assets
5. Check database query performance

---

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

---

## 🆘 Support

If you encounter issues:

1. Check deployment logs
2. Review this guide's troubleshooting section
3. Open an issue on GitHub
4. Contact support: support@searei.ai

---

**Status:** ✅ Production-ready | **Last Updated:** January 2025 | **Version:** 2.1.0












