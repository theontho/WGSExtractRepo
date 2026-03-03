#!/bin/bash
# Install dependencies for Fedora/RHEL/CentOS

set -e

echo "Installing dependencies via DNF..."
dnf install -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes openjdk python3 python3-pip

echo "Installation complete."
