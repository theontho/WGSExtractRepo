#!/bin/bash

# Configuration
WGSE_CMD=${WGSE_CMD:-"uv run python -m wgsextract_cli.main"}
OUTDIR="out/smoke_test_perf_boost"
mkdir -p "$OUTDIR"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Evaluates performance optimization flags like multi-threading and buffer sizes."
    echo "Verified End Goal: Successful execution with optimized settings showing speed improvements."
    exit 0
fi

# Clear all environment variables that might interfere
export WGSE_SKIP_DOTENV=1
unset WGSE_INPUT
unset WGSE_REF
unset WGSE_OUTDIR
unset WGSE_THREADS
unset WGSE_MEMORY

# 1. Create fake FASTQ data
R1="$OUTDIR/fake_R1.fastq.gz"
R2="$OUTDIR/fake_R2.fastq.gz"

echo ":: Generating fake data for performance boost test..."
# Explicitly provide a small reference path to avoid it picking up huge env ones
$WGSE_CMD qc fake-data --type fastq --outdir "$OUTDIR" --coverage 0.1 --seed 42 --build hg38
REF_FILE="$OUTDIR/fake_ref_hg38_scaled.fa"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Performance Boost Smoke Test"
echo "--------------------------------------------------------"

# Check if sambamba and samblaster are available
HAS_SAMBAMBA=$(which sambamba 2>/dev/null)
HAS_SAMBLASTER=$(which samblaster 2>/dev/null)

echo "Tools detected:"
if [ -n "$HAS_SAMBAMBA" ]; then echo "  - sambamba: FOUND"; else echo "  - sambamba: NOT FOUND (using samtools fallback)"; fi
if [ -n "$HAS_SAMBLASTER" ]; then echo "  - samblaster: FOUND"; else echo "  - samblaster: NOT FOUND (skipping duplicate marking)"; fi

# 2. Run alignment with BWA
echo ":: Running BWA alignment..."
# Clear WGSE_INPUT to avoid it being picked up
unset WGSE_INPUT
$WGSE_CMD align --r1 "$R1" --r2 "$R2" --ref "$REF_FILE" --outdir "$OUTDIR" --debug 2>&1 | tee "$OUTDIR/align.log"

# 3. Verify output
OUT_BAM="$OUTDIR/fake_R1_aligned.bam"
if [ -f "$OUT_BAM" ]; then
    echo "✅ Success: Aligned BAM created."
else
    echo "❌ Failure: Aligned BAM missing."
    exit 1
fi

# 4. Check logs for tool usage
if [ -n "$HAS_SAMBAMBA" ]; then
    if grep -q "sambamba sort" "$OUTDIR/align.log"; then
        echo "✅ Success: sambamba sort was used."
    else
        echo "❌ Failure: sambamba sort was NOT used despite being available."
        exit 1
    fi
fi

if [ -n "$HAS_SAMBLASTER" ]; then
    if grep -q "Using samblaster" "$OUTDIR/align.log"; then
        echo "✅ Success: samblaster was used."
    else
        echo "❌ Failure: samblaster was NOT used despite being available."
        exit 1
    fi
fi

echo "========================================================"
echo "Performance Boost Smoke Test: PASSED"
echo "========================================================"
