#!/bin/bash
set -e

# GCP Cloud Run Deployment Script for SeaRei Safety Service
# Usage: ./deploy.sh <project-id> <region>

PROJECT_ID=${1:-your-project-id}
REGION=${2:-us-central1}
SERVICE_NAME="searei-safety-service"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SeaRei GCP Cloud Run Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Project ID:    ${PROJECT_ID}"
echo "Region:        ${REGION}"
echo "Service Name:  ${SERVICE_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Set project
echo ""
echo "📝 Step 1: Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# 2. Enable required APIs
echo ""
echo "🔧 Step 2: Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com

# 3. Create secrets if they don't exist
echo ""
echo "🔐 Step 3: Checking secrets..."
gcloud secrets describe searei-session-secret || \
    echo -n "$(openssl rand -base64 32)" | gcloud secrets create searei-session-secret --data-file=-

gcloud secrets describe searei-database-url || \
    echo -n "sqlite:///./history.db" | gcloud secrets create searei-database-url --data-file=-

# 4. Build and deploy using Cloud Build
echo ""
echo "🏗️  Step 4: Building and deploying with Cloud Build..."
gcloud builds submit \
    --config=deployment/gcp/cloudbuild.yaml \
    --substitutions=_REGION=${REGION} \
    .

# 5. Get service URL
echo ""
echo "🔗 Step 5: Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service URL: ${SERVICE_URL}"
echo "Health Check: ${SERVICE_URL}/healthz"
echo "API Docs: ${SERVICE_URL}/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 6. Test deployment
echo ""
echo "🧪 Step 6: Testing deployment..."
sleep 10
curl -f ${SERVICE_URL}/healthz && echo "✅ Health check passed!" || echo "❌ Health check failed!"

# 7. Show logs
echo ""
echo "📋 Recent logs:"
gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit=20












