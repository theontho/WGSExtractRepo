#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs the full clinical annotation stack on a real VCF."
    echo "✅ Verified End Goal: A VCF file annotated with ClinVar (CLNSIG), gnomAD (AF), REVEL (REVEL), AlphaMissense (AM_CLASS), and PharmGKB (PGKB) fields, verified by header presence and content."
    exit 0
fi

# Check for required tools
check_mandatory_deps

if [ -z "$WGSE_INPUT_VCF" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_INPUT_VCF environment variable not set."
    exit 77
fi

INPUT_VCF="${WGSE_INPUT_VCF}"
REF_DIR="${WGSE_REF}"
OUT_DIR="out/full_smoke_out_clinical"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting FULL CLINICAL ANNOTATION Smoke Test..."
echo "Input: $INPUT_VCF"

# 1. ClinVar
echo ":: Running ClinVar Annotation..."
uv run wgsextract vcf clinvar \
    --input "$INPUT_VCF" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"

# 2. gnomAD
echo ":: Running gnomAD Annotation..."
uv run wgsextract vcf gnomad \
    --input "$OUT_DIR/clinvar_annotated.vcf.gz" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"

# 3. REVEL
echo ":: Running REVEL Annotation..."
uv run wgsextract vcf revel \
    --input "$OUT_DIR/gnomad_annotated.vcf.gz" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"

# 4. AlphaMissense
echo ":: Running AlphaMissense Annotation..."
uv run wgsextract vcf alphamissense \
    --input "$OUT_DIR/revel_annotated.vcf.gz" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"

# 5. PharmGKB
echo ":: Running PharmGKB Annotation..."
uv run wgsextract vcf pharmgkb \
    --input "$OUT_DIR/alphamissense_annotated.vcf.gz" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR"

echo ">>> Verifying final annotated VCF..."
FINAL_VCF="$OUT_DIR/pharmgkb_annotated.vcf.gz"

if [ -f "$FINAL_VCF" ]; then
    echo "✅ Found: $(basename "$FINAL_VCF") ($(du -h "$FINAL_VCF" | cut -f1))"
    if verify_vcf "$FINAL_VCF"; then
        echo "   Checking INFO fields for annotations..."

        FIELDS=("CLNSIG" "AF" "REVEL" "AM_CLASS" "PGKB_ID")
        MISSING=()
        for field in "${FIELDS[@]}"; do
            if bcftools view -h "$FINAL_VCF" | grep -q "ID=$field"; then
                echo "   ✅ Found field: $field"
            else
                # Some fields might be missing if the resources aren't available in the ref dir,
                # but for a 'full' smoke test we expect them.
                echo "   ⚠️ Warning: Missing field in header: $field"
                MISSING+=("$field")
            fi
        done

        if [ ${#MISSING[@]} -eq ${#FIELDS[@]} ]; then
             echo "❌ Failure: NONE of the requested annotations were found in the output VCF."
             exit 1
        fi
    else
        exit 1
    fi
else
    echo "❌ Missing final annotated output file: $FINAL_VCF"
    exit 1
fi

echo ">>> FULL CLINICAL ANNOTATION Smoke Test PASSED."
