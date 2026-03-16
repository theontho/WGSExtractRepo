#!/usr/bin/env python3

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from .commands import (
    align,
    bam,
    deps,
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


class EmojiFormatter(logging.Formatter):
    """Custom formatter to add emojis to log levels."""

    LEVEL_EMOJIS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨",
    }

    def format(self, record):
        level_fmt = self.LEVEL_EMOJIS.get(record.levelno, record.levelname)
        record.levelname = level_fmt
        return super().format(record)


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

    handler = logging.StreamHandler()
    handler.setFormatter(EmojiFormatter("%(levelname)s: %(message)s"))
    # Use force=True to ensure our handler replaces any existing ones
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

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
    base_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help="Input VCF file path.",
    )
    base_parser.add_argument(
        "--mother",
        default=os.environ.get("WGSE_MOTHER_VCF"),
        help="Mother VCF file path for trio analysis.",
    )
    base_parser.add_argument(
        "--father",
        default=os.environ.get("WGSE_FATHER_VCF"),
        help="Father VCF file path for trio analysis.",
    )
    base_parser.add_argument(
        "--parent-pid",
        type=int,
        help="Parent Process ID to monitor. If the parent dies, this process will exit.",
    )

    # 2. Main parser
    parser = argparse.ArgumentParser(
        description=CLI_HELP["description"], parents=[base_parser]
    )
    parser.add_argument(
        "--full-help",
        action="store_true",
        help=CLI_HELP["arg_full_help"],
    )
    subparsers = parser.add_subparsers(
        dest="command", required=False, title="subcommands"
    )

    # UI Commands
    gui_parser = subparsers.add_parser("gui", help=CLI_HELP["cmd_gui"])
    gui_parser.set_defaults(
        func=lambda args: __import__("wgsextract_cli.ui.gui", fromlist=["main"]).main()
    )

    webgui_parser = subparsers.add_parser("web-gui", help="Start the Web-based GUI.")
    webgui_parser.set_defaults(
        func=lambda args: __import__(
            "wgsextract_cli.ui.web_gui", fromlist=["main"]
        ).main()
    )

    # 3. Register all subcommands, passing the base_parser as a parent
    for cmd_module in [
        info,
        deps,
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

    if args.full_help:
        parser.print_help()
        print("\n" + "=" * 80)
        print("SUBCOMMAND DETAILS")
        print("=" * 80)
        # Sort subcommands alphabetically for better readability
        for name in sorted(subparsers.choices.keys()):
            subparser = subparsers.choices[name]
            print(f"\n--- {name} ---")
            subparser.print_help()
        sys.exit(0)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle signals for clean exit (allows finally blocks to run)
    import signal

    from .core.utils import cleanup_processes

    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, cleaning up...")
        cleanup_processes()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Parental monitoring
    if args.parent_pid:
        import threading
        import time

        def monitor_parent():
            while True:
                try:
                    # os.kill(pid, 0) is a standard way to check if a process is alive
                    os.kill(args.parent_pid, 0)
                except OSError:
                    logging.warning(
                        f"Parent process {args.parent_pid} disappeared, exiting..."
                    )
                    cleanup_processes()
                    os._exit(
                        1
                    )  # Use os._exit to bypass any other cleanup and exit immediately
                time.sleep(2)

        monitor_thread = threading.Thread(target=monitor_parent, daemon=True)
        monitor_thread.start()

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
