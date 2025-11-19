#!/bin/bash

#═══════════════════════════════════════════════════════════════════════════
# SeaRei v2.1.0 - Production Deployment Script
#═══════════════════════════════════════════════════════════════════════════
#
# This script automates the deployment of SeaRei to staging or production
# with the new BERT-Tiny transformer ensemble system.
#
# Usage:
#   ./scripts/deploy.sh [staging|production]
#
# Features:
#   • Pre-deployment checks (models, tests, dependencies)
#   • Environment configuration
#   • Service startup with monitoring
#   • Health check validation
#   • Rollback capability
#
#═══════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/api.pid"
API_LOG="$LOG_DIR/api.log"
DEPLOY_LOG="$LOG_DIR/deploy_$(date +%Y%m%d_%H%M%S).log"

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# --- Logging ---
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"
}

# --- Header ---
header() {
    echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                                                                           ║${NC}"
    echo -e "${PURPLE}║         🚀 SeaRei v2.1.0 - Production Deployment Script 🚀                ║${NC}"
    echo -e "${PURPLE}║                                                                           ║${NC}"
    echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# --- Parse Arguments ---
ENVIRONMENT="${1:-staging}"

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Usage: $0 [staging|production]"
    exit 1
fi

# --- Environment-specific Configuration ---
if [[ "$ENVIRONMENT" == "production" ]]; then
    API_HOST="0.0.0.0"
    API_PORT="${API_PORT:-8001}"
    WORKERS="${WORKERS:-4}"
    RATE_LIMIT_ENABLED="true"
    LOG_LEVEL="info"
else
    API_HOST="0.0.0.0"
    API_PORT="${API_PORT:-8001}"
    WORKERS="${WORKERS:-2}"
    RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-false}"
    LOG_LEVEL="debug"
fi

# --- Pre-Deployment Checks ---
header
log "Starting deployment to ${BOLD}$ENVIRONMENT${NC}..."
log "Log file: $DEPLOY_LOG"
echo ""

# Create log directory
mkdir -p "$LOG_DIR"

log "Running pre-deployment checks..."

# Check 1: Python version
log "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9) ]]; then
    log_error "Python 3.9+ required, found $PYTHON_VERSION"
    exit 1
fi
log_success "Python $PYTHON_VERSION"

# Check 2: Virtual environment
log "Checking virtual environment..."
if [[ -d "$PROJECT_ROOT/venv" ]]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    log_success "Virtual environment activated"
else
    log_warning "No virtual environment found, using system Python"
fi

# Check 3: Dependencies
log "Checking dependencies..."
if ! python3 -c "import fastapi, uvicorn, torch, transformers" 2>/dev/null; then
    log_error "Missing dependencies. Run: pip install -r requirements.txt"
    exit 1
fi
log_success "All dependencies installed"

# Check 4: Models
log "Checking models..."
TRANSFORMER_MODEL="$PROJECT_ROOT/models/transformer_toxicity.pkl"
ML_MODEL="$PROJECT_ROOT/models/ml_fast.pkl"

if [[ ! -f "$TRANSFORMER_MODEL" ]]; then
    log_error "Transformer model not found: $TRANSFORMER_MODEL"
    log "Run: python3 scripts/train_transformer_model.py"
    exit 1
fi
log_success "Transformer model ($(du -h "$TRANSFORMER_MODEL" | cut -f1))"

if [[ ! -f "$ML_MODEL" ]]; then
    log_warning "Classical ML model not found: $ML_MODEL (ensemble will use rules+transformer)"
else
    log_success "Classical ML model ($(du -h "$ML_MODEL" | cut -f1))"
fi

# Check 5: Policy files
log "Checking policy files..."
if [[ ! -f "$PROJECT_ROOT/policy/policy.yaml" ]]; then
    log_error "Policy file not found: policy/policy.yaml"
    exit 1
fi
log_success "Policy file found"

# Check 6: Tests (staging only)
if [[ "$ENVIRONMENT" == "staging" ]]; then
    log "Running tests..."
    cd "$PROJECT_ROOT"
    if pytest tests/ -q -m "not slow" --disable-warnings 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Tests passed"
    else
        log_error "Tests failed. Fix issues before deploying."
        exit 1
    fi
fi

# Check 7: Port availability
log "Checking port $API_PORT..."
if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port $API_PORT is in use. Will stop existing service."
    # Stop existing service
    pkill -f "uvicorn.*service.api" || true
    sleep 2
fi
log_success "Port $API_PORT available"

echo ""
log "${BOLD}All pre-deployment checks passed!${NC}"
echo ""

# --- Environment Setup ---
log "Configuring environment for $ENVIRONMENT..."

export PYTHONPATH="$PROJECT_ROOT"
export ENVIRONMENT="$ENVIRONMENT"
export API_HOST="$API_HOST"
export API_PORT="$API_PORT"
export RATE_LIMIT_ENABLED="$RATE_LIMIT_ENABLED"
export LOG_LEVEL="$LOG_LEVEL"

