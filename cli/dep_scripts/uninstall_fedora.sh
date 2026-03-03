#!/bin/bash
# Uninstall dependencies for Fedora/RHEL/CentOS

set -e

echo "Uninstalling dependencies..."
dnf remove -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes openjdk python3 python3-pip

echo "Uninstallation complete."
