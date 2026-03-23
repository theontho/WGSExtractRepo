#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies microarray data processing and conversion from raw formats."
    echo "Verified End Goal: Processed microarray data in a standard format (e.g., 23andMe)."
    exit 0
fi

OUTDIR="out/smoke_test_microarray_basics"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_micro"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
mkdir -p "$REFDIR/microarray"
mkdir -p "$REFDIR/raw_file_templates/body"
mkdir -p "$REFDIR/raw_file_templates/head"

# Dummy templates for 23andMe_V5
echo "# rsid	chromosome	position	genotype" > "$REFDIR/raw_file_templates/head/23andMe_V5.txt"
# Template body: rsid, chrom, pos
echo "rs1	chr1	10" > "$REFDIR/raw_file_templates/body/23andMe_V5_1.txt"
echo "rs2	chr1	20" > "$REFDIR/raw_file_templates/body/23andMe_V5_2.txt"

echo ">chr1" > "$REFDIR/genomes/hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/hg38.fa"
bgzip -c "$REFDIR/genomes/hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create a dummy SNP tab file
# Format: CHROM POS ID REF ALT
TABFILE="$REFDIR/microarray/All_SNPs_hg38_ref.tab.gz"
cat <<EOF > "$OUTDIR/snps.tab"
#CHROM	POS	ID	REF	ALT
chr1	10	rs1	A	G
chr1	20	rs2	C	T
EOF
bgzip -c "$OUTDIR/snps.tab" > "$TABFILE"
tabix -p vcf "$TABFILE"

# 3. Create a dummy input VCF
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	10	.	A	G	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Microarray Basics Smoke Test"
echo "--------------------------------------------------------"

# 4. Run microarray command
uv run wgsextract microarray \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" \
    --formats "23andme_v5"

if [ $? -eq 0 ] && [ -f "$OUTDIR/input_23andMe_V5.txt" ]; then
    echo "✅ Success: 'microarray' completed."
    # Check if variant was picked up
    grep -q "rs1" "$OUTDIR/input_23andMe_V5.txt"
    if [ $? -eq 0 ]; then
        echo "✅ Success: Variant rs1 found in output."
    else
        echo "❌ Failure: Variant rs1 missing in output."
        exit 1
    fi
else
    echo "❌ Failure: 'microarray' failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "Microarray Basics Smoke Test: PASSED"
echo "========================================================"
