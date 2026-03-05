"""Centralized help texts for WGS Extract CLI and UI."""

# Base help texts shared by all interfaces
HELP_TEXTS = {
    "info": "Perform a rapid analysis of your BAM/CRAM file to identify the reference genome build, file integrity, and sequencing metrics.",
    "calculate-coverage": "Generate a full breadth-of-coverage report. This accurately calculates how much of the genome was successfully sequenced (takes 1-3 hours).",
    "coverage-sample": "Quickly estimate sequencing coverage using statistical sampling. Provides a 'good enough' estimate in under 10 seconds.",
    "align": "Map raw FASTQ reads to a reference genome. This is the primary step to convert raw data into a usable BAM/CRAM file.",
    "sort": "Sort alignments by genomic coordinates. Required by almost all downstream tools (like variant callers) to function correctly.",
    "index": "Create a random-access index (.bai/.crai) for your file. This allows tools to jump to specific regions instantly without reading the whole file.",
    "unindex": "Remove the index file associated with your BAM/CRAM. Use this to force a re-indexing or to clean up workspace.",
    "unsort": "Mark the file as 'unsorted' in the header. Rarely needed, but useful if a tool requires a specific header state for processing.",
    "to-cram": "Convert BAM to the modern CRAM format. Highly recommended for long-term storage as it is ~30-50% smaller than BAM without losing data.",
    "to-bam": "Convert a CRAM file back to the traditional BAM format. Useful if you need to use an older tool that doesn't support CRAM.",
    "unalign": "Extract raw reads from a BAM/CRAM back into FASTQ format. Use this if you want to re-align your data to a different reference genome.",
    "subset": "Create a smaller version of your BAM file using a random fraction of reads (e.g. 0.1 for 10 percent). Useful for testing pipelines quickly.",
    "mt-extract": "Isolate all mitochondrial reads into a dedicated file. Perfect for focused mtDNA analysis or haplogroup prediction.",
    "repair-ftdna-bam": "Fix formatting errors specific to Family Tree DNA (FTDNA) BAM files that cause them to fail in standard tools like GATK.",
    "repair-ftdna-vcf": "Fix formatting errors in FTDNA VCF files to make them compatible with modern annotation tools like VEP.",
    "mito": "Directly extract the mitochondrial (chrM) sequence from your file.",
    "ydna": "Extract all Y-chromosome reads. Useful for males to perform detailed paternal lineage analysis.",
    "unmapped": "Extract reads that did not align to the reference. Often used to find viral contamination or non-human DNA.",
    "custom": "Extract reads from a specific chromosomal region or gene of interest.",
    "snp": "Call Single Nucleotide Polymorphisms (SNPs) using bcftools. Best for standard ancestry analysis and finding simple point mutations.",
    "indel": "Call Small Insertions and Deletions (InDels) using bcftools. Used to find small gaps or extra bases in the DNA sequence.",
    "sv": "Call Structural Variants (SVs) using Delly. Identifies large-scale DNA changes (over 50bp) like inversions, translocations, and large deletions.",
    "cnv": "Call Copy Number Variants (CNVs) using Delly. Detects large regions of DNA that have been duplicated or deleted, affecting gene dosage.",
    "freebayes": "A Bayesian genetic variant detector. Excellent for finding small variants in complex regions or when you have variable sequencing depth.",
    "gatk": "Industry-standard GATK HaplotypeCaller. Best for high-accuracy clinical-grade SNP and InDel calling using local de novo assembly.",
    "deepvariant": "Google's Deep Learning variant caller. Highly recommended for 30x+ WGS; uses a neural network to achieve superior accuracy by 'looking' at read alignments as images.",
    "annotate": "Add external metadata (like population frequencies or disease risk) to your VCF file.",
    "filter": "Filter your results. Use this to focus on specific genes of interest or to remove low-quality 'noisy' variant calls.",
    "trio": "Analyze inheritance patterns. Compares a child's VCF with their parents to identify de novo (new) mutations or inherited conditions.",
    "vcf-qc": "Generate statistical reports for your VCF file to check the quality and distribution of your variant calls.",
    "vep-run": "Ensembl Variant Effect Predictor. Predicts the functional impact of your variants (e.g., if a mutation likely breaks a gene or causes a specific disease).",
    "vep-download": "Download the VEP cache (standard GRCh37/38) to your local machine for faster, offline annotation.",
    "vep-verify": "Check your existing VEP cache for missing files or corruption.",
    "microarray": "Simulate a consumer microarray (like 23andMe or AncestryDNA) from your WGS data for use with older ancestry tools.",
    "lineage-y": "Predict your paternal haplogroup using the Yleaf tool. Requires a BAM with Y-chromosome reads.",
    "lineage-mt": "Predict your maternal haplogroup using Haplogrep. Requires a BAM with mitochondrial reads.",
    "fastqc": "The industry-standard quality check for raw reads. Produces a visual report of base quality, GC content, and adapter contamination.",
    "fastp": "An ultra-fast all-in-one pre-processor. Automatically trims adapters and filters low-quality reads while generating a QC report.",
    "ref-identify": "Analyze your BAM header to determine exactly which reference genome was used for the original alignment.",
    "ref-index": "Prepare a FASTA file for use by indexing it. This is required before you can align reads or call variants against it.",
    "ref-download": "Download curated, standard-compliant reference genomes (hg19, hg38, T2T) optimized for use with this tool.",
    "ref-verify": "Ensure your reference genome file isn't corrupted and has all the necessary companion files (indexes, dicts).",
    "ref-count-ns": "Calculate the percentage of 'N' (unknown) bases in a genome. Useful for understanding the 'mappability' of different reference builds.",
    "ref-download-genes": "Download lightweight gene-to-coordinate mapping files, enabling you to filter VCFs by gene name (e.g. BRCA1).",
    "ref-library": "Opens the interactive reference manager to help you organize and download genomic data.",
}

# Specialized UI tooltips (more descriptive for non-technical users)
UI_TOOLTIPS = HELP_TEXTS.copy()
UI_TOOLTIPS.update(
    {
        "ref-library": "Opens the interactive reference manager. Note: This will run in your terminal window.",
    }
)
