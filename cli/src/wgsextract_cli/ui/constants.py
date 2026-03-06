"""Shared UI metadata and constants for WGS Extract GUI."""

from typing import Any

from wgsextract_cli.core.help_texts import UI_TOOLTIPS

BUTTON_FONT = ("Courier", 13, "bold")

MICROARRAY_FORMATS: list[dict[str, Any]] = [
    {
        "id": "all",
        "label": "Combined ALL SNPs (GEDMATCH)",
        "vendor": "Everything",
        "recommended": True,
    },
    {"id": "23andme_v3", "label": "23andMe v3", "vendor": "23andMe"},
    {"id": "23andme_v4", "label": "23andMe v4", "vendor": "23andMe"},
    {
        "id": "23andme_v5",
        "label": "23andMe v5",
        "vendor": "23andMe",
        "recommended": True,
    },
    {
        "id": "23andme_v3+v5",
        "label": "23andMe v3+v5",
        "vendor": "23andMe",
        "recommended": True,
    },
    {"id": "23andme_api", "label": "23andMe API", "vendor": "23andMe"},
    {"id": "ancestry_v1", "label": "AncestryDNA v1", "vendor": "AncestryDNA"},
    {
        "id": "ancestry_v2",
        "label": "AncestryDNA v2",
        "vendor": "AncestryDNA",
    },
    {"id": "ftdna_v2", "label": "FamilyTreeDNA v2", "vendor": "FamilyTreeDNA"},
    {
        "id": "ftdna_v3",
        "label": "FamilyTreeDNA v3",
        "vendor": "FamilyTreeDNA",
    },
    {"id": "ldna_v1", "label": "Living DNA v1", "vendor": "Living DNA"},
    {"id": "ldna_v2", "label": "Living DNA v2", "vendor": "Living DNA"},
    {"id": "myheritage_v1", "label": "MyHeritage v1", "vendor": "MyHeritage"},
    {
        "id": "myheritage_v2",
        "label": "MyHeritage v2",
        "vendor": "MyHeritage",
    },
    {"id": "mthfr_uk", "label": "MTHFR Genetics UK", "vendor": "Other Vendors"},
    {"id": "genera_br", "label": "Genera BR", "vendor": "Other Vendors"},
    {"id": "meudna_br", "label": "meuDNA BR", "vendor": "Other Vendors"},
    {"id": "reich_aadr", "label": "AADR 1240K", "vendor": "Reich Lab"},
    {"id": "reich_human_origins", "label": "Human Origins v1", "vendor": "Reich Lab"},
    {
        "id": "reich_combined",
        "label": "Reich Combined",
        "vendor": "Reich Lab",
    },
]

