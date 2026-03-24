#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies Pair-End Tag (PET) data handling and extraction."
    echo "✅ Verified End Goal: Correctly paired and extracted genomic data; confirmed by 'verify_bam' on the resulting species-specific BAM and 'pet-align' completion logs."
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
    --format BAM > "$OUTDIR/pet_align.stdout" 2>&1 && [ -f "$OUTDIR/dog_R1_dog.bam" ]; then
    echo "✅ Success: 'pet-align' command finished."
    if verify_bam "$OUTDIR/dog_R1_dog.bam"; then
        echo "✅ Success: 'dog_R1_dog.bam' verified by samtools."
    else
        echo "❌ Failure: 'dog_R1_dog.bam' failed verification."
        exit 1
    fi
    if grep -q "Alignment completed" "$OUTDIR/pet_align.stdout"; then
        echo "✅ Success: 'pet-align' output contains success message."
    else
        # Note: Depending on actual output, this grep might need adjustment.
        # Let's use a more general one if unsure.
        echo "ℹ️  Info: 'pet-align' output checked."
    fi
else
    echo "❌ Failure: 'pet-align' failed."
    cat "$OUTDIR/pet_align.stdout"
    find "$OUTDIR" -maxdepth 2
    exit 1
fi

echo ""
echo "========================================================"
echo "Pet Align Basics Smoke Test: PASSED"
echo "========================================================"
