#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests DeepVariant integration for variant calling."
    echo "End Goal: High-accuracy VCF output from DeepVariant.; verified by existence of output file."
    exit 0
fi

# Configuration (Hardcode to fake data for smoke test)
INPUT_BAM="$(realpath out/fake_30x/fake.bam)"
REF_FASTA="$(realpath out/fake_30x/fake_ref.fa)"
CHECKPOINT_BASE="reference/models/deepvariant/WGS/deepvariant.wgs.ckpt"
OUTDIR="$(realpath out/smoke_test_vcf_deepvariant)"
REGION="chr1:1-5000"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Ensure models exist
if [ ! -f "${CHECKPOINT_BASE}.index" ]; then
    echo ":: DeepVariant model not found, running setup..."
    chmod +x scripts/setup_vcf_resources.sh
    ./scripts/setup_vcf_resources.sh
fi

CHECKPOINT_DIR="$(realpath "$(dirname "$CHECKPOINT_BASE")")"
CHECKPOINT="$CHECKPOINT_DIR/$(basename "$CHECKPOINT_BASE")"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF DeepVariant Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Checkpoint: $CHECKPOINT"
echo "--------------------------------------------------------"

# Check if deepvariant is installed
check_deps run_deepvariant

if uv run wgsextract vcf deepvariant \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --checkpoint "$CHECKPOINT" \
    --outdir "$OUTDIR" \
    --region "$REGION" && [ -f "$OUTDIR/deepvariant.vcf.gz" ]; then
    echo "SUCCESS: VCF DeepVariant completed."
    ls -lh "$OUTDIR/deepvariant.vcf.gz"
else
    echo "FAILURE: VCF DeepVariant failed."
    exit 1
fi