UI_METADATA: dict[str, dict[str, Any]] = {
    "flow": {
        "title": "Workflow",
        "help": "Visualize the bioinformatics workflow from raw sequencing data to final analysis results. Click on any node to jump to the corresponding tab.",
    },
    "gen": {
        "title": "Info / BAM",
        "help": "BAM (Binary Alignment Map) and CRAM are compressed files containing your DNA sequences aligned to a reference genome. Use this tab to identify your data's build, check sequence quality, or convert between alignment formats.",
        "info_commands": [
            {"label": "Detailed Info", "cmd": "info", "help": UI_TOOLTIPS["info"]},
            {
                "label": "Clear Info Cache",
                "cmd": "clear-cache",
                "help": "Delete the cached .wgse_info.json for the current input file.",
            },
            {
                "label": "Calc Coverage",
                "cmd": "calculate-coverage",
                "help": UI_TOOLTIPS["calculate-coverage"],
            },
            {
                "label": "Sample Coverage",
                "cmd": "coverage-sample",
                "help": UI_TOOLTIPS["coverage-sample"],
            },
        ],
        "bam_commands": [
            {"label": "Sort", "cmd": "sort", "help": UI_TOOLTIPS["sort"]},
            {"label": "Index", "cmd": "index", "help": UI_TOOLTIPS["index"]},
            {"label": "To CRAM", "cmd": "to-cram", "help": UI_TOOLTIPS["to-cram"]},
            {"label": "Unsort", "cmd": "unsort", "help": UI_TOOLTIPS["unsort"]},
            {"label": "Unindex", "cmd": "unindex", "help": UI_TOOLTIPS["unindex"]},
            {"label": "To BAM", "cmd": "to-bam", "help": UI_TOOLTIPS["to-bam"]},
            {
                "label": "Repair FTDNA BAM",
                "cmd": "repair-ftdna-bam",
                "help": UI_TOOLTIPS["repair-ftdna-bam"],
            },
        ],
    },
    "ext": {
        "title": "Extract",
        "help": "Extract specific subsets of your DNA data. This is useful for isolating Mitochondrial DNA (chrM) or Y-Chromosome data (chrY) for specialized analysis without processing the entire large BAM/CRAM file.",
        "commands": [
            {
                "label": "MT-only FASTA",
                "cmd": "mito-fasta",
                "help": UI_TOOLTIPS["mito-fasta"],
            },
            {
                "label": "MT-only BAM",
                "cmd": "mt-extract",
                "help": UI_TOOLTIPS["mt-extract"],
            },
            {
                "label": "MT-only VCF",
                "cmd": "mito-vcf",
                "help": UI_TOOLTIPS["mito-vcf"],
            },
            {"label": "Y-only BAM", "cmd": "ydna-bam", "help": UI_TOOLTIPS["ydna-bam"]},
            {"label": "Y-only VCF", "cmd": "ydna-vcf", "help": UI_TOOLTIPS["ydna-vcf"]},
            {
                "label": "Y and MT BAM",
                "cmd": "y-mt-extract",
                "help": UI_TOOLTIPS["y-mt-extract"],
            },
            {"label": "BAM Subset", "cmd": "subset", "help": UI_TOOLTIPS["subset"]},
            {"label": "Unmapped", "cmd": "unmapped", "help": UI_TOOLTIPS["unmapped"]},
            {"label": "Custom Extract", "cmd": "custom", "help": UI_TOOLTIPS["custom"]},
        ],
    },
    "micro": {
        "title": "Microarray",
        "help": "Generate 'CombinedKit' files that simulate the raw data format used by consumer testing companies like 23andMe, AncestryDNA, and FTDNA. This allows you to upload your WGS data to third-party tools and services like Gedmatch, Geneanet, MyHeritage, Promethease, and Genvue.",
        "commands": [
            {
                "label": "Generate CombinedKit",
                "cmd": "microarray",
                "help": UI_TOOLTIPS["microarray"],
            },
        ],
    },
    "anc": {
        "title": "Ancestry",
        "help": "Identify your haplogroups and deep ancestral lineages. Y-DNA analysis (Yleaf) tracks paternal descent, while Mitochondrial (Haplogrep) tracks maternal descent based on specific markers in your DNA.",
        "commands": [
            {
                "label": "Run Yleaf",
                "cmd": "lineage-y",
                "help": UI_TOOLTIPS["lineage-y"],
            },
            {
                "label": "Run Haplogrep",
                "cmd": "lineage-mt",
                "help": UI_TOOLTIPS["lineage-mt"],
            },
        ],
    },
    "vcf": {
        "title": "VCF",
        "help": "VCF (Variant Call Format) files list the specific positions where your DNA differs from the reference genome. Use this tab to 'call' variants (identify SNPs, InDels, SVs), filter them by quality, or predict their biological effects (VEP).",
        "commands": [
            {"label": "SNP Call", "cmd": "snp", "help": UI_TOOLTIPS["snp"]},
            {"label": "InDel Call", "cmd": "indel", "help": UI_TOOLTIPS["indel"]},
            {"label": "SV Call", "cmd": "sv", "help": UI_TOOLTIPS["sv"]},
            {"label": "CNV Call", "cmd": "cnv", "help": UI_TOOLTIPS["cnv"]},
            {
                "label": "Freebayes",
                "cmd": "freebayes",
                "help": UI_TOOLTIPS["freebayes"],
            },
            {"label": "GATK HC", "cmd": "gatk", "help": UI_TOOLTIPS["gatk"]},
            {
                "label": "DeepVariant",
                "cmd": "deepvariant",
                "help": UI_TOOLTIPS["deepvariant"],
            },
            {"label": "Annotate", "cmd": "annotate", "help": UI_TOOLTIPS["annotate"]},
            {"label": "Filter", "cmd": "filter", "help": UI_TOOLTIPS["filter"]},
            {"label": "Trio Analysis", "cmd": "trio", "help": UI_TOOLTIPS["trio"]},
            {"label": "VCF QC", "cmd": "vcf-qc", "help": UI_TOOLTIPS["vcf-qc"]},
            {"label": "Run VEP", "cmd": "vep-run", "help": UI_TOOLTIPS["vep-run"]},
            {
                "label": "Repair FTDNA VCF",
                "cmd": "repair-ftdna-vcf",
                "help": UI_TOOLTIPS["repair-ftdna-vcf"],
            },
        ],
    },
    "fastq": {
        "title": "FASTQ",
        "help": "FASTQ files contain the 'raw' reads directly from the sequencer before they are aligned. Use this tab to perform quality control (FastQC/FastP) or align these raw reads to a reference genome to create a BAM/CRAM file.",
        "commands": [
            {"label": "Run Align", "cmd": "align", "help": UI_TOOLTIPS["align"]},
            {"label": "Unalign", "cmd": "unalign", "help": UI_TOOLTIPS["unalign"]},
            {"label": "FastQC", "cmd": "fastqc", "help": UI_TOOLTIPS["fastqc"]},
            {"label": "FastP", "cmd": "fastp", "help": UI_TOOLTIPS["fastp"]},
        ],
    },
    "lib": {
        "title": "Library",
        "help": "Manage your reference data library. Download and verify standardized reference genomes (FASTA), gene maps for annotation, and VEP caches required for advanced variant effect prediction.",
        "commands": [
            {
                "label": "Gene Map",
                "cmd": "ref-gene-map",
                "help": UI_TOOLTIPS["ref-gene-map"],
            },
        ],
        "vep_commands": [
            {
                "label": "Download VEP Cache",
                "cmd": "vep-download",
                "help": UI_TOOLTIPS["vep-download"],
            },
            {
                "label": "Verify VEP Cache",
                "cmd": "vep-verify",
                "help": UI_TOOLTIPS["vep-verify"],
            },
        ],
    },
}
