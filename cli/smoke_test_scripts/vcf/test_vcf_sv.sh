#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Detects Structural Variations (SVs) like inversions and translocations."
    echo "End Goal: A VCF file identifying structural variants.; verified by existence of output file."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_sv"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF SV Smoke Test (Delly)"
echo "  Input: $(basename "$INPUT_BAM")"
echo "--------------------------------------------------------"

# Check if delly is installed
if ! command -v delly &> /dev/null; then
    echo "SKIP: delly not found in PATH."
    exit 0
fi

if uv run wgsextract vcf sv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/sv.vcf.gz" ]; then
    echo "SUCCESS: VCF SV completed."
    ls -lh "$OUTDIR/sv.vcf.gz"
else
    echo "FAILURE: VCF SV failed."
    exit 1
fi
