#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF calling using GATK HaplotypeCaller."
    echo "End Goal: Valid VCF output from GATK.; verified by existence of output file."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_gatk"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF GATK Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check if gatk is installed
check_deps gatk

if uv run wgsextract vcf gatk \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/gatk.vcf.gz" ]; then
    echo "SUCCESS: VCF GATK completed."
    ls -lh "$OUTDIR/gatk.vcf.gz"
else
    echo "FAILURE: VCF GATK failed."
    exit 1
fi
