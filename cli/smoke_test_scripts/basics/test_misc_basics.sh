#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests miscellaneous utility commands (e.g., version, help, config)."
    echo "🌕 End Goal: Successful output of utility information; verified by existence of generated sorted/unsorted BAMs, FASTQ files, and VCF statistics."
    exit 0
fi

OUTDIR="out/smoke_test_misc_basics"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
if [ ! -f "$FAKEDATA/fake.bam" ]; then
    echo ":: Generating dependency fake data..."
    chmod +x smoke_test_scripts/test_qc_fake_data.sh
    ./smoke_test_scripts/test_qc_fake_data.sh
fi

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Misc Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. BAM Sort
echo ":: Testing 'bam sort'..."
REF=$(find "$FAKEDATA" -name "fake_ref_hg38_*.fa" | head -n 1)
if uv run wgsextract bam sort \
    --input "$FAKEDATA/fake.bam" \
    --ref "$REF" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/fake_sorted.bam" ]; then
    echo "✅ Success: bam sort completed."
else
    echo "❌ Failure: bam sort failed."
    exit 1
fi

# 2. BAM Unindex
echo ":: Testing 'bam unindex'..."
cp "$OUTDIR/fake_sorted.bam" "$OUTDIR/test_unindex.bam"
touch "$OUTDIR/test_unindex.bam.bai"
if uv run wgsextract bam unindex --input "$OUTDIR/test_unindex.bam" && [ ! -f "$OUTDIR/test_unindex.bam.bai" ]; then
    echo "✅ Success: bam unindex completed."
else
    echo "❌ Failure: bam unindex failed or file still exists."
    exit 1
fi

# 3. BAM Unsort (Name sort)
echo ":: Testing 'bam unsort'..."
if uv run wgsextract bam unsort \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" && [ -f "$OUTDIR/fake_unsorted.bam" ]; then
    echo "✅ Success: bam unsort completed."
else
    echo "❌ Failure: bam unsort failed."
    exit 1
fi

# 4. BAM Unalign (BAM to FASTQ)
echo ":: Testing 'bam unalign'..."
if uv run wgsextract bam unalign \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR/unaligned" \
    --r1 "R1.fastq.gz" \
    --r2 "R2.fastq.gz" && [ -f "$OUTDIR/unaligned/R1.fastq.gz" ]; then
    echo "✅ Success: bam unalign completed."
else
    echo "❌ Failure: bam unalign failed."
    exit 1
fi

# 5. QC VCF
echo ":: Testing 'qc vcf'..."
if uv run wgsextract qc vcf --vcf-input "$FAKEDATA/fake.vcf.gz" --outdir "$OUTDIR" && [ -f "$OUTDIR/fake.vcf.gz.vcfstats.txt" ]; then
    echo "✅ Success: qc vcf completed."
else
    echo "❌ Failure: qc vcf failed."
    ls -R "$OUTDIR"
    exit 1
fi

# 6. BAM Identify
echo ":: Testing 'bam identify'..."
if uv run wgsextract bam identify --input "$FAKEDATA/fake.bam"; then
    echo "✅ Success: bam identify completed."
else
    echo "❌ Failure: bam identify failed."
    exit 1
fi

# 7. Optional QC tools (fastp/fastqc)
if command -v fastp >/dev/null 2>&1; then
    echo ":: Testing 'qc fastp'..."
    if uv run wgsextract qc fastp \
        --r1 "$OUTDIR/unaligned/R1.fastq.gz" \
        --r2 "$OUTDIR/unaligned/R2.fastq.gz" \
        --outdir "$OUTDIR/fastp"; then
        echo "✅ Success: qc fastp completed."
    fi
fi

echo ""
echo "========================================================"
echo "Misc Basics Smoke Test: PASSED"
echo "========================================================"
