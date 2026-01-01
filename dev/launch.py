#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    if sys.platform == "darwin":
        print("Launching WGS Extract for MacOS...")
        subprocess.run(["uv", "run", "bash", "installer_scripts/WGSExtract.command"])
    elif sys.platform.startswith("linux"):
        # Check for ubuntu
        try:
            with open("/etc/os-release", "r") as f:
                os_release = f.read().lower()
            if "ubuntu" in os_release:
                print("Launching WGS Extract for Ubuntu...")
                subprocess.run(["uv", "run", "bash", "installer_scripts/WGSExtract_ubuntu.sh"])
            else:
                print("Launching WGS Extract for Linux...")
                subprocess.run(["uv", "run", "bash", "installer_scripts/WGSExtract_linux.sh"])
        except FileNotFoundError:
            print("Launching WGS Extract for Linux...")
            subprocess.run(["uv", "run", "bash", "installer_scripts/WGSExtract_linux.sh"])
    elif sys.platform in ["win32", "cygwin", "msys"]:
        print("Launching WGS Extract for Windows...")
        # Run directly from root for dev environment compatibility
        subprocess.run(["uv", "run", "python", "program/wgsextract.py"])
    else:
        print(f"Unsupported OS: {sys.platform}")
        sys.exit(1)

if __name__ == "__main__":
    main()
