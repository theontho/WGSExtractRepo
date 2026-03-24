#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies CLI handles file paths with spaces and special characters."
    echo "✅ Verified End Goal: Successful execution of basic commands using paths containing spaces; verified by stdout presence."
    exit 0
fi

# We use a path with spaces and a common special character like '#' or '@'
SPECIAL_DIR="out/space test dir @#"
rm -rf "$SPECIAL_DIR"
mkdir -p "$SPECIAL_DIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Special Path Smoke Test"
echo "--------------------------------------------------------"

# 1. Prepare fake data in the special path
# We'll copy existing fake data to avoid full generation
ensure_fake_data
FAKEDATA="out/fake_30x"
SPECIAL_BAM="$SPECIAL_DIR/fake data.bam"
cp "$FAKEDATA/fake.bam" "$SPECIAL_BAM"
cp "$FAKEDATA/fake.bam.bai" "$SPECIAL_BAM.bai"

echo ":: Testing 'bam identify' with spaces in path..."
if uv run wgsextract bam identify --input "$SPECIAL_BAM" > "$SPECIAL_DIR/identify.log" 2>&1; then
    if grep -q "MD5 Signature" "$SPECIAL_DIR/identify.log"; then
        echo "✅ Success: 'bam identify' worked with spaces."
    else
        echo "❌ Failure: 'bam identify' output missing info."
        cat "$SPECIAL_DIR/identify.log"
        exit 1
    fi
else
    echo "❌ Failure: 'bam identify' failed with spaces."
    cat "$SPECIAL_DIR/identify.log"
    exit 1
fi

# 2. Test 'info' command
echo ":: Testing 'info' with spaces in path..."
if uv run wgsextract info --input "$SPECIAL_BAM" --outdir "$SPECIAL_DIR/info out" > "$SPECIAL_DIR/info.log" 2>&1; then
    echo "✅ Success: 'info' worked with spaces."
else
    echo "❌ Failure: 'info' failed with spaces."
    cat "$SPECIAL_DIR/info.log"
    exit 1
fi

# 3. Test 'extract custom' (simplest subprocess pipe test)
echo ":: Testing 'extract custom' with spaces in path..."
if uv run wgsextract extract custom \
    --input "$SPECIAL_BAM" \
    --outdir "$SPECIAL_DIR/extract out" \
    --region "chr1:1-1000" > "$SPECIAL_DIR/extract.log" 2>&1; then
    echo "✅ Success: 'extract custom' worked with spaces."
else
    echo "❌ Failure: 'extract custom' failed with spaces."
    cat "$SPECIAL_DIR/extract.log"
    exit 1
fi

echo ""
echo "========================================================"
echo "Special Path Smoke Test: PASSED"
echo "========================================================"
