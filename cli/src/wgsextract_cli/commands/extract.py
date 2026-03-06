import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.help_texts import HELP_TEXTS
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    ensure_vcf_indexed,
    get_chr_name,
    get_resource_defaults,
    resolve_reference,
    run_command,
    verify_paths_exist,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "extract", help="Extract specific chromosomes or unmapped reads."
    )
    ext_subs = parser.add_subparsers(dest="ext_cmd", required=True)

    # Mitochondrial commands
    mito_fasta_parser = ext_subs.add_parser(
        "mito-fasta", parents=[base_parser], help=HELP_TEXTS["mito-fasta"]
    )
    mito_fasta_parser.set_defaults(func=cmd_mito_fasta)

    mito_vcf_parser = ext_subs.add_parser(
        "mito-vcf", parents=[base_parser], help=HELP_TEXTS["mito-vcf"]
    )
    mito_vcf_parser.set_defaults(func=cmd_mito_vcf)

    # Y-DNA commands
    y_bam_parser = ext_subs.add_parser(
        "ydna-bam", parents=[base_parser], help=HELP_TEXTS["ydna-bam"]
    )
    y_bam_parser.set_defaults(func=cmd_ydna_bam)

    y_vcf_parser = ext_subs.add_parser(
        "ydna-vcf", parents=[base_parser], help=HELP_TEXTS["ydna-vcf"]
    )
    y_vcf_parser.set_defaults(func=cmd_ydna_vcf)

    # Combined command
    y_mt_parser = ext_subs.add_parser(
        "y-mt-extract", parents=[base_parser], help=HELP_TEXTS["y-mt-extract"]
    )
    y_mt_parser.set_defaults(func=cmd_y_mt_extract)

    # Legacy / Other
    unmapped_parser = ext_subs.add_parser(
        "unmapped", parents=[base_parser], help=HELP_TEXTS["unmapped"]
    )
    unmapped_parser.set_defaults(func=cmd_unmapped)

    custom_parser = ext_subs.add_parser(
        "custom", parents=[base_parser], help=HELP_TEXTS["custom"]
    )
    custom_parser.add_argument(
        "-r", "--region", required=True, help="Region to extract"
    )
    custom_parser.set_defaults(func=cmd_custom)


def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None

    if not verify_paths_exist({"--input": args.input}):
        return None

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )

    md5_sig = calculate_bam_md5(args.input, None)
    resolved_ref = resolve_reference(args.ref, md5_sig)

    paths_to_check = {}
    if resolved_ref:
        paths_to_check["--ref"] = resolved_ref

    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, outdir, cram_opt, resolved_ref


