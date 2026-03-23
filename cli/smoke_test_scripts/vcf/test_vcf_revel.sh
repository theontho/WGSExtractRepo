#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Annotates missense variants with REVEL pathogenicity scores."
    echo "Verified End Goal: VCF with REVEL scores in the INFO field."
    exit 0
fi

OUTDIR="out/vcf_revel_out"
mkdir -p "$OUTDIR"

# 1. Create a fake reference structure
REFDIR="$OUTDIR/fake_ref_revel"
mkdir -p "$REFDIR/ref"
mkdir -p "$REFDIR/genomes"
echo ">chr1" > "$REFDIR/genomes/fake_hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REFDIR/genomes/fake_hg38.fa"
# Compress it so ReferenceLibrary finds it (it expects .gz)
bgzip -c "$REFDIR/genomes/fake_hg38.fa" > "$REFDIR/genomes/hg38.fa.gz"
# Index it
samtools faidx "$REFDIR/genomes/hg38.fa.gz"

# 2. Create a dummy REVEL TSV.gz
# Annovar REVEL format: #Chr, Start, End, Ref, Alt, Score
REVEL_TSV="$REFDIR/ref/revel_hg38.tsv.gz"
cat <<EOF > "$OUTDIR/revel.tsv"
#Chr	Start	End	Ref	Alt	Score
chr1	100	100	A	G	0.85
chr1	200	200	C	T	0.45
EOF
bgzip -c "$OUTDIR/revel.tsv" > "$REVEL_TSV"
tabix -s 1 -b 2 -e 2 "$REVEL_TSV"

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
echo "  WGS Extract CLI: VCF REVEL Smoke Test"
echo "--------------------------------------------------------"

# 4. Run revel command (Annotation only)
echo ":: Running REVEL annotation..."
if uv run wgsextract vcf revel \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/revel_annotated.vcf.gz" ]; then
    echo "✅ Success: 'vcf revel' completed."
    # Check if annotation worked
    if zgrep "REVEL=0.85" "$OUTDIR/revel_annotated.vcf.gz" | grep -q "."; then
        echo "✅ Success: Annotation confirmed (REVEL=0.85 found)."
    else
        echo "❌ Failure: REVEL annotation missing in output."
        zgrep -v "^#" "$OUTDIR/revel_annotated.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: 'vcf revel' failed or missing output."
    exit 1
fi

# 5. Run revel command (with Filtering)
echo ":: Running REVEL annotation + filtering (score >= 0.5)..."
if uv run wgsextract vcf revel \
    --input "$INPUT_VCF" \
    --ref "$REFDIR" \
    --outdir "$OUTDIR" \
    --min-score 0.5 && [ -f "$OUTDIR/revel_gt_0.5.vcf.gz" ]; then
    echo "✅ Success: REVEL filtering produced output."
    # Should only have chr1:100 (0.85), not chr1:200 (0.45)
    COUNT=$(zgrep -v "^#" "$OUTDIR/revel_gt_0.5.vcf.gz" | wc -l)
    if [ "$COUNT" -eq 1 ]; then
        echo "✅ Success: Filtered correctly (1 variant remains)."
    else
        echo "❌ Failure: Incorrect number of variants after filter ($COUNT)."
        zgrep -v "^#" "$OUTDIR/revel_gt_0.5.vcf.gz"
        exit 1
    fi
else
    echo "❌ Failure: REVEL filtering failed or missing output."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF REVEL Smoke Test: ALL PASSED"
echo "========================================================"
