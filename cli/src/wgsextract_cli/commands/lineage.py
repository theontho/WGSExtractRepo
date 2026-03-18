import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import get_tool_path, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    get_chr_name,
    get_resource_defaults,
    get_vcf_build,
    get_vcf_chr_name,
    run_command,
    verify_paths_exist,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser("lineage", help="Executes Yleaf or Haplogrep.")
    lin_subs = parser.add_subparsers(dest="lin_cmd", required=True)

    ydna_parser = lin_subs.add_parser(
        "y-dna", parents=[base_parser], help=CLI_HELP["cmd_lineage-y"]
    )
    ydna_parser.add_argument(
        "--yleaf-path", help="Path to yleaf.py (optional if in PATH)"
    )
    ydna_parser.add_argument("--pos-file", help="Yleaf position file (optional)")
    ydna_parser.add_argument(
        "--extra-args", help="Extra arguments to pass to Yleaf (e.g. -force)"
    )
    ydna_parser.set_defaults(func=cmd_ydna)

    mtdna_parser = lin_subs.add_parser(
        "mt-dna", parents=[base_parser], help=CLI_HELP["cmd_lineage-mt"]
    )
    mtdna_parser.add_argument(
        "--haplogrep-path",
        help="Path to haplogrep executable or JAR (optional if in PATH)",
    )
    mtdna_parser.set_defaults(func=cmd_mtdna)


def cmd_ydna(args):
    # Check dependencies
    if not args.yleaf_path:
        verify_dependencies(["yleaf"])

    yleaf_path = args.yleaf_path or get_tool_path("yleaf")

    if not verify_paths_exist({"--input": args.input, "--yleaf-path": yleaf_path}):
        return

    # Build detection for -rg
    build = None
    if args.input.lower().endswith((".vcf", ".vcf.gz")):
        build = get_vcf_build(args.input)

    if not build:
        md5_sig = calculate_bam_md5(args.input, None)
        lib = ReferenceLibrary(args.ref, md5_sig)
        build = lib.build or "hg38"

    if build not in ["hg19", "hg38"]:
        logging.warning(f"Build {build} not supported by Yleaf, defaulting to hg38")
        build = "hg38"

    logging.info(LOG_MESSAGES["running_yleaf"].format(input=args.input))
    try:
        # Check if yleaf_path is a python script or a wrapper
        cmd = [yleaf_path]
        if yleaf_path.endswith(".py"):
            cmd = ["python3", yleaf_path]

        # Map input type to flag (Yleaf 3.2.1 style)
        input_ext = args.input.lower()
        if input_ext.endswith(".bam"):
            input_flag = "-bam"
        elif input_ext.endswith(".cram"):
            input_flag = "-cram"
        elif input_ext.endswith((".vcf", ".vcf.gz")):
            input_flag = "-vcf"
        elif input_ext.endswith((".fastq", ".fastq.gz", ".fq", ".fq.gz")):
            input_flag = "-fastq"
        else:
            # Fallback to -input for older versions
            input_flag = "-input"

        final_cmd = cmd + [input_flag, args.input, "-rg", build, "-o", args.outdir]

        # Add reference for CRAM if available
        if input_flag == "-cram":
            md5_sig = calculate_bam_md5(args.input, None)
            lib = ReferenceLibrary(args.ref, md5_sig)
            if lib.fasta:
                final_cmd.extend(["-cr", lib.fasta])

        # Add -pos if provided (legacy)
        if args.pos_file:
            final_cmd.extend(["-pos", args.pos_file])

        # Add extra args if provided
        if args.extra_args:
            import shlex

            final_cmd.extend(shlex.split(args.extra_args))

        run_command(final_cmd)
    except Exception as e:
        logging.error(f"Yleaf failed: {e}")


def cmd_mtdna(args):
    # Check dependencies
    if not args.haplogrep_path:
        verify_dependencies(["haplogrep", "bcftools"])

    haplogrep_path = args.haplogrep_path or get_tool_path("haplogrep")

    if not verify_paths_exist(
        {"--input": args.input, "--haplogrep-path": haplogrep_path}
    ):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    out_file = os.path.join(outdir, "haplogrep_results.txt")

    input_file = args.input
    temp_vcf = None

    try:
        is_vcf = input_file.lower().endswith((".vcf", ".vcf.gz"))
        is_alignment = input_file.lower().endswith((".bam", ".cram"))

        if is_alignment:
            logging.info(
                "Input is alignment. Extracting mitochondrial variants first..."
            )
            temp_vcf = os.path.join(outdir, "temp_haplogrep_input.vcf.gz")

            threads, _ = get_resource_defaults(args.threads, None)
            md5_sig = calculate_bam_md5(input_file, None)
            lib = ReferenceLibrary(args.ref, md5_sig)
            if not lib.fasta:
                logging.error(
                    "Reference genome required to call mitochondrial variants."
                )
                return

            cram_opt = ["-T", lib.fasta] if input_file.lower().endswith(".cram") else []
            chr_m = get_chr_name(input_file, "MT", cram_opt)

            # Fast variant calling for MT region
            p1 = subprocess.Popen(
                [
                    "bcftools",
                    "mpileup",
                    "-Ou",
                    "-r",
                    chr_m,
                    "-f",
                    lib.fasta,
                    input_file,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            p2 = subprocess.Popen(
                ["bcftools", "call", "-mv", "-Oz", "-o", temp_vcf],
                stdin=p1.stdout,
                stderr=subprocess.DEVNULL,
            )
            if p1.stdout:
                p1.stdout.close()
            p2.communicate()

            if p2.returncode != 0:
                logging.error("Failed to extract mitochondrial variants.")
                return
            input_file = temp_vcf

        elif is_vcf:
            # Filter VCF to chrM to avoid Haplogrep errors on large VCFs
            chr_m = get_vcf_chr_name(input_file, "MT")
            logging.info(f"Filtering VCF to {chr_m} for Haplogrep...")
            temp_vcf = os.path.join(outdir, "temp_haplogrep_filtered.vcf.gz")

            run_command(
                ["bcftools", "view", "-r", chr_m, "-Oz", "-o", temp_vcf, input_file]
            )
            input_file = temp_vcf

        logging.info(LOG_MESSAGES["running_haplogrep"].format(input=input_file))
        # Check if it's a JAR or a wrapper
        cmd = [haplogrep_path]
        if haplogrep_path.endswith(".jar"):
            verify_dependencies(["java"])
            cmd = ["java", "-jar", haplogrep_path]

        run_command(
            cmd
            + [
                "classify",
                "--format",
                "vcf",
                "--in",
                input_file,
                "--out",
                out_file,
            ]
        )
    except Exception as e:
        logging.error(f"Haplogrep failed: {e}")
    finally:
        if temp_vcf and os.path.exists(temp_vcf):
            try:
                os.remove(temp_vcf)
                if os.path.exists(temp_vcf + ".tbi"):
                    os.remove(temp_vcf + ".tbi")
            except Exception:
                pass
