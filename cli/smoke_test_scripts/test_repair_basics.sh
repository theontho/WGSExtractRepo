#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
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
cat "$OUTDIR/test.sam" | uv run wgsextract repair ftdna-bam > "$OUTDIR/repaired.sam"

if [ $? -eq 0 ] && grep -q "read:1" "$OUTDIR/repaired.sam"; then
    echo "✅ Success: 'repair ftdna-bam' completed and fixed QNAME."
else
    echo "❌ Failure: 'repair ftdna-bam' failed or did not fix QNAME."
    cat "$OUTDIR/repaired.sam"
    exit 1
fi

# 2. Test 'repair ftdna-vcf'
echo ":: Testing 'repair ftdna-vcf'..."
# Create a dummy VCF with illegal FILTER entry (e.g. DP=1)
cat <<EOF > "$OUTDIR/test.vcf"
##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	sample
chr1	100	.	A	G	100	DP=1	.	GT	0/1
EOF

# Run repair.
cat "$OUTDIR/test.vcf" | uv run wgsextract repair ftdna-vcf > "$OUTDIR/repaired.vcf"

if [ $? -eq 0 ] && grep -q "DP1" "$OUTDIR/repaired.vcf"; then
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
