#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks lineage assignment specifically from VCF input files."
    echo "End Goal: Performance report for VCF-based lineage identification."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration - Using VCF instead of CRAM
INPUT_VCF="${WGSE_INPUT_VCF:-out/smoke_test_vcf_gatk/gatk.vcf.gz}"
OUTDIR="out/benchmark_results_vcf"

# Tool Paths
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Benchmark (VCF Mode)"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# 1. MT-DNA Benchmark (Haplogrep)
echo ":: Running mt-DNA Lineage (Haplogrep)..."
start_mt=$(date +%s)
uv run wgsextract lineage mt-dna \
    --input "$INPUT_VCF" \
    --outdir "$OUTDIR/mt_dna" \
    --haplogrep-path "$HAPLOGREP_BIN"
end_mt=$(date +%s)
runtime_mt=$((end_mt - start_mt))

# 2. Y-DNA Benchmark (Yleaf)
echo ":: Running Y-DNA Lineage (Yleaf)..."
start_y=$(date +%s)
uv run wgsextract lineage y-dna \
    --input "$INPUT_VCF" \
    --outdir "$OUTDIR/y_dna" \
    --threads "${WGSE_THREADS:-8}"
end_y=$(date +%s)
runtime_y=$((end_y - start_y))

echo ""
echo "========================================================"
echo "                BENCHMARK SUMMARY (VCF)"
echo "========================================================"
echo "mt-DNA (Haplogrep): ${runtime_mt} seconds"
echo "Y-DNA (Yleaf):      ${runtime_y} seconds"
echo "Total Time:         $((runtime_mt + runtime_y)) seconds"
echo "========================================================"
echo "Results saved to: $OUTDIR"
