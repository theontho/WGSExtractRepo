#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF calling using FreeBayes."
    echo "✅ Verified End Goal: A valid VCF from FreeBayes; verified by output existence, validity (bcftools), and record presence."
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
ensure_fake_data

if uv run wgsextract vcf freebayes \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && verify_vcf "$OUTDIR/freebayes.vcf.gz"; then
    echo "SUCCESS: VCF Freebayes completed."
    ls -lh "$OUTDIR/freebayes.vcf.gz"

    # Verify tool name in header
    if bcftools view -h "$OUTDIR/freebayes.vcf.gz" | grep -iq "freeBayes"; then
        echo "✅ Success: Found 'freeBayes' in VCF header."
    else
        echo "❌ Failure: 'freeBayes' NOT found in VCF header."
        exit 1
    fi
else
    echo "FAILURE: VCF Freebayes failed."
    exit 1
fi
