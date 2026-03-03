#!/bin/bash
# Hybrid uninstall: Homebrew for core tools, Conda for VEP (macOS)
set -e

# Get the directory of the current script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Step 1: Removing Ensembl VEP via Conda..."
conda remove -y ensembl-vep

echo "Step 2: Uninstalling core tools via Homebrew..."
bash "$DIR/uninstall_macos.sh"

echo "Hybrid uninstallation complete."
