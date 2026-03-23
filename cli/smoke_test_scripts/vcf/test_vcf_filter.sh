#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Filters VCF records based on quality, depth, or other criteria."
    echo "End Goal: A filtered VCF file containing only records that meet the specified criteria.; verified by existence of output file."
    exit 0
fi

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
OUTDIR="out/smoke_test_vcf_filter"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

check_mandatory_deps
echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Filter Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
check_mandatory_deps
echo "--------------------------------------------------------"

if uv run wgsextract vcf filter \
    --vcf-input "$INPUT_VCF" \
    --expr "QUAL>10" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/filtered.vcf.gz" ]; then
    echo "SUCCESS: VCF Filter completed."
    ls -lh "$OUTDIR/filtered.vcf.gz"
else
    echo "FAILURE: VCF Filter failed."
    exit 1
fi
