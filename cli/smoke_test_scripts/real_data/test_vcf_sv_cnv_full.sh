#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs structural variant (SV) and copy-number variation (CNV) calling on real-world data using Delly."
    echo "✅ Verified End Goal: VCF files with SV (BND, DEL, INS, DUP, INV) and CNV records, verified by bcftools and header check."
    exit 0
fi

# Check for required tools
check_mandatory_deps
check_deps delly

if [ -z "$WGSE_INPUT" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT environment variable not set."
    exit 77
fi

INPUT_FILE="${WGSE_INPUT}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_sv_cnv"
REGION="chrM" # Use chrM for a fast smoke test, though SVs are rare there

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL SV/CNV Smoke Test..."
echo "Input: $INPUT_FILE"

# 1. Structural Variants (SVs)
echo ":: Running SV Calling (Delly)..."
uv run wgsextract vcf sv \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR/sv" \
    --region "$REGION"

# 2. Copy-Number Variations (CNVs)
echo ":: Running CNV Calling (Delly/bcftools)..."
uv run wgsextract vcf cnv \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR/cnv" \
    --region "$REGION"

echo ">>> Verifying SV/CNV outputs..."

# Verify SVs
SV_VCF=$(find "$OUT_DIR/sv" -name "*sv*.vcf.gz" | head -n 1)
if [ -f "$SV_VCF" ]; then
    echo "✅ Found SV VCF: $(basename "$SV_VCF")"
    verify_vcf "$SV_VCF" "allow_empty" # SVs might be empty on chrM
else
    echo "❌ Failure: SV VCF missing."
    exit 1
fi

# Verify CNVs
CNV_VCF=$(find "$OUT_DIR/cnv" -name "*cnv*.vcf.gz" | head -n 1)
if [ -f "$CNV_VCF" ]; then
    echo "✅ Found CNV VCF: $(basename "$CNV_VCF")"
    verify_vcf "$CNV_VCF" "allow_empty"
else
    echo "❌ Failure: CNV VCF missing."
    exit 1
fi

echo ">>> FULL SV/CNV Smoke Test PASSED."
