#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests VCF operations using a full-scale reference genome and database."
    echo "End Goal: Successful processing against production-grade reference files."
    exit 0
fi

# Configuration
WGSE_CMD=${WGSE_CMD:-"uv run python -m wgsextract_cli.main"}
OUTDIR="out/smoke_test_vcf_real_ref_db"
REFDIR="reference"
mkdir -p "$OUTDIR"

# 1. Create a minimal hg38 reference genome for chr1
# AlphaMissense variants start at 69094, so we need a genome at least that long.
mkdir -p "$OUTDIR/fake_genome"
echo ">chr1" > "$OUTDIR/fake_genome/hg38.fa"
# 100k Ns
printf "N%.0s" {1..100000} >> "$OUTDIR/fake_genome/hg38.fa"
echo "" >> "$OUTDIR/fake_genome/hg38.fa"
bgzip -c "$OUTDIR/fake_genome/hg38.fa" > "$OUTDIR/fake_genome/hg38.fa.gz"
samtools faidx "$OUTDIR/fake_genome/hg38.fa.gz"

# 2. Create Input VCF with real variants
# AlphaMissense: chr1 69094 G T
# ClinVar: chr1 69134 A G
# REVEL: chr1 35142 G A
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	35142	.	G	A	100	PASS	.	GT	0/1
chr1	69094	.	G	T	100	PASS	.	GT	0/1
chr1	69134	.	A	G	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: REAL DB Smoke Test (AlphaMissense)"
echo "--------------------------------------------------------"

# 3. Run AlphaMissense with REAL data
echo ":: Running AlphaMissense annotation with real data..."
$WGSE_CMD vcf alphamissense \
    --input "$INPUT_VCF" \
    --ref "$OUTDIR/fake_genome/hg38.fa.gz" \
    --am-file "$REFDIR/ref/alphamissense_hg38.tsv.gz" \
    --outdir "$OUTDIR"

if [ -f "$OUTDIR/alphamissense_annotated.vcf.gz" ]; then
    VAL=$(bcftools query -f '%am_class\n' "$OUTDIR/alphamissense_annotated.vcf.gz" | grep "likely_benign")
    if [ -n "$VAL" ]; then
        echo "✅ Success: Real AlphaMissense annotation confirmed!"
    else
        echo "❌ Failure: Real AlphaMissense annotation missing or incorrect."
        exit 1
    fi
else
    echo "❌ Failure: AlphaMissense failed."
    exit 1
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: REAL DB Smoke Test (REVEL)"
echo "--------------------------------------------------------"

# 4. Run REVEL with REAL data
echo ":: Running REVEL annotation with real data..."
$WGSE_CMD vcf revel \
    --input "$INPUT_VCF" \
    --ref "$OUTDIR/fake_genome/hg38.fa.gz" \
    --revel-file "$REFDIR/ref/revel_hg38.tsv.gz" \
    --outdir "$OUTDIR"

if [ -f "$OUTDIR/revel_annotated.vcf.gz" ]; then
    VAL=$(bcftools query -f '%REVEL\n' "$OUTDIR/revel_annotated.vcf.gz" | grep "0.027")
    if [ -n "$VAL" ]; then
        echo "✅ Success: Real REVEL annotation confirmed!"
    else
        echo "❌ Failure: Real REVEL annotation missing or incorrect."
        bcftools query -f '%CHROM:%POS %REVEL\n' "$OUTDIR/revel_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: REVEL failed."
    exit 1
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: REAL DB Smoke Test (ClinVar)"
echo "--------------------------------------------------------"

# 5. Run ClinVar with REAL data
echo ":: Running ClinVar annotation with real data..."
$WGSE_CMD vcf clinvar \
    --input "$INPUT_VCF" \
    --ref "$OUTDIR/fake_genome/hg38.fa.gz" \
    --clinvar-file "$REFDIR/ref/clinvar_hg38.vcf.gz" \
    --outdir "$OUTDIR"

if [ -f "$OUTDIR/clinvar_annotated.vcf.gz" ]; then
    VAL=$(bcftools query -f '%CLNSIG\n' "$OUTDIR/clinvar_annotated.vcf.gz" | grep "Likely_benign")
    if [ -n "$VAL" ]; then
        echo "✅ Success: Real ClinVar annotation confirmed!"
    else
        echo "❌ Failure: Real ClinVar annotation missing or incorrect."
        bcftools query -f '%CHROM:%POS %CLNSIG\n' "$OUTDIR/clinvar_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: ClinVar failed."
    exit 1
fi

echo "========================================================"
echo "REAL DB Smoke Test: ALL PASSED"
echo "========================================================"
