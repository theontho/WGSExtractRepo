#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs structural variant (SV) calling using Delly."
    echo "✅ Verified End Goal: A VCF file containing SV records; verified by presence of output file."
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
echo "  WGS Extract CLI: VCF SV Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check dependencies
check_deps delly
ensure_fake_data

if uv run wgsextract vcf sv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && verify_vcf "$OUTDIR/sv.vcf.gz" 1; then
    echo "SUCCESS: VCF SV completed."
    ls -lh "$OUTDIR/sv.vcf.gz"
else
    echo "FAILURE: VCF SV failed."
    exit 1
fi
