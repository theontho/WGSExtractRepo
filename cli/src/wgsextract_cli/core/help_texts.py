"""Centralized help texts for WGS Extract CLI and UI."""

# Base help texts shared by all interfaces
HELP_TEXTS = {
    "info": "Parses header, verifies coordinate sorting, calculates stats and detects reference genome signature.",
    "calculate-coverage": "Calculate FULL breadth coverage using samtools depth (1-3 hours).",
    "coverage-sample": "Estimate coverage using random sampling (under 10 seconds).",
    "align": "Align FASTQ reads to a reference model using BWA or Minimap2.",
    "sort": "Sort a BAM or CRAM file by coordinate.",
    "index": "Creates a BAM or CRAM index file.",
    "unindex": "Deletes the index file associated with the BAM/CRAM.",
    "unsort": "Changes the coordinate-sorted status in the BAM header to 'unsorted'.",
    "to-cram": "Convert BAM to CRAM (requires reference).",
    "to-bam": "Convert CRAM to BAM.",
    "unalign": "Converts aligned reads back to raw FASTQ files.",
    "subset": "Creates a random subset of a BAM file (requires fraction).",
    "mt-extract": "Extract mitochondrial (mtDNA) reads to a separate BAM.",
    "repair-ftdna-bam": "Repair formatting violations in FTDNA BAM files.",
    "repair-ftdna-vcf": "Repair formatting violations in FTDNA VCF files.",
    "mito": "Extract mitochondrial reads.",
    "ydna": "Extract Y-chromosome reads.",
    "unmapped": "Extract unmapped reads.",
    "custom": "Extract reads from a specific chromosomal region.",
    "snp": "Call SNPs using bcftools.",
    "indel": "Call InDels using bcftools.",
    "sv": "Call Structural Variants using delly.",
    "cnv": "Call Copy Number Variants using delly.",
    "freebayes": "Call variants using freebayes.",
    "gatk": "Call variants using GATK HaplotypeCaller.",
    "deepvariant": "Call variants using DeepVariant model.",
    "annotate": "Annotate VCF with external data.",
    "filter": "Filter VCF using expressions or genes.",
    "trio": "Inheritance analysis on a family trio.",
    "vcf-qc": "Variant call quality control stats.",
    "vep-run": "Run Ensembl Variant Effect Predictor.",
    "vep-download": "Download VEP cache for offline use.",
    "vep-verify": "Verify existing VEP cache integrity.",
    "microarray": "Generates a simulated microarray CombinedKit for ancestry tools.",
    "lineage-y": "Run Yleaf Y-DNA haplogroup prediction.",
    "lineage-mt": "Run Haplogrep MT-DNA haplogroup prediction.",
    "fastqc": "Run FastQC quality control.",
    "fastp": "Run fastp for adapter trimming and QC.",
    "ref-identify": "Automatically detect the reference genome used.",
    "ref-index": "Create FASTA index (.fai) and BWA/samtools indexes.",
    "ref-download": "Download common reference genomes (hg19, hg38).",
    "ref-verify": "Verify integrity of reference FASTA file.",
    "ref-count-ns": "Analyzes reference FASTA to count N segments.",
    "ref-download-genes": "Downloads lightweight gene mapping files (hg19/hg38).",
    "ref-library": "Interactive reference library manager to download genomes.",
}

# Specialized UI tooltips (more descriptive for non-technical users)
UI_TOOLTIPS = HELP_TEXTS.copy()
UI_TOOLTIPS.update(
    {
        "info": "Performs a detailed analysis of your BAM/CRAM file to identify the reference genome, sequencer type, and bio-gender. (Runs in --detailed mode)",
        "ref-library": "Opens the interactive reference manager. Note: This will run in your terminal window.",
        "custom": "Extracts reads from a chromosomal region you specify (e.g., 'chr1:1000-5000').",
        "vcf-qc": "Generates statistical reports for your VCF file using bcftools stats.",
    }
)
