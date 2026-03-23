#!/bin/bash

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

# Configuration
FAKE_DIR="out/fake_30x"
LOG_DIR="out/smoke_test_logs"
mkdir -p "$FAKE_DIR"
mkdir -p "$LOG_DIR"

# List of tests to run (grouped by directory)
BASICS_TESTS=(
    "test_deps_check.sh"
    "test_qc_fake_data.sh"
    "test_bam_basics.sh"
    "test_extract_basics.sh"
    "test_info_coverage.sh"
    "test_align_basics.sh"
    "test_perf_boost.sh"
    "test_ref_basics.sh"
    "test_ref_library_basics.sh"
    "test_repair_basics.sh"
    "test_pet_basics.sh"
    "test_vep_basics.sh"
    "test_lineage_basics.sh"
    "test_microarray_basics.sh"
    "test_misc_basics.sh"
)

VCF_TESTS=(
    "test_vcf_snp.sh"
    "test_vcf_indel.sh"
    "test_vcf_annotate.sh"
    "test_vcf_filter.sh"
    "test_vcf_freebayes.sh"
    "test_vcf_gatk.sh"
    "test_vcf_deepvariant.sh"
    "test_vcf_cnv.sh"
    "test_vcf_sv.sh"
    "test_vcf_trio.sh"
    "test_vcf_clinvar.sh"
    "test_vcf_revel.sh"
    "test_vcf_phylop.sh"
    "test_vcf_gnomad.sh"
    "test_vcf_pathogenicity_new.sh"
    "test_vcf_chain_annotate.sh"
    "test_vcf_real_ref_db.sh"
)

BENCHMARK_TESTS=(
    "test_benchmark_haplogrep.sh"
    "test_benchmark_lineage.sh"
    "test_benchmark_lineage_vcf.sh"
    "test_benchmark_yleaf.sh"
)

echo "========================================================"
echo "  WGS Extract CLI: Master Smoke Test Runner"
echo "========================================================"

if [[ "$1" == "--describe" ]]; then
    echo "Summary of all smoke tests:"
    echo ""
    echo "Definitions:"
    echo "  - Verified End Goal: The smoke test actually looks inside data files, stdout output, or similar to verify it's actually returning correct output."
    echo "  - End Goal: Just checks file existence or a 0 exit code or similar."
    echo ""

    describe_group() {
        local group_name=$1
        local group_dir=$2
        shift 2
        local tests=("$@")

        echo "--- Group: $group_name ---"
        for test_script in "${tests[@]}"; do
            echo ":: $test_script"
            ./smoke_test_scripts/"$group_dir"/"$test_script" --describe
            echo ""
        done
    }

    describe_group "Basics" "basics" "${BASICS_TESTS[@]}"
    describe_group "VCF Workflows" "vcf" "${VCF_TESTS[@]}"
    describe_group "Benchmarks" "benchmarks" "${BENCHMARK_TESTS[@]}"
    describe_group "Real Data" "real_data" "test_vcf_microarray.sh" "test_cram_microarray.sh"

    exit 0
fi

# 1. Prepare shared fake data if missing
if [ ! -f "$FAKE_DIR/fake.bam" ]; then
    echo ":: Generating shared fake data (30x scaled hg38)..."
    uv run wgsextract qc fake-data \
        --outdir "$FAKE_DIR" \
        --build hg38 \
        --type bam,vcf,fastq \
        --coverage 0.1 \
        --seed 123
fi

# Ensure generic names exist for tests
if [ ! -f "$FAKE_DIR/fake_ref.fa" ]; then
    FASTA=$(find "$FAKE_DIR" -name "fake_ref_hg38_*.fa" 2>/dev/null | head -n 1)
    if [ -n "$FASTA" ] && [ -f "$FASTA" ]; then
        cp "$FASTA" "$FAKE_DIR/fake_ref.fa"
        cp "$FASTA" "$FAKE_DIR/fake_ref_hg38_scaled.fa"
    fi
fi

if [ -f "$FAKE_DIR/fake_ref.fa" ] && [ ! -f "$FAKE_DIR/fake_ref.fa.fai" ]; then
    uv run wgsextract ref index --ref "$FAKE_DIR/fake_ref.fa"
fi

run_test_group() {
    local group_name=$1
    local group_dir=$2
    shift 2
    local tests=("$@")

    echo ""
    echo "--- Running Group: $group_name ---"
    for test_script in "${tests[@]}"; do
        echo -n ":: Running $test_script... "
        if ./smoke_test_scripts/"$group_dir"/"$test_script" > "$LOG_DIR/${test_script}.log" 2>&1; then
            echo "✅ PASSED"
        else
            echo "❌ FAILED (Check $LOG_DIR/${test_script}.log)"
        fi
    done
}

# Ensure all scripts are executable
chmod +x smoke_test_scripts/*.sh 2>/dev/null || true
chmod +x smoke_test_scripts/basics/*.sh
chmod +x smoke_test_scripts/vcf/*.sh
chmod +x smoke_test_scripts/benchmarks/*.sh
chmod +x smoke_test_scripts/real_data/*.sh

# Run Basics
run_test_group "Basics" "basics" "${BASICS_TESTS[@]}"

# Run VCF Workflows
run_test_group "VCF Workflows" "vcf" "${VCF_TESTS[@]}"

# Run Benchmarks
run_test_group "Benchmarks" "benchmarks" "${BENCHMARK_TESTS[@]}"

# Run Real Data Workflows if configured
if [ -n "$WGSE_INPUT_VCF" ] && [ -n "$WGSE_REF" ]; then
    run_test_group "Real Data (VCF)" "real_data" "test_vcf_microarray.sh"
else
    echo ""
    echo ":: Skipping Real Data VCF tests (WGSE_INPUT_VCF not set)"
fi

if [ -n "$WGSE_INPUT_CRAM" ] && [ -n "$WGSE_REF" ]; then
    run_test_group "Real Data (CRAM)" "real_data" "test_cram_microarray.sh"
else
    echo ""
    echo ":: Skipping Real Data CRAM tests (WGSE_INPUT_CRAM not set)"
fi

echo ""
echo "========================================================"
echo "  All Smoke Tests Completed."
echo "  Logs available in: $LOG_DIR"
echo "========================================================"
