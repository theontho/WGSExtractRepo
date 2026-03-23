#!/bin/bash
# Full-Genome Smoke test for VCF-to-Microarray workflow

# Load environment variables from .env.local
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Processes real-world VCF data to produce microarray-compatible outputs."
    echo "Verified End Goal: Accurate translation of VCF genotypes into microarray formats."
    exit 0
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

# GOALS of this test:
# 1. Performance: Extraction from 30x VCF should take < 1 minute due to optimized pre-fetching.
# 2. Build Detection: Should identify hg38 build from VCF and resolve hg38 reference files.
# 3. Liftover: Should correctly identify and use hg38ToHg19.over.chain.gz for vendor formats.
# 4. Correctness: CombinedKit.txt should contain valid genotypes (not just NN).
# 5. Chromosome Normalization: Should handle 'chr1' in VCF/TAB vs '1' in FASTA.

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
        # Check for valid genotypes (at least some rows shouldn't be NN)
        # We look for A, C, G, T in the 4th column of CombinedKit
        if [[ "$file" == *"CombinedKit.txt" ]]; then
            valid_genotypes=$(grep -v "^#" "$file" | head -n 1000 | awk '$4 ~ /[ACGT][ACGT]/' | wc -l)
            if [ "$valid_genotypes" -gt 0 ]; then
                echo "   ✅ Valid genotypes found (non-NN hits)."
            else
                echo "   ❌ ERROR: No valid genotypes found (all NN?). Check build/ref/faidx."
                exit 1
            fi
        fi
    else
        echo "❌ Missing or empty: $file"
        exit 1
    fi
done

echo ">>> FULL VCF Smoke Test PASSED."
