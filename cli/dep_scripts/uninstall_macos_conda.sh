#!/bin/bash
# Uninstall dependencies for macOS using Conda

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
    if command -v brew &> /dev/null && brew list --cask miniconda &> /dev/null; then
        echo "Removing Miniconda via Homebrew..."
        brew uninstall --cask miniconda
    elif [ -d "$HOME/miniconda" ]; then
        echo "Removing Miniconda directory: $HOME/miniconda..."
        rm -rf "$HOME/miniconda"
    elif [ -d "$HOME/opt/miniconda3" ]; then
        echo "Removing Miniconda directory: $HOME/opt/miniconda3..."
        rm -rf "$HOME/opt/miniconda3"
    else
        echo "Miniconda installation directory not found (checked brew, $HOME/miniconda, $HOME/opt/miniconda3)."
    fi
    echo "Note: You may still have conda initialization code in your ~/.zshrc or ~/.bash_profile."
else
    echo "Note: Conda was NOT removed. Use --remove-conda to delete the Conda installation."
fi

echo "Uninstallation complete."
