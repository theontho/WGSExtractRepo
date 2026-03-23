#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Detailed test of the 'vcf vep' command wrapper."
    echo "🌕 End Goal: VCF output with full VEP annotations."
    exit 0
fi

PERSON="byron"
GENOMES_DIR="${HOME}/Documents/genetics/genomes"
BASE_DIR="${GENOMES_DIR}/${PERSON}"
INPUT_DIR="${BASE_DIR}/vcf"
OUTPUT_DIR="out/vep_output"
FASTA="${HOME}/Documents/genetics/WGSExtract/WGSExtractv4/reference/genomes/hs38DH.fa.gz"
CACHE_DIR="${HOME}/.vep"
CACHE_VERSION="115"
THREADS="4"

echo "Starting VEP Batch Processing for ${PERSON}..."
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "------------------------------------------------------------"

# Check dependencies
check_deps vep

# Using the new batch-aware wgsextract vep command
# --vcf-type auto will detect snp-indel, sv, or cnv from filenames
# --add-chr handles the chromosome prefixing automatically
uv run wgsextract vep \
  --input "$INPUT_DIR" \
  --outdir "$OUTPUT_DIR" \
  --ref "$FASTA" \
  --vep-cache "$CACHE_DIR" \
  --vep-cache-version "$CACHE_VERSION" \
  --threads "$THREADS" \
  --add-chr \
  --vcf-type auto \
  --format vcf

echo "------------------------------------------------------------"
echo "Batch processing complete. Check $OUTPUT_DIR for results."
