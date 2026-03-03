#!/bin/bash
# Hybrid uninstall: Homebrew for core tools, Conda for VEP (macOS)
set -e

REMOVE_CONDA=false
for arg in "$@"; do
    if [ "$arg" == "--remove-conda" ]; then
        REMOVE_CONDA=true
    fi
done

# Get the directory of the current script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Step 1: Removing Ensembl VEP via Conda..."
if command -v conda &> /dev/null; then
    conda remove -y ensembl-vep || true
fi

if [ "$REMOVE_CONDA" = true ]; then
    if command -v brew &> /dev/null && brew list --cask miniconda &> /dev/null; then
        echo "Removing Miniconda via Homebrew..."
        brew uninstall --cask miniconda
    elif [ -d "$HOME/miniconda" ]; then
        echo "Removing Miniconda directory: $HOME/miniconda..."
        rm -rf "$HOME/miniconda"
    fi
fi

echo "Step 2: Uninstalling core tools via Homebrew..."
bash "$DIR/uninstall_macos.sh"

echo "Hybrid uninstallation complete."
