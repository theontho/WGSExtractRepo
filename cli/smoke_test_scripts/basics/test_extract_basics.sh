#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies the core genomic extraction functionality for various formats."
    echo "✅ Verified End Goal: Extracted sequences matching the requested regions and formats; verified by samtools/bcftools validation of output BAMs/VCFs and expected stdout logs."
    exit 0
fi

OUTDIR="out/smoke_test_extract_basics"
FAKEDATA="out/smoke_test_qc_fake/hg38"
HG19DATA="out/smoke_test_qc_fake/hg19"

# Ensure fake data exists by running the dependency test
if [ ! -f "$FAKEDATA/fake.bam" ] || [ ! -f "$HG19DATA/fake.cram" ]; then
    echo ":: Generating dependency fake data via test_qc_fake_data.sh..."
    chmod +x smoke_test_scripts/basics/test_qc_fake_data.sh
    ./smoke_test_scripts/basics/test_qc_fake_data.sh
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Extract Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Extract Mitochondrial BAM
echo ":: Testing 'extract mt-bam'..."
STDOUT=$(uv run wgsextract extract mt-bam \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Extracting mtDNA reads" && verify_bam "$OUTDIR/fake_mtDNA.bam"; then
    echo "✅ Success: mt-bam extraction verified."
else
    echo "❌ Failure: mt-bam extraction failed or verification failed."
    exit 1
fi

# 2. Extract Y-DNA BAM
echo ":: Testing 'extract ydna-bam'..."
STDOUT=$(uv run wgsextract extract ydna-bam \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Extracting Y-chromosome reads" && verify_bam "$OUTDIR/fake_Y.bam"; then
    echo "✅ Success: ydna-bam extraction verified."
else
    echo "❌ Failure: ydna-bam extraction failed or verification failed."
    exit 1
fi

# 3. Extract Unmapped Reads
echo ":: Testing 'extract unmapped'..."
STDOUT=$(uv run wgsextract extract unmapped \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Extracting unmapped reads" && verify_bam "$OUTDIR/fake_unmapped.bam" 1; then
    echo "✅ Success: unmapped extraction verified."
else
    echo "❌ Failure: unmapped extraction failed or verification failed."
    exit 1
fi

# 4. Extract Subset (Region)
echo ":: Testing 'extract bam-subset' (region chr1)..."
STDOUT=$(uv run wgsextract extract bam-subset \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --region "chr1" \
    --fraction 0.1 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Subsetting 0.1 of reads" && verify_bam "$OUTDIR/fake_subset.bam"; then
    echo "✅ Success: subset extraction verified."
else
    echo "❌ Failure: subset extraction failed or verification failed."
    exit 1
fi

# 5. Extract Y-DNA VCF
echo ":: Testing 'extract ydna-vcf'..."
STDOUT=$(uv run wgsextract extract ydna-vcf \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Calling Y-chromosome variants" && verify_vcf "$OUTDIR/fake_Y.vcf.gz"; then
    echo "✅ Success: ydna-vcf extraction verified."
else
    echo "❌ Failure: ydna-vcf extraction failed or verification failed."
    exit 1
fi

# 6. Combined Y-MT Extraction
echo ":: Testing 'extract y-mt-extract'..."
STDOUT=$(uv run wgsextract extract y-mt-extract \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR/y_mt" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Extracting Y and MT reads" && verify_bam "$OUTDIR/y_mt/fake_Y_MT.bam"; then
    echo "✅ Success: y-mt-extract verified."
else
    echo "❌ Failure: y-mt-extract failed or verification failed."
    exit 1
fi

# 7. Extract hg19 CRAM (Verification of CRAM + Ref support)
echo ":: Testing 'extract mt-bam' with hg19 CRAM..."
# We need to find the correct hg19 ref name
HG19_REF=$(find "$HG19DATA" -name "fake_ref_hg19_*.fa" | head -n 1)
STDOUT=$(uv run wgsextract extract mt-bam \
    --input "$HG19DATA/fake.cram" \
    --outdir "$OUTDIR/hg19" \
    --ref "$HG19_REF" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Extracting mtDNA reads" && verify_bam "$OUTDIR/hg19/fake_mtDNA.bam"; then
    echo "✅ Success: hg19 mt-bam extraction verified."
else
    echo "❌ Failure: hg19 mt-bam extraction failed or verification failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Extract Basics Smoke Test: PASSED"
echo "========================================================"
