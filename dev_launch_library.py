#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    if sys.platform == "darwin":
        print("Launching WGS Extract Library for MacOS...")
        # Note: Library.command might also need uv run internally or we wrap it here
        subprocess.run(["uv", "run", "bash", "installer_scripts/Library.command"])
    elif sys.platform.startswith("linux"):
        # Check for ubuntu
        try:
            with open("/etc/os-release", "r") as f:
                os_release = f.read().lower()
            if "ubuntu" in os_release:
                print("Launching WGS Extract Library for Ubuntu...")
                subprocess.run(["uv", "run", "bash", "installer_scripts/Library_ubuntu.sh"])
            else:
                print("Launching WGS Extract Library for Linux...")
                subprocess.run(["uv", "run", "bash", "installer_scripts/Library_linux.sh"])
        except FileNotFoundError:
            print("Launching WGS Extract Library for Linux...")
            subprocess.run(["uv", "run", "bash", "installer_scripts/Library_linux.sh"])
    elif sys.platform in ["win32", "cygwin", "msys"]:
        print("Launching WGS Extract Library for Windows...")
        subprocess.run(["uv", "run", "cmd.exe", "/c", "installer_scripts\\Library.bat"])
    else:
        print(f"Unsupported OS: {sys.platform}")
        sys.exit(1)

if __name__ == "__main__":
    main()
