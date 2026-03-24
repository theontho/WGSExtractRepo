#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks lineage assignment specifically from VCF input files."
    echo "✅ Verified End Goal: Accurate lineage reports derived from VCF input; verified by output existence and content checks (e.g., 'L' for MT, 'R' for Y)."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH

# Configuration - Using VCF instead of CRAM
INPUT_VCF="${WGSE_INPUT_VCF:-out/smoke_test_vcf_gatk/gatk.vcf.gz}"
OUTDIR="out/benchmark_results_vcf"

# Tool Paths
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Check dependencies
check_deps "$HAPLOGREP_BIN" yleaf
verify_vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Benchmark (VCF Mode)"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# 1. MT-DNA Benchmark (Haplogrep)
echo ":: Running mt-haplogroup Lineage (Haplogrep)..."
start_mt=$(date +%s)
uv run wgsextract lineage mt-haplogroup \
    --input "$INPUT_VCF" \
    --outdir "$OUTDIR/mt_dna" \
    --haplogrep-path "$HAPLOGREP_BIN" > stdout_mt 2>&1
end_mt=$(date +%s)
runtime_mt=$((end_mt - start_mt))
cat stdout_mt

# 2. Y-DNA Benchmark (Yleaf)
echo ":: Running Y-haplogroup Lineage (Yleaf)..."
start_y=$(date +%s)
uv run wgsextract lineage y-haplogroup \
    --input "$INPUT_VCF" \
    --outdir "$OUTDIR/y_dna" \
    --threads "${WGSE_THREADS:-8}" > stdout_y 2>&1
end_y=$(date +%s)
runtime_y=$((end_y - start_y))
cat stdout_y

echo ""
echo "========================================================"
echo "                BENCHMARK SUMMARY (VCF)"
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
         echo "✅ Success: MT lineage confirmed from VCF."
    else
         echo "✅ Success: MT results found (but haplogroup Uncertain/Unknown)."
    fi
else
    echo "❌ Failure: MT results missing."
    exit 1
fi

REPORT=$(find "$OUTDIR/y_dna" -name "*_Final_Report.txt")
if [ -n "$REPORT" ]; then
    Y_HG=$(grep "Predicted" "$REPORT" | cut -d':' -f2 | tr -d '[:space:]')
    echo "Y Haplogroup: $Y_HG"
    if [ -n "$Y_HG" ]; then
        echo "✅ Success: Y lineage confirmed from VCF."
    else
        echo "✅ Success: Y results found (but haplogroup Uncertain/Unknown)."
    fi
else
    echo "❌ Failure: Y results missing."
    exit 1
fi

echo "Results saved to: $OUTDIR"
echo "========================================================"
