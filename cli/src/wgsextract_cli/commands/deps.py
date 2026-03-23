import logging

from wgsextract_cli.core.dependencies import check_all_dependencies
from wgsextract_cli.core.messages import CLI_HELP


def register(subparsers, base_parser):
    deps_parser = subparsers.add_parser(
        "deps", parents=[base_parser], help=CLI_HELP["cmd_deps"]
    )
    deps_subparsers = deps_parser.add_subparsers(dest="subcommand", required=True)

    check_parser = deps_subparsers.add_parser(
        "check", parents=[base_parser], help=CLI_HELP["cmd_check-deps"]
    )
    check_parser.add_argument(
        "--tool", help="Check for a specific tool and return exit code 1 if missing."
    )
    check_parser.set_defaults(func=run)


def run(args):
    if args.tool:
        from wgsextract_cli.core.dependencies import get_tool_path

        path = get_tool_path(args.tool)
        if path:
            if not args.debug:
                print(path)
            else:
                logging.debug(f"Found {args.tool} at {path}")
            return
        else:
            if not args.debug:
                logging.error(f"Tool not found: {args.tool}")
            import sys

            sys.exit(1)

    logging.info("Verifying bioinformatics tool installations...")
    results = check_all_dependencies()

    print("\nMandatory Tools:")
    print("-" * 60)
    all_mandatory_present = True
    for tool in results["mandatory"]:
        status = "✅" if tool["path"] else "❌"
        version = f" ({tool['version']})" if tool["version"] else ""
        print(f"{status} {tool['name']:<20} {version}")
        if not tool["path"]:
            all_mandatory_present = False

    print("\nOptional Tools:")
    print("-" * 60)
    for tool in results["optional"]:
        status = "✅" if tool["path"] else "⚠️ "
        version = f" ({tool['version']})" if tool["version"] else ""
        print(f"{status} {tool['name']:<20} {version}")

    print("\n" + "=" * 60)
    if all_mandatory_present:
        logging.info("All mandatory tools verified successfully.")
    else:
        logging.error(
            "Some mandatory tools are missing. Please install them to ensure full functionality."
        )
