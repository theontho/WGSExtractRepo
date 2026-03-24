#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests DeepVariant integration for variant calling."
    echo "✅ Verified End Goal: A valid VCF from DeepVariant; verified by output existence, validity (bcftools), and record presence."
    exit 0
fi

# Configuration
INPUT_BAM="$(realpath out/fake_30x/fake.bam)"
REF_FASTA="$(realpath out/fake_30x/fake_ref.fa)"
OUTDIR="out/smoke_test_vcf_deepvariant"
CHECKPOINT_DIR="$(realpath reference/models/deepvariant/WGS/deepvariant.wgs.ckpt)"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF DeepVariant Smoke Test"
echo "  Input: $(basename "$INPUT_BAM")"
echo "  Checkpoint: $CHECKPOINT_DIR"
echo "--------------------------------------------------------"

# Check dependencies
check_deps run_deepvariant
ensure_fake_data

if uv run wgsextract vcf deepvariant \
    --input "$INPUT_BAM" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" \
    --model WGS && verify_vcf "$OUTDIR/deepvariant.vcf.gz"; then
    echo "SUCCESS: VCF DeepVariant completed."
    ls -lh "$OUTDIR/deepvariant.vcf.gz"

    # Verify tool name in header
    if bcftools view -h "$OUTDIR/deepvariant.vcf.gz" | grep -iq "DeepVariant"; then
        echo "✅ Success: Found 'DeepVariant' in VCF header."
    else
        echo "❌ Failure: 'DeepVariant' NOT found in VCF header."
        exit 1
    fi
else
    echo "FAILURE: VCF DeepVariant failed."
    exit 1
fi
