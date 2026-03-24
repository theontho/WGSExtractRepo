#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests trio inheritance logic (De Novo, CompHet) using synthetic data."
    echo "✅ Verified End Goal: Annotated Trio VCFs with correct inheritance markers; verified by presence of variants in trio_denovo.vcf.gz and trio_comphet.vcf.gz."
    exit 0
fi

OUTDIR="out/smoke_test_vcf_trio_inheritance"
mkdir -p "$OUTDIR"

# 1. Generate synthetic trio data
# Variant 1: De Novo in child (chr1:100 A>G)
# Variant 2: Compound Het 1 (chr1:200 C>T, from Mother)
# Variant 3: Compound Het 2 (chr1:300 G>A, from Father)

vcf_header='##fileformat=VCFv4.2
##contig=<ID=chr1,length=1000000>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT'

# Proband: 100(0/1), 200(0/1), 300(0/1)
{
    echo -e "$vcf_header\tPROBAND"
    echo -e "chr1\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/1"
    echo -e "chr1\t200\t.\tC\tT\t100\tPASS\t.\tGT\t0/1"
    echo -e "chr1\t300\t.\tG\tA\t100\tPASS\t.\tGT\t0/1"
} > "$OUTDIR/proband.vcf"

# Mother: 100(0/0), 200(0/1), 300(0/0)
{
    echo -e "$vcf_header\tMOTHER"
    echo -e "chr1\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/0"
    echo -e "chr1\t200\t.\tC\tT\t100\tPASS\t.\tGT\t0/1"
    echo -e "chr1\t300\t.\tG\tA\t100\tPASS\t.\tGT\t0/0"
} > "$OUTDIR/mother.vcf"

# Father: 100(0/0), 200(0/0), 300(0/1)
{
    echo -e "$vcf_header\tFATHER"
    echo -e "chr1\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/0"
    echo -e "chr1\t200\t.\tC\tT\t100\tPASS\t.\tGT\t0/0"
    echo -e "chr1\t300\t.\tG\tA\t100\tPASS\t.\tGT\t0/1"
} > "$OUTDIR/father.vcf"

for f in proband.vcf mother.vcf father.vcf; do
    bgzip -f "$OUTDIR/$f"
    tabix -p vcf "$OUTDIR/$f.gz"
done

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Trio Inheritance Smoke Test"
echo "--------------------------------------------------------"

# 2. Run Trio Analysis
echo ":: Running trio analysis (mode: all)..."
if uv run wgsextract vcf trio \
    --proband "$OUTDIR/proband.vcf.gz" \
    --mother "$OUTDIR/mother.vcf.gz" \
    --father "$OUTDIR/father.vcf.gz" \
    --mode all \
    --outdir "$OUTDIR"; then
    echo "✅ Success: 'vcf trio' command finished."
else
    echo "❌ Failure: 'vcf trio' failed."
    exit 1
fi

# 3. Verify Inheritance Results
echo ":: Verifying inheritance results in output..."

# Check denovo
if [ -f "$OUTDIR/trio_denovo.vcf.gz" ] && bcftools query -f '%POS\n' "$OUTDIR/trio_denovo.vcf.gz" | grep -q "100"; then
    echo "✅ Success: De Novo variant correctly identified at pos 100."
else
    echo "❌ Failure: De Novo variant NOT identified at pos 100."
    [ -f "$OUTDIR/trio_denovo.vcf.gz" ] && bcftools query -f '%POS\n' "$OUTDIR/trio_denovo.vcf.gz"
    exit 1
fi

# Check comphet
# Pos 200 and 300 should be in trio_comphet.vcf.gz
if [ -f "$OUTDIR/trio_comphet.vcf.gz" ]; then
    if bcftools query -f '%POS\n' "$OUTDIR/trio_comphet.vcf.gz" | grep -q "200" && \
       bcftools query -f '%POS\n' "$OUTDIR/trio_comphet.vcf.gz" | grep -q "300"; then
        echo "✅ Success: Compound Het variants correctly identified at pos 200 and 300."
    else
        echo "❌ Failure: Compound Het variants NOT correctly identified."
        bcftools query -f '%POS\n' "$OUTDIR/trio_comphet.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: trio_comphet.vcf.gz missing."
    exit 1
fi

# 4. Run individual modes
echo ":: Testing 'vcf trio' with --mode recessive..."
if uv run wgsextract vcf trio \
    --proband "$OUTDIR/proband.vcf.gz" \
    --mother "$OUTDIR/mother.vcf.gz" \
    --father "$OUTDIR/father.vcf.gz" \
    --mode recessive \
    --outdir "$OUTDIR/recessive" && [ -f "$OUTDIR/recessive/trio_recessive.vcf.gz" ]; then
    echo "✅ Success: 'vcf trio --mode recessive' completed."
else
    echo "❌ Failure: 'vcf trio --mode recessive' failed."
    exit 1
fi

echo ":: Testing 'vcf trio' with --mode comphet..."
if uv run wgsextract vcf trio \
    --proband "$OUTDIR/proband.vcf.gz" \
    --mother "$OUTDIR/mother.vcf.gz" \
    --father "$OUTDIR/father.vcf.gz" \
    --mode comphet \
    --outdir "$OUTDIR/comphet" && [ -f "$OUTDIR/comphet/trio_comphet.vcf.gz" ]; then
    echo "✅ Success: 'vcf trio --mode comphet' completed."
else
    echo "❌ Failure: 'vcf trio --mode comphet' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Trio Inheritance Smoke Test: PASSED"
echo "========================================================"
