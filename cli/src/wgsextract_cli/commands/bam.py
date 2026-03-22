import logging
import os
import shutil
import subprocess
import tempfile

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    get_chr_name,
    get_resource_defaults,
    get_sam_index_cmd,
    get_sam_sort_cmd,
    resolve_reference,
    run_command,
    verify_paths_exist,
)
from wgsextract_cli.core.warnings import check_free_space, print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser("bam", help=CLI_HELP["cmd_bam_mgmt"])
    bam_subs = parser.add_subparsers(dest="bam_cmd", required=True)

    sort_parser = bam_subs.add_parser(
        "sort", parents=[base_parser], help=CLI_HELP["cmd_sort"]
    )
    sort_parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    sort_parser.add_argument("--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)")
    sort_parser.set_defaults(func=cmd_sort)

    index_parser = bam_subs.add_parser(
        "index", parents=[base_parser], help=CLI_HELP["cmd_index"]
    )
    index_parser.set_defaults(func=cmd_index)

    unindex_parser = bam_subs.add_parser(
        "unindex", parents=[base_parser], help=CLI_HELP["cmd_unindex"]
    )
    unindex_parser.set_defaults(func=cmd_unindex)

    unsort_parser = bam_subs.add_parser(
        "unsort", parents=[base_parser], help=CLI_HELP["cmd_unsort"]
    )
    unsort_parser.set_defaults(func=cmd_unsort)

    tocram_parser = bam_subs.add_parser(
        "to-cram", parents=[base_parser], help=CLI_HELP["cmd_to-cram"]
    )
    tocram_parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    tocram_parser.add_argument("--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)")
    tocram_parser.add_argument(
        "--cram-version",
        choices=["2.1", "3.0", "3.1"],
        default="3.0",
        help="CRAM version to output (default: 3.0 for better compatibility)",
    )
    tocram_parser.set_defaults(func=cmd_tocram)

    tobam_parser = bam_subs.add_parser(
        "to-bam", parents=[base_parser], help=CLI_HELP["cmd_to-bam"]
    )
    tobam_parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    tobam_parser.add_argument("--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)")
    tobam_parser.set_defaults(func=cmd_tobam)

    unalign_parser = bam_subs.add_parser(
        "unalign", parents=[base_parser], help=CLI_HELP["cmd_unalign"]
    )
    unalign_parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    unalign_parser.add_argument("--r2", required=True, help=CLI_HELP["arg_r2"])
    unalign_parser.add_argument("--se", help=CLI_HELP["arg_se"])
    unalign_parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    unalign_parser.add_argument(
        "--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)"
    )
    unalign_parser.set_defaults(func=cmd_unalign)

    identify_parser = bam_subs.add_parser(
        "identify", parents=[base_parser], help=CLI_HELP["cmd_bam-identify"]
    )
    identify_parser.set_defaults(func=cmd_identify)


def get_base_args(args):
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return None

    if not verify_paths_exist({"--input": args.input}):
        return None

    logging.debug(f"Input file: {os.path.abspath(args.input)}")

    threads, memory = get_resource_defaults(args.threads, args.memory)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    try:
        md5_sig = calculate_bam_md5(args.input, None)
        resolved_ref = resolve_reference(args.ref, md5_sig)
        # Ensure it's a file, not a directory
        if resolved_ref and os.path.isdir(resolved_ref):
            from wgsextract_cli.core.utils import REF_GENOME_FILENAMES

            for f in REF_GENOME_FILENAMES:
                potential = os.path.join(resolved_ref, f)
                if os.path.exists(potential):
                    resolved_ref = potential
                    break

        logging.debug(f"Resolved reference: {resolved_ref}")
    except Exception as e:
        logging.error(f"Failed to initialize reference resolution: {e}")
        return None

    paths_to_check = {}
    if resolved_ref:
        paths_to_check["--ref"] = resolved_ref

    # If we still have a directory or None but ref was requested/required, we might fail later
    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, memory, outdir, cram_opt, resolved_ref


