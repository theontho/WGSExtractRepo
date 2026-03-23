#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs single-nucleotide polymorphism (SNP) calling from a BAM file."
    echo "End Goal: A VCF file containing valid SNP calls."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

# Configuration
INPUT_BAM="out/fake_30x/fake.bam"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_snp"
REGION="chr1"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF SNP Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Region: $REGION"
echo "--------------------------------------------------------"

if uv run wgsextract vcf snp \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --region "$REGION" \
    --ploidy 1 && [ -f "$OUTDIR/snps.vcf.gz" ]; then
    echo "SUCCESS: VCF SNP completed."
    ls -lh "$OUTDIR/snps.vcf.gz"
else
    echo "FAILURE: VCF SNP failed."
    exit 1
fi
