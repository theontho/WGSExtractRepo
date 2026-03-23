#!/bin/bash

# common.sh: Shared functions for WGS Extract CLI smoke tests

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common paths for bioinformatics tools
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

# Function to check for required tools and exit with 77 (SKIP) if any are missing
check_deps() {
    local missing=()
    for tool in "$@"; do
        if ! command -v "$tool" &> /dev/null; then
            missing+=("$tool")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "⏭️  SKIP: Missing required tools: ${missing[*]}"
        exit 77
    fi
}

# Function to check for mandatory tools (samtools, bcftools, tabix, bgzip, bwa)
check_mandatory_deps() {
    check_deps samtools bcftools tabix bgzip bwa
}

# Function to ensure shared fake data exists
ensure_fake_data() {
    local FAKE_DIR="out/fake_30x"
    mkdir -p "$FAKE_DIR"

    if [ ! -f "$FAKE_DIR/fake.bam" ] || [ ! -f "$FAKE_DIR/fake_ref.fa" ]; then
        echo ":: [Common] Shared fake data missing or incomplete. Generating (10x scaled hg38)..."
        uv run wgsextract qc fake-data \
            --outdir "$FAKE_DIR" \
            --build hg38 \
            --type bam,vcf,fastq \
            --coverage 10.0 \
            --seed 123 \
            --ref "$FAKE_DIR"

        # Ensure generic names exist for tests
        local FASTA
        FASTA=$(find "$FAKE_DIR" -name "fake_ref_hg38_*.fa" 2>/dev/null | head -n 1)
        if [ -n "$FASTA" ] && [ -f "$FASTA" ]; then
            cp "$FASTA" "$FAKE_DIR/fake_ref.fa"
            cp "$FASTA" "$FAKE_DIR/fake_ref_hg38_scaled.fa"
        fi
    fi

    if [ -f "$FAKE_DIR/fake_ref.fa" ] && [ ! -f "$FAKE_DIR/fake_ref.fa.fai" ]; then
        echo ":: [Common] Indexing fake reference..."
        uv run wgsextract ref index --ref "$FAKE_DIR/fake_ref.fa"
    fi
}
