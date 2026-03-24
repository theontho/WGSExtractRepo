#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies advanced 'Expert' scenarios: Quiet Mode, Multiple Regions, Complex VCF Filtering, and BAM/CRAM consistency."
    echo "✅ Verified End Goal: Identical results across formats, successful parsing of multi-region/complex expressions, and zero-log output in quiet mode."
    exit 0
fi

OUTDIR="out/smoke_test_expert"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

ensure_fake_data
FAKEDATA="out/fake_30x"
BAM="$FAKEDATA/fake.bam"
REF="$FAKEDATA/fake_ref.fa"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Expert Scenarios Smoke Test"
echo "--------------------------------------------------------"

# 1. Test Quiet Mode
echo ":: Testing --quiet mode..."
STDOUT=$(uv run wgsextract info --input "$BAM" --quiet 2>&1)
if echo "$STDOUT" | grep -q "ℹ️"; then
    echo "❌ Failure: Informational logs found in quiet mode output."
    echo "$STDOUT"
    exit 1
else
    echo "✅ Success: Quiet mode suppressed informational logs."
fi

# 2. Test Multiple Regions in 'extract custom'
echo ":: Testing 'extract custom' with multiple regions..."
# We try to extract two non-contiguous regions
REGION="chr1:1-1000,chr1:5000-6000"
EXPECTED_BAM="$OUTDIR/multi_region/fake_chr1_1-1000_chr1_5000-6000.bam"
if uv run wgsextract extract custom \
    --input "$BAM" \
    --outdir "$OUTDIR/multi_region" \
    --region "$REGION" \
    --debug && [ -f "$EXPECTED_BAM" ]; then
    echo "✅ Success: extract custom handled multiple regions."
    verify_bam "$EXPECTED_BAM"
else
    echo "❌ Failure: extract custom failed with multiple regions."
    exit 1
fi

# 3. Test Complex Boolean in 'vcf filter'
echo ":: Testing 'vcf filter' with complex boolean expression..."
VCF="$FAKEDATA/fake.vcf.gz"
# Expression: QUAL > 10 AND (POS < 5000 OR POS > 10000)
EXPR="QUAL>10 && (POS<5000 || POS>10000)"
if uv run wgsextract vcf filter \
    --input "$VCF" \
    --outdir "$OUTDIR/complex_filter" \
    --expr "$EXPR" && verify_vcf "$OUTDIR/complex_filter/filtered.vcf.gz"; then
    echo "✅ Success: vcf filter handled complex boolean expression."
else
    echo "❌ Failure: vcf filter failed with complex boolean expression."
    exit 1
fi

# 4. Test BAM vs CRAM Consistency
echo ":: Testing BAM vs CRAM Analysis Consistency (info)..."
# Convert to CRAM first if needed (usually exists from other tests, but let's be sure)
CRAM="$OUTDIR/consistency.cram"
uv run wgsextract bam to-cram --input "$BAM" --ref "$REF" --outdir "$OUTDIR" > /dev/null 2>&1
mv "$OUTDIR/fake.cram" "$CRAM"

# Run info on both and compare key metrics (MD5, Build)
# info prints to stdout, we capture it.
INFO_BAM=$(uv run wgsextract info --input "$BAM" --quiet 2>&1)
INFO_CRAM=$(uv run wgsextract info --input "$CRAM" --ref "$REF" --quiet 2>&1)

# Key check: MD5 Signature should be identical
MD5_BAM=$(echo "$INFO_BAM" | grep "MD5 Signature" | head -n 1 | awk '{print $NF}')
MD5_CRAM=$(echo "$INFO_CRAM" | grep "MD5 Signature" | head -n 1 | awk '{print $NF}')

if [ "$MD5_BAM" == "$MD5_CRAM" ] && [ -n "$MD5_BAM" ]; then
    echo "✅ Success: BAM and CRAM produced identical MD5 signatures ($MD5_BAM)."
else
    echo "❌ Failure: BAM and CRAM produced DIFFERENT or EMPTY MD5 signatures!"
    echo "BAM: '$MD5_BAM'"
    echo "CRAM: '$MD5_CRAM'"
    exit 1
fi

echo ""
echo "========================================================"
echo "Expert Scenarios Smoke Test: PASSED"
echo "========================================================"
