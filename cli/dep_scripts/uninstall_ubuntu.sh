#!/bin/bash
# Uninstall dependencies for Ubuntu/Debian/Mint

set -e

echo "Uninstalling dependencies..."
sudo apt-get remove -y samtools bcftools tabix bwa minimap2 fastp fastqc delly freebayes libensembl-vep-perl openjdk-17-jre python3 python3-pip

echo "Uninstallation complete."
