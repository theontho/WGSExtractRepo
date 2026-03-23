#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests reference genome management commands: download, index, count-ns, and verify."
    echo "End Goal: A verified reference genome with valid index files."
    exit 0
fi

OUTDIR="out/smoke_test_ref_basics"
FAKEREFDIR="$OUTDIR/fakeref"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$FAKEREFDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Ref Management Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Generate small fake reference
echo ":: Generating small fake reference..."
uv run wgsextract qc fake-data \
    --outdir "$FAKEREFDIR" \
    --build hg38 \
    --type fastq \
    --coverage 0.0001 \
    --seed 123 \
    --ref "$FAKEREFDIR" # Passing dir without fasta forces creation

REF_PATH=$(find "$FAKEREFDIR" -name "fake_ref_hg38_*.fa" | head -n 1)

if [ ! -f "$REF_PATH" ]; then
    echo "❌ Failure: Fake reference generation failed."
    exit 1
fi

# 2. Test 'ref download' (using local http server as source)
echo ":: Testing 'ref download'..."
# Start a local HTTP server in the background
python3 -m http.server 8080 --directory "$(dirname "$REF_PATH")" > /dev/null 2>&1 &
HTTP_PID=$!

# Give it a moment to start
sleep 2

if uv run wgsextract ref download \
    --url "http://localhost:8080/$(basename "$REF_PATH")" \
    --out "$OUTDIR/downloaded.fa" && [ -f "$OUTDIR/downloaded.fa" ]; then
    kill "$HTTP_PID"
    echo "✅ Success: 'ref download' completed."
else
    kill "$HTTP_PID"
    echo "❌ Failure: 'ref download' failed."
    exit 1
fi

# 3. Test 'ref index'
echo ":: Testing 'ref index'..."
if uv run wgsextract ref index \
    --ref "$OUTDIR/downloaded.fa" && [ -f "$OUTDIR/downloaded.fa.fai" ]; then
    echo "✅ Success: 'ref index' completed."
else
    echo "❌ Failure: 'ref index' failed."
    exit 1
fi

# 4. Test 'ref count-ns'
echo ":: Testing 'ref count-ns'..."
if uv run wgsextract ref count-ns \
    --ref "$OUTDIR/downloaded.fa"; then
    echo "✅ Success: 'ref count-ns' completed."
else
    echo "❌ Failure: 'ref count-ns' failed."
    exit 1
fi

# 5. Test 'ref verify'
echo ":: Testing 'ref verify'..."
if uv run wgsextract ref verify \
    --ref "$OUTDIR/downloaded.fa"; then
    echo "✅ Success: 'ref verify' completed."
else
    echo "❌ Failure: 'ref verify' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "Ref Management Basics Smoke Test: PASSED"
echo "========================================================"
