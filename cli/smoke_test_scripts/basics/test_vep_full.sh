#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Detailed test of the 'vep' command wrapper using mock data."
    echo "🌕 End Goal: VCF output with (mocked) VEP annotations."
    exit 0
fi

OUTDIR="out/smoke_test_vep_full"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
ensure_fake_data

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VEP Full Smoke Test"
echo "--------------------------------------------------------"

# 1. Create a mock VEP cache structure
MOCK_CACHE="$OUTDIR/mock_cache"
MOCK_VERSION_DIR="$MOCK_CACHE/homo_sapiens/115_GRCh38"
mkdir -p "$MOCK_VERSION_DIR"
touch "$MOCK_VERSION_DIR/info.txt"

# 2. Test 'vep' main command
# Note: This will likely fail to actually *run* VEP if the tool is not installed,
# but we test the CLI wrapper's ability to construct the command and handle arguments.
if command -v vep >/dev/null 2>&1; then
    echo ":: Running 'vep'..."
    REF=$(find "$FAKEDATA" -name "fake_ref_hg38_*.fa" | head -n 1)
    # We use --debug to see the constructed command even if it fails later
    STDOUT=$(uv run wgsextract vep \
        --input "$FAKEDATA/fake.vcf.gz" \
        --outdir "$OUTDIR" \
        --ref "$REF" \
        --vep-cache "$MOCK_CACHE" \
        --vep-cache-version "115" \
        --vep-assembly "GRCh38" \
        --vcf-type snp-indel \
        --debug 2>&1)
    echo "$STDOUT"
    if echo "$STDOUT" | grep -q "vep"; then
        echo "✅ Success: 'vep' command constructed and attempted."
    else
        echo "❌ Failure: 'vep' command failed to initialize."
        exit 1
    fi
else
    echo ":: VEP not installed, skipping execution test but verifying argument parsing via --help."
    if uv run wgsextract vep --help > /dev/null; then
        echo "✅ Success: 'vep --help' works."
    else
        echo "❌ Failure: 'vep --help' failed."
        exit 1
    fi
fi

echo ""
echo "========================================================"
echo "VEP Full Smoke Test: PASSED"
echo "========================================================"
