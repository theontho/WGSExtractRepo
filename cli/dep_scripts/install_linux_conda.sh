#!/bin/bash
# Install dependencies for Linux using Conda

set -e

SKIP_CONDA=false
for arg in "$@"; do
    if [ "$arg" == "--skip-conda" ]; then
        SKIP_CONDA=true
    fi
done

if [ "$SKIP_CONDA" = false ]; then
    if ! command -v conda &> /dev/null; then
        echo "Conda not found. Installing Miniconda..."
        curl -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
        bash miniconda.sh -b -p "$HOME/miniconda"
        rm miniconda.sh
        source "$HOME/miniconda/bin/activate"
        conda init bash
    else
        echo "Conda is already installed."
    fi
fi

echo "Installing dependencies via Conda..."
conda install -y -c bioconda -c conda-forge samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Installation complete."
