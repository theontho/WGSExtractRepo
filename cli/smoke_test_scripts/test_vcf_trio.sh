#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"

# Configuration
OUTDIR="out/smoke_test_vcf_trio"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Generate dummy trio data
echo ":: Generating dummy trio VCFs..."
vcf_header='##fileformat=VCFv4.2
##contig=<ID=chrM,length=16569>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE'
vcf_line="chrM	100	.	A	G	100	PASS	.	GT"

echo -e "$vcf_header\n$vcf_line\t0/1" > "$OUTDIR/child.vcf"
echo -e "$vcf_header\n$vcf_line\t0/0" > "$OUTDIR/mom.vcf"
echo -e "$vcf_header\n$vcf_line\t0/0" > "$OUTDIR/dad.vcf"

for f in child.vcf mom.vcf dad.vcf; do
    bgzip -f "$OUTDIR/$f"
    tabix -p vcf "$OUTDIR/$f.gz"
done

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Trio Smoke Test"
echo "  Mode: denovo"
echo "--------------------------------------------------------"

uv run wgsextract vcf trio \
    --proband "$OUTDIR/child.vcf.gz" \
    --mother "$OUTDIR/mom.vcf.gz" \
    --father "$OUTDIR/dad.vcf.gz" \
    --mode denovo \
    --outdir "$OUTDIR"

if [ $? -eq 0 ]; then
    echo "SUCCESS: VCF Trio completed."
    ls -lh "$OUTDIR/trio_denovo.vcf.gz"
else
    echo "FAILURE: VCF Trio failed."
    exit 1
fi
