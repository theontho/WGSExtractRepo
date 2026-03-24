#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests the alignment pipeline using BWA/minimap2 on small datasets."
    echo "✅ Verified End Goal: A valid, sorted, and indexed BAM/CRAM file aligned to the reference; verified by samtools quickcheck and read count validation, and expected stdout logs."
    exit 0
fi

OUTDIR="out/smoke_test_align_basics"
FASTQDIR="$OUTDIR/fastq"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$FASTQDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Align Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Generate small FASTQ for hg38
echo ":: Generating small hg38 FASTQ..."
STDOUT=$(uv run wgsextract qc fake-data \
    --outdir "$FASTQDIR" \
    --build hg38 \
    --type fastq \
    --coverage 0.01 \
    --seed 123 \
    --ref "$FASTQDIR" 2>&1)
echo "$STDOUT"
if [ -f "$FASTQDIR/fake_R1.fastq.gz" ] && verify_fastq "$FASTQDIR/fake_R1.fastq.gz"; then
    echo "✅ Success: FASTQ generated and verified."
else
    echo "❌ Failure: FASTQ generation failed."
    exit 1
fi

REF=$(find "$FASTQDIR" -name "fake_ref_hg38_*.fa" | head -n 1)
echo ":: Using reference: $REF"

# 2. Align to BAM
echo ":: Testing 'align' to BAM..."
STDOUT=$(uv run wgsextract align \
    --r1 "$FASTQDIR/fake_R1.fastq.gz" \
    --r2 "$FASTQDIR/fake_R2.fastq.gz" \
    --ref "$REF" \
    --outdir "$OUTDIR/bam" \
    --format BAM 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Aligning" && verify_bam "$OUTDIR/bam/fake_R1_aligned.bam"; then
    echo "✅ Success: Alignment to BAM verified."
else
    echo "❌ Failure: Alignment to BAM failed."
    exit 1
fi

# 3. Align to CRAM
echo ":: Testing 'align' to CRAM..."
STDOUT=$(uv run wgsextract align \
    --r1 "$FASTQDIR/fake_R1.fastq.gz" \
    --r2 "$FASTQDIR/fake_R2.fastq.gz" \
    --ref "$REF" \
    --outdir "$OUTDIR/cram" \
    --format CRAM 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Aligning" && verify_bam "$OUTDIR/cram/fake_R1_aligned.cram"; then
    echo "✅ Success: Alignment to CRAM verified."
else
    echo "❌ Failure: Alignment to CRAM failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Align Basics Smoke Test: PASSED"
echo "========================================================"
