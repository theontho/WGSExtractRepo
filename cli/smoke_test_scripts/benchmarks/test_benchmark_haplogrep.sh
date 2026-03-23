#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks HaploGrep integration for mitochondrial haplogroup assignment."
    echo "Verified End Goal: Comparison with standard HaploGrep results; extracts and displays the predicted haplogroup from the output."
    exit 0
fi

# Configuration
INPUT_CRAM="${WGSE_INPUT:-out/fake_30x/fake.bam}"
REF_PATH="${WGSE_REF:-reference/chrm/chrM.fa}"
OUTDIR="out/benchmark_results_haplogrep"

# Path to the specific conda environment for Haplogrep
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"
export PATH="$(dirname "$HAPLOGREP_BIN"):$PATH"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: mt-DNA (Haplogrep) Benchmark"
echo "  Input: $(basename "$INPUT_CRAM")"
echo "  Env:   $CONDA_ENV_PATH"
echo "--------------------------------------------------------"

start_time=$(date +%s)

# Run the mt-dna command
uv run wgsextract lineage mt-dna \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR" \
    --debug

end_time=$(date +%s)
runtime=$((end_time - start_time))

echo ""
echo "========================================================"
echo "Haplogrep Runtime: ${runtime} seconds"
echo "Results saved to:  $OUTDIR"
if [ -f "$OUTDIR/haplogrep_results.txt" ]; then
    echo "Haplogroup:        $(tail -n 1 "$OUTDIR/haplogrep_results.txt" | cut -f2)"
fi
echo "========================================================"
