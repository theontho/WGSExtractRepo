#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Calculates genome-wide or regional coverage statistics from a BAM/CRAM file."
    echo "End Goal: A coverage report with accurate depth calculations; verified by successful completion of 'info' and 'calculate-coverage' commands."
    exit 0
fi

OUTDIR="out/smoke_test_info_coverage"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
if [ ! -f "$FAKEDATA/fake.bam" ]; then
    echo ":: Generating dependency fake data..."
    chmod +x smoke_test_scripts/test_qc_fake_data.sh
    ./smoke_test_scripts/test_qc_fake_data.sh
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Info Coverage Smoke Test"
echo "--------------------------------------------------------"

# 1. Base info command
echo ":: Testing 'info'..."
if uv run wgsextract info --input "$FAKEDATA/fake.bam"; then
    echo "✅ Success: base info completed."
else
    echo "❌ Failure: base info failed."
    exit 1
fi

# 2. Coverage sampling
echo ":: Testing 'info coverage-sample'..."
if uv run wgsextract info coverage-sample \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR"; then
    echo "✅ Success: coverage-sample completed."
else
    echo "❌ Failure: coverage-sample failed."
    exit 1
fi

# 3. Calculate full coverage (small region to be fast)
echo ":: Testing 'info calculate-coverage' (region chr1)..."
if uv run wgsextract info calculate-coverage \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --region "chr1"; then
    echo "✅ Success: calculate-coverage completed."
else
    echo "❌ Failure: calculate-coverage failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Info Coverage Smoke Test: PASSED"
echo "========================================================"
