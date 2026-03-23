#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs multiple annotation steps in a sequential chain."
    echo "✅ Verified End Goal: Highly annotated VCF with combined information from multiple sources."
    exit 0
fi

OUTDIR="out/vcf_chain_annotate_out"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_chain"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create Dummy Annotation Files
# ClinVar VCF
CLINVAR_VCF="$REFDIR/ref/clinvar_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/clinvar.vcf"
##fileformat=VCFv4.2
##INFO=<ID=CLNSIG,Number=.,Type=String,Description="Clinical significance">
##INFO=<ID=CLNDN,Number=.,Type=String,Description="ClinVar Disease Name">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	.	.	CLNSIG=Pathogenic;CLNDN=Disease1
chr1	200	.	C	T	.	.	CLNSIG=Benign;CLNDN=Disease2
EOF
bgzip -c "$OUTDIR/clinvar.vcf" > "$CLINVAR_VCF"
tabix -p vcf "$CLINVAR_VCF"

# REVEL TSV
REVEL_TSV="$REFDIR/ref/revel_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/revel.tsv"
#Chr	Start	End	Ref	Alt	Score
chr1	100	100	A	G	0.85
chr1	200	200	C	T	0.45
EOF
bgzip -c "$OUTDIR/revel.tsv" > "$REVEL_TSV"
tabix -s 1 -b 2 -e 2 "$REVEL_TSV"

# PhyloP TSV
PHYLOP_TSV="$REFDIR/ref/phylop_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/phylop.tsv"
#Chr	Start	End	Score
chr1	100	100	2.5
chr1	200	200	0.5
EOF
bgzip -c "$OUTDIR/phylop.tsv" > "$PHYLOP_TSV"
tabix -s 1 -b 2 -e 2 "$PHYLOP_TSV"

# gnomAD VCF
GNOMAD_VCF="$REFDIR/ref/gnomad_hg38.vcf.bgz"
cat <<EOF > "$OUTDIR/gnomad.vcf"
##fileformat=VCFv4.2
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	.	A	G	.	.	AF=0.001
chr1	200	.	C	T	.	.	AF=0.05
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
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Chain Annotate Smoke Test"
echo "--------------------------------------------------------"

# 4. Run chain-annotate command
echo ":: Running chained annotation (clinvar,revel,phylop,gnomad)..."
if uv run wgsextract vcf chain-annotate \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" \
    --annotations "clinvar,revel,phylop,gnomad" && [ -f "$OUTDIR/chain_annotated.vcf.gz" ]; then
    echo "✅ Success: 'vcf chain-annotate' completed."

    # Check if ALL annotations worked
    # chr1:100 should have CLNSIG, REVEL, PHYLOP, and GNOMAD_AF
    VAL=$(zgrep -v "^#" "$OUTDIR/chain_annotated.vcf.gz" | grep "100")

    if echo "$VAL" | grep -q "CLNSIG=Pathogenic" && \
       echo "$VAL" | grep -q "REVEL=0.85" && \
       echo "$VAL" | grep -q "PHYLOP=2.5" && \
       echo "$VAL" | grep -q "GNOMAD_AF=0.001"; then
        echo "✅ Success: All annotations confirmed on variant 1."
    else
        echo "❌ Failure: Missing one or more annotations in output."
        zgrep -v "^#" "$OUTDIR/chain_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: 'vcf chain-annotate' failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF Chain Annotate Smoke Test: ALL PASSED"
echo "========================================================"
