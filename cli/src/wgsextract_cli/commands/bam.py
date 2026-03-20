import logging
import os
import subprocess
import tempfile

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    get_chr_name,
    get_resource_defaults,
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
    tobam_parser.set_defaults(func=cmd_tobam)

    unalign_parser = bam_subs.add_parser(
        "unalign", parents=[base_parser], help=CLI_HELP["cmd_unalign"]
    )
    unalign_parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    unalign_parser.add_argument("--r2", required=True, help=CLI_HELP["arg_r2"])
    unalign_parser.add_argument("--se", help=CLI_HELP["arg_se"])
    unalign_parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
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
        logging.debug(f"Resolved reference: {resolved_ref}")
    except Exception as e:
        logging.error(f"Failed to initialize reference resolution: {e}")
        return None

    paths_to_check = {}
    if resolved_ref:
        paths_to_check["--ref"] = resolved_ref

    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, memory, outdir, cram_opt, resolved_ref


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
        region_args = [args.region] if args.region else []
        view_cmd = (
            ["samtools", "view", "-uh", "--no-PG"]
            + cram_opt
            + [args.input]
            + region_args
        )
        sort_cmd = [
            "samtools",
            "sort",
            "-T",
            tempdir,
            "-m",
            memory,
            "-@",
            threads,
            "-o",
            out_file,
        ]

        logging.info(
            LOG_MESSAGES["sorting_file"].format(input=args.input, output=out_file)
        )
        try:
            p1 = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(sort_cmd, stdin=p1.stdout)
            if p1.stdout:
                p1.stdout.close()
            p2.communicate()
            if p2.returncode != 0:
                logging.error("Sort failed.")
        except Exception as e:
            logging.error(f"Execution failed: {e}")


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
        run_command(["samtools", "index", args.input])
    except Exception as e:
        logging.error(f"Indexing failed: {e}")


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
            run_command(
                ["samtools", "reheader", newhead, args.input],
                stdout=open(out_file, "w"),
            )
        except (subprocess.CalledProcessError, Exception) as e:
            logging.error(f"Failed to unsort {args.input}: {e}")


def cmd_tocram(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    print_warning("BAMtoCRAM", threads=threads)

    out_file = os.path.join(
        outdir, os.path.basename(args.input).replace(".bam", "") + ".cram"
    )
    logging.info(
        LOG_MESSAGES["converting_file"].format(input=args.input, output=out_file)
    )
    try:
        region_args = [args.region] if args.region else []
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
        run_command(["samtools", "index", out_file])
    except Exception as e:
        logging.error(f"Conversion to CRAM failed: {e}")


def cmd_tobam(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

    print_warning("CRAMtoBAM", threads=threads)

    out_file = os.path.join(
        outdir, os.path.basename(args.input).replace(".cram", "") + ".bam"
    )
    logging.info(
        LOG_MESSAGES["converting_file"].format(input=args.input, output=out_file)
    )
    try:
        region_args = [args.region] if args.region else []
        run_command(
            ["samtools", "view", "-bh"]
            + cram_opt
            + ["-@", threads, "-o", out_file, args.input]
            + region_args
        )
        run_command(["samtools", "index", out_file])
    except Exception as e:
        logging.error(f"Conversion to BAM failed: {e}")


def cmd_unalign(args):
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, memory, outdir, cram_opt, resolved_ref = base

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

    se_arg = ["-0", args.se] if args.se else ["-0", "/dev/null"]

    with tempfile.TemporaryDirectory() as tempdir:
        region_args = [args.region] if args.region else []
        view_cmd = (
            ["samtools", "view", "-uh", "--no-PG"]
            + cram_opt
            + [args.input]
            + region_args
        )
        sort_cmd = [
            "samtools",
            "sort",
            "-n",
            "-T",
            tempdir,
            "-m",
            memory,
            "-@",
            threads,
            "-O",
            "sam",
        ]
        fastq_cmd = (
            ["samtools", "fastq", "-1", args.r1, "-2", args.r2]
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
        except Exception as e:
            logging.error(f"Unalign failed: {e}")
