#!/bin/bash
# Install dependencies for macOS using Conda

set -e

SKIP_CONDA=false
for arg in "$@"; do
    if [ "$arg" == "--skip-conda" ]; then
        SKIP_CONDA=true
    fi
done

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

echo "Installing dependencies via Conda..."
echo "NOTE: On Apple Silicon, Ensembl VEP requires an Intel (osx-64) environment to avoid segmentation faults."

# Create a dedicated environment for bioinformatics tools to avoid conflicts with base Python
CONDA_SUBDIR=osx-64 conda create -y -n wgse -c conda-forge -c bioconda ensembl-vep samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes openjdk python=3.12

echo "Installation complete. To use these tools, run: conda activate wgse"
