#!/bin/bash

# Configuration for Nura VEP Run
PERSON="mahyar"
GENOMES_DIR="/Users/mac/Documents/genetics/genomes/"
BASE_DIR="${GENOMES_DIR}/${PERSON}"
INPUT_DIR="${BASE_DIR}/vcf"
OUTPUT_DIR="${BASE_DIR}/vep_output"
FASTA="/Users/mac/Documents/genetics/WGSExtract/WGSExtractv4/reference/genomes/hs38DH.fa.gz"
CACHE_DIR="/Users/mac/.vep"
CACHE_VERSION="115"
THREADS="4"

echo "Starting VEP Batch Processing for Mahyar..."
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "------------------------------------------------------------"

# Using the new batch-aware wgsextract vep command
# --vcf-type auto will detect snp-indel, sv, or cnv from filenames
# --add-chr handles the chromosome prefixing automatically
wgsextract vep \
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
