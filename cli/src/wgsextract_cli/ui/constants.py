"""Shared UI metadata and constants for WGS Extract GUI."""

from typing import Any

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS

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
        "title": GUI_LABELS["tab_flow"],
        "help": GUI_TOOLTIPS["workflow_help"],
    },
    "gen": {
        "title": GUI_LABELS["tab_gen"],
        "help": GUI_TOOLTIPS["info_bam_help"],
        "info_commands": [
            {
                "label": "Detailed Info",
                "cmd": "info",
                "help": GUI_TOOLTIPS["info"],
            },
            {
                "label": "Clear Info Cache",
                "cmd": "clear-cache",
                "help": "Delete the cached .wgse_info.json for the current input file.",
            },
            {
                "label": "Calc Coverage",
                "cmd": "calculate-coverage",
                "help": GUI_TOOLTIPS["calculate-coverage"],
            },
            {
                "label": "Sample Coverage",
                "cmd": "coverage-sample",
                "help": GUI_TOOLTIPS["coverage-sample"],
            },
        ],
        "bam_commands": [
            {"label": "Sort", "cmd": "sort", "help": GUI_TOOLTIPS["sort"]},
            {"label": "Index", "cmd": "index", "help": GUI_TOOLTIPS["index"]},
            {
                "label": "To CRAM",
                "cmd": "to-cram",
                "help": GUI_TOOLTIPS["to-cram"],
            },
            {
                "label": "Unsort",
                "cmd": "unsort",
                "help": GUI_TOOLTIPS["unsort"],
            },
            {
                "label": "Unindex",
                "cmd": "unindex",
                "help": GUI_TOOLTIPS["unindex"],
            },
            {"label": "To BAM", "cmd": "to-bam", "help": GUI_TOOLTIPS["to-bam"]},
            {
                "label": "Repair FTDNA BAM",
                "cmd": "repair-ftdna-bam",
                "help": GUI_TOOLTIPS["repair-ftdna-bam"],
            },
        ],
    },
    "ext": {
        "title": GUI_LABELS["tab_ext"],
        "help": GUI_TOOLTIPS["extract_help"],
        "commands": [
            {
                "label": "MT-only FASTA",
                "cmd": "mito-fasta",
                "help": GUI_TOOLTIPS["mito-fasta"],
            },
            {
                "label": "MT-only BAM",
                "cmd": "mt-extract",
                "help": GUI_TOOLTIPS["mt-extract"],
            },
            {
                "label": "MT-only VCF",
                "cmd": "mito-vcf",
                "help": GUI_TOOLTIPS["mito-vcf"],
            },
            {
                "label": "Y-only BAM",
                "cmd": "ydna-bam",
                "help": GUI_TOOLTIPS["ydna-bam"],
            },
            {
                "label": "Y-only VCF",
                "cmd": "ydna-vcf",
                "help": GUI_TOOLTIPS["ydna-vcf"],
            },
            {
                "label": "Y and MT BAM",
                "cmd": "y-mt-extract",
                "help": GUI_TOOLTIPS["y-mt-extract"],
            },
            {"label": "BAM Subset", "cmd": "subset", "help": GUI_TOOLTIPS["subset"]},
            {
                "label": "Unmapped",
                "cmd": "unmapped",
                "help": GUI_TOOLTIPS["unmapped"],
            },
            {
                "label": "Custom Extract",
                "cmd": "custom",
                "help": GUI_TOOLTIPS["custom"],
            },
        ],
    },
    "micro": {
        "title": GUI_LABELS["tab_micro"],
        "help": GUI_TOOLTIPS["microarray_help"],
        "commands": [
            {
                "label": GUI_LABELS["btn_generate_ck"],
                "cmd": "microarray",
                "help": GUI_TOOLTIPS["microarray"],
            },
        ],
    },
    "anc": {
        "title": GUI_LABELS["tab_anc"],
        "help": GUI_TOOLTIPS["ancestry_help"],
        "commands": [
            {
                "label": "Run Yleaf",
                "cmd": "lineage-y",
                "help": GUI_TOOLTIPS["lineage-y"],
            },
            {
                "label": "Run Haplogrep",
                "cmd": "lineage-mt",
                "help": GUI_TOOLTIPS["lineage-mt"],
            },
        ],
    },
    "vcf": {
        "title": GUI_LABELS["tab_vcf"],
        "help": GUI_TOOLTIPS["vcf_help"],
        "commands": [
            {"label": "SNP Call", "cmd": "snp", "help": GUI_TOOLTIPS["snp"]},
            {"label": "InDel Call", "cmd": "indel", "help": GUI_TOOLTIPS["indel"]},
            {"label": "SV Call", "cmd": "sv", "help": GUI_TOOLTIPS["sv"]},
            {"label": "CNV Call", "cmd": "cnv", "help": GUI_TOOLTIPS["cnv"]},
            {
                "label": "Freebayes",
                "cmd": "freebayes",
                "help": GUI_TOOLTIPS["freebayes"],
            },
            {"label": "GATK HC", "cmd": "gatk", "help": GUI_TOOLTIPS["gatk"]},
            {
                "label": "DeepVariant",
                "cmd": "deepvariant",
                "help": GUI_TOOLTIPS["deepvariant"],
            },
            {
                "label": "Annotate",
                "cmd": "annotate",
                "help": GUI_TOOLTIPS["annotate"],
            },
            {"label": "Filter", "cmd": "filter", "help": GUI_TOOLTIPS["filter"]},
            {
                "label": "Trio Analysis",
                "cmd": "trio",
                "help": GUI_TOOLTIPS["trio"],
            },
            {"label": "VCF QC", "cmd": "vcf-qc", "help": GUI_TOOLTIPS["vcf-qc"]},
            {"label": "Run VEP", "cmd": "vep-run", "help": GUI_TOOLTIPS["vep-run"]},
            {
                "label": "Repair FTDNA VCF",
                "cmd": "repair-ftdna-vcf",
                "help": GUI_TOOLTIPS["repair-ftdna-vcf"],
            },
        ],
    },
    "fastq": {
        "title": GUI_LABELS["tab_fastq"],
        "help": GUI_TOOLTIPS["fastq_help"],
        "commands": [
            {"label": "Run Align", "cmd": "align", "help": GUI_TOOLTIPS["align"]},
            {"label": "Unalign", "cmd": "unalign", "help": GUI_TOOLTIPS["unalign"]},
            {"label": "FastQC", "cmd": "fastqc", "help": GUI_TOOLTIPS["fastqc"]},
            {"label": "FastP", "cmd": "fastp", "help": GUI_TOOLTIPS["fastp"]},
        ],
    },
    "pet": {
        "title": GUI_LABELS["tab_pet"],
        "help": GUI_TOOLTIPS["pet_help"],
        "commands": [
            {
                "label": "Align Pet FASTQ",
                "cmd": "pet-analysis",
                "help": GUI_TOOLTIPS["pet-analysis"],
            },
        ],
    },
    "lib": {
        "title": GUI_LABELS["tab_lib"],
        "help": GUI_TOOLTIPS["library_help"],
        "commands": [
            {
                "label": "Gene Map",
                "cmd": "ref-gene-map",
                "help": GUI_TOOLTIPS["ref-gene-map"],
            },
        ],
        "vep_commands": [
            {
                "label": GUI_LABELS["btn_vep_dl"],
                "cmd": "vep-download",
                "help": GUI_TOOLTIPS["vep-download"],
            },
            {
                "label": GUI_LABELS["btn_vep_verify"],
                "cmd": "vep-verify",
                "help": GUI_TOOLTIPS["vep-verify"],
            },
        ],
    },
    "settings": {
        "title": "Settings",
        "help": "Configure application paths and settings cache.",
    },
}
