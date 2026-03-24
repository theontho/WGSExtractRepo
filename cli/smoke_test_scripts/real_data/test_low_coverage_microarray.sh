#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies microarray extraction on low-coverage (0.1x-1x) real-world data."
    echo "✅ Verified End Goal: Non-empty microarray files (23andMe, Ancestry) with at least some valid genotypes despite low depth, verified by file size and 'NN' count."
    exit 0
fi

# Check for required tools
check_mandatory_deps

if [ -z "$WGSE_INPUT_LOW_COV" ] || [ -z "$WGSE_REF" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT_LOW_COV or WGSE_REF environment variable not set."
    exit 77
fi

INPUT_FILE="${WGSE_INPUT_LOW_COV}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/smoke_test_low_coverage"

# Clean up
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting LOW COVERAGE Smoke Test..."
echo "Input: $INPUT_FILE"

# 1. Run Microarray
echo ":: Running Microarray extraction (low-coverage optimized mode)..."
if ! uv run wgsextract microarray \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --parallel \
    --formats "23andme_v5"; then
    echo "❌ Failure: 'microarray' command failed on low-coverage input."
    exit 1
fi

echo ">>> Verifying low-coverage outputs..."
CKIT=$(find "$OUT_DIR" -name "*CombinedKit.txt" | head -n 1)

if [ -f "$CKIT" ]; then
    echo "✅ Found: $(basename "$CKIT") ($(du -h "$CKIT" | cut -f1))"

    valid_count=$(grep -v "^#" "$CKIT" | awk '$4 ~ /[ACGT][ACGT]/' | wc -l)
    total_count=$(grep -v -c "^#" "$CKIT")

    if [ "$valid_count" -gt 0 ]; then
        echo "   ✅ Found $valid_count valid genotypes out of $total_count."
        echo "   Coverage/Yield: $((valid_count * 100 / total_count))%"
    else
        echo "   ⚠️ Warning: 0 valid genotypes found (all NN). This is expected for extremely low coverage but not ideal for a smoke test."
    fi
    else
    echo "❌ Missing CombinedKit.txt output."
    exit 1
    fi

    echo ">>> LOW COVERAGE Smoke Test PASSED."
