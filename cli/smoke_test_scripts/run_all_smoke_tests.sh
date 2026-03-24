#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/common.sh"

# Configuration
GLOBAL_START_TIME=$(date +%s)
FAKE_DIR="out/fake_30x"
LOG_DIR="out/smoke_test_logs"
mkdir -p "$FAKE_DIR"
mkdir -p "$LOG_DIR"

# Handle Ctrl+C (SIGINT) and SIGTERM
exit_on_signal() {
    echo ""
    echo "⚠️  Received signal, terminating all tests..."
    exit 130
}
trap exit_on_signal SIGINT SIGTERM

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
    "test_ref_databases.sh"
    "test_web_gui_basics.sh"
    "test_repair_basics.sh"
    "test_pet_basics.sh"
    "test_vep_basics.sh"
    "test_lineage_basics.sh"
    "test_microarray_basics.sh"
    "test_misc_basics.sh"
    "test_pixi_fallback.sh"
    "test_ref_download_index.sh"
    "test_build_detection_robustness.sh"
    "test_mixed_chrom_naming.sh"
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
    "test_vcf_trio_inheritance.sh"
    "test_vcf_clinvar.sh"
    "test_vcf_revel.sh"
    "test_vcf_phylop.sh"
    "test_vcf_gnomad.sh"
    "test_vcf_pathogenicity_new.sh"
    "test_vcf_chain_annotate.sh"
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

RUN_REAL_DATA=false
for arg in "$@"; do
    if [[ "$arg" == "--real-data" ]]; then
        RUN_REAL_DATA=true
    fi
done
export WGSE_USE_REAL_DATA=$RUN_REAL_DATA

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
    describe_group "Real Data" "real_data" \
        "test_vcf_real_ref_db.sh" \
        "test_vcf_trio_real.sh" \
        "test_vcf_microarray.sh" \
        "test_vcf_vep.sh" \
        "test_vcf_clinical_full.sh" \
        "test_vcf_calling_full.sh" \
        "test_vcf_sv_cnv_full.sh" \
        "test_cram_microarray.sh" \
        "test_mito_ydna_full.sh" \
        "test_lineage_full.sh" \
        "test_align_full.sh" \
        "test_pet_align_full.sh" \
        "test_ref_robustness_full.sh" \
        "test_low_coverage_microarray.sh"

    exit 0
fi

# 1. Prepare shared fake data if missing
ensure_fake_data

run_test_group() {
    local group_name=$1
    local group_dir=$2
    shift 2
    local tests=("$@")

    echo ""
    echo "--- Running Group: $group_name ---"
    for test_script in "${tests[@]}"; do
        echo -n ":: Running $test_script... "
        local start_time
        start_time=$(date +%s)
        ./smoke_test_scripts/"$group_dir"/"$test_script" > "$LOG_DIR/${test_script}.log" 2>&1
        local exit_code=$?
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        # Check if we were interrupted by SIGINT (Ctrl+C)
        if [ $exit_code -eq 130 ]; then
            echo "❌ INTERRUPTED"
            exit 130
        fi

        # Format duration
        local duration_fmt
        if [ $duration -ge 60 ]; then
            duration_fmt="$((duration / 60))m $((duration % 60))s"
        else
            duration_fmt="${duration}s"
        fi

        if [ $exit_code -eq 0 ]; then
            echo "✅ PASSED ($duration_fmt)"
        elif [ $exit_code -eq 77 ]; then
            local skip_reason
            skip_reason=$(grep -o '([a-zA-Z ]*)' "$LOG_DIR/${test_script}.log" | tail -n 1)
            if [ -n "$skip_reason" ]; then
                echo "⏭️  SKIPPED $skip_reason ($duration_fmt)"
            else
                echo "⏭️  SKIPPED ($duration_fmt)"
            fi
        else
            echo "❌ FAILED (Check $LOG_DIR/${test_script}.log) ($duration_fmt)"
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

# Run Real Data Workflows if requested and configured
if [ "$RUN_REAL_DATA" = true ]; then
    run_test_group "Real Data (Base)" "real_data" \
        "test_vcf_real_ref_db.sh" \
        "test_vcf_trio_real.sh"

    if [ -n "$WGSE_INPUT_VCF" ] && [ -n "$WGSE_REF" ]; then
        run_test_group "Real Data (VCF)" "real_data" \
            "test_vcf_microarray.sh" \
            "test_vcf_vep.sh" \
            "test_vcf_clinical_full.sh" \
            "test_vcf_calling_full.sh" \
            "test_vcf_sv_cnv_full.sh"
    else
        echo ""
        echo ":: Skipping Real Data VCF tests (WGSE_INPUT_VCF not set)"
    fi

    if [ -n "$WGSE_INPUT" ] && [ -n "$WGSE_REF" ]; then
        run_test_group "Real Data (BAM/CRAM)" "real_data" \
            "test_cram_microarray.sh" \
            "test_mito_ydna_full.sh" \
            "test_lineage_full.sh" \
            "test_ref_robustness_full.sh" \
            "test_low_coverage_microarray.sh"
    else
        echo ""
        echo ":: Skipping Real Data BAM/CRAM tests (WGSE_INPUT not set)"
    fi

    if [ -n "$WGSE_FASTQ_R1" ] && [ -n "$WGSE_REF" ]; then
        run_test_group "Real Data (Alignment)" "real_data" \
            "test_align_full.sh"
    else
        echo ""
        echo ":: Skipping Real Data Alignment tests (WGSE_FASTQ_R1 not set)"
    fi

    if [ -n "$WGSE_PET_R1" ] && [ -n "$WGSE_PET_REF" ]; then
        run_test_group "Real Data (Pet)" "real_data" \
            "test_pet_align_full.sh"
    else
        echo ""
        echo ":: Skipping Real Data Pet tests (WGSE_PET_R1 not set)"
    fi
else
    echo ""
    echo "--- Skipping Group: Real Data (Use --real-data to run) ---"
fi

echo ""
echo "========================================================"
echo "  All Smoke Tests Completed."
GLOBAL_END_TIME=$(date +%s)
TOTAL_DURATION=$((GLOBAL_END_TIME - GLOBAL_START_TIME))

if [ $TOTAL_DURATION -ge 60 ]; then
    TOTAL_DURATION_FMT="$((TOTAL_DURATION / 60))m $((TOTAL_DURATION % 60))s"
else
    TOTAL_DURATION_FMT="${TOTAL_DURATION}s"
fi

echo "  Total Execution Time: $TOTAL_DURATION_FMT"
echo "  Logs available in: $LOG_DIR"
echo "========================================================"
