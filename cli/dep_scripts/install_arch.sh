#!/bin/bash
# Install dependencies for Arch Linux/Manjaro

set -e

echo "Updating Pacman repositories..."
pacman -Syu --noconfirm

echo "Installing dependencies..."
pacman -S --noconfirm samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes jre17-openjdk python python-pip

echo "Installation complete."
