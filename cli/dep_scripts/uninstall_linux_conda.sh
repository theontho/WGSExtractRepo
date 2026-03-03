#!/bin/bash
# Uninstall dependencies for Linux using Conda

set -e

echo "Uninstalling dependencies via Conda..."
conda remove -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Uninstallation complete."
