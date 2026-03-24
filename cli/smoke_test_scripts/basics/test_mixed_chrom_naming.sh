#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies chromosome normalization (e.g., '1' vs 'chr1') when VCF and Reference use different naming conventions."
    echo "✅ Verified End Goal: Successful microarray extraction and VCF processing despite chromosome naming mismatch, verified by non-empty genotypes in output."
    exit 0
fi

# Check for required tools
check_mandatory_deps

OUT_DIR="out/smoke_test_mixed_naming"
mkdir -p "$OUT_DIR"

# 1. Create a reference with '1' and a VCF with 'chr1'
REF_DIR="$OUT_DIR/ref_lib"
mkdir -p "$REF_DIR/genomes"
mkdir -p "$REF_DIR/ref"
echo ">1" > "$REF_DIR/genomes/hg38.fa"
echo "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$REF_DIR/genomes/hg38.fa"
bgzip -c "$REF_DIR/genomes/hg38.fa" > "$REF_DIR/genomes/hg38.fa.gz"
samtools faidx "$REF_DIR/genomes/hg38.fa.gz"

# Create a dummy SNP tab file
SNP_TAB="$REF_DIR/ref/All_SNPs.vcf.gz"
cat <<EOF > "$OUT_DIR/snps.vcf"
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	20	rs123	A	G	100	PASS	.
EOF
bgzip -c "$OUT_DIR/snps.vcf" > "$SNP_TAB"
tabix -p vcf "$SNP_TAB"

INPUT_VCF="$OUT_DIR/input_chr1.vcf.gz"
cat <<EOF > "$OUT_DIR/input.vcf"
##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##contig=<ID=chr1,length=100>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	20	rs123	A	G	100	PASS	.	GT	0/1
EOF
bgzip -c "$OUT_DIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

echo ">>> Starting MIXED CHROMOSOME NAMING Smoke Test..."
echo "Input VCF Chrom: chr1"
echo "Ref Genome Chrom: 1"

# 2. Run microarray extraction
echo ":: Running Microarray extraction (should normalize chr1 to 1 or vice-versa)..."
if uv run wgsextract microarray \
    --input "$INPUT_VCF" \
    --ref "$REF_DIR" \
    --outdir "$OUT_DIR" \
    --formats "23andme_v5" \
    --debug; then


    echo ">>> Verifying output..."
    CKIT=$(find "$OUT_DIR" -name "*CombinedKit.txt" | head -n 1)
    if [ -f "$CKIT" ]; then
        # Check if rs123 was successfully extracted despite naming mismatch
        if grep -q "rs123" "$CKIT" && ! grep "rs123" "$CKIT" | grep -q "NN"; then
            echo "   ✅ Success: rs123 genotype correctly extracted and normalized."
        else
            echo "   ❌ ERROR: rs123 not found in CombinedKit or has 'NN' genotype."
            exit 1
        fi
    else
        echo "   ❌ ERROR: CombinedKit.txt missing."
        exit 1
    fi
else
    echo "❌ Failure: 'microarray' command failed during mixed-naming test."
    exit 1
fi

echo ">>> MIXED CHROMOSOME NAMING Smoke Test PASSED."
