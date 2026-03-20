#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Configuration
INPUT_VCF="${WGSE_INPUT_VCF:-/Users/mac/Documents/genetics/genomes/mahyar/vcf/Mahyar_McDonald_NU-NKQA-0638.vcf.gz}"
REF_ROOT="/Users/mac/src/WGSExtractRepo2/reference"
OUTDIR="benchmark_results_yleaf"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Path to the specific conda environment for Yleaf
CONDA_ENV_PATH="/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env"
# Yleaf also needs samtools/bcftools which are in the base env or wgse env
WGSE_ENV_PATH="/opt/homebrew/Caskroom/miniconda/base/envs/wgse"

export PATH="$CONDA_ENV_PATH/bin:$WGSE_ENV_PATH/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Y-DNA (Yleaf) Benchmark"
echo "  Input: $(basename "$INPUT_VCF")"
echo "  Env:   $CONDA_ENV_PATH (Local Editable)
--------------------------------------------------------"

# --- Verification Step ---
echo ":: Verifying Local Yleaf Installation..."
YLEAF_BIN=$(which yleaf)
if [ -z "$YLEAF_BIN" ]; then
    echo "❌ Error: 'yleaf' not found in PATH."
    exit 1
fi
echo "✅ Setup verified (using local editable install)."
echo ""
# -------------------------

start_time=$(date +%s)

# Run the y-dna command
# Note: Using absolute paths for input to be safe
INPUT_ABS=$(realpath "$INPUT_VCF")
OUTDIR_ABS=$(realpath "$OUTDIR")

uv run wgsextract lineage y-dna \
    --input "$INPUT_ABS" \
    --ref "$REF_ROOT" \
    --outdir "$OUTDIR_ABS" \
    --threads "${WGSE_THREADS:-8}" \
    --extra-args="-old" \
    --debug

end_time=$(date +%s)
runtime=$((end_time - start_time))

echo ""
echo "========================================================"
echo "Yleaf Runtime: ${runtime} seconds"
echo "Results saved to:  $OUTDIR"
# Check for report file in subdirectory (Yleaf creates a folder named after the sample)
REPORT=$(find "$OUTDIR" -name "*_Final_Report.txt")
if [ -n "$REPORT" ]; then
    echo "Report found at:   $REPORT"
    echo "Result:            $(grep "Predicted Haplogroup:" "$REPORT")"
fi
echo "========================================================"
