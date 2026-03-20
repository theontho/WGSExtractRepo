#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_filter"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Filter Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

uv run wgsextract vcf filter \
    --vcf-input "$INPUT_VCF" \
    --expr "QUAL>10" \
    --outdir "$OUTDIR"

if [ $? -eq 0 ]; then
    echo "SUCCESS: VCF Filter completed."
    ls -lh "$OUTDIR/filtered.vcf.gz"
else
    echo "FAILURE: VCF Filter failed."
    exit 1
fi
