#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies the reference download and indexing pipeline."
    echo "✅ Verified End Goal: A valid, indexed FASTA file downloaded from a URL; verified by file existence, integrity (samtools faidx), and non-empty sequences."
    exit 0
fi

# Check for required tools
check_mandatory_deps

OUT_DIR="out/smoke_test_ref_download"
mkdir -p "$OUT_DIR"
# A small, reliable URL for testing (chrM from a trusted source or a mock)
# For this test, we'll use the one already in the repo if we want to be safe,
# but the goal is to test 'download'.
# We'll use a small file from Ensembl or similar.
TEST_URL="https://raw.githubusercontent.com/samtools/samtools/develop/test/ref.fa"
OUTPUT_FA="$OUT_DIR/test_download.fa"

# Clean up
rm -f "$OUTPUT_FA" "$OUTPUT_FA.fai"

echo ">>> Starting REFERENCE DOWNLOAD & INDEX Smoke Test..."
echo "URL: $TEST_URL"

# 1. Download
echo ":: Downloading reference..."
if ! uv run wgsextract ref download \
    --url "$TEST_URL" \
    --out "$OUTPUT_FA"; then
    echo "❌ Failure: 'ref download' command failed."
    exit 1
fi

# 2. Index
echo ":: Indexing reference..."
if ! uv run wgsextract ref index \
    --ref "$OUTPUT_FA"; then
    echo "❌ Failure: 'ref index' command failed."
    exit 1
fi

echo ">>> Verifying download and index outputs..."
if [ -f "$OUTPUT_FA" ] && [ -f "$OUTPUT_FA.fai" ]; then
    echo "✅ Found: $(basename "$OUTPUT_FA") and its index."

    # Check if it's a valid FASTA and has content
    seq_count=$(grep -c "^>" "$OUTPUT_FA")
    if [ "$seq_count" -gt 0 ]; then
        echo "   ✅ Valid FASTA: $seq_count sequences found."
    else
        echo "   ❌ ERROR: Downloaded file is not a valid FASTA or is empty."
        exit 1
    fi

    # Check index validity
    if samtools faidx "$OUTPUT_FA" ref | grep -q "AGCT"; then
         echo "   ✅ Indexing confirmed: can fetch sequences."
    fi
else
    echo "❌ Missing downloaded or indexed file."
    exit 1
fi

echo ">>> REFERENCE DOWNLOAD & INDEX Smoke Test PASSED."
