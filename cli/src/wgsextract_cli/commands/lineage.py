import logging
import os

from wgsextract_cli.core.dependencies import get_tool_path, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import run_command, verify_paths_exist


def register(subparsers, base_parser):
    parser = subparsers.add_parser("lineage", help="Executes Yleaf or Haplogrep.")
    lin_subs = parser.add_subparsers(dest="lin_cmd", required=True)

    ydna_parser = lin_subs.add_parser(
        "y-dna", parents=[base_parser], help=CLI_HELP["cmd_lineage-y"]
    )
    ydna_parser.add_argument(
        "--yleaf-path", help="Path to yleaf.py (optional if in PATH)"
    )
    ydna_parser.add_argument("--pos-file", required=True, help="Yleaf position file")
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

    if not verify_paths_exist(
        {
            "--input": args.input,
            "--yleaf-path": yleaf_path,
            "--pos-file": args.pos_file,
        }
    ):
        return

    logging.info(LOG_MESSAGES["running_yleaf"].format(input=args.input))
    try:
        # Check if yleaf_path is a python script or a wrapper
        cmd = [yleaf_path]
        if yleaf_path.endswith(".py"):
            cmd = ["python3", yleaf_path]

        run_command(
            cmd
            + [
                "-input",
                args.input,
                "-pos",
                args.pos_file,
                "-out",
                args.outdir,
            ]
        )
    except Exception as e:
        logging.error(f"Yleaf failed: {e}")


def cmd_mtdna(args):
    # Check dependencies
    if not args.haplogrep_path:
        verify_dependencies(["haplogrep"])

    haplogrep_path = args.haplogrep_path or get_tool_path("haplogrep")

    if not verify_paths_exist(
        {"--input": args.input, "--haplogrep-path": haplogrep_path}
    ):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    out_file = os.path.join(outdir, "haplogrep_results.txt")
    logging.info(LOG_MESSAGES["running_haplogrep"].format(input=args.input))
    try:
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
                args.input,
                "--out",
                out_file,
            ]
        )
    except Exception as e:
        logging.error(f"Haplogrep failed: {e}")
