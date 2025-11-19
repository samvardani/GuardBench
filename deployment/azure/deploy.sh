#!/bin/bash
set -e

# Azure AKS Deployment Script for SeaRei Safety Service
# Usage: ./deploy.sh <resource-group> <aks-cluster> <acr-name> <region>

RESOURCE_GROUP=${1:-searei-rg}
AKS_CLUSTER=${2:-searei-aks}
ACR_NAME=${3:-seareiacr}
LOCATION=${4:-eastus}
NAMESPACE="production"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SeaRei Azure AKS Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "AKS Cluster:    ${AKS_CLUSTER}"
echo "ACR Name:       ${ACR_NAME}"
echo "Location:       ${LOCATION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Login to Azure
echo ""
echo "🔐 Step 1: Ensuring Azure login..."
az account show || az login

# 2. Create resource group if it doesn't exist
echo ""
echo "📝 Step 2: Ensuring resource group exists..."
az group create --name ${RESOURCE_GROUP} --location ${LOCATION} || true

# 3. Create ACR if it doesn't exist
echo ""
echo "📦 Step 3: Ensuring Azure Container Registry exists..."
az acr create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${ACR_NAME} \
    --sku Standard \
    --location ${LOCATION} || true

# 4. Build and push Docker image
echo ""
echo "🏗️  Step 4: Building and pushing Docker image..."
az acr build \
    --registry ${ACR_NAME} \
    --image searei-safety:$(git rev-parse --short HEAD) \
    --image searei-safety:latest \
    --file deployment/azure/Dockerfile.production \
    .

# 5. Get AKS credentials
echo ""
echo "🔑 Step 5: Getting AKS credentials..."
az aks get-credentials \
    --resource-group ${RESOURCE_GROUP} \
    --name ${AKS_CLUSTER} \
    --overwrite-existing

# 6. Create namespace if it doesn't exist
echo ""
echo "📂 Step 6: Creating namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 7. Create secrets
echo ""
echo "🔐 Step 7: Creating secrets..."
SESSION_SECRET=$(openssl rand -base64 32)
DATABASE_URL="sqlite:///./history.db"

kubectl create secret generic searei-secrets \
    --from-literal=session-secret=${SESSION_SECRET} \
    --from-literal=database-url=${DATABASE_URL} \
    --namespace=${NAMESPACE} \
    --dry-run=client -o yaml | kubectl apply -f -

# 8. Update deployment manifest with ACR name
echo ""
echo "📄 Step 8: Updating deployment manifest..."
sed "s/your-registry/${ACR_NAME}/g" deployment/azure/kubernetes/deployment.yaml > /tmp/deployment-updated.yaml

# 9. Apply Kubernetes manifests
echo ""
echo "🚀 Step 9: Deploying to Kubernetes..."
kubectl apply -f /tmp/deployment-updated.yaml

# 10. Wait for rollout
echo ""
echo "⏳ Step 10: Waiting for rollout to complete..."
kubectl rollout status deployment/searei-safety-service -n ${NAMESPACE} --timeout=5m

# 11. Get service external IP
echo ""
echo "🔗 Step 11: Getting service endpoint..."
echo "Waiting for external IP (this may take a few minutes)..."

EXTERNAL_IP=""
while [ -z $EXTERNAL_IP ]; do
    sleep 10
    EXTERNAL_IP=$(kubectl get service searei-safety-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    echo -n "."
done
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service URL: http://${EXTERNAL_IP}"
echo "Health Check: http://${EXTERNAL_IP}/healthz"
echo "API Docs: http://${EXTERNAL_IP}/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 12. Show deployment status
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n ${NAMESPACE} -l app=searei-safety
kubectl get hpa -n ${NAMESPACE}

# 13. Test deployment
echo ""
echo "🧪 Step 12: Testing deployment..."
sleep 10
curl -f http://${EXTERNAL_IP}/healthz && echo "✅ Health check passed!" || echo "❌ Health check failed!"












