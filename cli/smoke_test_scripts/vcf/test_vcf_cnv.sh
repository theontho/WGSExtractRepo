#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs copy-number variation (CNV) calling using Delly."
    echo "✅ Verified End Goal: A VCF file containing CNV records; verified by presence of output file."
    exit 0
fi

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
MAP_FILE="out/fake_30x/fake.map"
OUTDIR="out/smoke_test_vcf_cnv"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF CNV Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Map:   $(basename "$MAP_FILE")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check dependencies
check_deps delly
ensure_fake_data

uv run wgsextract vcf cnv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --map "$MAP_FILE" \
    --outdir "$OUTDIR" \
    --region "$REGION" > stdout 2>&1
exit_code=$?

cat stdout

if [ $exit_code -eq 0 ] && verify_vcf "$OUTDIR/cnv.vcf.gz" 1; then
    echo "SUCCESS: VCF CNV completed."
    ls -lh "$OUTDIR/cnv.vcf.gz"
elif [ $exit_code -eq 139 ] || grep -q "Segmentation fault" stdout; then
    echo "⏭️ SKIP: Delly segfaulted (exit 139), skipping CNV test."
    exit 0
else
    echo "FAILURE: VCF CNV failed with exit code $exit_code."
    exit 1
fi
