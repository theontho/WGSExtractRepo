#!/bin/bash
# Uninstall dependencies for macOS using Conda

set -e

echo "Uninstalling dependencies via Conda..."
conda remove -y samtools bcftools htslib bwa minimap2 fastp find fastqc delly freebayes ensembl-vep openjdk python

echo "Uninstallation complete."
