#!/bin/bash
# Full-Genome Smoke test for CRAM-to-Microarray workflow

# Load environment variables from .env.local
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

INPUT_FILE="${WGSE_INPUT}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_cram"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL GENOME CRAM Smoke Test..."
echo "Input: $INPUT_FILE"
echo "Mode: Parallel Variant Calling"

# GOALS of this test:
# 1. Performance: Parallel variant calling should finish 30x genome in < 30 minutes.
# 2. Build Detection: Should identify build (hg38/hg19) from CRAM header and resolve reference.
# 3. Parallelism: Should successfully split by chromosome and merge results.
# 4. Correctness: CombinedKit.txt should contain valid genotypes (non-NN).

# Run the command
uv run wgsextract microarray \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --parallel \
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
        # Check for valid genotypes (at least some rows shouldn't be NN)
        if [[ "$file" == *"CombinedKit.txt" ]]; then
            # We look for A, C, G, T in the 4th column
            valid_genotypes=$(grep -v "^#" "$file" | head -n 1000 | awk '$4 ~ /[ACGT][ACGT]/' | wc -l)
            if [ "$valid_genotypes" -gt 0 ]; then
                echo "   ✅ Valid genotypes found (non-NN calls)."
            else
                echo "   ❌ ERROR: No valid genotypes found (all NN?). Check variant calling."
                exit 1
            fi
        fi
    else
        echo "❌ Missing or empty: $file"
        exit 1
    fi
done

echo ">>> FULL CRAM Smoke Test PASSED."
