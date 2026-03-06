"""Pet Analysis command for aligning and calling variants in non-human species."""

import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.help_texts import HELP_TEXTS
from wgsextract_cli.core.utils import get_resource_defaults, run_command


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "pet-analysis", parents=[base_parser], help=HELP_TEXTS["pet-analysis"]
    )
    parser.add_argument("--r1", required=True, help="Read 1 FASTQ file")
    parser.add_argument("--r2", help="Read 2 FASTQ file (optional)")
    parser.add_argument(
        "--species", choices=["dog", "cat"], required=True, help="Species for analysis"
    )
    parser.add_argument(
        "--format", choices=["BAM", "CRAM"], default="BAM", help="Output format"
    )
    parser.set_defaults(func=run)


def run(args):
    verify_dependencies(["bwa", "samtools", "bcftools"])
    threads, _ = get_resource_defaults(args.threads, None)

    if not args.ref:
        logging.error("--ref (reference library directory) is required.")
        return

    # Map species to filename
    ref_map = {
        "dog": "GCF_011100685.1_UU_Cfam_GSD_1.0_genomic.fna.gz",
        "cat": "GCF_018350175.1_F.catus_Fca126_mat1.0_genomic.fna.gz",
    }
    ref_file = os.path.join(args.ref, "genomes", ref_map[args.species])

    if not os.path.exists(ref_file):
        logging.error(f"Reference genome for {args.species} not found at {ref_file}")
        logging.info("Please download it in the Library tab of the GUI.")
        return

    outdir = args.outdir if args.outdir else os.getcwd()
    base_name = os.path.basename(args.r1).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_{args.species}.bam")
    if args.format == "CRAM":
        out_bam = os.path.join(outdir, f"{base_name}_{args.species}.cram")

    out_vcf = os.path.join(outdir, f"{base_name}_{args.species}.vcf.gz")

    # 1. Alignment
    logging.info(f"Step 1/2: Aligning {args.species} reads...")
    r2_args = [args.r2] if args.r2 else []

    try:
        # BWA MEM -> Samtools view (BAM/CRAM)
        sam_args = ["samtools", "view", "-bh"]
        if args.format == "CRAM":
            sam_args = ["samtools", "view", "-Ch", "--reference", ref_file]
        sam_args += ["-o", out_bam]

        p1 = subprocess.Popen(
            ["bwa", "mem", "-t", threads, ref_file, args.r1] + r2_args,
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(sam_args, stdin=p1.stdout)
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()

        if p2.returncode != 0:
            logging.error("Alignment failed.")
            return

        logging.info(f"Indexing {args.format}...")
        run_command(["samtools", "index", out_bam])

    except Exception as e:
        logging.error(f"Alignment error: {e}")
        return

    # 2. Variant Calling (Simple MPileup + BCFTools)
    logging.info("Step 2/2: Calling variants...")
    try:
        # bcftools mpileup | bcftools call -mv -Oz -o out.vcf.gz
        p1 = subprocess.Popen(
            [
                "bcftools",
                "mpileup",
                "--threads",
                threads,
                "-f",
                ref_file,
                out_bam,
            ],
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            [
                "bcftools",
                "call",
                "--threads",
                threads,
                "-mv",
                "-Oz",
                "-o",
                out_vcf,
            ],
            stdin=p1.stdout,
        )
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()

        if p2.returncode != 0:
            logging.error("Variant calling failed.")
            return

        logging.info("Indexing VCF...")
        run_command(["bcftools", "index", out_vcf])

        logging.info("Pet Analysis complete!")
        logging.info(f"Results: {out_bam}, {out_vcf}")

    except Exception as e:
        logging.error(f"Variant calling error: {e}")
