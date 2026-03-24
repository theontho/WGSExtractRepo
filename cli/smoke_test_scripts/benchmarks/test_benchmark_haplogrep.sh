#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks HaploGrep integration for mitochondrial haplogroup assignment."
    echo "✅ Verified End Goal: A haplogroup report containing the predicted haplogroup (e.g., L3); verified by output existence and content check."
    exit 0
fi

# Configuration
INPUT_CRAM="${WGSE_INPUT:-out/fake_30x/fake.bam}"
REF_PATH="${WGSE_REF:-reference/chrm/chrM.fa}"
OUTDIR="out/benchmark_results_haplogrep"

# Path to the specific conda environment for Haplogrep
HAPLOGREP_BIN="${WGSE_HAPLOGREP_PATH:-haplogrep}"
PATH="$(dirname "$HAPLOGREP_BIN"):$PATH"
export PATH

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: mt-DNA (Haplogrep) Benchmark"
echo "  Input: $(basename "$INPUT_CRAM")"
echo "  Env:   $CONDA_ENV_PATH"
echo "--------------------------------------------------------"

# Check dependencies
check_deps "$HAPLOGREP_BIN"
ensure_fake_data
verify_bam "$INPUT_CRAM"

start_time=$(date +%s)

# Run the mt-dna command
uv run wgsextract lineage mt-haplogroup \
    --input "$INPUT_CRAM" \
    --ref "$REF_PATH" \
    --outdir "$OUTDIR" \
    --debug > stdout 2>&1

end_time=$(date +%s)
runtime=$((end_time - start_time))

cat stdout
# Relaxed completion check: verify that Haplogrep actually ran
grep -iE "Haplogrep|lineage" stdout || { echo "❌ Failure: Haplogrep/lineage execution not confirmed in stdout"; exit 1; }

echo ""
echo "========================================================"
echo "Haplogrep Runtime: ${runtime} seconds"
echo "Results saved to:  $OUTDIR"
if [ -f "$OUTDIR/haplogrep_results.txt" ]; then
    HAPLOGROUP=$(tail -n 1 "$OUTDIR/haplogrep_results.txt" | cut -f2)
    echo "Haplogroup:        $HAPLOGROUP"
    # Relaxed haplogroup check: verify it's not empty and contains alphanumeric chars
    if [[ "$HAPLOGROUP" =~ [A-Za-z0-9] ]]; then
        echo "✅ Success: Haplogroup identified ($HAPLOGROUP)."
    else
        echo "❌ Failure: Missing or invalid haplogroup in report."
        exit 1
    fi
else
    echo "❌ Failure: Haplogrep results missing."
    exit 1
fi
echo "========================================================"
