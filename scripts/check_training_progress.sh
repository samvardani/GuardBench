#!/bin/bash

# Check if training is still running
if pgrep -f "train_transformer_model.py" > /dev/null; then
    echo "✓ Training is running"
    echo ""
    
    # Show latest progress
    echo "📊 Latest Progress:"
    tail -15 training.log | grep -E "Epoch|Batch|Loss|ROC-AUC|Train Loss"
    
    echo ""
    echo "💡 Monitor live with: tail -f training.log"
else
    echo "✓ Training completed!"
    echo ""
    echo "📊 Final Results:"
    grep -E "ROC-AUC|Train Loss|Training complete" training.log | tail -10
    
    if [ -f models/transformer_toxicity.pkl ]; then
        MODEL_SIZE=$(du -h models/transformer_toxicity.pkl | cut -f1)
        echo ""
        echo "✓ Model saved: models/transformer_toxicity.pkl ($MODEL_SIZE)"
    fi
fi












