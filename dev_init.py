#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

MANIFEST = "installer_scripts/release.json"
TMP_DIR = Path("tmp")

def run_command(cmd, shell=False, check=True):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)

def install_system_packages():
    print("=== Checking System Packages ===")
    if sys.platform == "darwin":
        # MacOS
        try:
            run_command(["brew", "--version"])
        except FileNotFoundError:
            print("Homebrew not found. Please install Homebrew first.")
            return

        brewfile = Path("Brewfile")
        if brewfile.exists():
            print("Installing system packages from Brewfile...")
            run_command(["brew", "bundle", "--file", str(brewfile)])
        else:
            print("Warning: Brewfile not found. Falling back to manual installation.")
            packages = ["jq", "samtools", "bcftools", "bwa", "sevenzip"]
            for pkg in packages:
                print(f"Checking {pkg}...")
                res = subprocess.run(["brew", "list", pkg], capture_output=True)
                if res.returncode != 0:
                    print(f"Installing {pkg}...")
                    run_command(["brew", "install", pkg])
    elif sys.platform.startswith("linux"):
        # Ubuntu/Debian assumed
        try:
            run_command(["apt", "--version"])
            packages = ["jq", "samtools", "bcftools", "bwa", "p7zip-full", "python3-pip", "python3-tk", "python3-pil", "python3-pil.imagetk", "openjdk-17-jre"]
            print("Updating apt...")
            subprocess.run(["sudo", "apt", "update"])
            for pkg in packages:
                print(f"Checking {pkg}...")
                res = subprocess.run(["dpkg", "-s", pkg], capture_output=True)
                if res.returncode != 0:
                    print(f"Installing {pkg}...")
                    run_command(["sudo", "apt", "install", "-y", pkg])
        except FileNotFoundError:
            print("Apt not found. Skipping system package installation.")

def check_uv():
    print("=== Checking for uv ===")
    try:
        run_command(["uv", "--version"])
        return True
    except FileNotFoundError:
        print("uv not found. Please install uv (see https://github.com/astral-sh/uv).")
        return False

def setup_venv():
    print("=== Setting up Virtual Environment ===")
    if not Path(".venv").exists():
        print("Creating virtual environment...")
        run_command(["uv", "venv"])
    else:
        print("Virtual environment already exists.")

def install_python_dependencies():
    print("=== Installing Python Dependencies with uv ===")
    # Use uv pip install which is part of the venv workflow
    run_command(["uv", "pip", "install", "-e", "."])
    if sys.platform == "darwin":
        run_command(["uv", "pip", "install", "-e", ".[macos]"])

def download_and_extract(pack, manifest_data):
    if pack not in manifest_data:
        print(f"Warning: No entry for '{pack}' in manifest.")
        return

    url = manifest_data[pack].get("URL")
    if not url:
        print(f"Warning: No URL found for '{pack}'")
        return

    filename = url.split("/")[-1]
    dest_path = TMP_DIR / filename
    
    print(f"--- Preparing {pack} ---")
    if dest_path.exists():
        print(f"Found existing {dest_path}, skipping download...")
    else:
        print(f"Downloading {pack} from {url}...")
        run_command(["curl", "-L", "-o", str(dest_path), url])

    print(f"Extracting {pack}...")
    if sys.platform == "darwin":
        # Extract using 7zz if available, else unzip
        try:
            run_command(["7zz", "x", "-y", str(dest_path)])
        except FileNotFoundError:
            run_command(["unzip", "-o", str(dest_path)])
    elif sys.platform.startswith("linux"):
        try:
            run_command(["7z", "x", "-y", str(dest_path)])
        except FileNotFoundError:
            run_command(["unzip", "-o", str(dest_path)])
    elif sys.platform in ["win32", "cygwin", "msys"]:
        run_command(["powershell", "-Command", f"Expand-Archive -Path '{dest_path}' -DestinationPath './' -Force"])
    else:
        run_command(["unzip", "-o", str(dest_path)])

    # Clean up nested folder if it exists
    nested = Path("WGSExtractv4")
    if nested.exists() and nested.is_dir():
        print("Cleaning up nested extraction folder...")
        for item in nested.iterdir():
            dest = Path(".") / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        shutil.rmtree(nested)

def main():
    print("==========================================")
    print("WGS Extract Development Environment Init")
    print("==========================================")

    TMP_DIR.mkdir(exist_ok=True)

    if not os.path.exists(MANIFEST):
        print(f"Error: {MANIFEST} not found.")
        sys.exit(1)

    with open(MANIFEST, "r") as f:
        manifest_data = json.load(f)

    if not check_uv():
        sys.exit(1)

    install_system_packages()
    setup_venv()
    install_python_dependencies()

    download_and_extract("reflib", manifest_data)
    download_and_extract("tools", manifest_data)

    # Merge base_reference into reference
    base_ref = Path("base_reference")
    ref = Path("reference")
    if base_ref.exists():
        print("Merging base_reference into reference...")
        ref.mkdir(exist_ok=True)
        for item in base_ref.iterdir():
            dest = ref / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    if sys.platform in ["cygwin", "msys", "win32"]:
        print("\nDetected Windows environment.")
        print("1) Cygwin64")
        print("2) MSYS2")
        choice = input("Enter choice [1-2]: ")
        if choice == "1":
            download_and_extract("cygwin64", manifest_data)
            download_and_extract("bioinfo", manifest_data)
        elif choice == "2":
            download_and_extract("msys2", manifest_data)
            download_and_extract("bioinfo-msys2", manifest_data)
        else:
            print("Invalid choice. Skipping platform-specific dependencies.")

    print("\n==========================================")
    print("Initialization Complete!")
    print("==========================================")

if __name__ == "__main__":
    main()
