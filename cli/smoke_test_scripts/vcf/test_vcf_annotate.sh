#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Annotates a VCF file with basic metadata and region information."
    echo "✅ Verified End Goal: Annotated VCF with additional INFO fields; verified by output existence, validity, and header check."
    exit 0
fi

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_annotate"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

check_mandatory_deps
ensure_fake_data

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Annotate Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# Note: Annotate requires --ann-vcf.
# We use the same VCF as annotation source for testing connectivity.
if uv run wgsextract vcf annotate \
    --input "$INPUT_VCF" \
    --ann-vcf "$INPUT_VCF" \
    --cols "ID,QUAL" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" && verify_vcf "$OUTDIR/annotated.vcf.gz"; then
    echo "SUCCESS: VCF Annotate completed."
    ls -lh "$OUTDIR/annotated.vcf.gz"

    # Check for bcftools annotate command in header to confirm tool was used
    if bcftools view -h "$OUTDIR/annotated.vcf.gz" | grep -q "bcftools_annotateCommand"; then
        echo "✅ Success: bcftools annotation command found in header."
    else
        echo "❌ Failure: bcftools annotation command NOT found in header."
        exit 1
    fi
else
    echo "FAILURE: VCF Annotate failed."
    exit 1
fi
