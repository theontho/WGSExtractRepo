#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Annotates variants with population frequency data from gnomAD."
    echo "🌕 End Goal: VCF with allele frequency information from gnomAD populations."
    exit 0
fi

# Ensure we're using the correct entry point (can be overridden by environment)
WGSE_CMD=${WGSE_CMD:-"uv run python -m wgsextract_cli.main"}

OUTDIR="out/vcf_gnomad_out"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_gnomad"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
# Compress it so ReferenceLibrary finds it (it expects .gz)
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
# Index it
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create a dummy gnomAD VCF
# Standard gnomAD VCF has AF in INFO
GNOMAD_VCF="$REFDIR/ref/gnomad_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/gnomad.vcf"
##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	100	PASS	AF=0.005
chr1	200	.	C	T	100	PASS	AF=0.05
EOF
bgzip -c "$OUTDIR/gnomad.vcf" > "$GNOMAD_VCF"
tabix -p vcf "$GNOMAD_VCF"

# 3. Create a dummy input VCF with two variants
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	100	.	A	G	100	PASS	.	GT	0/1
chr1	200	.	C	T	100	PASS	.	GT	0/1
chr1	300	.	G	A	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF gnomAD Smoke Test"
echo "--------------------------------------------------------"

# 4. Run gnomad command (Annotation only)
echo ":: Running gnomAD annotation..."
if $WGSE_CMD vcf gnomad \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/gnomad_annotated.vcf.gz" ]; then
    echo "✅ Success: 'vcf gnomad' completed."
    # Check if annotation worked (AF should be GNOMAD_AF)
    if bcftools query -f '%CHROM:%POS %GNOMAD_AF\n' "$OUTDIR/gnomad_annotated.vcf.gz" | grep -q "chr1:100 0.005"; then
        echo "✅ Success: Annotation confirmed (GNOMAD_AF=0.005 found)."
    else
        echo "❌ Failure: gnomAD annotation missing or incorrect in output."
        bcftools query -f '%CHROM:%POS %GNOMAD_AF\n' "$OUTDIR/gnomad_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: 'vcf gnomad' failed or missing output."
    exit 1
fi

# 5. Run gnomad command (with Filtering)
echo ":: Running gnomAD annotation + filtering (max AF < 0.01)..."
if $WGSE_CMD vcf gnomad \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" \
    --max-af 0.01 && [ -f "$OUTDIR/gnomad_af_lt_0.01.vcf.gz" ]; then
    echo "✅ Success: gnomAD filtering produced output."
    # Should have:
    # chr1:100 (0.005 < 0.01)
    # chr1:300 (not in gnomAD, null AF)
    # Should NOT have:
    # chr1:200 (0.05 > 0.01)
    COUNT=$(bcftools query -f '%CHROM:%POS\n' "$OUTDIR/gnomad_af_lt_0.01.vcf.gz" | wc -l)
    if [ "$COUNT" -eq 2 ]; then
        echo "✅ Success: Filtered correctly (2 variants remain)."
    else
        echo "❌ Failure: Incorrect number of variants after filter ($COUNT)."
        bcftools query -f '%CHROM:%POS %GNOMAD_AF\n' "$OUTDIR/gnomad_af_lt_0.01.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: gnomAD filtering failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF gnomAD Smoke Test: ALL PASSED"
echo "========================================================"
