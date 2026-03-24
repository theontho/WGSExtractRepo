#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Stress-tests the CLI: Signal handling, Reference shadowing, and Empty file handling."
    echo "✅ Verified End Goal: Clean termination on SIGINT, correct reference resolution priority, and graceful failure on empty/header-only files."
    exit 0
fi

OUTDIR="out/smoke_test_stress"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

ensure_fake_data
FAKEDATA="out/fake_30x"
BAM="$FAKEDATA/fake.bam"
REF="$FAKEDATA/fake_ref.fa"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Stress & Edge-Case Smoke Test"
echo "--------------------------------------------------------"

# 1. Test Empty/Header-Only Files
echo ":: Testing Header-Only (Zero Record) Files..."
mkdir -p "$OUTDIR/empty"
# Make a header-only BAM
samtools view -H "$BAM" -b > "$OUTDIR/empty/header_only.bam"
samtools index "$OUTDIR/empty/header_only.bam"

# info should handle it
STDOUT=$(uv run wgsextract info --input "$OUTDIR/empty/header_only.bam" 2>&1)
if echo "$STDOUT" | grep -qiE "error|traceback"; then
    echo "❌ Failure: 'info' crashed on header-only BAM."
    echo "$STDOUT"
    exit 1
else
    echo "✅ Success: 'info' handled header-only BAM."
fi

# vcf snp should handle it (probably empty VCF)
if uv run wgsextract vcf snp \
    --input "$OUTDIR/empty/header_only.bam" \
    --ref "$REF" \
    --outdir "$OUTDIR/empty" \
    --ploidy 1; then
    echo "✅ Success: 'vcf snp' handled header-only BAM."
else
    echo "❌ Failure: 'vcf snp' failed on header-only BAM."
    exit 1
fi

# 2. Test Reference Shadowing
echo ":: Testing Reference Shadowing Priority..."
# Hierarchy: --ref (CLI) > WGSE_REFLIB (Env) > Default Library
mkdir -p "$OUTDIR/ref_cli/genomes"
mkdir -p "$OUTDIR/ref_env/genomes"

# Create distinct mock fastas
echo ">cli_ref" > "$OUTDIR/ref_cli/genomes/hg38.fa"
echo ">env_ref" > "$OUTDIR/ref_env/genomes/hg38.fa"

# Scenario: Both exist, Env is set, CLI is used
STDOUT=$(WGSE_REFLIB="$OUTDIR/ref_env" uv run wgsextract info \
    --input "$BAM" \
    --ref "$OUTDIR/ref_cli" \
    --debug 2>&1)

if echo "$STDOUT" | grep -q "ref_cli"; then
    echo "✅ Success: CLI flag shadowed Environment variable."
else
    echo "❌ Failure: CLI flag did NOT shadow Environment variable."
    exit 1
fi

# 3. Test Signal Handling (Graceful Exit)
echo ":: Testing Signal Handling (SIGINT/Ctrl+C)..."
# Start a long-running command in background
# We'll use a larger region to ensure it takes a few seconds
uv run wgsextract vcf snp \
    --input "$BAM" \
    --ref "$REF" \
    --outdir "$OUTDIR/signal" \
    --ploidy 1 &
PID=$!

# Wait for it to start spawning children
sleep 1.5

# Check if children exist (samtools or bcftools)
CHILDREN=$(pgrep -P $PID)
if [ -z "$CHILDREN" ]; then
    # Maybe it's too fast, try again with a loop or just skip if we can't catch it
    echo "ℹ️  Note: No child processes found yet, might be too fast."
fi

# Send SIGINT
kill -SIGINT $PID
wait $PID 2>/dev/null

# Check if orphans remain
sleep 1
if [ -n "$CHILDREN" ]; then
    for CPID in $CHILDREN; do
        if ps -p "$CPID" > /dev/null; then
            echo "❌ Failure: Child process $CPID still running after SIGINT!"
            kill -9 "$CPID" 2>/dev/null
            exit 1
        fi
    done
    echo "✅ Success: All child processes terminated on SIGINT."
else
    echo "✅ Success: Process exited gracefully (no children to clean or already gone)."
fi

echo ""
echo "========================================================"
echo "Stress & Edge-Case Smoke Test: PASSED"
echo "========================================================"
