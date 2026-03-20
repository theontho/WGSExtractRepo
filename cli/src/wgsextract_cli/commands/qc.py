import logging
import os

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    get_resource_defaults,
    run_command,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "qc", help="Runs quality control or calculates coverage."
    )
    qc_subs = parser.add_subparsers(dest="qc_cmd", required=True)

    fastp_parser = qc_subs.add_parser(
        "fastp", parents=[base_parser], help=CLI_HELP["cmd_fastp"]
    )
    fastp_parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    fastp_parser.add_argument("--r2", help=CLI_HELP["arg_r2"])
    fastp_parser.set_defaults(func=cmd_fastp)

    fastqc_parser = qc_subs.add_parser(
        "fastqc", parents=[base_parser], help=CLI_HELP["cmd_fastqc"]
    )
    fastqc_parser.set_defaults(func=cmd_fastqc)

    vcf_parser = qc_subs.add_parser(
        "vcf", parents=[base_parser], help=CLI_HELP["cmd_vcf-qc"]
    )
    vcf_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    vcf_parser.set_defaults(func=cmd_vcf_qc)


def cmd_fastp(args):
    verify_dependencies(["fastp"])
    log_dependency_info(["fastp"])

    from wgsextract_cli.core.utils import verify_paths_exist

    paths = {"--r1": args.r1}
    if args.r2:
        paths["--r2"] = args.r2
    if not verify_paths_exist(paths):
        return

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.r1))

    logging.debug(f"Input file (R1): {os.path.abspath(args.r1)}")
    if args.r2:
        logging.debug(f"Input file (R2): {os.path.abspath(args.r2)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    base_name = os.path.basename(args.r1).split(".")[0]
    out_r1 = os.path.join(outdir, f"{base_name}_fp_1.fastq.gz")
    out_json = os.path.join(outdir, f"{base_name}_fastp.json")
    out_html = os.path.join(outdir, f"{base_name}_fastp.html")

    cmd = [
        "fastp",
        "--thread",
        threads,
        "-i",
        args.r1,
        "-o",
        out_r1,
        "-j",
        out_json,
        "-h",
        out_html,
    ]
    if args.r2:
        out_r2 = os.path.join(outdir, f"{base_name}_fp_2.fastq.gz")
        cmd.extend(["-I", args.r2, "-O", out_r2])

    logging.info(LOG_MESSAGES["running_fastp"].format(input=args.r1))
    try:
        run_command(cmd)
    except Exception as e:
        logging.error(f"fastp failed: {e}")


def cmd_fastqc(args):
    verify_dependencies(["fastqc"])
    log_dependency_info(["fastqc"])

    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    from wgsextract_cli.core.utils import verify_paths_exist

    if not verify_paths_exist({"--input": args.input}):
        return

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )

    logging.debug(f"Input file: {os.path.abspath(args.input)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    logging.info(LOG_MESSAGES["running_fastqc"].format(input=args.input))
    try:
        run_command(["fastqc", "-t", threads, "-o", outdir, args.input])
    except Exception as e:
        logging.error(f"FastQC failed: {e}")


def cmd_vcf_qc(args):
    verify_dependencies(["bcftools"])
    log_dependency_info(["bcftools"])
    input_file = args.vcf_input if args.vcf_input else args.input
    if not input_file:
        logging.error("--input is required.")
        return

    from wgsextract_cli.core.utils import verify_paths_exist

    if not verify_paths_exist({"--input": input_file}):
        return

    logging.debug(f"Input file: {os.path.abspath(input_file)}")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    base_name = os.path.basename(input_file)
    out_stats = os.path.join(outdir, f"{base_name}.vcfstats.txt")

    logging.info(LOG_MESSAGES["vcf_stats"].format(input=input_file, output=out_stats))
    try:
        import subprocess

        with open(out_stats, "w") as f:
            subprocess.run(["bcftools", "stats", input_file], stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"VCF stats failed: {e}")
