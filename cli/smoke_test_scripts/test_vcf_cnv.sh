#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration - Pull paths from .env.local if present, otherwise use defaults
INPUT_BAM="${WGSE_INPUT:-out/fake_30x/fake.bam}"
REF_FASTA="${WGSE_REF_FASTA:-out/fake_30x/fake_ref.fa}"
MAP_FILE="${WGSE_MAP:-}"
OUTDIR="out/smoke_test_vcf_cnv"
REGION="${WGSE_REGION:-chr1}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF CNV Smoke Test (Delly)"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Map:   $(basename "$MAP_FILE")"
echo "--------------------------------------------------------"

# Check if delly is installed
if ! command -v delly &> /dev/null; then
    echo "SKIP: delly not found in PATH."
    exit 0
fi

uv run wgsextract vcf cnv \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --map "$MAP_FILE" \
    --outdir "$OUTDIR" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo "SUCCESS: VCF CNV completed."
    ls -lh "$OUTDIR/cnv.vcf.gz"
else
    echo "FAILURE: VCF CNV failed."
    exit 1
fi
