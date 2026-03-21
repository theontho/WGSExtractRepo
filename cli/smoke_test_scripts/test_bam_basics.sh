#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

OUTDIR="out/smoke_test_bam_basics"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
if [ ! -f "$FAKEDATA/fake.bam" ]; then
    echo ":: Generating dependency fake data..."
    chmod +x smoke_test_scripts/test_qc_fake_data.sh
    ./smoke_test_scripts/test_qc_fake_data.sh
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: BAM Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Identify BAM build
echo ":: Testing 'bam identify'..."
uv run wgsextract bam identify --input "$FAKEDATA/fake.bam"

if [ $? -eq 0 ]; then
    echo "✅ Success: bam identify completed."
else
    echo "❌ Failure: bam identify failed."
    exit 1
fi

# 2. Index BAM
echo ":: Testing 'bam index'..."
# Create a copy to avoid modifying the fake data source
cp "$FAKEDATA/fake.bam" "$OUTDIR/test.bam"
uv run wgsextract bam index --input "$OUTDIR/test.bam"

if [ $? -eq 0 ] && [ -f "$OUTDIR/test.bam.bai" ]; then
    echo "✅ Success: bam index completed."
else
    echo "❌ Failure: bam index failed."
    exit 1
fi

# 3. Convert to CRAM
echo ":: Testing 'bam to-cram'..."
REF=$(ls "$FAKEDATA"/fake_ref_hg38_*.fa | head -n 1)
uv run wgsextract bam to-cram \
    --input "$OUTDIR/test.bam" \
    --outdir "$OUTDIR" \
    --ref "$REF"

if [ $? -eq 0 ] && [ -f "$OUTDIR/test.cram" ]; then
    echo "✅ Success: bam to-cram completed."
else
    echo "❌ Failure: bam to-cram failed."
    exit 1
fi

# 4. Convert back to BAM
echo ":: Testing 'bam to-bam'..."
uv run wgsextract bam to-bam \
    --input "$OUTDIR/test.cram" \
    --outdir "$OUTDIR" \
    --ref "$REF"

if [ $? -eq 0 ] && [ -f "$OUTDIR/test.bam" ]; then
    echo "✅ Success: bam to-bam completed."
else
    echo "❌ Failure: bam to-bam failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "BAM Basics Smoke Test: PASSED"
echo "========================================================"
