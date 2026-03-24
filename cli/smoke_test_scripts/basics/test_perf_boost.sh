#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Evaluates performance optimization flags like multi-threading and buffer sizes."
    echo "✅ Verified End Goal: Successful execution with optimized settings showing tool usage; verified by samtools quickcheck on output BAM and log inspection for sambamba/samblaster."
    exit 0
fi

OUTDIR="out/smoke_test_perf_boost"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# 1. Create fake FASTQ data
R1="$OUTDIR/fake_R1.fastq.gz"
R2="$OUTDIR/fake_R2.fastq.gz"

echo ":: Generating fake data for performance boost test..."
uv run wgsextract qc fake-data --type fastq --outdir "$OUTDIR" --coverage 0.1 --seed 42 --build hg38 --ref "$OUTDIR"
REF_FILE=$(find "$OUTDIR" -name "fake_ref_hg38_*.fa" | head -n 1)

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Performance Boost Smoke Test"
echo "--------------------------------------------------------"

# Check if sambamba and samblaster are available (includes Pixi fallback)
HAS_SAMBAMBA=""
if uv run wgsextract deps check --tool sambamba &> /dev/null; then
    HAS_SAMBAMBA="YES"
fi

HAS_SAMBLASTER=""
if uv run wgsextract deps check --tool samblaster &> /dev/null; then
    HAS_SAMBLASTER="YES"
fi

echo "Tools detected:"
if [ -n "$HAS_SAMBAMBA" ]; then echo "  - sambamba: FOUND"; else echo "  - sambamba: NOT FOUND (using samtools fallback)"; fi
if [ -n "$HAS_SAMBLASTER" ]; then echo "  - samblaster: FOUND"; else echo "  - samblaster: NOT FOUND (skipping duplicate marking)"; fi

# 2. Run alignment with BWA
echo ":: Running BWA alignment with potential performance boosts..."
STDOUT=$(uv run wgsextract align --r1 "$R1" --r2 "$R2" --ref "$REF_FILE" --outdir "$OUTDIR" --debug 2>&1)
echo "$STDOUT"

# 3. Verify output
OUT_BAM="$OUTDIR/fake_R1_aligned.bam"
if verify_bam "$OUT_BAM"; then
    echo "✅ Success: Aligned BAM verified."
else
    echo "❌ Failure: Aligned BAM missing or invalid."
    exit 1
fi

# 4. Check logs for tool usage
# Note: On macOS, we might intentionally avoid sambamba for stability in some versions
if [ -n "$HAS_SAMBAMBA" ] && [[ "$(uname)" != "Darwin" ]]; then
    if echo "$STDOUT" | grep -q "sambamba sort"; then
        echo "✅ Success: sambamba sort was used."
    else
        echo "❌ Failure: sambamba sort was NOT used despite being available."
        exit 1
    fi
fi

if [ -n "$HAS_SAMBLASTER" ]; then
    if echo "$STDOUT" | grep -q "Using samblaster"; then
        echo "✅ Success: samblaster was used."
    else
        echo "❌ Failure: samblaster was NOT used despite being available."
        exit 1
    fi
fi

echo ""
echo "========================================================"
echo "Performance Boost Smoke Test: PASSED"
echo "========================================================"
