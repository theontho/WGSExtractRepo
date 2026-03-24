#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs single-nucleotide polymorphism (SNP) calling from a BAM file."
    echo "✅ Verified End Goal: A VCF file containing valid, non-zero SNP records for the specified region; verified by zgrep SNP count."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_snp"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF SNP Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check dependencies
check_mandatory_deps
ensure_fake_data

if uv run wgsextract vcf snp \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" \
    --ploidy 1 && [ -f "$OUTDIR/snps.vcf.gz" ]; then
    echo "SUCCESS: VCF SNP completed."
    ls -lh "$OUTDIR/snps.vcf.gz"

    # Verification: Ensure VCF contains SNP records (not just header)
    SNP_COUNT=$(zgrep -v "^#" "$OUTDIR/snps.vcf.gz" | wc -l)
    if [ "$SNP_COUNT" -gt 0 ]; then
        echo "VERIFIED: VCF contains $SNP_COUNT SNP records."
    else
        echo "FAILURE: VCF is empty or missing expected SNP records."
        exit 1
    fi
else
    echo "FAILURE: VCF SNP failed."
    exit 1
fi

# 2. Test SNP calling on a different region
REGION2="chr1:100-2000"
echo ":: Testing 'vcf snp' on region $REGION2..."
if uv run wgsextract vcf snp \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR/region2" \
    --region "$REGION2" \
    --ploidy 1 && verify_vcf "$OUTDIR/region2/snps.vcf.gz"; then
    echo "SUCCESS: VCF SNP on region $REGION2 completed."
else
    echo "FAILURE: VCF SNP on region $REGION2 failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF SNP Smoke Test: PASSED"
echo "========================================================"
