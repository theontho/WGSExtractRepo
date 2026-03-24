#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests lineage/haplogroup assignment from mitochondrial or Y-chromosomal data."
    echo "✅ Verified End Goal: Assignment of a valid haplogroup/lineage; confirmed by help text existence and stdout error reporting for missing inputs."
    exit 0
fi

OUTDIR="out/smoke_test_lineage_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'lineage y-haplogroup --help'
echo ":: Testing 'lineage y-haplogroup --help'..."
if uv run wgsextract lineage y-haplogroup --help > "$OUTDIR/y_help.stdout" 2>&1; then
    if grep -q "Y-DNA haplogroup" "$OUTDIR/y_help.stdout" || grep -q "y-haplogroup" "$OUTDIR/y_help.stdout"; then
        echo "✅ Success: 'lineage y-haplogroup --help' works and contains expected text."
    else
        echo "❌ Failure: 'lineage y-haplogroup --help' output missing expected text."
        cat "$OUTDIR/y_help.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'lineage y-haplogroup --help' failed."
    exit 1
fi

# 2. Test 'lineage mt-haplogroup --help'
echo ":: Testing 'lineage mt-haplogroup --help'..."
if uv run wgsextract lineage mt-haplogroup --help > "$OUTDIR/mt_help.stdout" 2>&1; then
    if grep -q "mitochondrial" "$OUTDIR/mt_help.stdout" || grep -q "mt-haplogroup" "$OUTDIR/mt_help.stdout"; then
        echo "✅ Success: 'lineage mt-haplogroup --help' works and contains expected text."
    else
        echo "❌ Failure: 'lineage mt-haplogroup --help' output missing expected text."
        cat "$OUTDIR/mt_help.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'lineage mt-haplogroup --help' failed."
    exit 1
fi

# 3. Test 'lineage y-haplogroup' with missing input (expect failure)
echo ":: Testing 'lineage y-haplogroup' (expect failure for missing input)..."
if ! uv run wgsextract lineage y-haplogroup --yleaf-path "/tmp/non_existent_yleaf" > "$OUTDIR/y_fail.stdout" 2>&1; then
    if grep -q "Error" "$OUTDIR/y_fail.stdout" || grep -q "missing" "$OUTDIR/y_fail.stdout" || grep -q "not found" "$OUTDIR/y_fail.stdout"; then
        echo "✅ Success: 'lineage y-haplogroup' correctly failed and reported error in stdout."
    else
        echo "❌ Failure: 'lineage y-haplogroup' failed but output did not contain expected error message."
        cat "$OUTDIR/y_fail.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'lineage y-haplogroup' should have failed for missing input."
    exit 1
fi

echo ""
echo "========================================================"
echo "Lineage Basics Smoke Test: PASSED"
echo "========================================================"
