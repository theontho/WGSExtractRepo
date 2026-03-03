# Uninstall dependencies via Conda (PowerShell)

param (
    [switch]$RemoveConda
)

$ErrorActionPreference = "Stop"

echo "Uninstalling tools from Conda..."
if (Get-Command conda -ErrorAction SilentlyContinue) {
    conda remove -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python
}

if ($RemoveConda) {
    echo "Note: Automatic removal of Conda installation directory on Windows is not supported by this script."
    echo "Please uninstall Miniconda/Anaconda manually via 'Apps & Features' or by deleting its installation folder."
} else {
    echo "Note: Conda was NOT removed. Use -RemoveConda to see instructions for deletion."
}

echo "Uninstallation complete."
