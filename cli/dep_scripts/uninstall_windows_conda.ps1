# Uninstall dependencies via Conda (PowerShell)

$ErrorActionPreference = "Stop"

echo "Uninstalling tools from Conda..."
conda remove -y samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Uninstallation complete."
