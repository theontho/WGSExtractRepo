#!/bin/bash
# Uninstall dependencies for Arch Linux/Manjaro

set -e

echo "Uninstalling dependencies..."
pacman -Rs --noconfirm samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes jre17-openjdk python python-pip

echo "Uninstallation complete."
