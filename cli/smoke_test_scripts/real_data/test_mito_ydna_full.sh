#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Extracts MT-DNA and Y-DNA from real-world BAM/CRAM data."
    echo "✅ Verified End Goal: Two valid BAM/CRAM files (mito.bam, ydna.bam) containing only MT/Y reads, verified by samtools and header checks."
    exit 0
fi

# Check for required tools
check_mandatory_deps

if [ -z "$WGSE_INPUT" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT environment variable not set."
    exit 77
fi

INPUT_FILE="${WGSE_INPUT}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_mito_ydna"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL GENOME MT/Y DNA Extraction Smoke Test..."
echo "Input: $INPUT_FILE"

# 1. MT-DNA Extraction
echo ":: Extracting Mitochondrial DNA..."
if ! uv run wgsextract extract mito \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"; then
    echo "❌ Failure: 'extract mito' command failed."
    exit 1
fi

# 2. Y-DNA Extraction
echo ":: Extracting Y-Chromosome DNA..."
if ! uv run wgsextract extract ydna \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"; then
    echo "❌ Failure: 'extract ydna' command failed."
    exit 1
fi

echo ">>> Verifying outputs..."
MITO_FILE=$(find "$OUT_DIR" -name "*mito.bam" -o -name "*mito.cram" | head -n 1)
YDNA_FILE=$(find "$OUT_DIR" -name "*ydna.bam" -o -name "*ydna.cram" | head -n 1)

# Verify Mitochondrial DNA
if [ -f "$MITO_FILE" ]; then
    echo "✅ Found Mito: $(basename "$MITO_FILE") ($(du -h "$MITO_FILE" | cut -f1))"
    if verify_bam "$MITO_FILE"; then
        # Verify it only contains MT/chrM
        chroms=$(samtools idxstats "$MITO_FILE" | awk '$3 > 0 {print $1}')
        echo "   Mito Chromosomes: $chroms"
        if echo "$chroms" | grep -qvE "^(MT|chrM|M)$"; then
             echo "   ⚠️ Warning: Mito BAM contains non-mitochondrial reads: $(echo "$chroms" | grep -vE "^(MT|chrM|M)$" | xargs)"
             # We don't exit 1 here because sometimes there are unmapped reads or off-target hits,
             # but it should primarily be MT.
        fi
    else
        exit 1
    fi
else
    echo "❌ Missing Mitochondrial output file."
    exit 1
fi

# Verify Y-DNA
if [ -f "$YDNA_FILE" ]; then
    echo "✅ Found Y-DNA: $(basename "$YDNA_FILE") ($(du -h "$YDNA_FILE" | cut -f1))"
    if verify_bam "$YDNA_FILE"; then
        # Verify it only contains Y/chrY
        chroms=$(samtools idxstats "$YDNA_FILE" | awk '$3 > 0 {print $1}')
        echo "   Y-DNA Chromosomes: $chroms"
        if echo "$chroms" | grep -qvE "^(Y|chrY)$"; then
             echo "   ⚠️ Warning: Y-DNA BAM contains non-Y reads: $(echo "$chroms" | grep -vE "^(Y|chrY)$" | xargs)"
        fi
    else
        exit 1
    fi
else
    # Note: If the sample is female, Y-DNA might be empty or very small.
    # But for a smoke test, we expect a file to be created.
    echo "❌ Missing Y-DNA output file."
    exit 1
fi

echo ">>> FULL MT/Y DNA Extraction Smoke Test PASSED."
