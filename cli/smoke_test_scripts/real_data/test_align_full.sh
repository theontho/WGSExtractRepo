#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Maps raw FASTQ reads to a reference genome using real-world data."
    echo "✅ Verified End Goal: A valid, sorted, and indexed BAM/CRAM file with mapping statistics, verified by samtools quickcheck and flagstat."
    exit 0
fi

# Check for required tools
check_mandatory_deps
check_deps bwa-mem2 sambamba samblaster

if [ -z "$WGSE_FASTQ_R1" ] || [ -z "$WGSE_FASTQ_R2" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_FASTQ_R1/R2 environment variables not set."
    exit 77
fi

FASTQ_R1="${WGSE_FASTQ_R1}"
FASTQ_R2="${WGSE_FASTQ_R2}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_align"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL ALIGNMENT Smoke Test..."
echo "Input R1: $FASTQ_R1"
echo "Input R2: $FASTQ_R2"

# 1. Align
echo ":: Aligning FASTQ reads..."
# Note: This is an expensive operation, so for a smoke test,
# it's recommended to use a small subset (e.g., first 100k reads).
# The CLI doesn't have a subset flag, so we rely on the input being small
# OR we let it run if the user provides it.
if ! uv run wgsextract align \
    --input "$FASTQ_R1" \
    --input-r2 "$FASTQ_R2" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --sample "SmokeSample" \
    --threads "${WGSE_THREADS:-8}"; then
    echo "❌ Failure: 'align' command failed."
    exit 1
fi

echo ">>> Verifying alignment outputs..."
ALIGN_FILE=$(find "$OUT_DIR" -name "*.bam" -o -name "*.cram" | head -n 1)

if [ -f "$ALIGN_FILE" ]; then
    echo "✅ Found: $(basename "$ALIGN_FILE") ($(du -h "$ALIGN_FILE" | cut -f1))"
    if verify_bam "$ALIGN_FILE"; then
        echo "   Checking mapping statistics..."
        MAP_STATS=$(samtools flagstat "$ALIGN_FILE")
        mapped=$(echo "$MAP_STATS" | grep "mapped (" | awk -F'(' '{print $2}' | cut -d'%' -f1)
        echo "   Mapped: $mapped%"
        if (( $(echo "$mapped > 0" | bc -l) )); then
             echo "   ✅ Alignment confirmed (non-zero mapping rate)."
        else
             echo "   ❌ ERROR: 0% reads mapped. Check reference or input data compatibility."
             exit 1
        fi
    else
        exit 1
    fi
else
    echo "❌ Missing alignment output file."
    exit 1
fi

echo ">>> FULL ALIGNMENT Smoke Test PASSED."
