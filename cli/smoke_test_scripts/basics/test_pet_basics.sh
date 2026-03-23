#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies Pair-End Tag (PET) data handling and extraction."
    echo "🌕 End Goal: Correctly paired and extracted genomic data; verified by existence of generated species-specific BAM file."
    exit 0
fi

OUTDIR="out/smoke_test_pet_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Pet Align Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Generate small fake reference and FASTQ for "dog"
echo ":: Generating small fake reference..."
{
    echo ">chr1"
    echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
} > "$OUTDIR/dog_ref.fa"

# Generate fake reads from this reference
{
    echo "@read1"
    echo "ACGTACGT"
    echo "+"
    echo "########"
} > "$OUTDIR/dog_R1.fastq"

{
    echo "@read1"
    echo "ACGTACGT"
    echo "+"
    echo "########"
} > "$OUTDIR/dog_R2.fastq"

# 2. Test 'pet-align'
echo ":: Testing 'pet-align' for dog..."
if uv run wgsextract pet-align \
    --r1 "$OUTDIR/dog_R1.fastq" \
    --r2 "$OUTDIR/dog_R2.fastq" \
    --species dog \
    --ref "$OUTDIR/dog_ref.fa" \
    --outdir "$OUTDIR" \
    --format BAM && [ -f "$OUTDIR/dog_R1_dog.bam" ]; then
    echo "✅ Success: 'pet-align' completed."
else
    echo "❌ Failure: 'pet-align' failed."
    find "$OUTDIR" -maxdepth 2
    exit 1
fi

echo ""
echo "========================================================"
echo "Pet Align Basics Smoke Test: PASSED"
echo "========================================================"
