#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
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
uv run wgsextract qc fake-data \
    --outdir "$FASTQDIR" \
    --build hg38 \
    --type fastq \
    --coverage 0.001 \
    --seed 123

if [ $? -eq 0 ] && [ -f "$FASTQDIR/fake_R1.fastq.gz" ]; then
    echo "✅ Success: FASTQ generated."
else
    echo "❌ Failure: FASTQ generation failed."
    exit 1
fi

REF=$(ls "$FASTQDIR"/fake_ref_hg38_*.fa | head -n 1)
if [ ! -f "$REF" ]; then
    # Maybe it used a real library reference, try to find it from logs or assume it's NOT what we want for a self-contained smoke test.
    # Force it to be local by passing --ref to qc fake-data
    echo ":: Retrying FASTQ generation with forced local ref..."
    uv run wgsextract qc fake-data \
        --outdir "$FASTQDIR" \
        --build hg38 \
        --type fastq \
        --coverage 0.001 \
        --seed 123 \
        --ref "$FASTQDIR" # Passing a directory without fasta forces creation
    REF=$(ls "$FASTQDIR"/fake_ref_hg38_*.fa | head -n 1)
fi

echo ":: Using reference: $REF"

# 2. Align to BAM
echo ":: Testing 'align' to BAM..."
uv run wgsextract align \
    --r1 "$FASTQDIR/fake_R1.fastq.gz" \
    --r2 "$FASTQDIR/fake_R2.fastq.gz" \
    --ref "$REF" \
    --outdir "$OUTDIR/bam" \
    --format BAM

if [ $? -eq 0 ] && [ -f "$OUTDIR/bam/fake_R1_aligned.bam" ]; then
    echo "✅ Success: Alignment to BAM completed."
else
    echo "❌ Failure: Alignment to BAM failed."
    # List files to see what happened
    ls -R "$OUTDIR/bam"
    exit 1
fi

# 3. Align to CRAM
echo ":: Testing 'align' to CRAM..."
uv run wgsextract align \
    --r1 "$FASTQDIR/fake_R1.fastq.gz" \
    --r2 "$FASTQDIR/fake_R2.fastq.gz" \
    --ref "$REF" \
    --outdir "$OUTDIR/cram" \
    --format CRAM

if [ $? -eq 0 ] && [ -f "$OUTDIR/cram/fake_R1_aligned.cram" ]; then
    echo "✅ Success: Alignment to CRAM completed."
else
    echo "❌ Failure: Alignment to CRAM failed."
    ls -R "$OUTDIR/cram"
    exit 1
fi

echo ""
echo "========================================================"
echo "Align Basics Smoke Test: PASSED"
echo "========================================================"
