#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF calling using the FreeBayes variant caller."
    echo "End Goal: Valid VCF output from FreeBayes."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_freebayes"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Freebayes Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

# Check if freebayes is installed
if ! command -v freebayes &> /dev/null; then
    echo "SKIP: freebayes not found in PATH."
    exit 0
fi

if uv run wgsextract vcf freebayes \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/freebayes.vcf.gz" ]; then
    echo "SUCCESS: VCF Freebayes completed."
    ls -lh "$OUTDIR/freebayes.vcf.gz"
else
    echo "FAILURE: VCF Freebayes failed."
    exit 1
fi
