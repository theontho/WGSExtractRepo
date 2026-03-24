#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Performs joint variant calling and analysis for a family trio (Mother, Father, Proband)."
    echo "✅ Verified End Goal: A joint VCF containing samples for Proband, Father, and Mother; verified by output existence, validity (bcftools), and sample presence."
    exit 0
fi

# Configuration
OUTDIR="out/smoke_test_vcf_trio"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Generate dummy trio data with unique sample names
echo ":: Generating dummy trio VCFs..."
vcf_header='##fileformat=VCFv4.2
##contig=<ID=chrM,length=16569>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT'

echo -e "$vcf_header\tPROBAND\nchrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/1" > "$OUTDIR/child.vcf"
echo -e "$vcf_header\tMOTHER\nchrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/0" > "$OUTDIR/mom.vcf"
echo -e "$vcf_header\tFATHER\nchrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/0" > "$OUTDIR/dad.vcf"

for f in child.vcf mom.vcf dad.vcf; do
    bgzip -f "$OUTDIR/$f"
    tabix -p vcf "$OUTDIR/$f.gz"
done

check_mandatory_deps
echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Trio Smoke Test"
echo "  Mode: denovo"
echo "--------------------------------------------------------"

if uv run wgsextract vcf trio \
    --proband "$OUTDIR/child.vcf.gz" \
    --mother "$OUTDIR/mom.vcf.gz" \
    --father "$OUTDIR/dad.vcf.gz" \
    --mode denovo \
    --outdir "$OUTDIR" && verify_vcf "$OUTDIR/trio_denovo.vcf.gz" 1; then
    echo "SUCCESS: VCF Trio completed."
    ls -lh "$OUTDIR/trio_denovo.vcf.gz"

    # Verify all samples are present in the output
    SAMPLES=$(bcftools query -l "$OUTDIR/trio_denovo.vcf.gz")
    echo "Detected samples: $SAMPLES"
    for s in PROBAND MOTHER FATHER; do
        if echo "$SAMPLES" | grep -q "$s"; then
            echo "✅ Success: Sample '$s' found in output."
        else
            echo "❌ Failure: Sample '$s' NOT found in output."
            exit 1
        fi
    done
else
    echo "FAILURE: VCF Trio failed."
    exit 1
fi
