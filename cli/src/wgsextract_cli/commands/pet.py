"""Pet Analysis command for aligning and calling variants in non-human species."""

import logging
import os
import shutil
import subprocess

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    get_resource_defaults,
    get_sam_index_cmd,
    get_sam_sort_cmd,
    run_command,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "pet-align", parents=[base_parser], help=CLI_HELP["cmd_pet-align"]
    )
    parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    parser.add_argument("--r2", help=CLI_HELP["arg_r2"])
    parser.add_argument(
        "--species", choices=["dog", "cat"], required=True, help="Species for analysis"
    )
    parser.add_argument(
        "--format", choices=["BAM", "CRAM"], default="BAM", help="Output format"
    )
    parser.set_defaults(func=run)


def run(args):
    verify_dependencies(["bwa", "samtools", "bcftools"])
    log_dependency_info(["bwa", "samtools", "bcftools"])

    logging.debug(f"Input file (R1): {os.path.abspath(args.r1)}")
    if args.r2:
        logging.debug(f"Input file (R2): {os.path.abspath(args.r2)}")

    threads, _ = get_resource_defaults(args.threads, None)

    if not args.ref:
        logging.error(LOG_MESSAGES["ref_required"])
        return

    # Map species to filename
    ref_map = {
        "dog": "GCF_011100685.1_UU_Cfam_GSD_1.0_genomic.fna.gz",
        "cat": "GCF_018350175.1_F.catus_Fca126_mat1.0_genomic.fna.gz",
    }

    if os.path.isfile(args.ref):
        ref_file = args.ref
    else:
        ref_file = os.path.join(args.ref, "genomes", ref_map[args.species])

    logging.debug(f"Resolved reference: {ref_file}")

    if not os.path.exists(ref_file):
        logging.error(f"Reference genome for {args.species} not found at {ref_file}")
        if not os.path.isfile(args.ref):
            logging.info("Please download it in the Library tab of the GUI.")
        return

    # Check for BWA index files, if missing, run indexing
    bwt_index = ref_file + ".bwt"
    if not os.path.exists(bwt_index):
        logging.info(
            f"BWA index missing for {ref_file}. Generating now (may take a while)..."
        )
        try:
            run_command(["bwa", "index", ref_file])
        except Exception as e:
            logging.error(f"Automatic indexing failed: {e}")
            return

    outdir = args.outdir if args.outdir else os.getcwd()
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    base_name = os.path.basename(args.r1).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_{args.species}.bam")
    if args.format == "CRAM":
        out_bam = os.path.join(outdir, f"{base_name}_{args.species}.cram")

    out_vcf = os.path.join(outdir, f"{base_name}_{args.species}.vcf.gz")

    # 1. Alignment
    logging.info(LOG_MESSAGES["pet_aligning"].format(species=args.species))
    r2_args = [args.r2] if args.r2 else []

    try:
        _, memory = get_resource_defaults(args.threads, None)
        # 1. Mark duplicates (optional)
        use_blaster = shutil.which("samblaster") is not None
        if use_blaster:
            logging.info("Using samblaster for marking duplicates...")

        # 2. Samtools sort (BAM/CRAM)
        sam_args = get_sam_sort_cmd(
            out_bam, threads, memory, fmt=args.format, reference=ref_file
        )

        p1 = subprocess.Popen(
            ["bwa", "mem", "-t", threads, ref_file, args.r1] + r2_args,
            stdout=subprocess.PIPE,
        )

        if use_blaster:
            p_blaster = subprocess.Popen(
                ["samblaster"], stdin=p1.stdout, stdout=subprocess.PIPE
            )
            if p1.stdout:
                p1.stdout.close()
            p2 = subprocess.Popen(sam_args, stdin=p_blaster.stdout)
            if p_blaster.stdout:
                p_blaster.stdout.close()
        else:
            p2 = subprocess.Popen(sam_args, stdin=p1.stdout)
            if p1.stdout:
                p1.stdout.close()

        p2.communicate()

        if p2.returncode != 0:
            logging.error("Alignment failed.")
            import sys

            sys.exit(1)

        logging.info(LOG_MESSAGES["pet_indexing"].format(format=args.format))
        run_command(get_sam_index_cmd(out_bam, threads=threads))

    except Exception as e:
        logging.error(f"Alignment error: {e}")
        import sys

        sys.exit(1)

    # 2. Variant Calling (Simple MPileup + BCFTools)
    logging.info(LOG_MESSAGES["pet_calling"])
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
            import sys

            sys.exit(1)

        logging.info("Indexing VCF...")
        run_command(["bcftools", "index", out_vcf])

        logging.info(LOG_MESSAGES["pet_complete"])
        logging.info(LOG_MESSAGES["pet_results"].format(bam=out_bam, vcf=out_vcf))

    except Exception as e:
        logging.error(f"Variant calling error: {e}")
        import sys

        sys.exit(1)
