#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs insertion/deletion (indel) calling from a BAM file."
    echo "✅ Verified End Goal: A VCF file containing valid, non-zero indel records for the specified region; verified by zgrep indel count."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_indel"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Indel Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check dependencies
check_mandatory_deps
ensure_fake_data

if uv run wgsextract vcf indel \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" \
    --ploidy 1 && [ -f "$OUTDIR/indels.vcf.gz" ]; then
    echo "SUCCESS: VCF Indel completed."
    ls -lh "$OUTDIR/indels.vcf.gz"

    # Verification: Ensure VCF contains indel records (not just header)
    INDEL_COUNT=$(zgrep -v "^#" "$OUTDIR/indels.vcf.gz" | wc -l)
    if [ "$INDEL_COUNT" -gt 0 ]; then
        echo "VERIFIED: VCF contains $INDEL_COUNT indel records."
    else
        echo "FAILURE: VCF is empty or missing expected indel records."
        exit 1
    fi
else
    echo "FAILURE: VCF Indel failed."
    exit 1
fi
