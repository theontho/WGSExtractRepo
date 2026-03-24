#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests advanced extraction operations: mito-fasta, mito-vcf, and custom (region/gene)."
    echo "✅ Verified End Goal: Valid FASTA and VCF for mtDNA, and custom BAM for a specific region."
    exit 0
fi

OUTDIR="out/smoke_test_extract_advanced"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
ensure_fake_data

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Extract Advanced Smoke Test"
echo "--------------------------------------------------------"

REF=$(find "$FAKEDATA" -name "fake_ref_hg38_*.fa" | head -n 1)

# 1. Test 'extract mito-fasta'
echo ":: Testing 'extract mito-fasta'..."
if uv run wgsextract extract mito-fasta \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --ref "$REF" && \
    [ -f "$OUTDIR/fake_MT.fasta" ] && \
    grep -q ">" "$OUTDIR/fake_MT.fasta"; then
    echo "✅ Success: mito-fasta completed and verified."
else
    echo "❌ Failure: mito-fasta failed or verification failed."
    exit 1
fi

# 2. Test 'extract mito-vcf'
echo ":: Testing 'extract mito-vcf'..."
if uv run wgsextract extract mito-vcf \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --ref "$REF" && \
    verify_vcf "$OUTDIR/fake_MT.vcf.gz"; then
    echo "✅ Success: mito-vcf completed and verified."
else
    echo "❌ Failure: mito-vcf failed or verification failed."
    exit 1
fi

# 3. Test 'extract custom' (Region)
echo ":: Testing 'extract custom' (region chr1:800-2000)..."
if uv run wgsextract extract custom \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --region "chr1:800-2000" && \
    verify_bam "$OUTDIR/fake_chr1_800-2000.bam"; then
    echo "✅ Success: extract custom (region) completed."
else
    echo "❌ Failure: extract custom (region) failed."
    exit 1
fi

# 4. Test 'extract custom' (BED)
echo ":: Testing 'extract custom' with a BED file..."
echo -e "chr1\t800\t2000" > "$OUTDIR/test.bed"
# The filename logic in extract.py now uses basename of the region file
if uv run wgsextract extract custom \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --region "$OUTDIR/test.bed" && \
    [ -f "$OUTDIR/fake_test.bed.bam" ] && \
    verify_bam "$OUTDIR/fake_test.bed.bam"; then
    echo "✅ Success: extract custom (BED) completed."
else
    echo "❌ Failure: extract custom (BED) failed or output not found."
    ls "$OUTDIR"
    exit 1
fi

# 5. Test 'extract custom' (Gene)
echo ":: Testing 'extract custom' (--gene GENE1)..."
# Create dummy gene map
mkdir -p "$OUTDIR/ref"
echo -e "symbol\tchrom\tstart\tend" > "$OUTDIR/ref/genes_hg38.tsv"
echo -e "GENE1\tchr1\t1\t2000" >> "$OUTDIR/ref/genes_hg38.tsv"

# We need to point WGSE_REFLIB or similar to this directory
# Or just use --ref as it often points to the library root
if WGSE_REFLIB="$OUTDIR" uv run wgsextract extract custom \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --gene "GENE1" \
    --ref "$REF" && \
    [ -f "$OUTDIR/fake_chr1_1-2000.bam" ] && \
    verify_bam "$OUTDIR/fake_chr1_1-2000.bam"; then
    echo "✅ Success: extract custom (gene) completed."
else
    echo "❌ Failure: extract custom (gene) failed or output not found."
    ls -R "$OUTDIR"
    exit 1
fi

echo ""
echo "========================================================"
echo "Extract Advanced Smoke Test: PASSED"
echo "========================================================"
