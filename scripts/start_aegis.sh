#!/bin/bash
# Start AEGIS Platform
# Revolutionary AI Safety System

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                                           ║${NC}"
echo -e "${PURPLE}║     🚀 PROJECT AEGIS - REVOLUTIONARY AI SAFETY PLATFORM 🚀                ║${NC}"
echo -e "${PURPLE}║     'The Last AI Safety System Humanity Will Ever Need'                  ║${NC}"
echo -e "${PURPLE}║                                                                           ║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

MODE="${1:-help}"

case "$MODE" in
    start)
        echo -e "${GREEN}🚀 Starting AEGIS Platform${NC}"
        echo ""
        
        # 1. Check if models exist
        if [ ! -f "models/ml_fast.pkl" ]; then
            echo -e "${YELLOW}⚠  ML model not found, training...${NC}"
            python3 scripts/train_ml_model.py
            echo ""
        fi
        
        # 2. Start ML training daemon (background)
        echo -e "${CYAN}🤖 Starting ML training daemon...${NC}"
        mkdir -p logs
        nohup python3 scripts/ml_training_daemon.py --interval 3600 --schedule weekly > logs/ml_daemon.log 2>&1 &
        ML_DAEMON_PID=$!
        echo "   ✓ Daemon started (PID: $ML_DAEMON_PID)"
        
        # 3. Start API with AEGIS
        echo -e "${CYAN}🛡️ Starting AEGIS API...${NC}"
        echo "   URL: http://localhost:8001"
        echo "   Documentation: http://localhost:8001/technical.html"
        echo "   AEGIS Demo: python3 demos/aegis_demo.py"
        echo ""
        echo -e "${GREEN}✅ AEGIS Platform Running${NC}"
        echo -e "${YELLOW}   Press Ctrl+C to stop API (daemon continues)${NC}"
        echo ""
        
        # Start API (foreground)
        export AEGIS_ENABLED=true
        python3 -m uvicorn service.api:app --host 0.0.0.0 --port 8001 --reload
        ;;
    
    stop)
        echo -e "${RED}🛑 Stopping AEGIS Platform...${NC}"
        
        # Stop daemon
        if pgrep -f "ml_training_daemon" > /dev/null; then
            pkill -f "ml_training_daemon"
            echo "   ✓ ML daemon stopped"
        fi
        
        # Stop API
        if pgrep -f "uvicorn service.api" > /dev/null; then
            pkill -f "uvicorn service.api"
            echo "   ✓ API stopped"
        fi
        
        echo -e "${GREEN}✓ AEGIS Platform stopped${NC}"
        ;;
    
    demo)
        echo -e "${PURPLE}🎭 Running AEGIS Demo...${NC}"
        echo ""
        python3 demos/aegis_demo.py
        ;;
    
    test)
        echo -e "${CYAN}🧪 Testing AEGIS Guard...${NC}"
        echo ""
        python3 src/guards/aegis_guard.py
        ;;
    
    status)
        echo -e "${CYAN}📊 AEGIS Platform Status${NC}"
        echo ""
        
        # Check daemon
        if pgrep -f "ml_training_daemon" > /dev/null; then
            PID=$(pgrep -f "ml_training_daemon")
            echo -e "   ML Daemon:  ${GREEN}✓ Running${NC} (PID: $PID)"
        else
            echo -e "   ML Daemon:  ${YELLOW}✗ Not running${NC}"
        fi
        
        # Check API
        if pgrep -f "uvicorn service.api" > /dev/null; then
            PID=$(pgrep -f "uvicorn service.api")
            echo -e "   API:        ${GREEN}✓ Running${NC} (PID: $PID)"
        else
            echo -e "   API:        ${YELLOW}✗ Not running${NC}"
        fi
        
        # Check ML model
        if [ -f "models/ml_fast.pkl" ]; then
            SIZE=$(du -h models/ml_fast.pkl | cut -f1)
            echo -e "   ML Model:   ${GREEN}✓ Exists${NC} (${SIZE})"
        else
            echo -e "   ML Model:   ${YELLOW}✗ Not found${NC}"
        fi
        
        # Check AIS state
        if [ -f "aegis_antibodies.json" ]; then
            COUNT=$(python3 -c "import json; d=json.load(open('aegis_antibodies.json')); print(len(d.get('antibodies', [])))" 2>/dev/null || echo "0")
            echo -e "   AIS:        ${GREEN}✓ Active${NC} ($COUNT antibodies)"
        else
            echo -e "   AIS:        ${CYAN}⚡ Fresh${NC} (no antibodies yet)"
        fi
        
        echo ""
        ;;
    
    export)
        echo -e "${CYAN}📦 Exporting AEGIS antibodies...${NC}"
        python3 -c "
from guards.aegis_guard import export_ais_state
stats = export_ais_state('aegis_antibodies.json')
print(f'✓ Exported {stats.get(\"antibody_count\", 0)} antibodies')
print(f'  Stats: {stats}')
"
        echo ""
        ;;
    
    import)
        FILE="${2:-aegis_antibodies.json}"
        echo -e "${CYAN}📥 Importing AEGIS antibodies from $FILE...${NC}"
        python3 -c "
from guards.aegis_guard import import_ais_state
stats = import_ais_state('$FILE')
print(f'✓ Imported antibodies')
print(f'  Stats: {stats}')
"
        echo ""
        ;;
    
    train)
        echo -e "${CYAN}🎓 Training ML model...${NC}"
        python3 scripts/train_ml_model.py --validate
        echo ""
        ;;
    
    docs)
        echo -e "${CYAN}📖 Opening documentation...${NC}"
        echo ""
        echo "Available documentation:"
        echo "  • REVOLUTIONARY_VISION.md - Complete AEGIS blueprint"
        echo "  • scripts/README_ML_TRAINING.md - ML training system"
        echo "  • http://localhost:8001/technical.html - Web docs (API must be running)"
        echo ""
        cat REVOLUTIONARY_VISION.md | head -100
        echo ""
        echo "[... Full vision in REVOLUTIONARY_VISION.md ...]"
        ;;
    
    help|*)
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  ${GREEN}start${NC}    - Start complete AEGIS platform (API + ML daemon + AIS)"
        echo "  ${GREEN}stop${NC}     - Stop all AEGIS services"
        echo "  ${GREEN}demo${NC}     - Run interactive AEGIS demo"
        echo "  ${GREEN}test${NC}     - Test AEGIS guard"
        echo "  ${GREEN}status${NC}   - Show platform status"
        echo "  ${GREEN}export${NC}   - Export AIS antibodies for sharing"
        echo "  ${GREEN}import${NC}   - Import AIS antibodies from network"
        echo "  ${GREEN}train${NC}    - Train ML model manually"
        echo "  ${GREEN}docs${NC}     - View documentation"
        echo ""
        echo "Examples:"
        echo "  $0 start              # Start AEGIS platform"
        echo "  $0 demo               # See AIS learning in action"
        echo "  $0 export             # Share antibodies with network"
        echo "  $0 import network.json # Import antibodies from peers"
        echo ""
        echo -e "${PURPLE}🎯 Quick Start:${NC}"
        echo "  1. Run: $0 demo      # See the magic"
        echo "  2. Run: $0 start     # Launch platform"
        echo "  3. Open: http://localhost:8001/technical.html"
        echo ""
        ;;
esac












