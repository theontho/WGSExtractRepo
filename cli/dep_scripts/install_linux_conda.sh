#!/bin/bash
# Install dependencies for Linux using Conda

set -e

echo "Installing dependencies via Conda..."
conda install -y -c bioconda -c conda-forge samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Installation complete."
