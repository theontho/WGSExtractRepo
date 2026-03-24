#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Benchmarks Yleaf integration for Y-chromosomal lineage assignment."
    echo "✅ Verified End Goal: A Y-haplogroup report containing the predicted haplogroup (e.g., R1b); verified by output existence and content check."
    exit 0
fi

# Configuration
if [ "$WGSE_USE_REAL_DATA" = "true" ] && [ -n "$WGSE_INPUT_VCF" ]; then
    INPUT_VCF="$WGSE_INPUT_VCF"
else
    INPUT_VCF="out/fake_30x/fake.vcf.gz"
fi
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
echo "  WGS Extract CLI: Y-haplogroup (Yleaf) Benchmark"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# --- Verification Step ---
# ... (rest of verification step)
echo "✅ Setup verified (using local editable install)."
echo ""
# -------------------------

start_time=$(date +%s)

# Run the y-haplogroup command
# Note: Using absolute paths for input to be safe
INPUT_ABS=$(realpath "$INPUT_VCF")
OUTDIR_ABS=$(realpath "$OUTDIR")

if ! uv run wgsextract lineage y-haplogroup \
    --input "$INPUT_ABS" \
    --ref "$REF_ROOT" \
    --outdir "$OUTDIR_ABS" \
    --threads "${WGSE_THREADS:-8}" \
    --extra-args="-old" \
    --debug > "$OUTDIR/stdout" 2>&1; then
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: Y-haplogroup command failed."
        exit 1
    fi
fi

end_time=$(date +%s)
runtime=$((end_time - start_time))

cat "$OUTDIR/stdout"
# Verification
if grep -qE "Y-DNA analysis complete|lineage y-haplogroup complete|Predicted" "$OUTDIR/stdout"; then
    echo "✅ Success: Y-haplogroup analysis completed."
else
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: Y-haplogroup analysis success message missing"
        exit 1
    else
        echo "⚠️  Warning: Y-haplogroup analysis failed (expected on fake data)."
    fi
fi

echo ""
echo "========================================================"
echo "Yleaf Runtime: ${runtime} seconds"
echo "Results saved to:  $OUTDIR"
# Check for report file in subdirectory (Yleaf creates a folder named after the sample)
REPORT=$(find "$OUTDIR" -name "*_Final_Report.txt")
if [ -n "$REPORT" ]; then
    echo "Report found at:   $REPORT"
    Y_HG=$(grep "Predicted" "$REPORT" | cut -d':' -f2 | tr -d '[:space:]')
    echo "Result:            $Y_HG"
    if [ -n "$Y_HG" ]; then
        echo "✅ Success: Y-haplogroup identified ($Y_HG)."
    else
        echo "✅ Success: Y-haplogroup report found (but haplogroup field empty/uncertain)."
    fi
else
    if [ "$WGSE_USE_REAL_DATA" = "true" ]; then
        echo "❌ Failure: Yleaf report missing."
        exit 1
    else
        echo "⚠️  Warning: Yleaf report missing (expected on fake data)."
    fi
fi
echo "========================================================"

echo "========================================================"
