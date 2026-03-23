#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Generates synthetic genome data (BAM, VCF, FASTQ) using the 'qc fake-data' command."
    echo "End Goal: Successful creation of a test dataset in the output directory."
    exit 0
fi

OUTDIR="out/smoke_test_qc_fake"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: QC Fake Data Smoke Test"
echo "--------------------------------------------------------"

# 1. Generate small fake BAM and VCF for hg38
echo ":: Generating small hg38 BAM and VCF..."
uv run wgsextract qc fake-data \
    --outdir "$OUTDIR/hg38" \
    --build hg38 \
    --type bam,vcf \
    --coverage 0.1 \
    --seed 123 \
    --ref "$OUTDIR/hg38"

if [ $? -eq 0 ] && [ -f "$OUTDIR/hg38/fake.bam" ] && [ -f "$OUTDIR/hg38/fake.vcf.gz" ]; then
    echo "✅ Success: hg38 BAM and VCF generated."
    # Find the generated reference (it has Scaled in name usually)
    FASTA=$(ls "$OUTDIR/hg38"/fake_ref_hg38_*.fa | head -n 1)
    if [ -f "$FASTA" ]; then
        cp "$FASTA" "$OUTDIR/hg38/fake_ref_hg38_scaled.fa"
    fi
else
    echo "❌ Failure: hg38 data generation failed."
    exit 1
fi

# 2. Generate small fake CRAM for hg19
echo ":: Generating small hg19 CRAM..."
uv run wgsextract qc fake-data \
    --outdir "$OUTDIR/hg19" \
    --build hg19 \
    --type cram \
    --coverage 0.05

if [ $? -eq 0 ] && [ -f "$OUTDIR/hg19/fake.cram" ]; then
    echo "✅ Success: hg19 CRAM generated."
else
    echo "❌ Failure: hg19 CRAM generation failed."
    exit 1
fi

# 3. Generate small FASTQ
echo ":: Generating small FASTQ..."
uv run wgsextract qc fake-data \
    --outdir "$OUTDIR/fastq" \
    --type fastq \
    --coverage 0.01

if [ $? -eq 0 ] && [ -f "$OUTDIR/fastq/fake_R1.fastq.gz" ]; then
    echo "✅ Success: FASTQ generated."
else
    echo "❌ Failure: FASTQ generation failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "QC Fake Data Smoke Test: PASSED"
echo "========================================================"
