#!/bin/bash

# common.sh: Shared functions for WGS Extract CLI smoke tests

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common system paths for bioinformatics tools
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

# Function to check for required tools and exit with 77 (SKIP) if any are missing
check_deps() {
    local tools=("$@")
    local missing=()

    # Use the CLI itself to check if tools are available (including Pixi fallback)
    # We can check all tools in one go if we wanted to parse output, but for now
    # let's just make sure the loop is efficient.
    for tool in "${tools[@]}"; do
        # Use a faster check if it's already in PATH
        if command -v "$tool" &> /dev/null; then
            continue
        fi

        if ! uv run python3 -m wgsextract_cli.main deps check --tool "$tool" &> /dev/null; then
            missing+=("$tool")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        echo "⏭️  SKIP: (missing dep) Missing required tools: ${missing[*]}"
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
        FASTA=$(find "$FAKE_DIR" -name "fake_ref_hg38_*.fa" | head -n 1)
        if [ -n "$FASTA" ] && [ -f "$FASTA" ]; then
            cp "$FASTA" "$FAKE_DIR/fake_ref.fa"
            cp "$FASTA" "$FAKE_DIR/fake_ref_hg38_scaled.fa"
        fi

        local VCF
        VCF=$(find "$FAKE_DIR" -name "fake_*.vcf.gz" | head -n 1)
        if [ -n "$VCF" ] && [ -f "$VCF" ]; then
            cp "$VCF" "$FAKE_DIR/fake.vcf.gz"
            cp "$VCF.tbi" "$FAKE_DIR/fake.vcf.gz.tbi" 2>/dev/null || true
        fi

        # Generate a dummy map file for CNV tests
        if [ ! -f "$FAKE_DIR/fake.map" ]; then
            echo ">chr1" > "$FAKE_DIR/fake.map"
            # 500kb of 1s (mappable)
            # Using a loop instead of printf to avoid 'argument list too long'
            for _ in {1..50}; do
                printf '1%.0s' {1..10000} >> "$FAKE_DIR/fake.map"
            done
            echo "" >> "$FAKE_DIR/fake.map"
        fi
    fi

    if [ -f "$FAKE_DIR/fake_ref.fa" ] && [ ! -f "$FAKE_DIR/fake_ref.fa.fai" ]; then
        echo ":: [Common] Indexing fake reference..."
        uv run wgsextract ref index --ref "$FAKE_DIR/fake_ref.fa"
    fi
}

# Helper to verify a BAM/CRAM file
verify_bam() {
    local file=$1
    local allow_empty=$2
    if [ ! -f "$file" ]; then
        echo "❌ Failure: BAM/CRAM file missing: $file"
        return 1
    fi
    if ! samtools quickcheck "$file"; then
        echo "❌ Failure: BAM/CRAM file corrupted: $file"
        return 1
    fi
    # Check if it has any reads
    if [ "$allow_empty" != "allow_empty" ] && [ "$allow_empty" != "1" ]; then
        local count
        count=$(samtools view -c "$file")
        if [ "$count" -eq 0 ]; then
            echo "❌ Failure: BAM/CRAM file is empty: $file"
            return 1
        fi
    fi
    return 0
}

# Helper to verify a VCF file
verify_vcf() {
    local file=$1
    local allow_empty=$2
    if [ ! -f "$file" ]; then
        echo "❌ Failure: VCF file missing: $file"
        return 1
    fi
    # Check if it's a valid VCF/BCF
    if ! bcftools view -h "$file" > /dev/null 2>&1; then
        echo "❌ Failure: VCF file is invalid or corrupted: $file"
        return 1
    fi

    # Check if it has any records (excluding header)
    if [ "$allow_empty" != "allow_empty" ] && [ "$allow_empty" != "1" ]; then
        local count
        count=$(bcftools view -H "$file" | head -n 100 | wc -l)
        if [ "$count" -eq 0 ]; then
            echo "❌ Failure: VCF file has no records: $file"
            return 1
        fi
    fi
    return 0
}

# Helper to verify a FASTQ file
verify_fastq() {
    local file=$1
    if [ ! -f "$file" ]; then
        echo "❌ Failure: FASTQ file missing: $file"
        return 1
    fi
    # Check if it has any reads (4 lines per read)
    local lines
    if [[ "$file" == *.gz ]]; then
        lines=$(zcat "$file" | head -n 4 | wc -l)
    else
        lines=$(head -n 4 "$file" | wc -l)
    fi
    if [ "$lines" -lt 4 ]; then
        echo "❌ Failure: FASTQ file is empty or malformed: $file"
        return 1
    fi
    return 0
}
