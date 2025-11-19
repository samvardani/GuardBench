#!/bin/bash
# Start ML Training System
# Usage: ./scripts/start_ml_system.sh [mode]
# Modes: daemon, once, api, all

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SeaRei ML Training System${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

MODE="${1:-help}"

case "$MODE" in
    daemon)
        echo -e "${GREEN}🤖 Starting ML Training Daemon (continuous mode)${NC}"
        echo "   Check interval: 1 hour"
        echo "   Retrain schedule: weekly"
        echo ""
        
        # Create logs directory
        mkdir -p logs
        
        # Start daemon in background
        nohup python3 scripts/ml_training_daemon.py \
            --interval 3600 \
            --schedule weekly \
            > logs/ml_daemon.log 2>&1 &
        
        PID=$!
        echo "   Daemon started (PID: $PID)"
        echo "   Logs: tail -f logs/ml_daemon.log"
        echo ""
        echo -e "${GREEN}✓ Daemon running${NC}"
        ;;
    
    once)
        echo -e "${GREEN}🔄 Running training cycle once${NC}"
        echo ""
        
        python3 scripts/ml_training_daemon.py --once
        
        echo ""
        echo -e "${GREEN}✓ Training cycle complete${NC}"
        ;;
    
    api)
        echo -e "${GREEN}🚀 Starting API with ML hybrid guard${NC}"
        echo "   URL: http://localhost:8001"
        echo "   Press Ctrl+C to stop"
        echo ""
        
        # Check if model exists
        if [ ! -f "models/ml_fast.pkl" ]; then
            echo -e "${YELLOW}⚠  No ML model found, training first...${NC}"
            python3 scripts/train_ml_model.py
            echo ""
        fi
        
        # Start API
        python3 -m uvicorn service.api:app \
            --host 0.0.0.0 \
            --port 8001 \
            --reload
        ;;
    
    all)
        echo -e "${GREEN}🎯 Starting complete ML system${NC}"
        echo ""
        
        # 1. Check/train model if needed
        if [ ! -f "models/ml_fast.pkl" ]; then
            echo -e "${BLUE}📦 Training initial model...${NC}"
            python3 scripts/train_ml_model.py --validate
            echo ""
        else
            echo -e "${GREEN}✓ Model exists${NC}"
        fi
        
        # 2. Start daemon
        echo -e "${BLUE}🤖 Starting training daemon...${NC}"
        mkdir -p logs
        nohup python3 scripts/ml_training_daemon.py \
            --interval 3600 \
            --schedule weekly \
            > logs/ml_daemon.log 2>&1 &
        DAEMON_PID=$!
        echo "   Daemon started (PID: $DAEMON_PID)"
        echo ""
        
        # 3. Start API
        echo -e "${BLUE}🚀 Starting API...${NC}"
        echo "   URL: http://localhost:8001"
        echo "   Documentation: http://localhost:8001/technical.html"
        echo "   Daemon logs: tail -f logs/ml_daemon.log"
        echo ""
        echo -e "${GREEN}✓ System running${NC}"
        echo -e "${YELLOW}   Press Ctrl+C to stop API (daemon will continue)${NC}"
        echo ""
        
        # Start API (foreground)
        python3 -m uvicorn service.api:app \
            --host 0.0.0.0 \
            --port 8001 \
            --reload
        ;;
    
    stop)
        echo -e "${YELLOW}🛑 Stopping ML system...${NC}"
        echo ""
        
        # Stop daemon
        if pgrep -f "ml_training_daemon" > /dev/null; then
            pkill -f "ml_training_daemon"
            echo "   ✓ Daemon stopped"
        else
            echo "   ⚠  Daemon not running"
        fi
        
        # Stop API
        if pgrep -f "uvicorn service.api" > /dev/null; then
            pkill -f "uvicorn service.api"
            echo "   ✓ API stopped"
        else
            echo "   ⚠  API not running"
        fi
        
        echo ""
        echo -e "${GREEN}✓ System stopped${NC}"
        ;;
    
    status)
        echo -e "${BLUE}📊 System Status${NC}"
        echo ""
        
        # Check daemon
        if pgrep -f "ml_training_daemon" > /dev/null; then
            DAEMON_PID=$(pgrep -f "ml_training_daemon")
            echo -e "   Daemon:  ${GREEN}✓ Running${NC} (PID: $DAEMON_PID)"
        else
            echo -e "   Daemon:  ${YELLOW}✗ Not running${NC}"
        fi
        
        # Check API
        if pgrep -f "uvicorn service.api" > /dev/null; then
            API_PID=$(pgrep -f "uvicorn service.api")
            echo -e "   API:     ${GREEN}✓ Running${NC} (PID: $API_PID)"
        else
            echo -e "   API:     ${YELLOW}✗ Not running${NC}"
        fi
        
        # Check model
        if [ -f "models/ml_fast.pkl" ]; then
            MODEL_SIZE=$(du -h models/ml_fast.pkl | cut -f1)
            MODEL_AGE=$(find models/ml_fast.pkl -mtime +0 -printf '%T+\n' 2>/dev/null || stat -f "%Sm" -t "%Y-%m-%d %H:%M" models/ml_fast.pkl 2>/dev/null)
            echo -e "   Model:   ${GREEN}✓ Exists${NC} (${MODEL_SIZE}, modified: ${MODEL_AGE})"
        else
            echo -e "   Model:   ${YELLOW}✗ Not found${NC}"
        fi
        
        # Check data
        if [ -f "datasets_raw/train.csv" ]; then
            DATA_SIZE=$(wc -l < datasets_raw/train.csv)
            echo -e "   Data:    ${GREEN}✓ Loaded${NC} (${DATA_SIZE} rows)"
        else
            echo -e "   Data:    ${YELLOW}✗ Not found${NC}"
        fi
        
        echo ""
        ;;
    
    train)
        echo -e "${GREEN}🎓 Training new model${NC}"
        echo ""
        
        python3 scripts/train_ml_model.py --validate
        
        echo ""
        echo -e "${GREEN}✓ Training complete${NC}"
        echo -e "${BLUE}   API will auto-reload on next request${NC}"
        ;;
    
    download)
        echo -e "${GREEN}📥 Downloading datasets${NC}"
        echo ""
        
        python3 scripts/download_datasets.py --dataset all
        
        echo ""
        echo -e "${GREEN}✓ Download complete${NC}"
        ;;
    
    test)
        echo -e "${GREEN}🧪 Testing ML hybrid system${NC}"
        echo ""
        
        # Check if API is running
        if ! curl -s http://localhost:8001/healthz > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠  API not running, starting...${NC}"
            python3 -m uvicorn service.api:app --host 0.0.0.0 --port 8001 > /dev/null 2>&1 &
            sleep 3
        fi
        
        # Test cases
        echo "Testing API:"
        for text in "I will kill you" "you should die" "have a great day"; do
            echo "  '$text':"
            curl -s -X POST http://localhost:8001/score \
                -H "Content-Type: application/json" \
                -d "{\"text\": \"$text\"}" | \
                python3 -c "import sys, json; d=json.load(sys.stdin); print(f'    Score: {d[\"score\"]:.3f}, Method: {d.get(\"rationale\", \"N/A\")}')"
        done
        
        echo ""
        echo -e "${GREEN}✓ Tests complete${NC}"
        ;;
    
    help|*)
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  daemon    - Start training daemon (continuous, background)"
        echo "  once      - Run one training cycle and exit"
        echo "  api       - Start API only"
        echo "  all       - Start everything (daemon + API)"
        echo "  stop      - Stop all services"
        echo "  status    - Show system status"
        echo "  train     - Train model manually"
        echo "  download  - Download new datasets"
        echo "  test      - Test API with sample requests"
        echo "  help      - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 all                  # Start complete system"
        echo "  $0 daemon               # Start daemon only"
        echo "  $0 once                 # Train once"
        echo "  $0 status               # Check status"
        echo ""
        ;;
esac

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"












