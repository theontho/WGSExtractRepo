#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Filters VCF records based on quality, depth, or other criteria."
    echo "End Goal: A filtered VCF file containing only records that meet the specified criteria."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

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

if uv run wgsextract vcf filter \
    --vcf-input "$INPUT_VCF" \
    --expr "QUAL>10" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/filtered.vcf.gz" ]; then
    echo "SUCCESS: VCF Filter completed."
    ls -lh "$OUTDIR/filtered.vcf.gz"
else
    echo "FAILURE: VCF Filter failed."
    exit 1
fi
