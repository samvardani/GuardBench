#!/bin/bash
# AEGIS Quick Start - Run this file to see everything

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║          🚀 AEGIS QUICK START - Choose Your Adventure 🚀                  ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "What do you want to do?"
echo ""
echo "  1) 🎭 Watch the magic (Run AEGIS demo)"
echo "  2) 🚀 Launch the platform (Start API + ML + AIS)"
echo "  3) 📖 Read the blueprint (Open REVOLUTIONARY_VISION.md)"
echo "  4) 📋 Get the launch guide (Open LETS_GO.md)"
echo "  5) 🧪 Test it yourself (Interactive test)"
echo "  6) 📊 Check status (What's running?)"
echo "  7) 💡 Show me everything"
echo ""
read -p "Enter your choice (1-7): " choice

case $choice in
    1)
        echo ""
        echo "🎭 Running AEGIS Demo..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ./scripts/start_aegis.sh demo
        ;;
    2)
        echo ""
        echo "🚀 Launching AEGIS Platform..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Platform will start at: http://localhost:8001"
        echo "Documentation: http://localhost:8001/technical.html"
        echo ""
        echo "Press Ctrl+C to stop when done."
        echo ""
        sleep 2
        ./scripts/start_aegis.sh start
        ;;
    3)
        echo ""
        echo "📖 Opening REVOLUTIONARY_VISION.md..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        less REVOLUTIONARY_VISION.md
        ;;
    4)
        echo ""
        echo "📋 Opening LETS_GO.md..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        less LETS_GO.md
        ;;
    5)
        echo ""
        echo "🧪 Interactive Testing..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 src/guards/aegis_guard.py
        echo ""
        echo "Want to test more? Try:"
        echo "  ./scripts/start_aegis.sh test"
        ;;
    6)
        echo ""
        echo "📊 System Status..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ./scripts/start_aegis.sh status
        ;;
    7)
        echo ""
        echo "💡 Complete Overview..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "📁 Files Created:"
        echo ""
        ls -lh REVOLUTIONARY_VISION.md LETS_GO.md | awk '{print "  ✓", $9, "(" $5 ")"}'
        ls -lh src/aegis/*.py src/guards/aegis_guard.py demos/aegis_demo.py 2>/dev/null | awk '{print "  ✓", $9, "(" $5 ")"}'
        echo ""
        echo "🎯 Quick Commands:"
        echo "  ./scripts/start_aegis.sh demo    - Watch AIS learn"
        echo "  ./scripts/start_aegis.sh start   - Launch platform"
        echo "  ./scripts/start_aegis.sh status  - Check status"
        echo ""
        echo "📖 Documentation:"
        echo "  REVOLUTIONARY_VISION.md - Complete blueprint (10K words)"
        echo "  LETS_GO.md             - Launch guide"
        echo ""
        echo "💰 Business Opportunity:"
        echo "  TAM:              \$100B/year"
        echo "  Target (5y):      \$10B/year revenue"
        echo "  Exit valuation:   \$50B-\$200B"
        echo ""
        echo "🚀 Next Steps:"
        echo "  1. Run the demo (./scripts/start_aegis.sh demo)"
        echo "  2. Read REVOLUTIONARY_VISION.md"
        echo "  3. Read LETS_GO.md for launch plan"
        echo "  4. Start building!"
        echo ""
        ;;
    *)
        echo "Invalid choice. Run './QUICK_START.sh' again."
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛡️  AEGIS - Making AI Safe for Humanity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"












