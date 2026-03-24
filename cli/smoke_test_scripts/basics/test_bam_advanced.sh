#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests advanced BAM operations: unalign (FASTQ extraction), unindex, and unsort."
    echo "✅ Verified End Goal: Valid FASTQ files from BAM, removed index files, and reheadered unsorted BAM."
    exit 0
fi

OUTDIR="out/smoke_test_bam_advanced"
FAKEDATA="out/smoke_test_qc_fake/hg38"

# Ensure fake data exists
ensure_fake_data

# Ensure output directory is clean
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: BAM Advanced Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'bam unalign' (BAM to FASTQ)
echo ":: Testing 'bam unalign'..."
if uv run wgsextract bam unalign \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" \
    --r1 "unaligned_R1.fastq.gz" \
    --r2 "unaligned_R2.fastq.gz" && \
    verify_fastq "$OUTDIR/unaligned_R1.fastq.gz" && \
    verify_fastq "$OUTDIR/unaligned_R2.fastq.gz"; then
    echo "✅ Success: bam unalign completed and verified."
else
    echo "❌ Failure: bam unalign failed or verification failed."
    exit 1
fi

# 2. Test 'bam unindex'
echo ":: Testing 'bam unindex'..."
cp "$FAKEDATA/fake.bam" "$OUTDIR/test_unindex.bam"
# Create index first
uv run wgsextract bam index --input "$OUTDIR/test_unindex.bam"
if [ -f "$OUTDIR/test_unindex.bam.bai" ]; then
    echo "   Index created. Now removing..."
    if uv run wgsextract bam unindex --input "$OUTDIR/test_unindex.bam" && [ ! -f "$OUTDIR/test_unindex.bam.bai" ]; then
        echo "✅ Success: bam unindex completed."
    else
        echo "❌ Failure: bam unindex failed to remove index."
        exit 1
    fi
else
    echo "❌ Failure: Could not create index for unindex test."
    exit 1
fi

# 3. Test 'bam unsort'
echo ":: Testing 'bam unsort'..."
if uv run wgsextract bam unsort \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR" && \
    [ -f "$OUTDIR/fake_unsorted.bam" ]; then
    # Check header
    if samtools view -H "$OUTDIR/fake_unsorted.bam" | grep -q "SO:unsorted"; then
        echo "✅ Success: bam unsort completed and header verified."
    else
        echo "❌ Failure: bam unsort header does not say SO:unsorted."
        samtools view -H "$OUTDIR/fake_unsorted.bam" | grep "SO:"
        exit 1
    fi
else
    echo "❌ Failure: bam unsort failed."
    exit 1
fi

# 4. Test --gene for bam unalign
echo ":: Testing 'bam unalign' with --gene..."
mkdir -p "$OUTDIR/ref"
echo -e "symbol\tchrom\tstart\tend" > "$OUTDIR/ref/genes_hg38.tsv"
echo -e "GENE1\tchr1\t1\t10000" >> "$OUTDIR/ref/genes_hg38.tsv"

if WGSE_REFLIB="$OUTDIR" uv run wgsextract bam unalign \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR/unalign_gene" \
    --gene "GENE1" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" \
    --r1 "gene_R1.fastq.gz" \
    --r2 "gene_R2.fastq.gz" && \
    verify_fastq "$OUTDIR/unalign_gene/gene_R1.fastq.gz"; then
    echo "✅ Success: 'bam unalign --gene' completed."
else
    echo "❌ Failure: 'bam unalign --gene' failed."
    exit 1
fi

# 5. Test --gene for bam sort (which acts as a regional extractor + sorter)
echo ":: Testing 'bam sort' with --gene..."
if WGSE_REFLIB="$OUTDIR" uv run wgsextract bam sort \
    --input "$FAKEDATA/fake.bam" \
    --outdir "$OUTDIR/sort_gene" \
    --gene "GENE1" \
    --ref "$FAKEDATA/fake_ref_hg38_scaled.fa" && \
    verify_bam "$OUTDIR/sort_gene/fake_sorted.bam"; then
    echo "✅ Success: 'bam sort --gene' completed."
else
    echo "❌ Failure: 'bam sort --gene' failed."
    exit 1
fi

echo ""
echo "========================================================"
echo "BAM Advanced Smoke Test: PASSED"
echo "========================================================"
