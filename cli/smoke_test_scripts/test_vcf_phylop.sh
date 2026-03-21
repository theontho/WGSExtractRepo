#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

OUTDIR="out/vcf_phylop_out"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_phylop"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
# Compress it so ReferenceLibrary finds it (it expects .gz)
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
# Index it
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create a dummy PhyloP TSV.gz
# Annovar PhyloP format: #Chr, Start, End, Score
PHYLOP_TSV="$REFDIR/ref/phylop_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/phylop.tsv"
#Chr	Start	End	Score
chr1	100	100	2.5
chr1	200	200	0.5
EOF
bgzip -c "$OUTDIR/phylop.tsv" > "$PHYLOP_TSV"
tabix -s 1 -b 2 -e 2 "$PHYLOP_TSV"

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
echo "  WGS Extract CLI: VCF PhyloP Smoke Test"
echo "--------------------------------------------------------"

# 4. Run phylop command (Annotation only)
echo ":: Running PhyloP annotation..."
uv run wgsextract vcf phylop \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR"

if [ $? -eq 0 ] && [ -f "$OUTDIR/phylop_annotated.vcf.gz" ]; then
    echo "✅ Success: 'vcf phylop' completed."
    # Check if annotation worked
    VAL=$(zgrep "PHYLOP=2.5" "$OUTDIR/phylop_annotated.vcf.gz")
    if [ -n "$VAL" ]; then
        echo "✅ Success: Annotation confirmed (PHYLOP=2.5 found)."
    else
        echo "❌ Failure: PhyloP annotation missing in output."
        zgrep -v "^#" "$OUTDIR/phylop_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: 'vcf phylop' failed or missing output."
    exit 1
fi

# 5. Run phylop command (with Filtering)
echo ":: Running PhyloP annotation + filtering (score >= 2.0)..."
uv run wgsextract vcf phylop \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" \
    --min-score 2.0

if [ $? -eq 0 ] && [ -f "$OUTDIR/phylop_gt_2.0.vcf.gz" ]; then
    echo "✅ Success: PhyloP filtering produced output."
    # Should only have chr1:100 (2.5), not chr1:200 (0.5)
    COUNT=$(zgrep -v "^#" "$OUTDIR/phylop_gt_2.0.vcf.gz" | wc -l)
    if [ "$COUNT" -eq 1 ]; then
        echo "✅ Success: Filtered correctly (1 variant remains)."
    else
        echo "❌ Failure: Incorrect number of variants after filter ($COUNT)."
        zgrep -v "^#" "$OUTDIR/phylop_gt_2.0.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: PhyloP filtering failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF PhyloP Smoke Test: ALL PASSED"
echo "========================================================"
