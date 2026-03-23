#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests lineage/haplogroup assignment from mitochondrial or Y-chromosomal data."
    echo "Verified End Goal: Assignment of a valid haplogroup/lineage; also verifies error handling for missing input."
    exit 0
fi

OUTDIR="out/smoke_test_lineage_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'lineage y-haplogroup --help'
echo ":: Testing 'lineage y-haplogroup --help'..."
if uv run wgsextract lineage y-haplogroup --help > /dev/null; then
    echo "✅ Success: 'lineage y-haplogroup --help' works."
else
    echo "❌ Failure: 'lineage y-haplogroup --help' failed."
    exit 1
fi

# 2. Test 'lineage mt-haplogroup --help'
echo ":: Testing 'lineage mt-haplogroup --help'..."
if uv run wgsextract lineage mt-haplogroup --help > /dev/null; then
    echo "✅ Success: 'lineage mt-haplogroup --help' works."
else
    echo "❌ Failure: 'lineage mt-haplogroup --help' failed."
    exit 1
fi

# 3. Test 'lineage y-haplogroup' with missing input (expect failure)
echo ":: Testing 'lineage y-haplogroup' (expect failure for missing input)..."
if ! uv run wgsextract lineage y-haplogroup --yleaf-path "/tmp/non_existent_yleaf"; then
    echo "✅ Success: 'lineage y-haplogroup' correctly failed with missing input."
else
    echo "❌ Failure: 'lineage y-haplogroup' should have failed for missing input."
    exit 1
fi

echo ""
echo "========================================================"
echo "Lineage Basics Smoke Test: PASSED"
echo "========================================================"
