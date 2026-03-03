#!/bin/bash
# Install dependencies for Ubuntu/Debian/Mint

set -e

echo "Updating APT repositories..."
sudo apt-get update

echo "Installing dependencies..."
sudo apt-get install -y samtools bcftools htslib-test bwa minimap2 fastp fastqc delly freebayes libensembl-vep-perl openjdk-17-jre python3 python3-pip

echo "Installation complete."
