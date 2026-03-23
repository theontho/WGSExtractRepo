#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Annotates a VCF file with basic metadata and region information."
    echo "End Goal: Annotated VCF with additional INFO fields.; verified by existence of output file."
    exit 0
fi

# Configuration
INPUT_VCF="out/fake_30x/fake.vcf.gz"
REF_FASTA="out/fake_30x/fake_ref.fa"
OUTDIR="out/smoke_test_vcf_annotate"

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

check_mandatory_deps
echo "--------------------------------------------------------"
echo "  WGS Extract CLI: VCF Annotate Smoke Test"
echo "  Input: $(basename "$INPUT_VCF")"
check_mandatory_deps
echo "--------------------------------------------------------"

# Note: Annotate requires --ann-vcf. Since we don't have a small dummy one easily,
# we verify that the command routing and error checking works.
# If we have real data from env, we could use it.

if uv run wgsextract vcf annotate \
    --input "$INPUT_VCF" \
    --ann-vcf "$INPUT_VCF" \
    --ref "$REF_FASTA" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/annotated.vcf.gz" ]; then
    echo "SUCCESS: VCF Annotate completed."
    ls -lh "$OUTDIR/annotated.vcf.gz"
else
    echo "FAILURE: VCF Annotate failed."
    exit 1
fi
