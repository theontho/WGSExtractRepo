#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests FASTQ/BAM repair and sanitation tools for corrupted or malformed files."
    echo "Verified End Goal: Cleaned and valid genomic files that can be processed by downstream tools."
    exit 0
fi

OUTDIR="out/smoke_test_repair_basics"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Repair Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'repair ftdna-bam'
echo ":: Testing 'repair ftdna-bam'..."
# Create a dummy SAM with a space in QNAME
cat <<EOF > "$OUTDIR/test.sam"
@HD	VN:1.6	SO:coordinate
@SQ	SN:chr1	LN:1000
read 1	99	chr1	100	60	100M	=	200	100	AAAAAAAAAA	##########
EOF

# Run repair. Input is stdin, output is stdout.
if uv run wgsextract repair ftdna-bam < "$OUTDIR/test.sam" > "$OUTDIR/repaired.sam" && grep -q "read:1" "$OUTDIR/repaired.sam"; then
    echo "✅ Success: 'repair ftdna-bam' completed and fixed QNAME."
else
    echo "❌ Failure: 'repair ftdna-bam' failed or did not fix QNAME."
    cat "$OUTDIR/repaired.sam"
    exit 1
fi

# 2. Test 'repair ftdna-vcf'
echo ":: Testing 'repair ftdna-vcf'..."
# Create a dummy VCF with illegal FILTER entry (e.g. DP=1)
{
    echo "##fileformat=VCFv4.2"
    echo '##FILTER=<ID=PASS,Description="All filters passed">'
    echo '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">'
    echo '##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">'
    echo -e "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample"
    echo -e "chr1\t100\t.\tA\tG\t100\tDP=1\t.\tGT\t0/1"
} > "$OUTDIR/test.vcf"

# Run repair.
if uv run wgsextract repair ftdna-vcf < "$OUTDIR/test.vcf" > "$OUTDIR/repaired.vcf" && grep -q "DP1" "$OUTDIR/repaired.vcf"; then
    echo "✅ Success: 'repair ftdna-vcf' completed and fixed FILTER."
else
    echo "❌ Failure: 'repair ftdna-vcf' failed or did not fix FILTER."
    cat "$OUTDIR/repaired.vcf"
    exit 1
fi

echo ""
echo "========================================================"
echo "Repair Basics Smoke Test: PASSED"
echo "========================================================"
