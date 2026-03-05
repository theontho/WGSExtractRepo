import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.help_texts import HELP_TEXTS
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    get_resource_defaults,
    resolve_reference,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "align", parents=[base_parser], help=HELP_TEXTS["align"]
    )
    parser.add_argument("--r1", required=True, help="Read 1 FASTQ file")
    parser.add_argument("--r2", help="Read 2 FASTQ file (optional)")
    parser.add_argument(
        "--long-read", action="store_true", help="Use minimap2 for long-read alignment"
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
    threads, _ = get_resource_defaults(args.threads, None)

    # Use --input's path if outdir not set, or r1's path
    input_path = args.input if args.input else args.r1
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_path))
    )

    md5_sig = calculate_bam_md5(input_path, None) if args.input else None
    resolved_ref = resolve_reference(args.ref, md5_sig)

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for BWA alignment.")
        return

    print_warning("ButtonBWAAlign", threads=threads)

    base_name = os.path.basename(args.r1).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_aligned.bam")

    r2_args = [args.r2] if args.r2 else []

    logging.info(f"Aligning {args.r1} to {out_bam} using BWA")
    try:
        p1 = subprocess.Popen(
            ["bwa", "mem", "-t", threads, resolved_ref, args.r1] + r2_args,
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["samtools", "view", "-bh", "-o", out_bam], stdin=p1.stdout
        )
        p1.stdout.close()
        p2.communicate()

        logging.info("Indexing output BAM...")
        subprocess.run(["samtools", "index", out_bam], check=True)
    except Exception as e:
        logging.error(f"BWA alignment failed: {e}")


def align_minimap2(args):
    verify_dependencies(["minimap2", "samtools"])
    threads, _ = get_resource_defaults(args.threads, None)

    input_path = args.input if args.input else args.r1
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_path))
    )

    md5_sig = calculate_bam_md5(input_path, None) if args.input else None
    resolved_ref = resolve_reference(args.ref, md5_sig)

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for Minimap2 alignment.")
        return

    base_name = os.path.basename(args.r1).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_aligned.bam")

    r2_args = [args.r2] if args.r2 else []

    logging.info(f"Aligning {args.r1} to {out_bam} using Minimap2")
    try:
        p1 = subprocess.Popen(
            ["minimap2", "-ax", "sr", "-t", threads, resolved_ref, args.r1] + r2_args,
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["samtools", "view", "-bh", "-o", out_bam], stdin=p1.stdout
        )
        p1.stdout.close()
        p2.communicate()

        logging.info("Indexing output BAM...")
        subprocess.run(["samtools", "index", out_bam], check=True)
    except Exception as e:
        logging.error(f"Minimap2 alignment failed: {e}")
