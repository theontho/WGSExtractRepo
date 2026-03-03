#!/bin/bash
# Uninstall dependencies for macOS using Homebrew

set -e

echo "Uninstalling dependencies..."
brew uninstall samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes openjdk python3

echo "Uninstallation complete."
