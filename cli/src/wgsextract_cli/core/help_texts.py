"""Centralized help texts for WGS Extract CLI and UI."""

# Base help texts shared by all interfaces
HELP_TEXTS = {
    "info": "Perform a rapid analysis of your BAM/CRAM file to identify the reference genome build, file integrity, and sequencing metrics. (Time: <1 min)",
    "calculate-coverage": "Generate a full breadth-of-coverage report. This accurately calculates how much of the genome was successfully sequenced. (Time: 1-3 hours, Space: 1-2 GB)",
    "coverage-sample": "Quickly estimate sequencing coverage using statistical sampling. Provides a 'good enough' estimate. (Time: <10 seconds)",
    "align": "Map raw FASTQ reads to a reference genome. This is the primary step to convert raw data into a usable BAM/CRAM file. (Time: 8-160 hours, Space: 150-300 GB)",
    "sort": "Sort alignments by genomic coordinates. Required by almost all downstream tools (like variant callers) to function correctly. (Time: 1-2 hours, Space: Input Size x 2)",
    "index": "Create a random-access index (.bai/.crai) for your file. This allows tools to jump to specific regions instantly without reading the whole file. (Time: 1-5 mins)",
    "unindex": "Remove the index file associated with your BAM/CRAM. Use this to force a re-indexing or to clean up workspace. (Time: instant)",
    "unsort": "Mark the file as 'unsorted' in the header. Rarely needed, but useful if a tool requires a specific header state for processing. (Time: <1 min)",
    "to-cram": "Convert BAM to the modern CRAM format. Highly recommended for long-term storage as it is ~30-50% smaller than BAM without losing data. (Time: 1-2 hours)",
    "to-bam": "Convert a CRAM file back to the traditional BAM format. Useful if you need to use an older tool that doesn't support CRAM. (Time: 1-2 hours)",
    "unalign": "Extract raw reads from a BAM/CRAM back into FASTQ format. Use this if you want to re-align your data to a different reference genome. (Time: 1-2 hours)",
    "subset": "Create a smaller version of your BAM file using a random fraction of reads (e.g. 0.1 for 10 percent). Useful for testing pipelines quickly. (Time: 10-30 mins)",
    "mt-extract": "Isolate all mitochondrial reads into a dedicated file. Perfect for focused mtDNA analysis or haplogroup prediction. (Time: 5-10 mins)",
    "repair-ftdna-bam": "Fix formatting errors specific to Family Tree DNA (FTDNA) BAM files that cause them to fail in standard tools like GATK. (Time: 1-2 hours)",
    "repair-ftdna-vcf": "Fix formatting errors in FTDNA VCF files to make them compatible with modern annotation tools like VEP. (Time: <1 min)",
    "mito": "Directly extract the mitochondrial (chrM) sequence from your file. (Time: 1-5 mins)",
    "ydna": "Extract all Y-chromosome reads. Useful for males to perform detailed paternal lineage analysis. (Time: 5-10 mins)",
    "unmapped": "Extract reads that did not align to the reference. Often used to find viral contamination or non-human DNA. (Time: 5-15 mins)",
    "custom": "Extract reads from a specific chromosomal region or gene of interest. (Time: 1-5 mins)",
    "snp": "Call Single Nucleotide Polymorphisms (SNPs) using bcftools. Best for standard ancestry analysis and finding simple point mutations. (Time: 30-60 mins)",
    "indel": "Call Small Insertions and Deletions (InDels) using bcftools. Used to find small gaps or extra bases in the DNA sequence. (Time: 30-60 mins)",
    "sv": "Call Structural Variants (SVs) using Delly. Identifies large-scale DNA changes (over 50bp) like inversions, translocations, and large deletions. (Time: 1-2 hours)",
    "cnv": "Call Copy Number Variants (CNVs) using Delly. Detects large regions of DNA that have been duplicated or deleted, affecting gene dosage. (Time: 1-2 hours)",
    "freebayes": "A Bayesian genetic variant detector. Excellent for finding small variants in complex regions or when you have variable sequencing depth. (Time: 2-10 hours)",
    "gatk": "Industry-standard GATK HaplotypeCaller. Best for high-accuracy clinical-grade SNP and InDel calling using local de novo assembly. (Time: 10-30 hours)",
    "deepvariant": "Google's Deep Learning variant caller. Highly recommended for 30x+ WGS; uses a neural network to achieve superior accuracy by 'looking' at read alignments as images. (Time: 2-6 hours)",
    "annotate": "Add external metadata (like population frequencies or disease risk) to your VCF file. (Time: 5-15 mins)",
    "filter": "Filter your results. Use this to focus on specific genes of interest or to remove low-quality 'noisy' variant calls. (Time: <1 min)",
    "trio": "Analyze inheritance patterns. Compares a child's VCF with their parents to identify de novo (new) mutations or inherited conditions. (Time: 5-10 mins)",
    "vcf-qc": "Generate statistical reports for your VCF file to check the quality and distribution of your variant calls. (Time: 1-5 mins)",
    "vep-run": "Ensembl Variant Effect Predictor. Predicts the functional impact of your variants (e.g., if a mutation likely breaks a gene or causes a specific disease). (Time: 15-60 mins)",
    "vep-download": "Download the VEP cache (standard GRCh37/38) to your local machine for faster, offline annotation. (Time: 1-3 hours, Space: 20 GB)",
    "vep-verify": "Check your existing VEP cache for missing files or corruption. (Time: 5-10 mins)",
    "microarray": "Simulate a consumer microarray (like 23andMe or AncestryDNA) from your WGS data for use with older ancestry tools. (Time: 10-30 mins)",
    "lineage-y": "Predict your paternal haplogroup using the Yleaf tool. Requires a BAM with Y-chromosome reads. (Time: 5-15 mins)",
    "lineage-mt": "Predict your maternal haplogroup using Haplogrep. Requires a BAM with mitochondrial reads. (Time: 1-5 mins)",
    "fastqc": "The industry-standard quality check for raw reads. Produces a visual report of base quality, GC content, and adapter contamination. (Time: 30-60 mins)",
    "fastp": "An ultra-fast all-in-one pre-processor. Automatically trims adapters and filters low-quality reads while generating a QC report. (Time: 15-30 mins)",
    "ref-identify": "Analyze your BAM header to determine exactly which reference genome was used for the original alignment. (Time: <1 min)",
    "ref-index": "Prepare a FASTA file for use by indexing it. This is required before you can align reads or call variants against it. (Time: 30-60 mins, Space: FASTA Size x 2)",
    "ref-download": "Download curated, standard-compliant reference genomes (hg19, hg38, T2T) optimized for use with this tool. (Time: 10-30 mins, Space: 3-5 GB)",
    "ref-verify": "Ensure your reference genome file isn't corrupted and has all the necessary companion files (indexes, dicts). (Time: 1-5 mins)",
    "ref-count-ns": "Calculate the percentage of 'N' (unknown) bases in a genome. Useful for understanding the 'mappability' of different reference builds. (Time: 5-10 mins)",
    "ref-download-genes": "Download lightweight gene-to-coordinate mapping files, enabling you to filter VCFs by gene name (e.g. BRCA1). (Time: <1 min)",
    "ref-library": "Opens the interactive reference manager to help you organize and download genomic data.",
}

# Specialized UI tooltips (more descriptive for non-technical users)
UI_TOOLTIPS = HELP_TEXTS.copy()
UI_TOOLTIPS.update(
    {
        "ref-library": "Opens the interactive reference manager. Note: This will run in your terminal window.",
    }
)
