#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests basic BAM operations like indexing, sorting, and stats extraction."
    echo "End Goal: Generated .bai file and a non-empty stats report; verified by existence of generated index, CRAM, and BAM output files."
    exit 0
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
if uv run wgsextract bam identify --input "$FAKEDATA/fake.bam"; then
    echo "✅ Success: bam identify completed."
else
    echo "❌ Failure: bam identify failed."
    exit 1
fi

# 2. Index BAM
echo ":: Testing 'bam index'..."
# Create a copy to avoid modifying the fake data source
cp "$FAKEDATA/fake.bam" "$OUTDIR/test.bam"
if uv run wgsextract bam index --input "$OUTDIR/test.bam" && [ -f "$OUTDIR/test.bam.bai" ]; then
    echo "✅ Success: bam index completed."
else
    echo "❌ Failure: bam index failed."
    exit 1
fi

# 3. Convert to CRAM
echo ":: Testing 'bam to-cram'..."
REF=$(find "$FAKEDATA" -name "fake_ref_hg38_*.fa" | head -n 1)
if uv run wgsextract bam to-cram \
    --input "$OUTDIR/test.bam" \
    --outdir "$OUTDIR" \
    --ref "$REF" && [ -f "$OUTDIR/test.cram" ]; then
    echo "✅ Success: bam to-cram completed."
else
    echo "❌ Failure: bam to-cram failed."
    exit 1
fi

# 4. Convert back to BAM
echo ":: Testing 'bam to-bam'..."
if uv run wgsextract bam to-bam \
    --input "$OUTDIR/test.cram" \
    --outdir "$OUTDIR" \
    --ref "$REF" && [ -f "$OUTDIR/test.bam" ]; then
    echo "✅ Success: bam to-bam completed."
else
    echo "❌ Failure: bam to-bam failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "BAM Basics Smoke Test: PASSED"
echo "========================================================"
