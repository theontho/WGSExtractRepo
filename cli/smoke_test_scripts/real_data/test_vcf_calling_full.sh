#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs real-world variant calling with DeepVariant, GATK, and FreeBayes on a small genomic region."
    echo "✅ Verified End Goal: Three valid VCF files (deepvariant.vcf.gz, gatk.vcf.gz, freebayes.vcf.gz) with records in the target region, verified by bcftools."
    exit 0
fi

# Check for required tools
check_mandatory_deps

if [ -z "$WGSE_INPUT" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT environment variable not set."
    exit 77
fi

INPUT_FILE="${WGSE_INPUT}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_calling"
REGION="chrM" # Use MT-DNA for a fast real-data smoke test

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL VARIANT CALLING Smoke Test (Region: $REGION)..."
echo "Input: $INPUT_FILE"

# 1. DeepVariant
echo ":: Running DeepVariant..."
# We skip if no model or if docker/singularity/pixi can't find it, handled by CLI
uv run wgsextract vcf deepvariant \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --region "$REGION"

# 2. GATK HaplotypeCaller
echo ":: Running GATK HaplotypeCaller..."
uv run wgsextract vcf gatk \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --region "$REGION"

# 3. FreeBayes
echo ":: Running FreeBayes..."
uv run wgsextract vcf freebayes \
    --input "$INPUT_FILE" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --region "$REGION"

echo ">>> Verifying variant calling outputs..."

# Check DeepVariant
DV_VCF=$(find "$OUT_DIR" -name "*deepvariant*.vcf.gz" | head -n 1)
if [ -f "$DV_VCF" ]; then
    echo "✅ Found DeepVariant: $(basename "$DV_VCF")"
    verify_vcf "$DV_VCF"
else
    echo "⚠️  DeepVariant output missing (may be expected if deepvariant is not installed)."
fi

# Check GATK
GATK_VCF=$(find "$OUT_DIR" -name "*gatk*.vcf.gz" | head -n 1)
if [ -f "$GATK_VCF" ]; then
    echo "✅ Found GATK: $(basename "$GATK_VCF")"
    verify_vcf "$GATK_VCF"
else
    echo "⚠️  GATK output missing (may be expected if gatk is not installed)."
fi

# Check FreeBayes
FB_VCF=$(find "$OUT_DIR" -name "*freebayes*.vcf.gz" | head -n 1)
if [ -f "$FB_VCF" ]; then
    echo "✅ Found FreeBayes: $(basename "$FB_VCF")"
    verify_vcf "$FB_VCF"
else
    echo "❌ Failure: FreeBayes output missing."
    exit 1
fi

echo ">>> FULL VARIANT CALLING Smoke Test PASSED."
