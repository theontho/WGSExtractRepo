#!/usr/bin/env python3
import sys
import os
import argparse

# Ensure the repository root is in sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.append(repo_root)

def main():
    parser = argparse.ArgumentParser(description="WGS Extract Dev Tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    subparsers.add_parser("init", help="Initialize development environment")
    # launch
    subparsers.add_parser("launch", help="Launch WGS Extract")
    # library
    subparsers.add_parser("library", help="Launch WGS Extract Library")
    # release-cache
    subparsers.add_parser("release-cache", help="Setup local release override/cache")
    # release
    release_parser = subparsers.add_parser("release", help="Create WGSExtract release packages")
    release_parser.add_argument("-ro", "--release-override", action="store_true", help="Use release-override.json from repo root")

    args = parser.parse_args()

    if args.command == "init":
        from dev.init_dev import main as init_main
        init_main()
    elif args.command == "launch":
        from dev.launch import main as launch_main
        launch_main()
    elif args.command == "library":
        from dev.launch_library import main as library_main
        library_main()
    elif args.command == "release-cache":
        from dev.setup_release_local import setup_local_release
        setup_local_release()
    elif args.command == "release":
        from dev.release import create_release
        create_release(use_override=args.release_override)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
