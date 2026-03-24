#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Verifies build detection when BAM/CRAM headers lack build information (e.g., missing AS: in @SQ)."
    echo "✅ Verified End Goal: Correct identification of genome build (hg38/hg19) via sequence length matching or other heuristics, verified by 'info' output."
    exit 0
fi

# Check for required tools
check_mandatory_deps
ensure_fake_data

OUT_DIR="out/smoke_test_build_robustness"
mkdir -p "$OUT_DIR"

# 1. Create a BAM with 'stripped' build info
echo ":: Creating test BAM with missing build info (no AS tags)..."
STRIPPED_BAM="$OUT_DIR/stripped.bam"
# Take the fake BAM and strip AS tags from @SQ lines
samtools view -H out/fake_30x/fake.bam | sed 's/\tAS:[^\t]*//g' | samtools reheader - out/fake_30x/fake.bam > "$STRIPPED_BAM"
samtools index "$STRIPPED_BAM"

echo ">>> Starting BUILD DETECTION ROBUSTNESS Smoke Test..."
echo "Input: $STRIPPED_BAM (Stripped of AS: tags)"

# 2. Run 'info' to trigger detection
DETECTION_LOG="$OUT_DIR/detection_info.txt"
uv run wgsextract info \
    --input "$STRIPPED_BAM" \
    --ref out/fake_30x \
    --outdir "$OUT_DIR" > "$DETECTION_LOG" 2>&1

# 3. Verify
echo ">>> Verifying build detection..."
if grep -qE "Reference Genome.*hg38" "$DETECTION_LOG"; then
    echo "   ✅ Success: Correctly detected 'hg38' via chromosome lengths/heuristics."
else
    echo "❌ Failure: Could not correctly detect build (Expected hg38)."
    cat "$DETECTION_LOG"
    exit 1
fi

echo ">>> BUILD DETECTION ROBUSTNESS Smoke Test PASSED."
