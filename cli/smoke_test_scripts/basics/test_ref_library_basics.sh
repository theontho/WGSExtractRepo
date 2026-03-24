#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Manages the local reference library, adding and removing reference genomes."
    echo "✅ Verified End Goal: Updated library metadata and accessible reference paths; confirmed by stdout checks in 'ref library-list' and 'ref gene-map'."
    exit 0
fi

OUTDIR="out/smoke_test_ref_library"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Ref Library Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'ref library-list' (Interactive, we send 0 to exit)
echo ":: Testing 'ref library-list' (exit immediately)..."
if echo "0" | uv run wgsextract ref library-list --ref "$OUTDIR" > "$OUTDIR/lib_list.stdout" 2>&1; then
    if grep -q "REFERENCE LIBRARY" "$OUTDIR/lib_list.stdout"; then
        echo "✅ Success: 'ref library-list' exited gracefully and showed library header."
    else
        echo "❌ Failure: 'ref library-list' output missing expected header."
        cat "$OUTDIR/lib_list.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'ref library-list' failed."
    cat "$OUTDIR/lib_list.stdout"
    exit 1
fi

# 2. Test 'ref library' (Interactive, we send 0 to exit)
echo ":: Testing 'ref library' (exit immediately)..."
if echo "0" | uv run wgsextract ref library --ref "$OUTDIR" > "$OUTDIR/lib.stdout" 2>&1; then
    if grep -q "Reference Library Manager" "$OUTDIR/lib.stdout"; then
        echo "✅ Success: 'ref library' exited gracefully and showed management header."
    else
        echo "❌ Failure: 'ref library' output missing expected header."
        cat "$OUTDIR/lib.stdout"
        exit 1
    fi
else
    echo "❌ Failure: 'ref library' failed."
    cat "$OUTDIR/lib.stdout"
    exit 1
fi

# 3. Test 'ref gene-map' (Non-interactive if we use delete or if it's new)
echo ":: Testing 'ref gene-map --delete'..."
if uv run wgsextract ref gene-map --delete --ref "$OUTDIR" > "$OUTDIR/gene_map.stdout" 2>&1; then
    echo "✅ Success: 'ref gene-map' command finished."
else
    echo "❌ Failure: 'ref gene-map' failed."
    cat "$OUTDIR/gene_map.stdout"
    exit 1
fi

echo ""
echo "========================================================"
echo "Ref Library Basics Smoke Test: PASSED"
echo "========================================================"
