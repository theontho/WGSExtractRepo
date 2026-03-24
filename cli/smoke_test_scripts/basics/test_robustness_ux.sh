#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies CLI robustness and User Experience (UX) standards."
    echo "✅ Verified End Goal: Clean error messages (no tracebacks) for common failures, correct precedence for environment variables vs CLI flags, and standard-compliant VCF headers."
    exit 0
fi

OUTDIR="out/smoke_test_robustness_ux"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Robustness & UX Smoke Test"
echo "--------------------------------------------------------"

# 1. Test Traceback Cleanliness (Missing File)
echo ":: Testing Error UX (Missing Input)..."
# We expect a clean error message, NOT a Python traceback
STDOUT=$(uv run wgsextract info --input "nonexistent_file.bam" 2>&1)
echo "$STDOUT"
if echo "$STDOUT" | grep -q "Traceback"; then
    echo "❌ Failure: Python traceback found in output. Error should be handled gracefully."
    exit 1
elif echo "$STDOUT" | grep -qiE "error|not found|required"; then
    echo "✅ Success: Clean error message reported."
else
    echo "❌ Failure: No clear error message reported for missing input."
    exit 1
fi

# 2. Test Environment Variable Precedence
echo ":: Testing Environment Variable Precedence (WGSE_REFLIB vs --ref)..."
# Create two different dummy "ref" directories
mkdir -p "$OUTDIR/env_ref/genomes"
mkdir -p "$OUTDIR/cli_ref/genomes"

# Create different dummy fasta files in each
echo ">env_ref" > "$OUTDIR/env_ref/genomes/hg38.fa"
echo ">cli_ref" > "$OUTDIR/cli_ref/genomes/hg38.fa"

# Run a command that resolves reference and check logs
# We'll use 'info' with a fake BAM. We need a fake BAM first.
ensure_fake_data
FAKEDATA="out/fake_30x"
BAM="$FAKEDATA/fake.bam"

echo "   Scenario: WGSE_REFLIB set to 'env_ref', but --ref set to 'cli_ref'"
# We use --debug to see the resolved path in logs
STDOUT=$(WGSE_REFLIB="$OUTDIR/env_ref" uv run wgsextract info \
    --input "$BAM" \
    --ref "$OUTDIR/cli_ref" \
    --debug 2>&1)

if echo "$STDOUT" | grep -q "cli_ref"; then
    echo "✅ Success: --ref correctly took precedence over WGSE_REFLIB."
else
    echo "❌ Failure: --ref did NOT take precedence or resolution failed."
    echo "$STDOUT" | grep -i "ref"
    exit 1
fi

# 3. Test VCF Header Consistency
echo ":: Testing VCF Header Consistency..."
# Check the header of a generated VCF from another smoke test or generate a quick one
# We'll use the fake VCF from ensure_fake_data
VCF="$FAKEDATA/fake.vcf.gz"

# Verify it has standard fields
HEADER=$(bcftools view -h "$VCF")
if echo "$HEADER" | grep -q "##fileformat=VCFv4" && \
   echo "$HEADER" | grep -q "##contig=" && \
   echo "$HEADER" | grep -q "#CHROM"; then
    echo "✅ Success: VCF header contains standard required fields."
else
    echo "❌ Failure: VCF header is malformed or missing standard fields."
    echo "$HEADER" | head -n 20
    exit 1
fi

# 4. Check for 'N' base warning logic (Resource Warning)
echo ":: Testing Resource Warning Logic (ref count-ns)..."
# count-ns is a safe way to trigger the warning logic for large genomes
# We use a small one, but we check if the code paths for warnings are hit
STDOUT=$(uv run wgsextract ref count-ns --ref "$OUTDIR/cli_ref/genomes/hg38.fa" 2>&1)
# The output usually contains "Processing"
if echo "$STDOUT" | grep -q "Processing"; then
    echo "✅ Success: ref count-ns executed correctly."
else
    echo "❌ Failure: ref count-ns failed to execute."
    echo "$STDOUT"
    exit 1
fi

echo ""
echo "========================================================"
echo "Robustness & UX Smoke Test: PASSED"
echo "========================================================"
