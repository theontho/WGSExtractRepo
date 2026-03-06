#!/usr/bin/env python3

import argparse
import logging
import os

from dotenv import load_dotenv

from .commands import (
    align,
    bam,
    extract,
    info,
    lineage,
    microarray,
    pet,
    qc,
    ref,
    repair,
    vcf,
    vep,
)
from .core.messages import CLI_HELP


def main():
    # Load environment variables
    if os.environ.get("WGSE_SKIP_DOTENV") != "1":
        cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        env_local = os.path.join(cli_root, ".env.local")
        env_std = os.path.join(cli_root, ".env")
        if os.path.exists(env_local):
            load_dotenv(dotenv_path=env_local)
        if os.path.exists(env_std):
            load_dotenv(dotenv_path=env_std)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 1. Create a parent parser for shared arguments
    # This allows arguments like --input to be placed AFTER the subcommand
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("WGSE_DEBUG") == "1",
        help=CLI_HELP["arg_debug"],
    )
    base_parser.add_argument(
        "--input",
        "-i",
        default=os.environ.get("WGSE_INPUT"),
        help=CLI_HELP["arg_input"],
    )
    base_parser.add_argument(
        "--outdir",
        "-o",
        default=os.environ.get("WGSE_OUTDIR"),
        help=CLI_HELP["arg_outdir"],
    )
    base_parser.add_argument(
        "--ref",
        default=os.environ.get("WGSE_REF"),
        help=CLI_HELP["arg_ref"],
    )
    base_parser.add_argument(
        "--threads",
        "-t",
        type=int,
        default=os.environ.get("WGSE_THREADS"),
        help=CLI_HELP["arg_threads"],
    )
    base_parser.add_argument(
        "--memory",
        "-m",
        default=os.environ.get("WGSE_MEMORY"),
        help=CLI_HELP["arg_memory"],
    )

    # 2. Main parser
    parser = argparse.ArgumentParser(
        description=CLI_HELP["description"], parents=[base_parser]
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, title="subcommands"
    )

    # UI Commands
    gui_parser = subparsers.add_parser("gui", help=CLI_HELP["cmd_gui"])
    gui_parser.set_defaults(
        func=lambda args: __import__("wgsextract_cli.ui.gui", fromlist=["main"]).main()
    )

    # 3. Register all subcommands, passing the base_parser as a parent
    for cmd_module in [
        info,
        bam,
        extract,
        microarray,
        lineage,
        vcf,
        repair,
        qc,
        ref,
        align,
        pet,
        vep,
    ]:
        cmd_module.register(subparsers, base_parser)

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
