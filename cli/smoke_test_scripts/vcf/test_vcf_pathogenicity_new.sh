#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests the latest pathogenicity scoring integration (SpliceAI, AlphaMissense, PharmGKB, REVEL, PhyloP)."
    echo "✅ Verified End Goal: Comprehensive pathogenicity scores assigned to variants; verified by output existence, validity (bcftools), and score presence."
    exit 0
fi

# Ensure we're using the correct entry point
WGSE_CMD="uv run wgsextract"

OUTDIR="out/smoke_test_vcf_pathogenicity_new"
# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_patho"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create Dummy Data Files

# SpliceAI (VCF format)
SPLICEAI_FILE="$REFDIR/ref/spliceai_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/spliceai.vcf"
##fileformat=VCFv4.2
##INFO=<ID=SpliceAI,Number=.,Type=String,Description="SpliceAI scores">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	100	PASS	SpliceAI=G|GENE1|0.1|0.1|0.8|0.1|0|0|0|0
EOF
bgzip -c "$OUTDIR/spliceai.vcf" > "$SPLICEAI_FILE"
tabix -p vcf "$SPLICEAI_FILE"

# AlphaMissense (VCF format)
AM_FILE="$REFDIR/ref/alphamissense_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/am.vcf"
##fileformat=VCFv4.2
##INFO=<ID=am_pathogenicity,Number=1,Type=Float,Description="AlphaMissense pathogenicity score">
##INFO=<ID=am_class,Number=1,Type=String,Description="AlphaMissense classification">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	100	PASS	am_pathogenicity=0.9;am_class=likely_pathogenic
EOF
bgzip -c "$OUTDIR/am.vcf" > "$AM_FILE"
tabix -p vcf "$AM_FILE"

# PharmGKB (VCF format)
PHARMGKB_FILE="$REFDIR/ref/pharmgkb_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/pharmgkb.vcf"
##fileformat=VCFv4.2
##INFO=<ID=PHARMGKB,Number=1,Type=String,Description="PharmGKB annotation">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	100	PASS	PHARMGKB=Ibuprofen_Slow_Metabolizer
EOF
bgzip -c "$OUTDIR/pharmgkb.vcf" > "$PHARMGKB_FILE"
tabix -p vcf "$PHARMGKB_FILE"

# REVEL (TSV format)
REVEL_TSV="$REFDIR/ref/revel_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/revel.tsv"
#Chr	Start	End	Ref	Alt	Score
chr1	100	100	A	G	0.85
EOF
bgzip -c "$OUTDIR/revel.tsv" > "$REVEL_TSV"
tabix -s 1 -b 2 -e 2 "$REVEL_TSV"

# PhyloP (TSV format)
PHYLOP_TSV="$REFDIR/ref/phylop_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/phylop.tsv"
#Chr	Start	End	Score
chr1	100	100	2.5
EOF
bgzip -c "$OUTDIR/phylop.tsv" > "$PHYLOP_TSV"
tabix -s 1 -b 2 -e 2 "$PHYLOP_TSV"

# 3. Create Input VCF
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	100	.	A	G	100	PASS	.	GT	0/1
chr1	200	.	C	T	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Pathogenicity Smoke Test"
echo "--------------------------------------------------------"

# 4. Run SpliceAI Test
echo ":: Running SpliceAI annotation..."
if $WGSE_CMD vcf spliceai --input "$INPUT_VCF" --ref "$REFDIR" --outdir "$OUTDIR" && verify_vcf "$OUTDIR/spliceai_annotated.vcf.gz"; then
    echo "✅ Success: SpliceAI annotation completed."
    bcftools query -f '%CHROM:%POS %SpliceAI\n' "$OUTDIR/spliceai_annotated.vcf.gz" | grep -q "chr1:100 G|GENE1|0.1|0.1|0.8|0.1|0|0|0|0"
else
    echo "❌ Failure: SpliceAI failed."
    exit 1
fi

# 5. Run AlphaMissense Test
echo ":: Running AlphaMissense annotation..."
if $WGSE_CMD vcf alphamissense --input "$INPUT_VCF" --ref "$REFDIR" --outdir "$OUTDIR" --min-score 0.5 && verify_vcf "$OUTDIR/alphamissense_gt_0.5.vcf.gz" 1; then
    echo "✅ Success: AlphaMissense completed."
    bcftools query -f '%CHROM:%POS %am_class\n' "$OUTDIR/alphamissense_gt_0.5.vcf.gz" | grep -q "chr1:100 likely_pathogenic"
else
    echo "❌ Failure: AlphaMissense failed."
    exit 1
fi

# 6. Run PharmGKB Test
echo ":: Running PharmGKB annotation..."
if $WGSE_CMD vcf pharmgkb --input "$INPUT_VCF" --ref "$REFDIR" --outdir "$OUTDIR" && verify_vcf "$OUTDIR/pharmgkb_annotated.vcf.gz"; then
    echo "✅ Success: PharmGKB completed."
    bcftools query -f '%CHROM:%POS %PHARMGKB\n' "$OUTDIR/pharmgkb_annotated.vcf.gz" | grep -q "chr1:100 Ibuprofen_Slow_Metabolizer"
else
    echo "❌ Failure: PharmGKB failed."
    exit 1
fi

# 7. Run REVEL Test
echo ":: Running REVEL annotation..."
if $WGSE_CMD vcf revel --input "$INPUT_VCF" --ref "$REFDIR" --outdir "$OUTDIR" && verify_vcf "$OUTDIR/revel_annotated.vcf.gz"; then
    echo "✅ Success: REVEL completed."
    bcftools query -f '%CHROM:%POS %REVEL\n' "$OUTDIR/revel_annotated.vcf.gz" | grep -q "chr1:100 0.85"
else
    echo "❌ Failure: REVEL failed."
    exit 1
fi

# 8. Run PhyloP Test
echo ":: Running PhyloP annotation..."
if $WGSE_CMD vcf phylop --input "$INPUT_VCF" --ref "$REFDIR" --outdir "$OUTDIR" && verify_vcf "$OUTDIR/phylop_annotated.vcf.gz"; then
    echo "✅ Success: PhyloP completed."
    bcftools query -f '%CHROM:%POS %PHYLOP\n' "$OUTDIR/phylop_annotated.vcf.gz" | grep -q "chr1:100 2.5"
else
    echo "❌ Failure: PhyloP failed."
    exit 1
fi

echo "========================================================"
echo "Pathogenicity Smoke Test: ALL PASSED"
echo "========================================================"
