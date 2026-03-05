"""Shared UI metadata and constants for WGS Extract TUI and GUI."""
from wgsextract_cli.core.help_texts import UI_TOOLTIPS

UI_METADATA = {
    "gen": {
        "title": "General",
        "help": "Basic analysis and alignment",
        "commands": [
            {"label": "Run Info", "cmd": "info", "help": UI_TOOLTIPS["info"]},
            {"label": "Calc Coverage", "cmd": "calculate-coverage", "help": UI_TOOLTIPS["calculate-coverage"]},
            {"label": "Sample Coverage", "cmd": "coverage-sample", "help": UI_TOOLTIPS["coverage-sample"]},
            {"label": "Run Align", "cmd": "align", "help": UI_TOOLTIPS["align"]},
        ]
    },
    "bam": {
        "title": "BAM / CRAM",
        "help": "File management and format conversion",
        "commands": [
            {"label": "Sort", "cmd": "sort", "help": UI_TOOLTIPS["sort"]},
            {"label": "Index", "cmd": "index", "help": UI_TOOLTIPS["index"]},
            {"label": "Unindex", "cmd": "unindex", "help": UI_TOOLTIPS["unindex"]},
            {"label": "Unsort", "cmd": "unsort", "help": UI_TOOLTIPS["unsort"]},
            {"label": "To CRAM", "cmd": "to-cram", "help": UI_TOOLTIPS["to-cram"]},
            {"label": "To BAM", "cmd": "to-bam", "help": UI_TOOLTIPS["to-bam"]},
            {"label": "Unalign", "cmd": "unalign", "help": UI_TOOLTIPS["unalign"]},
            {"label": "Subset", "cmd": "subset", "help": UI_TOOLTIPS["subset"]},
            {"label": "MT-Extract", "cmd": "mt-extract", "help": UI_TOOLTIPS["mt-extract"]},
            {"label": "Repair BAM", "cmd": "repair-ftdna-bam", "help": UI_TOOLTIPS["repair-ftdna-bam"]},
            {"label": "Repair VCF", "cmd": "repair-ftdna-vcf", "help": UI_TOOLTIPS["repair-ftdna-vcf"]},
        ]
    },
    "ext": {
        "title": "Extract",
        "help": "Extract specific regions or reads",
        "commands": [
            {"label": "Mito (chrM)", "cmd": "mito", "help": UI_TOOLTIPS["mito"]},
            {"label": "Y-DNA (chrY)", "cmd": "ydna", "help": UI_TOOLTIPS["ydna"]},
            {"label": "Unmapped", "cmd": "unmapped", "help": UI_TOOLTIPS["unmapped"]},
            {"label": "Custom Extract", "cmd": "custom", "help": UI_TOOLTIPS["custom"]},
        ]
    },
    "vcf": {
        "title": "Variants",
        "help": "Variant calling, filtering, and effect prediction",
        "commands": [
            {"label": "SNP Call", "cmd": "snp", "help": UI_TOOLTIPS["snp"]},
            {"label": "InDel Call", "cmd": "indel", "help": UI_TOOLTIPS["indel"]},
            {"label": "SV Call", "cmd": "sv", "help": UI_TOOLTIPS["sv"]},
            {"label": "CNV Call", "cmd": "cnv", "help": UI_TOOLTIPS["cnv"]},
            {"label": "Freebayes", "cmd": "freebayes", "help": UI_TOOLTIPS["freebayes"]},
            {"label": "GATK HC", "cmd": "gatk", "help": UI_TOOLTIPS["gatk"]},
            {"label": "DeepVariant", "cmd": "deepvariant", "help": UI_TOOLTIPS["deepvariant"]},
            {"label": "Annotate", "cmd": "annotate", "help": UI_TOOLTIPS["annotate"]},
            {"label": "Filter", "cmd": "filter", "help": UI_TOOLTIPS["filter"]},
            {"label": "Trio Analysis", "cmd": "trio", "help": UI_TOOLTIPS["trio"]},
            {"label": "VCF QC", "cmd": "vcf-qc", "help": UI_TOOLTIPS["vcf-qc"]},
            {"label": "Run VEP", "cmd": "vep-run", "help": UI_TOOLTIPS["vep-run"]},
            {"label": "Download Cache", "cmd": "vep-download", "help": UI_TOOLTIPS["vep-download"]},
            {"label": "Verify Cache", "cmd": "vep-verify", "help": UI_TOOLTIPS["vep-verify"]},
        ]
    },
    "anc": {
        "title": "Ancestry",
        "help": "Microarray simulation and lineage prediction",
        "commands": [
            {"label": "CombinedKit", "cmd": "microarray", "help": UI_TOOLTIPS["microarray"]},
            {"label": "Run Yleaf", "cmd": "lineage-y", "help": UI_TOOLTIPS["lineage-y"]},
            {"label": "Run Haplogrep", "cmd": "lineage-mt", "help": UI_TOOLTIPS["lineage-mt"]},
        ]
    },
    "qc": {
        "title": "QC",
        "help": "Quality control for reads and files",
        "commands": [
            {"label": "FastQC", "cmd": "fastqc", "help": UI_TOOLTIPS["fastqc"]},
            {"label": "FastP", "cmd": "fastp", "help": UI_TOOLTIPS["fastp"]},
        ]
    },
    "lib": {
        "title": "Library",
        "help": "Reference data management and common genomes",
        "commands": [
            {"label": "Identify Ref", "cmd": "ref-identify", "help": UI_TOOLTIPS["ref-identify"]},
            {"label": "Index Ref", "cmd": "ref-index", "help": UI_TOOLTIPS["ref-index"]},
            {"label": "Download Ref", "cmd": "ref-download", "help": UI_TOOLTIPS["ref-download"]},
            {"label": "Verify Ref", "cmd": "ref-verify", "help": UI_TOOLTIPS["ref-verify"]},
            {"label": "Count Ns", "cmd": "ref-count-ns", "help": UI_TOOLTIPS["ref-count-ns"]},
            {"label": "Download Genes", "cmd": "ref-download-genes", "help": UI_TOOLTIPS["ref-download-genes"]},
        ]
    }
}
