#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Maps raw FASTQ reads to a cat or dog reference genome using real-world data."
    echo "✅ Verified End Goal: A valid BAM/CRAM file and a VCF file containing pet variants, verified by samtools and bcftools."
    exit 0
fi

# Check for required tools
check_mandatory_deps
check_deps bwa-mem2 sambamba samblaster

if [ -z "$WGSE_PET_R1" ] || [ -z "$WGSE_PET_R2" ] || [ -z "$WGSE_PET_REF" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_PET_R1/R2/REF environment variables not set."
    exit 77
fi

PET_R1="${WGSE_PET_R1}"
PET_R2="${WGSE_PET_R2}"
PET_REF="${WGSE_PET_REF}"
OUT_DIR="out/full_smoke_out_pet"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL PET ALIGNMENT Smoke Test..."
echo "Input R1: $PET_R1"
echo "Input R2: $PET_R2"
echo "Ref:      $PET_REF"

# 1. Pet Align
echo ":: Aligning Pet reads and calling variants..."
if ! uv run wgsextract pet-align \
    --input "$PET_R1" \
    --input-r2 "$PET_R2" \
    --ref "$PET_REF" \
    --outdir "$OUT_DIR" \
    --threads "${WGSE_THREADS:-8}"; then
    echo "❌ Failure: 'pet-align' command failed."
    exit 1
fi

echo ">>> Verifying pet outputs..."
ALIGN_FILE=$(find "$OUT_DIR" -name "*.bam" -o -name "*.cram" | head -n 1)
VCF_FILE=$(find "$OUT_DIR" -name "*.vcf.gz" | head -n 1)

# Verify BAM
if [ -f "$ALIGN_FILE" ]; then
    echo "✅ Found BAM: $(basename "$ALIGN_FILE")"
    verify_bam "$ALIGN_FILE"
else
    echo "❌ Missing pet alignment output file."
    exit 1
fi

# Verify VCF
if [ -f "$VCF_FILE" ]; then
    echo "✅ Found VCF: $(basename "$VCF_FILE")"
    verify_vcf "$VCF_FILE"
else
    echo "❌ Missing pet variant calling output file."
    exit 1
fi

echo ">>> FULL PET ALIGNMENT Smoke Test PASSED."
