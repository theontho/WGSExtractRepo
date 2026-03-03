#!/bin/bash
# Uninstall dependencies for Linux using Conda

set -e

REMOVE_CONDA=false
for arg in "$@"; do
    if [ "$arg" == "--remove-conda" ]; then
        REMOVE_CONDA=true
    fi
done

echo "Uninstalling tools from Conda..."
if command -v conda &> /dev/null; then
    conda remove -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python || true
fi

if [ "$REMOVE_CONDA" = true ]; then
    if [ -d "$HOME/miniconda" ]; then
        echo "Removing Miniconda directory: $HOME/miniconda..."
        rm -rf "$HOME/miniconda"
    elif [ -d "$HOME/miniconda3" ]; then
        echo "Removing Miniconda directory: $HOME/miniconda3..."
        rm -rf "$HOME/miniconda3"
    elif [ -d "/opt/miniconda3" ]; then
        echo "Removing Miniconda directory: /opt/miniconda3 (requires sudo)..."
        sudo rm -rf "/opt/miniconda3"
    else
        echo "Miniconda installation directory not found."
    fi
    echo "Note: You may still have conda initialization code in your ~/.bashrc."
else
    echo "Note: Conda was NOT removed. Use --remove-conda to delete the Conda installation."
fi

echo "Uninstallation complete."
