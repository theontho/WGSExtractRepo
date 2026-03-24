#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests reference database download commands for all supported databases."
    echo "✅ Verified End Goal: All reference download commands (ClinVar, REVEL, etc.) correctly respond to --help and are registered in the CLI."
    exit 0
fi

OUTDIR="out/smoke_test_ref_databases"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Ref Database Commands Smoke Test"
echo "--------------------------------------------------------"

DB_CMDS=("clinvar" "revel" "phylop" "gnomad" "spliceai" "alphamissense" "pharmgkb")

for cmd in "${DB_CMDS[@]}"; do
    echo ":: Testing 'ref $cmd --help'..."
    if uv run wgsextract ref "$cmd" --help > "$OUTDIR/ref_${cmd}_help.stdout" 2>&1; then
        echo "✅ Success: 'ref $cmd --help' completed."
    else
        echo "❌ Failure: 'ref $cmd --help' failed."
        exit 1
    fi
done

echo ""
echo "========================================================"
echo "Ref Database Commands Smoke Test: PASSED"
echo "========================================================"
