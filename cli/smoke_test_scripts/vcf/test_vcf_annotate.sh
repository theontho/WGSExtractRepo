#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Annotates a VCF file with basic metadata and region information."
    echo "End Goal: Annotated VCF with additional INFO fields."
    exit 0
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_annotate"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Annotate Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
echo "--------------------------------------------------------"

# Note: Annotate requires --ann-vcf. Since we don't have a small dummy one easily,
# we verify that the command routing and error checking works.
# If we have real data from env, we could use it.

uv run wgsextract vcf annotate \
    --input "$INPUT_VCF" \
    --ann-vcf "$INPUT_VCF" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR"

if [ $? -eq 0 ] && [ -f "$OUTDIR/annotated.vcf.gz" ]; then
    echo "SUCCESS: VCF Annotate completed."
    ls -lh "$OUTDIR/annotated.vcf.gz"
else
    echo "FAILURE: VCF Annotate failed."
    exit 1
fi
