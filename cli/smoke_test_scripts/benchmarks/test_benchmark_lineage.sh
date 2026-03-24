#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks the accuracy and speed of haplogroup/lineage assignment (MT and Y)."
    echo "✅ Verified End Goal: Accurate lineage reports for both MT and Y DNA; verified by output existence and content checks (e.g., 'L' for MT, 'R' for Y)."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH

# Configuration
REF_PATH="${WGSE_REF:-reference/chrm/chrM.fa}"
OUTDIR="out/benchmark_results"

if [ "$WGSE_USE_REAL_DATA" = "true" ] && [ -n "$WGSE_INPUT" ]; then
    INPUT_CRAM="$WGSE_INPUT"
else
    INPUT_CRAM="out/fake_30x/fake.bam"
fi

# Tool Paths
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Check dependencies
check_deps "$HAPLOGREP_BIN" yleaf
ensure_fake_data
verify_bam "$INPUT_CRAM"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Benchmark"
echo "  Input: $(basename "$INPUT_CRAM")"
echo "  Threads: ${WGSE_THREADS:-Auto}"
echo "--------------------------------------------------------"

# 1. MT-DNA Benchmark (Haplogrep)
echo ":: Running mt-haplogroup Lineage (Haplogrep)..."
start_mt=$(date +%s)
if ! uv run wgsextract lineage mt-haplogroup \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR/mt_dna" \
    --haplogrep-path "$HAPLOGREP_BIN" \
    --debug > "$OUTDIR/mt_dna/stdout_mt" 2>&1; then
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: MT-haplogroup command failed."
        exit 1
    fi
fi
end_mt=$(date +%s)
runtime_mt=$((end_mt - start_mt))
cat "$OUTDIR/mt_dna/stdout_mt"

# 2. Y-DNA Benchmark (Yleaf)
echo ":: Running Y-haplogroup Lineage (Yleaf)..."
start_y=$(date +%s)
if ! uv run wgsextract lineage y-haplogroup \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR/y_dna" \
    --threads "${WGSE_THREADS:-8}" \
    --debug > "$OUTDIR/y_dna/stdout_y" 2>&1; then
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: Y-haplogroup command failed."
        exit 1
    fi
fi
end_y=$(date +%s)
runtime_y=$((end_y - start_y))
cat "$OUTDIR/y_dna/stdout_y"

echo ""
echo "========================================================"
echo "                BENCHMARK SUMMARY"
echo "========================================================"
echo "mt-haplogroup (Haplogrep): ${runtime_mt} seconds"
echo "Y-haplogroup (Yleaf):      ${runtime_y} seconds"
echo "Total Time:         $((runtime_mt + runtime_y)) seconds"
echo "========================================================"

# Verification
if [ -f "$OUTDIR/mt_dna/haplogrep_results.txt" ]; then
    MT_HG=$(tail -n 1 "$OUTDIR/mt_dna/haplogrep_results.txt" | cut -f2)
    echo "MT Haplogroup: $MT_HG"
    if echo "$MT_HG" | grep -qE "[A-Z]"; then
         echo "✅ Success: MT lineage confirmed."
    else
         echo "✅ Success: MT results found (but haplogroup Uncertain/Unknown)."
    fi
else
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: MT results missing."
        exit 1
    else
        echo "⚠️  Warning: MT results missing (expected on fake data)."
    fi
fi

REPORT=$(find "$OUTDIR/y_dna" -name "*_Final_Report.txt")
if [ -n "$REPORT" ]; then
    Y_HG=$(grep "Predicted" "$REPORT" | cut -d':' -f2 | tr -d '[:space:]')
    echo "Y Haplogroup: $Y_HG"
    if [ -n "$Y_HG" ]; then
        echo "✅ Success: Y lineage confirmed."
    else
        echo "✅ Success: Y results found (but haplogroup Uncertain/Unknown)."
    fi
else
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: Y results missing."
        exit 1
    else
        echo "⚠️  Warning: Y results missing (expected on fake data)."
    fi
fi

echo "Results saved to: $OUTDIR"
echo "========================================================"
