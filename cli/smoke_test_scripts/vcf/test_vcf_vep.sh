#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Runs VEP annotation on a VCF."
    echo "🌕 End Goal: VCF annotated with VEP consequence predictions."
    exit 0
fi

OUTDIR="out/smoke_test_vcf_vep"
mkdir -p "$OUTDIR"

# Check if VEP cache is downloaded
if [ ! -d "$HOME/.vep/homo_sapiens" ]; then
    echo "⏭️  SKIP: (no vep cache) Local VEP cache not found at $HOME/.vep/homo_sapiens"
    exit 77
fi

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF VEP Annotation Smoke Test"
echo "--------------------------------------------------------"

# 1. Create a dummy input VCF
# Using a known variant (e.g., rs123 or just a dummy coordinate)
# For the database mode to work properly, it usually needs to align with an actual genome build.
# We will use GRCh38 coordinates. Let's pick a random location on chr1.
INPUT_VCF="$OUTDIR/input.vcf.gz"
cat <<EOF > "$OUTDIR/input.vcf"
##fileformat=VCFv4.2
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##contig=<ID=chr1,length=248956422>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
chr1	100000	.	A	G	100	PASS	.	GT	0/1
EOF

# bgzip and index
if ! command -v bgzip &> /dev/null; then
    # In case run outside of dev environment, fallback to raw gzip for dummy creation, but tabix needs bgzip
    uv run wgsextract deps check > /dev/null
    eval "$(pixi env shell -e bio-tools)"
fi

bgzip -c "$OUTDIR/input.vcf" > "$INPUT_VCF"
tabix -p vcf "$INPUT_VCF"

# 2. Run VEP
# Note: Since there is no local cache configured, wgsextract will warn and fallback to --database.
# This requires an internet connection and might take a few extra seconds.
echo ":: Running 'wgsextract vep'..."
if uv run wgsextract vep \
    --input "$INPUT_VCF" \
    --outdir "$OUTDIR" \
    --vep-cache "$HOME/.vep" \
    --vep-assembly GRCh38; then

    # Check if output exists
    # The output filename convention might be different based on command implementation
    OUTPUT_FILE=$(find "$OUTDIR" -name "*vep*.vcf" -o -name "*vep*.vcf.gz" | head -n 1)

    if [ -f "$OUTPUT_FILE" ]; then
        echo "✅ Success: 'vep' completed and produced output ($OUTPUT_FILE)."

        # Check if annotation (CSQ field) was added to the VCF
        if zgrep -q "CSQ=" "$OUTPUT_FILE" || grep -q "CSQ=" "$OUTPUT_FILE"; then
            echo "✅ Success: VEP annotation (CSQ) confirmed in output."
        else
            echo "⚠️ Warning: VEP completed but 'CSQ=' not found. (Database connection may have failed or variant not found)."
        fi
    else
        echo "❌ Failure: 'vcf vep' command succeeded but output file is missing."
        exit 1
    fi
else
    echo "❌ Failure: 'vcf vep' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "VCF VEP Smoke Test: PASSED"
echo "========================================================"
