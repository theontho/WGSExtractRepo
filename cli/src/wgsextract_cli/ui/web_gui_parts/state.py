"""Global state management for the Web GUI."""

import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class State:
    def __init__(self):
        # Load environment variables
        cli_root = Path(__file__).parent.parent.parent.parent.parent
        env_local = cli_root / ".env.local"
        env_std = cli_root / ".env"
        if env_local.exists():
            load_dotenv(dotenv_path=env_local)
        if env_std.exists():
            load_dotenv(dotenv_path=env_std)

        # Paths
        init_input = os.environ.get("WGSE_INPUT", "")
        init_vcf = os.environ.get("WGSE_INPUT_VCF", "")

        self.bam_path = init_input
        self.vcf_path = init_vcf
        self.fastq_path = ""

        # Auto-detect input types if VCF not set but input looks like VCF
        if not self.vcf_path and init_input.lower().endswith(
            (".vcf", ".vcf.gz", ".bcf")
        ):
            self.vcf_path = init_input
            self.bam_path = ""
        elif not self.fastq_path and init_input.lower().endswith(
            (".fastq", ".fq", ".fastq.gz", ".fq.gz")
        ):
            self.fastq_path = init_input
            self.bam_path = ""

        self.vcf_mother = os.environ.get("WGSE_MOTHER_VCF", "")
        self.vcf_father = os.environ.get("WGSE_FATHER_VCF", "")
        self.ref_path = os.environ.get("WGSE_REF", "")
        self.out_dir = os.environ.get("WGSE_OUTDIR", "")
        self.yleaf_path = os.environ.get("WGSE_YLEAF_PATH", "")
        self.yleaf_pos = ""
        self.haplogrep_path = os.environ.get("WGSE_HAPLOGREP_PATH", "")

        # VCF Advanced
        self.vcf_ann_vcf = ""
        self.vcf_filter_expr = ""
        self.vcf_gene = ""
        self.vcf_region = ""
        self.vcf_vep_args = ""
        self.vep_cache_path = os.environ.get("WGSE_VEP_CACHE", "")

        # Extract Advanced
        self.extract_region = ""
        self.extract_extra = ""

        # Pet Paths
        self.pet_species = "Select Pet Species..."
        self.pet_ref_fasta = ""
        self.pet_fastq_r1 = ""
        self.pet_fastq_r2 = ""
        self.pet_output_format = "BAM"

        # Options
        self.vcf_exclude_gaps = False
        self.cram_version = "3.0"

        # UI state
        self.active_tab = "flow"
        self.logs: dict[str, list[str]] = {"Main": []}
        self.log_tabs: list[str] = ["Main"]
        self.current_log_tab = "Main"
        self.running_processes: dict[str, asyncio.subprocess.Process] = {}
        self.active_downloads: dict[str, Any] = {}

    def get_info(self, path: str):
        """Placeholder for fast info update."""
        # This will be imported or injected to avoid circular dependency
        from .controller import controller

        if path and os.path.exists(path):
            asyncio.create_task(controller.get_info_fast(path))


state = State()
