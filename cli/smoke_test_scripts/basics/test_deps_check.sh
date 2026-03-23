#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies that all mandatory bioinformatics tools (samtools, bcftools, bwa, etc.) are installed and accessible in the system PATH."
    echo "End Goal: Success exit code (0) and a report showing all mandatory tools as 'verified'."
    exit 0
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
