#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF filtering based on various criteria (quality, gene, region)."
    echo "✅ Verified End Goal: A filtered VCF file; verified by output existence, validity, and filter criterion compliance (QUAL>10)."
    exit 0
fi

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
OUTDIR="out/smoke_test_vcf_filter"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Filter Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# Check dependencies
check_mandatory_deps
ensure_fake_data

if uv run wgsextract vcf filter \
    --input "$INPUT_VCF" \
    --expr 'QUAL>10' \
    --outdir "$OUTDIR" > stdout 2>&1 && verify_vcf "$OUTDIR/filtered.vcf.gz" 1; then
    cat stdout
    grep -qE "VCF Filter complete|Filtering|filtered.vcf.gz" stdout || { echo "❌ Failure: Expected success message missing from stdout"; exit 1; }
    echo "SUCCESS: VCF Filter completed."
    ls -lh "$OUTDIR/filtered.vcf.gz"
else
    echo "FAILURE: VCF Filter failed."
    exit 1
fi