def cmd_mito_fasta(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    if not resolved_ref:
        logging.error("--ref is required for mitochondrial extraction.")
        return

    print_warning("ButtonMitoFASTA", threads=threads)

    chr_m = get_chr_name(args.input, "MT", cram_opt)
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_MT_temp.bam")
    out_vcf = os.path.join(outdir, f"{base_name}_MT_temp.vcf.gz")
    out_fasta = os.path.join(outdir, f"{base_name}_MT.fasta")

    try:
        # 1. Extract temp BAM
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, chr_m]
        )
        run_command(["samtools", "index", out_bam])

        # 2. Call variants
        p1 = subprocess.Popen(
            ["bcftools", "mpileup", "-Ou", "-f", resolved_ref, out_bam],
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["bcftools", "call", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout
        )
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()
        ensure_vcf_indexed(out_vcf)

        # 3. Generate Consensus
        logging.info(f"Generating consensus FASTA to {out_fasta}")
        with open(out_fasta, "w") as f:
            subprocess.run(
                ["bcftools", "consensus", "-f", resolved_ref, "-H", "1", out_vcf],
                stdout=f,
                check=True,
            )

        # Cleanup
        os.remove(out_bam)
        os.remove(out_bam + ".bai")
        os.remove(out_vcf)
        os.remove(out_vcf + ".tbi")

    except Exception as e:
        logging.error(f"Mito FASTA extraction failed: {e}")


def cmd_mito_vcf(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    if not resolved_ref:
        logging.error("--ref is required for mitochondrial extraction.")
        return

    print_warning("ButtonMitoVCF", threads=threads)

    chr_m = get_chr_name(args.input, "MT", cram_opt)
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_MT_temp.bam")
    out_vcf = os.path.join(outdir, f"{base_name}_MT.vcf.gz")

    try:
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, chr_m]
        )
        run_command(["samtools", "index", out_bam])

        logging.info(f"Calling mitochondrial variants to {out_vcf}")
        p1 = subprocess.Popen(
            ["bcftools", "mpileup", "-Ou", "-f", resolved_ref, out_bam],
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["bcftools", "call", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout
        )
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()
        ensure_vcf_indexed(out_vcf)

        os.remove(out_bam)
        os.remove(out_bam + ".bai")

    except Exception as e:
        logging.error(f"Mito VCF extraction failed: {e}")


def cmd_ydna_bam(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    print_warning("ButtonYOnlyBAM", threads=threads)

    chr_y = get_chr_name(args.input, "Y", cram_opt)
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_Y.bam")

    logging.info(f"Extracting Y-chromosome reads ({chr_y}) to {out_bam}")
    try:
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, chr_y]
        )
        run_command(["samtools", "index", out_bam])
    except Exception as e:
        logging.error(f"Y BAM extraction failed: {e}")


def cmd_ydna_vcf(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    if not resolved_ref:
        logging.error("--ref is required for Y extraction.")
        return

    print_warning("ButtonYOnlyVCF", threads=threads)

    chr_y = get_chr_name(args.input, "Y", cram_opt)
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_Y_temp.bam")
    out_vcf = os.path.join(outdir, f"{base_name}_Y.vcf.gz")

    try:
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, chr_y]
        )
        run_command(["samtools", "index", out_bam])

        logging.info(f"Calling Y-chromosome variants to {out_vcf}")
        p1 = subprocess.Popen(
            ["bcftools", "mpileup", "-Ou", "-f", resolved_ref, out_bam],
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(
            ["bcftools", "call", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout
        )
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()
        ensure_vcf_indexed(out_vcf)

        os.remove(out_bam)
        os.remove(out_bam + ".bai")

    except Exception as e:
        logging.error(f"Y VCF extraction failed: {e}")


def cmd_y_mt_extract(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    print_warning("ButtonYMTBAM", threads=threads)

    chr_y = get_chr_name(args.input, "Y", cram_opt)
    chr_m = get_chr_name(args.input, "MT", cram_opt)
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_Y_MT.bam")

    logging.info(f"Extracting Y and MT reads to {out_bam}")
    try:
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, chr_y, chr_m]
        )
        run_command(["samtools", "index", out_bam])
    except Exception as e:
        logging.error(f"Y+MT extraction failed: {e}")


def cmd_unmapped(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    print_warning("ButtonUnmappedBAM", threads=threads)

    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_unmapped.bam")

    logging.info(f"Extracting unmapped reads to {out_bam}")
    try:
        # -f 4 gets unmapped reads
        run_command(
            ["samtools", "view", "-bh", "-f", "4"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input]
        )
    except Exception as e:
        logging.error(f"Unmapped extraction failed: {e}")


def cmd_custom(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, cram_opt, resolved_ref = base

    region = args.region
    base_name = os.path.basename(args.input).split(".")[0]
    out_bam = os.path.join(outdir, f"{base_name}_{region.replace(':', '_')}.bam")

    logging.info(f"Extracting region {region} to {out_bam}")
    try:
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_bam, args.input, region]
        )
        run_command(["samtools", "index", out_bam])
    except Exception as e:
        logging.error(f"Custom extraction failed: {e}")
