#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
REF_PATH="${WGSE_REF:-reference/chrm/chrM.fa}"
INPUT_CRAM="${WGSE_INPUT:-out/fake_30x/fake.bam}"
OUTDIR="out/benchmark_results"

# Tool Paths
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Lineage Benchmark"
echo "  Input: $(basename "$INPUT_CRAM")"
echo "  Threads: ${WGSE_THREADS:-Auto}"
echo "--------------------------------------------------------"

# 1. MT-DNA Benchmark (Haplogrep)
echo ":: Running mt-DNA Lineage (Haplogrep)..."
start_mt=$(date +%s)
uv run wgsextract lineage mt-dna \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR/mt_dna" \
    --haplogrep-path "$HAPLOGREP_BIN" \
    --debug
end_mt=$(date +%s)
runtime_mt=$((end_mt - start_mt))

# 2. Y-DNA Benchmark (Yleaf)
echo ":: Running Y-DNA Lineage (Yleaf)..."
start_y=$(date +%s)
uv run wgsextract lineage y-dna \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR/y_dna" \
    --threads "${WGSE_THREADS:-8}" \
    --debug
end_y=$(date +%s)
runtime_y=$((end_y - start_y))

echo ""
echo "========================================================"
echo "                BENCHMARK SUMMARY"
echo "========================================================"
echo "mt-DNA (Haplogrep): ${runtime_mt} seconds"
echo "Y-DNA (Yleaf):      ${runtime_y} seconds"
echo "Total Time:         $((runtime_mt + runtime_y)) seconds"
echo "========================================================"
echo "Results saved to: $OUTDIR"
