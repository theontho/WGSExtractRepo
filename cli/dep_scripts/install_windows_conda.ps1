# Install dependencies via Conda (PowerShell)

$ErrorActionPreference = "Stop"

echo "Updating Conda environments and installing tools..."
conda install -y -c bioconda -c conda-forge samtools bcftools htslib bwa minimap2 fastp fastqc delly freebayes ensembl-vep openjdk python

echo "Installation complete."
