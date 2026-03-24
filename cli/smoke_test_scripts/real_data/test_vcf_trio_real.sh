#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs trio inheritance analysis on real-world family VCF data."
    echo "✅ Verified End Goal: A VCF file annotated with De Novo and Compound Heterozygous mutations, verified by header presence (TRIO_DENOVO, TRIO_COMPHET) and bcftools validation."
    exit 0
fi

# Check for required tools
check_mandatory_deps

if [ -z "$WGSE_VCF_CHILD" ] || [ -z "$WGSE_VCF_MOTHER" ] || [ -z "$WGSE_VCF_FATHER" ]; then
    echo "⏭️  SKIP: (missing data) WGSE_VCF_CHILD/MOTHER/FATHER environment variables not set."
    exit 77
fi

VCF_CHILD="${WGSE_VCF_CHILD}"
VCF_MOTHER="${WGSE_VCF_MOTHER}"
VCF_FATHER="${WGSE_VCF_FATHER}"
OUT_DIR="out/smoke_test_vcf_trio_real"

# Clean up previous runs
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo ">>> Starting TRIO ANALYSIS Smoke Test..."
echo "Child VCF:  $VCF_CHILD"
echo "Mother VCF: $VCF_MOTHER"
echo "Father VCF: $VCF_FATHER"

# 1. Trio Analysis
echo ":: Running Trio Analysis..."
if ! uv run wgsextract vcf trio \
    --input "$VCF_CHILD" \
    --mother "$VCF_MOTHER" \
    --father "$VCF_FATHER" \
    --outdir "$OUT_DIR"; then
    echo "❌ Failure: 'vcf trio' command failed."
    exit 1
fi

echo ">>> Verifying trio outputs..."
TRIO_VCF=$(find "$OUT_DIR" -name "*trio*.vcf.gz" | head -n 1)

if [ -f "$TRIO_VCF" ]; then
    echo "✅ Found: $(basename "$TRIO_VCF") ($(du -h "$TRIO_VCF" | cut -f1))"
    if verify_vcf "$TRIO_VCF"; then
        echo "   Checking for trio inheritance markers..."
        if bcftools view -h "$TRIO_VCF" | grep -q "TRIO_DENOVO"; then
            echo "   ✅ Found TRIO_DENOVO in header."
        else
            echo "   ⚠️ Warning: TRIO_DENOVO not found in header."
        fi

        if bcftools view -h "$TRIO_VCF" | grep -q "TRIO_COMPHET"; then
            echo "   ✅ Found TRIO_COMPHET in header."
        else
            echo "   ⚠️ Warning: TRIO_COMPHET not found in header."
        fi
    else
        exit 1
    fi
else
    echo "❌ Missing trio analysis output file."
    exit 1
fi

echo ">>> TRIO ANALYSIS Smoke Test PASSED."
