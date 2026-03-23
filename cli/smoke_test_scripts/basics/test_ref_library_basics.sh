#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Manages the local reference library, adding and removing reference genomes."
    echo "End Goal: Updated library metadata and accessible reference paths; verified by successful completion of 'ref library-list' and 'ref gene-map' commands."
    exit 0
fi

OUTDIR="out/smoke_test_ref_library"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Ref Library Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'ref library-list' (Interactive, we send 0 to exit)
echo ":: Testing 'ref library-list' (exit immediately)..."
if echo "0" | uv run wgsextract ref library-list --ref "$OUTDIR"; then
    echo "✅ Success: 'ref library-list' exited gracefully."
else
    echo "❌ Failure: 'ref library-list' failed."
    exit 1
fi

# 2. Test 'ref library' (Interactive, we send 0 to exit)
echo ":: Testing 'ref library' (exit immediately)..."
if echo "0" | uv run wgsextract ref library --ref "$OUTDIR"; then
    echo "✅ Success: 'ref library' exited gracefully."
else
    echo "❌ Failure: 'ref library' failed."
    exit 1
fi

# 3. Test 'ref gene-map' (Non-interactive if we use delete or if it's new)
# We won't actually download unless we want to wait, but we can test the command structure.
# Let's try to 'delete' them even if they don't exist.
echo ":: Testing 'ref gene-map --delete'..."
if uv run wgsextract ref gene-map --delete --ref "$OUTDIR"; then
    echo "✅ Success: 'ref gene-map' command finished."
else
    echo "❌ Failure: 'ref gene-map' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Ref Library Basics Smoke Test: PASSED"
echo "========================================================"
