#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "installer_scripts" / "release.json"
CACHE_DIR = REPO_ROOT / "download_tmp"

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    print("==========================================")
    print("WGS Extract Test Cache Downloader")
    print("==========================================")
    
    if not MANIFEST_PATH.exists():
        print(f"Error: {MANIFEST_PATH} not found.")
        return

    CACHE_DIR.mkdir(exist_ok=True)

    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)

    # Identify keys with "URL"
    for key, value in data.items():
        if isinstance(value, dict) and "URL" in value:
            url = value["URL"]
            filename = url.split("/")[-1]
            dest = CACHE_DIR / filename
            
            print(f"\n[-] Checking {key}...")
            if dest.exists():
                print(f"    [+] {filename} already exists. Skipping.")
            else:
                print(f"    [*] Downloading {url}...")
                try:
                    run_command(["curl", "-L", "-o", str(dest), url])
                except subprocess.CalledProcessError:
                    print(f"    [!] Failed to download {url}")

    print("\n==========================================")
    print("Download Cache Complete")
    print("==========================================")

if __name__ == "__main__":
    main()
