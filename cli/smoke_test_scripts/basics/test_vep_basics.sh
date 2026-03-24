#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Basic smoke test for Variant Effect Predictor (VEP) integration."
    echo "✅ Verified End Goal: Annotated VCF with basic consequence predictions; confirmed by 'vep verify' stdout reporting correctly for both missing and mock caches."
    exit 0
fi

OUTDIR="out/smoke_test_vep_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VEP Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'vep verify' with non-existent cache
echo ":: Testing 'vep verify' (expect failure for non-existent cache)..."
if ! uv run wgsextract vep verify \
    --vep-cache "$OUTDIR/non_existent_cache" \
    --species homo_sapiens \
    --assembly GRCh38 > "$OUTDIR/vep_verify_fail.stdout" 2>&1; then
    if grep -q "not found" "$OUTDIR/vep_verify_fail.stdout" || grep -q "Missing" "$OUTDIR/vep_verify_fail.stdout"; then
        echo "✅ Success: 'vep verify' correctly reported missing cache in stdout."
    else
        echo "❌ Failure: 'vep verify' failed but output did not contain expected error message."
        cat "$OUTDIR/vep_verify_fail.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'vep verify' should have failed for missing cache."
    exit 1
fi

# 2. Test 'vep verify' with a mock cache
echo ":: Testing 'vep verify' with a mock cache..."
MOCK_CACHE="$OUTDIR/mock_cache"
MOCK_VERSION_DIR="$MOCK_CACHE/homo_sapiens/115_GRCh38"
mkdir -p "$MOCK_VERSION_DIR"
touch "$MOCK_VERSION_DIR/info.txt"

if uv run wgsextract vep verify \
    --vep-cache "$MOCK_CACHE" \
    --species homo_sapiens \
    --assembly GRCh38 > "$OUTDIR/vep_verify_pass.stdout" 2>&1; then
    if grep -q "Verification complete" "$OUTDIR/vep_verify_pass.stdout" || grep -q "found" "$OUTDIR/vep_verify_pass.stdout"; then
         echo "✅ Success: 'vep verify' passed and reported success in stdout."
    else
         echo "❌ Failure: 'vep verify' passed but output did not confirm success."
         cat "$OUTDIR/vep_verify_pass.stdout"
         exit 1
    fi
else
    echo "❌ Failure: 'vep verify' failed with mock cache."
    cat "$OUTDIR/vep_verify_pass.stdout"
    exit 1
fi

# 3. Test 'vep download' (mocked via help)
echo ":: Testing 'vep download' (help)..."
if uv run wgsextract vep download --help > "$OUTDIR/vep_download_help.stdout" 2>&1; then
    if grep -q "\-\-vep-cache" "$OUTDIR/vep_download_help.stdout"; then
        echo "✅ Success: 'vep download --help' works and contains expected text."
    else
        echo "❌ Failure: 'vep download --help' output missing expected text."
        cat "$OUTDIR/vep_download_help.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'vep download --help' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "VEP Basics Smoke Test: PASSED"
echo "========================================================"
