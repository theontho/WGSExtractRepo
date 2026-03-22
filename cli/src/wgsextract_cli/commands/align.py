import logging
import os
import shutil
import subprocess

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    get_resource_defaults,
    get_sam_index_cmd,
    get_sam_sort_cmd,
    resolve_reference,
    run_command,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "align", parents=[base_parser], help=CLI_HELP["cmd_align"]
    )
    parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    parser.add_argument("--r2", help=CLI_HELP["arg_r2"])
    parser.add_argument(
        "--long-read", action="store_true", help=CLI_HELP["arg_long_read"]
    )
    parser.add_argument(
        "--format", choices=["BAM", "CRAM"], default="BAM", help="Output format"
    )
    parser.set_defaults(func=run)


def run(args):
    # Determine which aligner to use
    if args.long_read:
        align_minimap2(args)
    else:
        align_bwa(args)


def align_bwa(args):
    verify_dependencies(["bwa", "samtools"])
    log_dependency_info(["bwa", "samtools"])
    threads, memory = get_resource_defaults(args.threads, args.memory)

    # Use --input's path if outdir not set, or r1's path
    input_path = args.input if args.input else args.r1
    logging.debug(f"Input file: {os.path.abspath(input_path)}")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_path))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    md5_sig = calculate_bam_md5(input_path, None) if args.input else None
    resolved_ref = resolve_reference(args.ref, md5_sig)
    logging.debug(f"Resolved reference: {resolved_ref}")

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error(LOG_MESSAGES["ref_required_for"].format(task="BWA alignment"))
        return

    # Check for BWA index files, if missing, run indexing
    bwt_index = resolved_ref + ".bwt"
    if not os.path.exists(bwt_index):
        logging.info(
            f"BWA index missing for {resolved_ref}. Generating now (may take a while)..."
        )
        try:
            run_command(["bwa", "index", resolved_ref])
        except Exception as e:
            logging.error(f"Automatic indexing failed: {e}")
            return

    print_warning("ButtonBWAAlign", threads=threads)

    base_name = os.path.basename(args.r1).split(".")[0]
    ext = ".cram" if args.format == "CRAM" else ".bam"
    out_bam = os.path.join(outdir, f"{base_name}_aligned{ext}")

    r2_args = [args.r2] if args.r2 else []

    logging.info(
        LOG_MESSAGES["aligning_reads"].format(input=args.r1, output=out_bam, tool="BWA")
    )
    try:
        # 1. Aligner command
        align_cmd = ["bwa", "mem", "-t", threads, resolved_ref, args.r1] + r2_args

        # 2. Mark duplicates (optional)
        use_blaster = shutil.which("samblaster") is not None
        if use_blaster:
            logging.info("Using samblaster for marking duplicates...")

        # 3. Sorter command
        sort_cmd = get_sam_sort_cmd(
            out_bam, threads, memory, fmt=args.format, reference=resolved_ref
        )

        # Pipe align -> [samblaster] -> sort
        p_align = subprocess.Popen(align_cmd, stdout=subprocess.PIPE)

        if use_blaster:
            p_blaster = subprocess.Popen(
                ["samblaster"], stdin=p_align.stdout, stdout=subprocess.PIPE
            )
            if p_align.stdout:
                p_align.stdout.close()
            p_sort = subprocess.Popen(sort_cmd, stdin=p_blaster.stdout)
            if p_blaster.stdout:
                p_blaster.stdout.close()
        else:
            p_sort = subprocess.Popen(sort_cmd, stdin=p_align.stdout)
            if p_align.stdout:
                p_align.stdout.close()

        p_sort.communicate()

        logging.info(LOG_MESSAGES["indexing_output"])
        index_cmd = get_sam_index_cmd(out_bam, threads=threads)
        subprocess.run(index_cmd, check=True)
    except Exception as e:
        logging.error(f"BWA alignment failed: {e}")


def align_minimap2(args):
    verify_dependencies(["minimap2", "samtools"])
    log_dependency_info(["minimap2", "samtools"])
    threads, memory = get_resource_defaults(args.threads, args.memory)

    input_path = args.input if args.input else args.r1
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_path))
    )
    logging.debug(f"Input file: {os.path.abspath(input_path)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    md5_sig = calculate_bam_md5(input_path, None) if args.input else None
    resolved_ref = resolve_reference(args.ref, md5_sig)
    logging.debug(f"Resolved reference: {resolved_ref}")

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error(
            LOG_MESSAGES["ref_required_for"].format(task="Minimap2 alignment")
        )
        return

    base_name = os.path.basename(args.r1).split(".")[0]
    ext = ".cram" if args.format == "CRAM" else ".bam"
    out_bam = os.path.join(outdir, f"{base_name}_aligned{ext}")

    r2_args = [args.r2] if args.r2 else []

    logging.info(
        LOG_MESSAGES["aligning_reads"].format(
            input=args.r1, output=out_bam, tool="Minimap2"
        )
    )
    try:
        # 1. Aligner command
        align_cmd = [
            "minimap2",
            "-ax",
            "sr",
            "-t",
            threads,
            resolved_ref,
            args.r1,
        ] + r2_args

        # 2. Mark duplicates (optional) - minimap2 typically used for long reads where marking dups might differ
        # but the --long-read flag handles this.
        use_blaster = shutil.which("samblaster") is not None and not args.long_read
        if use_blaster:
            logging.info("Using samblaster for marking duplicates...")

        # 3. Sorter command
        sort_cmd = get_sam_sort_cmd(
            out_bam, threads, memory, fmt=args.format, reference=resolved_ref
        )

        # Pipe align -> [samblaster] -> sort
        p_align = subprocess.Popen(align_cmd, stdout=subprocess.PIPE)

        if use_blaster:
            p_blaster = subprocess.Popen(
                ["samblaster"], stdin=p_align.stdout, stdout=subprocess.PIPE
            )
            if p_align.stdout:
                p_align.stdout.close()
            p_sort = subprocess.Popen(sort_cmd, stdin=p_blaster.stdout)
            if p_blaster.stdout:
                p_blaster.stdout.close()
        else:
            p_sort = subprocess.Popen(sort_cmd, stdin=p_align.stdout)
            if p_align.stdout:
                p_align.stdout.close()

        p_sort.communicate()

        logging.info(LOG_MESSAGES["indexing_output"])
        index_cmd = get_sam_index_cmd(out_bam, threads=threads)
        subprocess.run(index_cmd, check=True)
    except Exception as e:
        logging.error(f"Minimap2 alignment failed: {e}")
