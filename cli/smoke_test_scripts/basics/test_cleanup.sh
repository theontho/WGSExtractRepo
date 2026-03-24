#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies that CLI cleans up intermediate temporary files after execution."
    echo "✅ Verified End Goal: No .tmp or .temp files/directories remaining in the output folder after a complex command; verified by 'find' checks."
    exit 0
fi

OUTDIR="out/smoke_test_cleanup"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Cleanup Smoke Test"
echo "--------------------------------------------------------"

# We use 'vcf snp' as it uses multiple intermediate steps (mpileup | call | view)
ensure_fake_data
FAKEDATA="out/fake_30x"
BAM="$FAKEDATA/fake.bam"
REF="$FAKEDATA/fake_ref.fa"

echo ":: Running 'vcf snp'..."
if uv run wgsextract vcf snp \
    --input "$BAM" \
    --ref "$REF" \
    --outdir "$OUTDIR" \
    --region "chr1:1-10000" \
    --ploidy 1; then
    echo "✅ Success: Command finished."

    # Check for leftovers
    # Note: We look for common patterns like *.tmp, *.temp, *_temp
    LEFTOVERS=$(find "$OUTDIR" -name "*.tmp*" -o -name "*.temp*" -o -name "*_temp*" | grep -v "logs")

    if [ -n "$LEFTOVERS" ]; then
        echo "❌ Failure: Temporary files found in output directory:"
        echo "$LEFTOVERS"
        exit 1
    else
        echo "✅ Success: No temporary files found."
    fi
else
    echo "❌ Failure: Command failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Cleanup Smoke Test: PASSED"
echo "========================================================"
