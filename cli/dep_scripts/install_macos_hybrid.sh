#!/bin/bash
# Hybrid install: Homebrew for core tools, Conda for VEP (macOS)
set -e

SKIP_CONDA=false
for arg in "$@"; do
    if [ "$arg" == "--skip-conda" ]; then
        SKIP_CONDA=true
    fi
done

# Get the directory of the current script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Step 1: Installing core tools via Homebrew..."
bash "$DIR/install_macos.sh"

echo "Step 2: Installing Ensembl VEP via Conda..."
if [ "$SKIP_CONDA" = false ]; then
    if ! command -v conda &> /dev/null; then
        if command -v brew &> /dev/null; then
            echo "Conda not found. Installing Miniconda via Homebrew..."
            brew install --cask miniconda
            # Initialize for the current shell
            export PATH="/usr/local/anaconda3/bin:/usr/local/minioconda/bin:/opt/homebrew/anaconda3/bin:/opt/homebrew/miniconda/bin:$PATH"
            conda init bash
        else
            echo "Conda and Homebrew not found. Installing Miniconda via curl..."
            ARCH=$(uname -m)
            curl -L "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-$ARCH.sh" -o miniconda.sh
            bash miniconda.sh -b -p "$HOME/miniconda"
            rm miniconda.sh
            source "$HOME/miniconda/bin/activate"
            conda init bash
        fi
    else
        echo "Conda is already installed."
    fi
fi

echo "Creating dedicated environment for VEP and DeepVariant (Intel/osx-64) to avoid Apple Silicon crashes..."
CONDA_SUBDIR=osx-64 conda create -y -n vep_env -c conda-forge -c bioconda ensembl-vep deepvariant

echo "Hybrid installation complete."
echo "To run VEP or DeepVariant, you must first run: conda activate vep_env"
