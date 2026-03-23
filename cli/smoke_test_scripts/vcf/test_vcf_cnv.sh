#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Detects Copy Number Variations (CNVs) from sequencing data."
    echo "End Goal: A VCF/BED file identifying CNV regions.; verified by existence of output file."
    exit 0
fi

# Configuration (Hardcode to fake data for smoke test)
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
MAP_FILE="out/fake_30x/fake.map"
OUTDIR="out/smoke_test_vcf_cnv"
REGION="chr1"

# Ensure map file exists
if [ ! -f "$MAP_FILE" ]; then
    echo ">chr1" > "$MAP_FILE"
    echo "11111111111111111111111111111111111111111111111111" >> "$MAP_FILE"
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF CNV Smoke Test (Delly)"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Map:   $(basename "$MAP_FILE")"
echo "--------------------------------------------------------"

# Check if delly is installed
if ! command -v delly &> /dev/null; then
    echo "SKIP: delly not found in PATH."
    exit 0
fi

if uv run wgsextract vcf cnv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --map "$MAP_FILE" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/cnv.vcf.gz" ]; then
    echo "SUCCESS: VCF CNV completed."
    ls -lh "$OUTDIR/cnv.vcf.gz"
else
    echo "FAILURE: VCF CNV failed."
    exit 1
fi
