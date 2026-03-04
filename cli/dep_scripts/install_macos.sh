#!/bin/bash
# Install dependencies for macOS using Homebrew

set -e

echo "Installing core tools and aligners..."
brew install samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes gatk openjdk python3

echo "Core tools installed. NOTE: Ensembl VEP and DeepVariant are NOT available via standard Homebrew on macOS."
echo "If you need VEP or DeepVariant, please use the Conda installer."

echo "Installation complete."
