#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
INPUT_BAM="${WGSE_INPUT:-out/fake_30x/fake.bam}"
REF_FASTA="${WGSE_REF_FASTA:-out/fake_30x/fake_ref.fa}"
CHECKPOINT="${WGSE_DV_CHECKPOINT:-reference/models/deepvariant/WGS/deepvariant.wgs.ckpt}"
OUTDIR="out/smoke_test_vcf_deepvariant"
REGION="${WGSE_REGION:-chr1:1-5000}"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Ensure models exist
if [ ! -f "$CHECKPOINT.index" ]; then
    echo ":: DeepVariant model not found, running setup..."
    chmod +x scripts/setup_vcf_resources.sh
    ./scripts/setup_vcf_resources.sh
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF DeepVariant Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Checkpoint: $CHECKPOINT"
echo "--------------------------------------------------------"

# Check if deepvariant is installed
if ! command -v dv_make_examples.py &> /dev/null; then
    echo "SKIP: DeepVariant not found in PATH."
    exit 0
fi

uv run wgsextract vcf deepvariant \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --checkpoint "$CHECKPOINT" \
    --outdir "$OUTDIR" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo "SUCCESS: VCF DeepVariant completed."
    ls -lh "$OUTDIR/deepvariant.vcf.gz"
else
    echo "FAILURE: VCF DeepVariant failed."
    exit 1
fi
