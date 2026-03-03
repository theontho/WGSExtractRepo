#!/bin/bash
# Hybrid install: Homebrew for core tools, Conda for VEP (macOS)
set -e

# Get the directory of the current script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Step 1: Installing core tools via Homebrew..."
bash "$DIR/install_macos.sh"

echo "Step 2: Installing Ensembl VEP via Conda..."
# Note: This assumes conda is already initialized in the shell
conda install -y -c bioconda -c conda-forge ensembl-vep

echo "Hybrid installation complete."
