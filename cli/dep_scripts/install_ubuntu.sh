#!/bin/bash
# Install dependencies for Ubuntu/Debian/Mint

set -e

echo "Updating APT repositories..."
sudo apt-get update

echo "Installing dependencies..."
sudo apt-get install -y samtools bcftools tabix bwa minimap2 fastp fastqc delly freebayes libensembl-vep-perl openjdk-17-jre python3 python3-pip

echo "Core tools installed."
echo "NOTE: GATK and DeepVariant are not available in standard Ubuntu repositories."
echo "For these tools, we recommend using the Conda installer (install_linux_conda.sh)."

echo "Installation complete."
