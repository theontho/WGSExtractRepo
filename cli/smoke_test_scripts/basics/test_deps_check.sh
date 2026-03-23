#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies that all mandatory bioinformatics tools (samtools, bcftools, bwa, etc.) are installed and accessible in the system PATH."
    echo "✅ Verified End Goal: Success exit code (0) and a report showing mandatory tools as 'verified'; verified by grepping output for 'Verified'."
    exit 0
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Dependency Check Smoke Test"
echo "--------------------------------------------------------"

# 1. Check dependencies
echo ":: Running 'deps check'..."
OUTPUT=$(uv run wgsextract deps check 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -qi "verified"; then
    echo "✅ Success: deps check completed and confirmed tools."
else
    echo "❌ Failure: deps check did not report any verified tools."
    exit 1
fi

echo ""
echo "========================================================"
echo "Dependency Check Smoke Test: PASSED"
echo "========================================================"
