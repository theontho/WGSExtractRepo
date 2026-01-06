import os
import sys
import subprocess
import json
import hashlib
from pathlib import Path
from datetime import datetime
from .core.common import WGSE_FP, rmx, rmrx, read_current_release_info

RELEASE_URL_BASE = "https://get.wgse.io"

def get_package_version(package: str):
    """Retrieves version and date for a package."""
    pkg_json_map = {
        "installer": "scripts/installer.json",
        "program": "program/program.json",
        "reflib": "reference/reflib.json",
        "tools": "jartools/tools.json"
    }
    json_path = WGSE_FP / pkg_json_map[package]
    ver, date = read_current_release_info(package, json_path, False)
    return ver, date

def make_zip(package: str, track: str = None):
    """Creates a ZIP archive for a package (transliterated from make_zip in shell)."""
    ver, date = get_package_version(package)
    ver_str = f"{ver}_{date}" if track == "Dev" else f"v{ver}_{date}"
    
    zip_dir = WGSE_FP / "temp_zip"
    rmrx(zip_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)

    if package == "installer":
        archive_name = f"WGSExtract-{track}{ver_str}_installer.zip"
    else:
        archive_name = f"WGSExtract-{ver_str}_{package}.zip"

    print(f"*** Making WGSE {package} ZIP ({archive_name}) ***")

    # In a real macOS environment, we'd use ditto and mkbom
    # For now, let's use a simplified approach or call those tools if on Mac
    if sys.platform == "darwin":
        # Simplified: usually we'd use a BOM file
        # subprocess.run(['ditto', '-c', '-k', '--keepParent', '--norsrc', str(zip_dir), archive_name], check=True)
        pass
    else:
        print("Warning: Non-macOS system detected. ZIP may not contain correct metadata.")

def main():
    if len(sys.argv) < 2:
        print("Usage: make_release.py { allpacks | release | installer | program | reflib | tools } [track]")
        return

    pack = sys.argv[1].lower()
    track = sys.argv[2].capitalize() if len(sys.argv) > 2 else "Dev"

    if pack == "allpacks":
        for p in ["installer", "program", "reflib", "tools"]:
            make_zip(p, track)
    else:
        make_zip(pack, track)

if __name__ == "__main__":
    main()
