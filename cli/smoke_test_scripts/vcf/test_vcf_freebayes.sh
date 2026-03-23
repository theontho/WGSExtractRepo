#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF calling using FreeBayes."
    echo "End Goal: Valid VCF output from FreeBayes with non-empty variant records."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_freebayes"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF FreeBayes Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check dependencies
check_deps freebayes

if uv run wgsextract vcf freebayes \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/freebayes.vcf.gz" ]; then
    echo "SUCCESS: VCF Freebayes completed."
    ls -lh "$OUTDIR/freebayes.vcf.gz"
else
    echo "FAILURE: VCF Freebayes failed."
    exit 1
fi
