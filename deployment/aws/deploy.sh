#!/bin/bash
set -e

# AWS ECS Deployment Script for SeaRei Safety Service
# Usage: ./deploy.sh <environment> <region>

ENVIRONMENT=${1:-production}
AWS_REGION=${2:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="searei-safety"
ECS_CLUSTER="searei-${ENVIRONMENT}"
ECS_SERVICE="searei-api"
TASK_FAMILY="searei-safety-service"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SeaRei AWS ECS Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Environment: ${ENVIRONMENT}"
echo "Region:      ${AWS_REGION}"
echo "Account ID:  ${AWS_ACCOUNT_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Build Docker image
echo ""
echo "📦 Step 1: Building Docker image..."
docker build -f deployment/aws/Dockerfile.production -t ${ECR_REPOSITORY}:latest .
docker tag ${ECR_REPOSITORY}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
docker tag ${ECR_REPOSITORY}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:$(git rev-parse --short HEAD)

# 2. Login to ECR
echo ""
echo "🔐 Step 2: Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# 3. Create ECR repository if it doesn't exist
echo ""
echo "📝 Step 3: Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} || \
    aws ecr create-repository --repository-name ${ECR_REPOSITORY} --region ${AWS_REGION}

# 4. Push to ECR
echo ""
echo "⬆️  Step 4: Pushing image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:$(git rev-parse --short HEAD)

# 5. Update task definition
echo ""
echo "📄 Step 5: Registering new task definition..."
TASK_DEFINITION=$(cat deployment/aws/ecs-task-definition.json | \
    sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" | \
    sed "s/REGION/${AWS_REGION}/g")

NEW_TASK_DEF_ARN=$(echo $TASK_DEFINITION | \
    aws ecs register-task-definition --cli-input-json file:///dev/stdin --region ${AWS_REGION} | \
    jq -r '.taskDefinition.taskDefinitionArn')

echo "✅ New task definition: ${NEW_TASK_DEF_ARN}"

# 6. Update ECS service
echo ""
echo "🚀 Step 6: Updating ECS service..."
aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${ECS_SERVICE} \
    --task-definition ${NEW_TASK_DEF_ARN} \
    --force-new-deployment \
    --region ${AWS_REGION}

# 7. Wait for deployment to complete
echo ""
echo "⏳ Step 7: Waiting for deployment to stabilize..."
aws ecs wait services-stable \
    --cluster ${ECS_CLUSTER} \
    --services ${ECS_SERVICE} \
    --region ${AWS_REGION}

# 8. Get service URL
echo ""
echo "🔗 Step 8: Getting service endpoint..."
LOAD_BALANCER=$(aws ecs describe-services \
    --cluster ${ECS_CLUSTER} \
    --services ${ECS_SERVICE} \
    --region ${AWS_REGION} | \
    jq -r '.services[0].loadBalancers[0].targetGroupArn')

if [ ! -z "$LOAD_BALANCER" ] && [ "$LOAD_BALANCER" != "null" ]; then
    LB_ARN=$(aws elbv2 describe-target-groups \
        --target-group-arns ${LOAD_BALANCER} \
        --region ${AWS_REGION} | \
        jq -r '.TargetGroups[0].LoadBalancerArns[0]')
    
    DNS_NAME=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns ${LB_ARN} \
        --region ${AWS_REGION} | \
        jq -r '.LoadBalancers[0].DNSName')
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Deployment Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Service URL: http://${DNS_NAME}"
    echo "Health Check: http://${DNS_NAME}/healthz"
    echo "API Docs: http://${DNS_NAME}/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Deployment Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Note: Load balancer DNS not found. Service may be using direct task IPs."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# 9. Test deployment
echo ""
echo "🧪 Step 9: Testing deployment..."
if [ ! -z "$DNS_NAME" ]; then
    sleep 10
    curl -f http://${DNS_NAME}/healthz && echo "✅ Health check passed!" || echo "❌ Health check failed!"
fi












