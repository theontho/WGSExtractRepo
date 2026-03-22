#!/bin/bash

# Configuration
WGSE_CMD=${WGSE_CMD:-"uv run python -m wgsextract_cli.main"}
LOGFILE="out/smoke_tests.log"
mkdir -p out
echo "=== Smoke Test Run: $(date) ===" > "$LOGFILE"

run_test() {
    echo ":: Running $1..." | tee -a "$LOGFILE"
    bash "$1" >> "$LOGFILE" 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ $1: PASSED" | tee -a "$LOGFILE"
    else
        echo "❌ $1: FAILED" | tee -a "$LOGFILE"
        return 1
    fi
}

FAILED_TESTS=0

# List of smoke tests to run
TESTS=(
    "smoke_test_scripts/test_deps_check.sh"
    "smoke_test_scripts/test_perf_boost.sh"
    "smoke_test_scripts/test_vcf_real_ref_db.sh"
    "smoke_test_scripts/test_align_basics.sh"
    "smoke_test_scripts/test_bam_basics.sh"
    "smoke_test_scripts/test_extract_basics.sh"
)

for t in "${TESTS[@]}"; do
    if [ ! -f "$t" ]; then
        echo "⚠️  Test script not found: $t" | tee -a "$LOGFILE"
        continue
    fi
    run_test "$t" || ((FAILED_TESTS++))
done

echo "--------------------------------------------------------" | tee -a "$LOGFILE"
if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 ALL SMOKE TESTS PASSED!" | tee -a "$LOGFILE"
else
    echo "❌ $FAILED_TESTS SMOKE TEST(S) FAILED. Check $LOGFILE for details." | tee -a "$LOGFILE"
    exit 1
fi
