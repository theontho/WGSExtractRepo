#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Dependency Check Smoke Test"
echo "--------------------------------------------------------"

# 1. Check dependencies
echo ":: Running 'deps check'..."
uv run wgsextract deps check

if [ $? -eq 0 ]; then
    echo "✅ Success: deps check completed."
else
    echo "❌ Failure: deps check failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Dependency Check Smoke Test: PASSED"
echo "========================================================"
