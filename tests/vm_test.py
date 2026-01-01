#!/usr/bin/env python3
import sys
from pathlib import Path

#######################################
# Buggy, doesn't work correctly, WIP.
#######################################

# Ensure repo root is in sys.path so we can import tests.vm_testing
# This allows running as ./tests/vm_test.py or python3 tests/vm_test.py
current_file = Path(__file__).resolve()
repo_root = current_file.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import argparse
import subprocess
from tests.vm_testing.core import IMAGES
from tests.vm_testing.utils import cleanup_stale_vms, run_release_script
from tests.vm_testing.suites import run_platform_test, run_aptfile_test, run_dev_scripts_test
from tests.download_test_cache import main as download_cache

def main():
    parser = argparse.ArgumentParser(description="WGS Extract VM Installation Test System")
    parser.add_argument("--platform", choices=["ubuntu", "fedora", "macos", "all"], default="all",
                        help="Platform to test (default: all)")
    parser.add_argument("--no-release", action="store_true", help="Skip running release.py")
    parser.add_argument("--setup-only", action="store_true", help="Only setup Tart and pull images")
    parser.add_argument("--test-aptfile", action="store_true", help="Test Aptfile installation on Ubuntu")
    parser.add_argument("--test-dev", action="store_true", help="Test dev_init.py and dev_launch.py on Ubuntu/MacOS")
    parser.add_argument("--gui", action="store_true", help="Run VM with GUI enabled (and install desktop env on Linux)")
    
    args = parser.parse_args()

    try:
        # Check for Virtualization Backend
        if sys.platform != "win32":
            # Check for Tart
            res = subprocess.run(["command", "-v", "tart"], shell=True, capture_output=True)
            if res.returncode != 0:
                print("[*] Tart not found. Installing via Homebrew...")
                subprocess.run(["brew", "install", "cirruslabs/cli/tart"], check=True)
        else:
            # Check for WSL
            res = subprocess.run(["wsl", "--status"], shell=True, capture_output=True)
            if res.returncode != 0:
                print("[!] WSL is not installed or not working. Please enable WSL2.")
                sys.exit(1)

        if args.setup_only:
            # Setup logic depends on backend.
            if sys.platform != "win32":
                for img in IMAGES.values():
                    print(f"[*] Pulling {img}...")
                    subprocess.run(["tart", "pull", img])
            else:
                from tests.vm_testing.wsl import WSLImageManager
                mgr = WSLImageManager()
                # Pre-download supported images
                for p in ["ubuntu", "fedora"]:
                    print(f"[*] Pre-fetching rootfs for {p}...")
                    try:
                        mgr.get_image_path(p)
                    except Exception as e:
                        print(f"[!] Failed to fetch {p}: {e}")
            return

        # Clean up any mess from before
        cleanup_stale_vms()

        if args.test_aptfile:
            success = run_aptfile_test()
            sys.exit(0 if success else 1)

        if args.test_dev:
            print("[*] Verifying test artifact cache...")
            download_cache()

            target_platforms = ["ubuntu", "macos"]
            if args.platform != "all":
                target_platforms = [p for p in target_platforms if p == args.platform]
                if not target_platforms:
                     print(f"[!] Platform {args.platform} not supported for dev tests (only ubuntu/macos).")
                     sys.exit(1)
            
            if sys.platform == "win32":
                target_platforms = [p for p in target_platforms if p != "macos"]
                if not target_platforms and args.platform == "macos":
                     print("[!] MacOS dev tests not supported on Windows.")
                     sys.exit(1)

            results = {}
            for p in target_platforms:
                results[p] = run_dev_scripts_test(p)
            
            print("\n" + "="*50)
            print("DEV TEST RESULTS SUMMARY")
            print("="*50)
            for p, success in results.items():
                status = "PASSED" if success else "FAILED"
                print(f"{p.ljust(10)}: {status}")
            print("="*50)
            
            cleanup_stale_vms()
            sys.exit(0 if all(results.values()) else 1)

        if not args.no_release:
            run_release_script()

        platforms = ["ubuntu", "fedora", "macos"] if args.platform == "all" else [args.platform]
        
        if sys.platform == "win32":
            platforms = [p for p in platforms if p != "macos"]

        results = {}
        for p in platforms:
            results[p] = run_platform_test(p, gui=args.gui)

        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        for p, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"{p.ljust(10)}: {status}")
        print("="*50)

        # Final sweep
        cleanup_stale_vms()

        if not all(results.values()):
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user. Cleaning up...")
        cleanup_stale_vms()
        sys.exit(130)

if __name__ == "__main__":
    main()
