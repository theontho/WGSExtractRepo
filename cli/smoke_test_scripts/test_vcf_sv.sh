#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_sv"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF SV Smoke Test (Delly)"
echo "  Input: $(basename "$INPUT_BAM")"
echo "--------------------------------------------------------"

# Check if delly is installed
if ! command -v delly &> /dev/null; then
    echo "SKIP: delly not found in PATH."
    exit 0
fi

uv run wgsextract vcf sv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo "SUCCESS: VCF SV completed."
    ls -lh "$OUTDIR/sv.vcf.gz"
else
    echo "FAILURE: VCF SV failed."
    exit 1
fi
