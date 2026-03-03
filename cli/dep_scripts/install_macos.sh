#!/bin/bash
# Install dependencies for macOS using Homebrew

set -e

echo "Installing core tools and aligners..."
brew install samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes openjdk python3

echo "Core tools installed. NOTE: Ensembl VEP is NOT available via standard Homebrew on macOS."
echo "If you need VEP, please install it manually (https://github.com/Ensembl/ensembl-vep) or use the Conda installer."

echo "Installation complete."
