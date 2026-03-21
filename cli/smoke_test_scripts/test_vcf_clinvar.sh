#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

OUTDIR="out/vcf_clinvar_out"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_clinvar"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
# Compress it so ReferenceLibrary finds it (it expects .gz)
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
# Index it
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create a dummy ClinVar VCF
# It needs CLNSIG and CLNDN in INFO
CLINVAR="$REFDIR/ref/clinvar_hg38.vcf.gz"
cat <<EOF > "$OUTDIR/clinvar.vcf"
##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=CLNSIG,Number=.,Type=String,Description="Clinical significance">
##INFO=<ID=CLNDN,Number=.,Type=String,Description="Clinical disease name">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	100	rs123	A	G	100	PASS	CLNSIG=Pathogenic;CLNDN=Test_Disease
EOF
bgzip -c "$OUTDIR/clinvar.vcf" > "$CLINVAR"
tabix -p vcf "$CLINVAR"

# 3. Create a dummy input VCF that matches the ClinVar entry
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	100	.	A	G	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF ClinVar Smoke Test"
echo "--------------------------------------------------------"

# 4. Run clinvar command
# We need to point --ref to our fake ref dir so it finds the clinvar vcf
uv run wgsextract vcf clinvar \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR"

if [ $? -eq 0 ] && [ -f "$OUTDIR/clinvar_pathogenic.vcf.gz" ]; then
    echo "✅ Success: 'vcf clinvar' completed and produced pathogenic output."
    # Check if annotation worked
    zgrep "CLNSIG" "$OUTDIR/clinvar_annotated.vcf.gz" | grep -q "Pathogenic"
    if [ $? -eq 0 ]; then
        echo "✅ Success: Annotation confirmed."
    else
        echo "❌ Failure: Annotation missing in output."
        exit 1
    fi
else
    echo "❌ Failure: 'vcf clinvar' failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF ClinVar Smoke Test: PASSED"
echo "========================================================"