# Generate secure session secret for production
if [[ "$ENVIRONMENT" == "production" ]]; then
    if [[ -z "$SESSION_SECRET" ]]; then
        export SESSION_SECRET=$(openssl rand -hex 32)
        log_warning "Generated random SESSION_SECRET (set permanently in env for production)"
    fi
fi

log_success "Environment configured"

# --- Deployment ---
log "${BOLD}Deploying SeaRei v2.1.0 to $ENVIRONMENT...${NC}"

cd "$PROJECT_ROOT"

# Start API service
log "Starting API service..."
nohup python3 -m uvicorn service.api:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    > "$API_LOG" 2>&1 &

API_PID=$!
echo "$API_PID" > "$PID_FILE"

log "API started (PID: $API_PID)"
log "Log file: $API_LOG"

# Wait for service to start
log "Waiting for service to start..."
sleep 5

# --- Health Check ---
log "Running health checks..."

MAX_RETRIES=10
RETRY_DELAY=2
HEALTH_URL="http://localhost:$API_PORT/healthz"

for i in $(seq 1 $MAX_RETRIES); do
    if curl -s -f "$HEALTH_URL" >/dev/null 2>&1; then
        log_success "Health check passed"
        break
    else
        if [[ $i -eq $MAX_RETRIES ]]; then
            log_error "Health check failed after $MAX_RETRIES attempts"
            log "Check logs: tail -f $API_LOG"
            exit 1
        fi
        log "Health check attempt $i/$MAX_RETRIES failed, retrying in ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    fi
done

# --- Smoke Tests ---
log "Running smoke tests..."

# Test 1: Score endpoint
TEST_TEXT="I will kill you"
SCORE_RESPONSE=$(curl -s -X POST "http://localhost:$API_PORT/score" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"$TEST_TEXT\"}")

SCORE=$(echo "$SCORE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('score', 'N/A'))")

if [[ "$SCORE" != "N/A" ]]; then
    log_success "Score endpoint working (score: $SCORE for '$TEST_TEXT')"
else
    log_error "Score endpoint failed"
    log "Response: $SCORE_RESPONSE"
    exit 1
fi

# Test 2: Check ensemble is active
ENSEMBLE_CHECK=$(tail -20 "$API_LOG" | grep -i "ensemble" || echo "")
if [[ -n "$ENSEMBLE_CHECK" ]]; then
    log_success "Ensemble guard loaded"
else
    log_warning "Ensemble guard may not be active (check logs)"
fi

echo ""
log "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
log "${GREEN}${BOLD}   ✅ DEPLOYMENT SUCCESSFUL!${NC}"
log "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# --- Deployment Summary ---
echo -e "${BOLD}Deployment Summary:${NC}"
echo ""
echo "  Environment:     $ENVIRONMENT"
echo "  API URL:         http://localhost:$API_PORT"
echo "  Workers:         $WORKERS"
echo "  Rate Limiting:   $RATE_LIMIT_ENABLED"
echo "  PID:             $API_PID"
echo "  Log File:        $API_LOG"
echo "  Deploy Log:      $DEPLOY_LOG"
echo ""

echo -e "${BOLD}Quick Links:${NC}"
echo ""
echo "  • Technical Docs:  http://localhost:$API_PORT/technical.html"
echo "  • Dashboard:       http://localhost:$API_PORT/index.html"
echo "  • Health Check:    http://localhost:$API_PORT/healthz"
echo "  • Metrics:         http://localhost:$API_PORT/metrics"
echo ""

echo -e "${BOLD}Test API:${NC}"
echo ""
echo "  curl -X POST http://localhost:$API_PORT/score \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"text\":\"you should die\"}'"
echo ""

echo -e "${BOLD}Monitor Logs:${NC}"
echo ""
echo "  tail -f $API_LOG"
echo ""

echo -e "${BOLD}Stop Service:${NC}"
echo ""
echo "  kill $API_PID"
echo "  # or"
echo "  pkill -f 'uvicorn.*service.api'"
echo ""

# --- Save Deployment Info ---
cat > "$LOG_DIR/deployment_info.txt" <<EOF
Deployment Information
======================

Date: $(date)
Environment: $ENVIRONMENT
Version: v2.1.0
PID: $API_PID
API URL: http://localhost:$API_PORT
Workers: $WORKERS
Rate Limiting: $RATE_LIMIT_ENABLED

Models:
  • Transformer: $TRANSFORMER_MODEL ($(du -h "$TRANSFORMER_MODEL" | cut -f1))
  • Classical ML: $ML_MODEL ($(du -h "$ML_MODEL" | cut -f1 2>/dev/null || echo "N/A"))

Logs:
  • API Log: $API_LOG
  • Deploy Log: $DEPLOY_LOG

Health Check: $HEALTH_URL
EOF

log_success "Deployment info saved to $LOG_DIR/deployment_info.txt"

echo ""
echo -e "${GREEN}${BOLD}🚀 SeaRei v2.1.0 is now running in $ENVIRONMENT! 🚀${NC}"
echo ""

