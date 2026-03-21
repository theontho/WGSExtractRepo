#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

OUTDIR="out/smoke_test_pet_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Pet Align Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Generate small fake reference and FASTQ for "dog"
echo ":: Generating small fake reference..."
echo ">chr1" > "$OUTDIR/dog_ref.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$OUTDIR/dog_ref.fa"

# Generate fake reads from this reference
echo "@read1" > "$OUTDIR/dog_R1.fastq"
echo "ACGTACGT" >> "$OUTDIR/dog_R1.fastq"
echo "+" >> "$OUTDIR/dog_R1.fastq"
echo "########" >> "$OUTDIR/dog_R1.fastq"

echo "@read1" > "$OUTDIR/dog_R2.fastq"
echo "ACGTACGT" >> "$OUTDIR/dog_R2.fastq"
echo "+" >> "$OUTDIR/dog_R2.fastq"
echo "########" >> "$OUTDIR/dog_R2.fastq"

# 2. Test 'pet-align'
echo ":: Testing 'pet-align' for dog..."
uv run wgsextract pet-align \
    --r1 "$OUTDIR/dog_R1.fastq" \
    --r2 "$OUTDIR/dog_R2.fastq" \
    --species dog \
    --ref "$OUTDIR/dog_ref.fa" \
    --outdir "$OUTDIR" \
    --format BAM

if [ $? -eq 0 ] && [ -f "$OUTDIR/dog_R1_dog.bam" ]; then
    echo "✅ Success: 'pet-align' completed."
else
    echo "❌ Failure: 'pet-align' failed."
    ls -R "$OUTDIR"
    exit 1
fi

echo ""
echo "========================================================"
echo "Pet Align Basics Smoke Test: PASSED"
echo "========================================================"
