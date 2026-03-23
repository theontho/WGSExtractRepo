#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks Yleaf integration for Y-chromosomal lineage assignment."
    echo "Verified End Goal: Comparison with standard Yleaf results; extracts and displays the predicted haplogroup from the report."
    exit 0
fi

# Configuration
INPUT_VCF="${WGSE_INPUT_VCF:-out/smoke_test_vcf_gatk/gatk.vcf.gz}"
REF_ROOT="${WGSE_REF:-reference}"
OUTDIR="out/benchmark_results_yleaf"

# Tool Paths - Use environment variables for conda environments if not in path
YLEAF_ENV="${WGSE_YLEAF_ENV_PATH:-}"
WGSE_ENV="${WGSE_WGSE_ENV_PATH:-}"

if [ -n "$YLEAF_ENV" ]; then
    PATH="$YLEAF_ENV/bin:$PATH"
    export PATH
fi
if [ -n "$WGSE_ENV" ]; then
    PATH="$WGSE_ENV/bin:$PATH"
    export PATH
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Y-DNA (Yleaf) Benchmark"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

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
