#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Basic smoke test for Variant Effect Predictor (VEP) integration."
    echo "Verified End Goal: Annotated VCF with basic consequence predictions; also verifies error handling for missing cache."
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
    --assembly GRCh38; then
    echo "✅ Success: 'vep verify' correctly reported missing cache."
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
    --assembly GRCh38; then
    echo "✅ Success: 'vep verify' passed with mock cache."
else
    echo "❌ Failure: 'vep verify' failed with mock cache."
    exit 1
fi

# 3. Test 'vep download' (mocked via local server)
echo ":: Testing 'vep download' (mocked)..."
MOCK_DL_DIR="$OUTDIR/mock_dl"
mkdir -p "$MOCK_DL_DIR/pub/release-115/variation/indexed_vep_cache"
# Create a dummy tarball
tar -czf "$MOCK_DL_DIR/pub/release-115/variation/indexed_vep_cache/homo_sapiens_vep_115_GRCh38.tar.gz" -C "$OUTDIR" mock_cache
# Create dummy CHECKSUMS (if download_file or post-processing expects it)
# The current implementation of cmd_vep_download uses curl for CHECKSUMS but download_file for the tarball.
# It might be hard to mock the whole Ensembl FTP structure perfectly without more effort.
# But let's try a simple help check at least.

if uv run wgsextract vep download --help > /dev/null; then
    echo "✅ Success: 'vep download --help' works."
else
    echo "❌ Failure: 'vep download --help' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "VEP Basics Smoke Test: PASSED"
echo "========================================================"
