# Install dependencies via Conda (PowerShell)

param (
    [switch]$SkipConda
)

$ErrorActionPreference = "Stop"

if (-not $SkipConda) {
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        echo "Conda not found. Please install Miniconda manually on Windows or use WSL2."
        # Automatic silent install on Windows is more complex, pointing user to manual install for now.
        exit 1
    }
}

echo "Updating Conda environments and installing tools..."
conda install -y -c bioconda -c conda-forge samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Installation complete."
