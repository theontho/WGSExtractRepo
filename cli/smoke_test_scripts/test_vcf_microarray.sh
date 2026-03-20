#!/bin/bash
# Full-Genome Smoke test for VCF-to-Microarray workflow

# Load environment variables from .env.local
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

INPUT_FILE="${WGSE_INPUT_VCF}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_vcf"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL GENOME VCF Smoke Test..."
echo "Input: $INPUT_FILE"
echo "Mode: Optimized VCF Extraction + Gap Filling"

# Run the command
uv run wgsextract microarray \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --formats "23andme_v5,ancestry_v2" \
    --debug

# Verification
echo ">>> Verifying outputs..."
FILES=(
    "$OUT_DIR"/*_CombinedKit.txt
    "$OUT_DIR"/*_23andMe_V5.txt
    "$OUT_DIR"/*_Ancestry_V2.txt
)

for file in "${FILES[@]}"; do
    if [ -s "$file" ]; then
        echo "✅ Found: $(basename "$file") ($(du -h "$file" | cut -f1))"
    else
        echo "❌ Missing or empty: $file"
        exit 1
    fi
done

echo ">>> FULL VCF Smoke Test PASSED."