def resolve_region_or_gene(args, resolved_ref):
    """Helper to resolve either a raw region or a gene name to coordinates."""
    if args.region:
        return args.region

    if hasattr(args, "gene") and args.gene:
        from wgsextract_cli.core.gene_map import GeneMap

        # Determine reference library directory
        reflib_dir = os.environ.get("WGSE_REFLIB")
        if not reflib_dir and resolved_ref:
            # resolved_ref is usually path/to/reflib/ref/genome.fa
            reflib_dir = os.path.dirname(os.path.dirname(resolved_ref))

        if not reflib_dir:
            logging.error(
                "Reference library not found. Please set WGSE_REFLIB or provide a --ref."
            )
            return None

        gm = GeneMap(reflib_dir)
        # We need a build name. Default to hg38 if we can't detect it.
        build = "hg38"
        if resolved_ref:
            if "hg19" in resolved_ref.lower() or "b37" in resolved_ref.lower():
                build = "hg19"

        resolved_region = gm.get_coords(args.gene, build)
        if resolved_region:
            logging.info(f"Resolved gene {args.gene} to {resolved_region}")
            return resolved_region
        else:
            logging.error(f"Could not resolve gene name: {args.gene}")
            return None

    return None


def cmd_identify(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    logging.debug(f"Input file: {os.path.abspath(args.input)}")

    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")
    logging.debug(f"Resolved reference: {resolved_ref}")

    md5_sig = calculate_bam_md5(args.input, resolved_ref)
    logging.info(
        LOG_MESSAGES["ref_md5_signature"].format(input=args.input, sig=md5_sig)
    )


def cmd_sort(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    region = resolve_region_or_gene(args, resolved_ref)
    if (args.region or (hasattr(args, "gene") and args.gene)) and not region:
        return

    file_size = os.path.getsize(args.input)
    is_cram = args.input.lower().endswith(".cram")
    print_warning(
        "infoFreeSpace", app_name="Coord Sort", file_size=file_size, is_cram=is_cram
    )
    print_warning("GenSortedBAM", threads=threads)

    # Calculate needed space to perform check_free_space
    from wgsextract_cli.core.warnings import get_free_space_needed

    temp_needed, final_needed = get_free_space_needed(file_size, "Coord", is_cram)
    check_free_space(outdir, temp_needed + final_needed)

    out_file = os.path.join(
        outdir,
        os.path.basename(args.input).replace(".bam", "").replace(".cram", "")
        + "_sorted.bam",
    )
    with tempfile.TemporaryDirectory() as tempdir:
        region_args = [region] if region else []
        view_cmd = (
            ["samtools", "view", "-uh", "--no-PG"]
            + cram_opt
            + [args.input]
            + region_args
        )
        sort_cmd = get_sam_sort_cmd(
            out_file,
            threads,
            memory,
            fmt="CRAM" if is_cram else "BAM",
            reference=resolved_ref,
            temp_dir=tempdir,
        )

        logging.info(
            LOG_MESSAGES["sorting_file"].format(input=args.input, output=out_file)
        )
        try:
            p1 = subprocess.Popen(
                view_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            p2 = subprocess.Popen(sort_cmd, stdin=p1.stdout, stderr=subprocess.PIPE)
            if p1.stdout:
                p1.stdout.close()
            _, stderr2 = p2.communicate()
            _, stderr1 = p1.communicate()
            if p2.returncode != 0:
                logging.error(
                    f"Sort failed: {stderr2.decode() if stderr2 else 'Unknown error'}"
                )
                if stderr1:
                    logging.error(f"View error: {stderr1.decode()}")
                import sys

                sys.exit(1)
        except Exception as e:
            logging.error(f"Execution failed: {e}")
            import sys

            sys.exit(1)


def cmd_index(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    print_warning("GenBAMIndex")

    logging.info(LOG_MESSAGES["indexing_file"].format(path=args.input))
    try:
        run_command(get_sam_index_cmd(args.input))
    except Exception as e:
        logging.error(f"Indexing failed: {e}")
        import sys

        sys.exit(1)


def cmd_unindex(args):
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not os.path.exists(args.input) or os.path.isdir(args.input):
        logging.error(f"Input is not a valid file: {args.input}")
        return

    bai = args.input + ".bai"
    crai = args.input + ".crai"
    if os.path.exists(bai):
        os.remove(bai)
        logging.info(
            LOG_MESSAGES["delete_success"].format(filename=os.path.basename(bai))
        )
    if os.path.exists(crai):
        os.remove(crai)
        logging.info(
            LOG_MESSAGES["delete_success"].format(filename=os.path.basename(crai))
        )


def cmd_unsort(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    out_file = os.path.join(
        outdir,
        os.path.basename(args.input).replace(".bam", "").replace(".cram", "")
        + "_unsorted.bam",
    )
    with tempfile.TemporaryDirectory() as tempdir:
        newhead = os.path.join(tempdir, "newhead.sam")

        view_cmd = ["samtools", "view", "-H"] + cram_opt + [args.input]
        try:
            res = subprocess.run(view_cmd, capture_output=True, text=True, check=True)
            header = res.stdout
            header = header.replace("SO:coordinate", "SO:unsorted")

            with open(newhead, "w") as f:
                f.write(header)

            logging.info(
                LOG_MESSAGES["converting_file"].format(
                    input=args.input, output=out_file
                )
            )
            with open(out_file, "w") as f_out:
                subprocess.run(
                    ["samtools", "reheader", newhead, args.input],
                    stdout=f_out,
                    check=True,
                )
        except (subprocess.CalledProcessError, Exception) as e:
            logging.error(f"Failed to unsort {args.input}: {e}")
            import sys

            sys.exit(1)


def cmd_tocram(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    region = resolve_region_or_gene(args, resolved_ref)
    if (args.region or (hasattr(args, "gene") and args.gene)) and not region:
        return

    print_warning("BAMtoCRAM", threads=threads)

    out_file = os.path.join(
        outdir, os.path.basename(args.input).replace(".bam", "") + ".cram"
    )
    logging.info(
        LOG_MESSAGES["converting_file"].format(input=args.input, output=out_file)
    )
    try:
        region_args = [region] if region else []
        run_command(
            [
                "samtools",
                "view",
                "-Ch",
                "--output-fmt-option",
                f"version={args.cram_version}",
            ]
            + cram_opt
            + ["-@", threads, "-o", out_file, args.input]
            + region_args
        )
        run_command(get_sam_index_cmd(out_file))
    except Exception as e:
        logging.error(f"Conversion to CRAM failed: {e}")
        import sys

        sys.exit(1)


def cmd_tobam(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    region = resolve_region_or_gene(args, resolved_ref)
    if (args.region or (hasattr(args, "gene") and args.gene)) and not region:
        return

    print_warning("CRAMtoBAM", threads=threads)

    out_file = os.path.join(
        outdir, os.path.basename(args.input).replace(".cram", "") + ".bam"
    )
    logging.info(
        LOG_MESSAGES["converting_file"].format(input=args.input, output=out_file)
    )
    try:
        region_args = [region] if region else []
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_file, args.input]
            + region_args
        )
        run_command(get_sam_index_cmd(out_file))
    except Exception as e:
        logging.error(f"Conversion to BAM failed: {e}")
        import sys

        sys.exit(1)


def cmd_unalign(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    region = resolve_region_or_gene(args, resolved_ref)
    if (args.region or (hasattr(args, "gene") and args.gene)) and not region:
        return

    file_size = os.path.getsize(args.input)
    is_cram = args.input.lower().endswith(".cram")
    print_warning(
        "infoFreeSpace", app_name="Name Sort", file_size=file_size, is_cram=is_cram
    )
    print_warning("ButtonUnalignBAM", threads=threads)

    # Calculate needed space to perform check_free_space
    from wgsextract_cli.core.warnings import get_free_space_needed

    temp_needed, final_needed = get_free_space_needed(file_size, "Name", is_cram)
    check_free_space(outdir, temp_needed + final_needed)

    # Resolve output paths
    out_r1 = args.r1 if os.path.isabs(args.r1) else os.path.join(outdir, args.r1)
    out_r2 = args.r2 if os.path.isabs(args.r2) else os.path.join(outdir, args.r2)

    out_se = "/dev/null"
    if args.se:
        out_se = args.se if os.path.isabs(args.se) else os.path.join(outdir, args.se)

    se_arg = ["-0", out_se]

    with tempfile.TemporaryDirectory() as tempdir:
        region_args = [region] if region else []
        view_cmd = (
            ["samtools", "view", "-uh", "--no-PG"]
            + cram_opt
            + [args.input]
            + region_args
        )
        sort_cmd = get_sam_sort_cmd(
            "-",  # output to stdout
            threads,
            memory,
            fmt="SAM",
            name_sort=True,
            temp_dir=tempdir,
        )
        fastq_cmd = (
            ["samtools", "fastq", "-1", out_r1, "-2", out_r2]
            + se_arg
            + ["-s", "/dev/null", "-n", "-@", threads, "-"]
        )

        logging.info(LOG_MESSAGES["unaligning_reads"])
        try:
            p1 = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(sort_cmd, stdin=p1.stdout, stdout=subprocess.PIPE)
            if p1.stdout:
                p1.stdout.close()
            p3 = subprocess.Popen(fastq_cmd, stdin=p2.stdout)
            if p2.stdout:
                p2.stdout.close()
            p3.communicate()
            if p3.returncode != 0:
                logging.error("Unalign failed.")
                import sys

                sys.exit(1)
        except Exception as e:
            logging.error(f"Unalign failed: {e}")
            import sys

            sys.exit(1)
