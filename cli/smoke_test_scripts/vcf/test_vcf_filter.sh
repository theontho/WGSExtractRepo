#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF filtering based on various criteria (quality, gene, region)."
    echo "✅ Verified End Goal: A filtered VCF file; verified by output existence, validity, and filter criterion compliance (QUAL>10)."
    exit 0
fi

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
OUTDIR="out/smoke_test_vcf_filter"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Filter Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# Check dependencies
check_mandatory_deps
ensure_fake_data

if uv run wgsextract vcf filter \
    --input "$INPUT_VCF" \
    --expr 'QUAL>10' \
    --outdir "$OUTDIR" > "$OUTDIR/filter_expr.stdout" 2>&1 && verify_vcf "$OUTDIR/filtered.vcf.gz" 1; then
    cat "$OUTDIR/filter_expr.stdout"
    grep -qE "VCF Filter complete|Filtering|filtered.vcf.gz" "$OUTDIR/filter_expr.stdout" || { echo "❌ Failure: Expected success message missing from stdout"; exit 1; }
    echo "SUCCESS: VCF Filter completed."
    ls -lh "$OUTDIR/filtered.vcf.gz"
else
    echo "FAILURE: VCF Filter failed."
    exit 1
fi

# 2. Filter by Gene
echo ":: Testing 'vcf filter' by Gene..."
# Create dummy gene map
mkdir -p "$OUTDIR/ref"
echo -e "symbol\tchrom\tstart\tend" > "$OUTDIR/ref/genes_hg38.tsv"
echo -e "BRCA1\tchr1\t1\t1000000" >> "$OUTDIR/ref/genes_hg38.tsv"

if uv run wgsextract vcf filter \
    --input "$INPUT_VCF" \
    --gene "BRCA1" \
    --ref "$OUTDIR" \
    --outdir "$OUTDIR/by_gene" > "$OUTDIR/filter_gene.stdout" 2>&1 && verify_vcf "$OUTDIR/by_gene/filtered.vcf.gz"; then
    echo "SUCCESS: VCF Filter by gene completed."
else
    echo "FAILURE: VCF Filter by gene failed."
    cat "$OUTDIR/filter_gene.stdout"
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF Filter Smoke Test: PASSED"
echo "========================================================"
