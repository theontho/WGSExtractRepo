import argparse
import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
    get_resource_defaults,
    verify_paths_exist,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "microarray",
        parents=[base_parser],
        help=CLI_HELP["cmd_microarray"],
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--formats", default="all", help=CLI_HELP["micro_formats_help"])
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable per-chromosome parallel variant calling",
    )
    parser.add_argument(
        "--ref-vcf-tab",
        help="Master tabulated list of all consumer microarray SNPs (auto-resolved from --ref if possible)",
    )
    parser.add_argument(
        "--ploidy-file",
        help="File defining ploidy per chromosome (auto-resolved from --ref if possible)",
    )
    parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    parser.set_defaults(func=run)


def run(args):
    verify_dependencies(["bcftools", "tabix", "samtools"])
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )

    md5_sig = calculate_bam_md5(args.input, None)
    lib = ReferenceLibrary(args.ref, md5_sig)

    ref_fasta = lib.fasta
    ref_vcf_tab = args.ref_vcf_tab if args.ref_vcf_tab else lib.ref_vcf_tab
    ploidy_file = args.ploidy_file if args.ploidy_file else lib.ploidy_file

    if not ref_fasta or not os.path.isfile(ref_fasta):
        logging.error(
            LOG_MESSAGES["ref_required_for"].format(task="microarray generation")
        )
        return

    if not ref_vcf_tab:
        logging.error("--ref-vcf-tab is required and could not be auto-resolved.")
        return

    print_warning("ButtonMicroarray", threads=threads)

    # 1. Variant Calling at target SNP positions
    base_name = os.path.basename(args.input).split(".")[0]
    out_vcf = os.path.join(outdir, f"{base_name}_combined.vcf.gz")

    region_args = ["-r", args.region] if args.region else []
    ploidy_args = (
        ["--ploidy-file", ploidy_file] if ploidy_file else ["--ploidy", "human"]
    )

    logging.info(LOG_MESSAGES["micro_generating_vcf"].format(output=out_vcf))
    try:
        # mpileup restricted to target SNPs
        p1 = subprocess.Popen(
            [
                "bcftools",
                "mpileup",
                "-B",
                "-I",
                "-C",
                "50",
                "-f",
                ref_fasta,
                "-R",
                ref_vcf_tab,
                args.input,
            ]
            + region_args,
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["bcftools", "call"]
            + ploidy_args
            + ["-m", "-V", "indels", "-Oz", "-o", out_vcf],
            stdin=p1.stdout,
        )
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()

        ensure_vcf_indexed(out_vcf)
    except Exception as e:
        logging.error(f"Variant calling failed: {e}")
        return

    # 2. Liftover if needed (to hg19 for most vendors)
    # The All_SNPs tab file is usually build-specific.
    # If the input was hg38, we might need to liftover the results to hg19.
    if lib.build and "38" in lib.build:
        logging.info(LOG_MESSAGES["micro_liftover_warn"])
        # liftover_hg38_to_hg19(out_vcf, ...)

    # 3. Convert to vendor formats
    requested_formats = args.formats.split(",")
    for fmt in requested_formats:
        fmt = fmt.strip()
        logging.info(LOG_MESSAGES["micro_generating_fmt"].format(format=fmt))
        # convert_to_vendor_format(final_vcf, fmt, outdir)
