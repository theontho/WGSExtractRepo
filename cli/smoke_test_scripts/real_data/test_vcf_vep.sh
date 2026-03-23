#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs VEP annotation on a real-world full-genome VCF."
    echo "✅ Verified End Goal: Annotated VCF with CSQ fields from Ensembl VEP."
    exit 0
fi

# Check if VEP cache is downloaded
if [ ! -d "$HOME/.vep/homo_sapiens" ]; then
    echo "⏭️  SKIP: (no vep cache) Local VEP cache not found at $HOME/.vep/homo_sapiens"
    exit 77
fi

if [ -z "$WGSE_INPUT_VCF" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT_VCF environment variable not set."
    exit 77
fi

INPUT_FILE="${WGSE_INPUT_VCF}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_vep"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Slicing VCF to chr20:1-1000000 for smoke test..."
SLICED_VCF="$OUT_DIR/sliced.vcf.gz"
uv run bcftools view -r chr20:1-1000000 -Oz -o "$SLICED_VCF" "$INPUT_FILE"
uv run tabix -p vcf "$SLICED_VCF"

echo ">>> Starting FULL GENOME VCF VEP Smoke Test (Sliced Region)..."
echo "Input: $SLICED_VCF"
echo "Mode: VEP Annotation"

uv run wgsextract vep \
    --input "$SLICED_VCF" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --vep-cache "$HOME/.vep" \
    --vep-assembly GRCh38

echo ">>> Verifying outputs..."
OUTPUT_FILE=$(find "$OUT_DIR" -name "*vep*.vcf.gz" | head -n 1)

if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Found: $(basename "$OUTPUT_FILE") ($(du -h "$OUTPUT_FILE" | cut -f1))"
    # Verify CSQ annotation
    if zgrep -q "CSQ=" "$OUTPUT_FILE" || grep -q "CSQ=" "$OUTPUT_FILE"; then
        echo "   ✅ Valid VEP annotation (CSQ) found."
    else
        echo "   ❌ ERROR: No CSQ annotations found in output."
        exit 1
    fi
else
    echo "❌ Missing or empty output file."
    exit 1
fi

echo ">>> FULL VCF VEP Smoke Test PASSED."
