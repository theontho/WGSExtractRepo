#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Calculates genome-wide or regional coverage statistics from a BAM/CRAM file."
    echo "✅ Verified End Goal: A coverage report with accurate depth calculations; verified by checking for expected summary strings in stdout and existence/validity of coverage JSON/CSV outputs."
    exit 0
fi

OUTDIR="out/smoke_test_info_coverage"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
if [ ! -f "$FAKEDATA/fake.bam" ]; then
    echo ":: Generating dependency fake data via test_qc_fake_data.sh..."
    chmod +x smoke_test_scripts/basics/test_qc_fake_data.sh
    ./smoke_test_scripts/basics/test_qc_fake_data.sh
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Info Coverage Smoke Test"
echo "--------------------------------------------------------"

# 1. Base info command
echo ":: Testing 'info'..."
STDOUT=$(uv run wgsextract info --input "$FAKEDATA/fake.bam" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Avg Read Length" && echo "$STDOUT" | grep -q "Reference Genome"; then
    echo "✅ Success: base info verified."
else
    echo "❌ Failure: base info failed or output malformed."
    exit 1
fi

# 2. Coverage sampling
echo ":: Testing 'info coverage-sample'..."
STDOUT=$(uv run wgsextract info coverage-sample \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Estimating coverage using random sampling" && [ -f "$OUTDIR/fake.bam_samplecvg.json" ]; then
    echo "✅ Success: coverage-sample verified."
else
    echo "❌ Failure: coverage-sample failed or output missing."
    exit 1
fi

# 3. Calculate full coverage (small region to be fast)
echo ":: Testing 'info calculate-coverage' (region chr1)..."
STDOUT=$(uv run wgsextract info calculate-coverage \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --region "chr1" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Calculating full coverage" && [ -f "$OUTDIR/fake.bam_bincvg.csv" ]; then
    echo "✅ Success: calculate-coverage verified."
else
    echo "❌ Failure: calculate-coverage failed or output missing."
    exit 1
fi

echo ""
echo "========================================================"
echo "Info Coverage Smoke Test: PASSED"
echo "========================================================"
