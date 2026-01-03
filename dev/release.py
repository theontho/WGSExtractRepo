#!/usr/bin/env -S uv run python3
import os
import shutil
import json
import zipfile
from datetime import datetime
import pathspec
from typing import List

def copy_and_ensure_lf(src: str, dst: str) -> None:
    """Copy a file and ensure it has LF line endings if it is a shell script."""
    if src.endswith(('.sh', '.command')):
        with open(src, 'rb') as f:
            content = f.read()
        # Convert CRLF to LF
        new_content = content.replace(b'\r\n', b'\n')
        with open(dst, 'wb') as f:
            f.write(new_content)
        # Preserve permissions
        shutil.copymode(src, dst)
    else:
        shutil.copy2(src, dst)

import argparse

def create_release(use_override: bool = False, use_new_scripts: bool = False, verbose: bool = False) -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    build_dir = os.path.join(repo_root, "build")
    
    if use_override:
        manifest_path = os.path.join(repo_root, "release-override.json")
    else:
        manifest_path = os.path.join(repo_root, "release.json")

    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found at {manifest_path}")
        return

    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Load .gitignore patterns
    gitignore_path = os.path.join(repo_root, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
    else:
        spec = None

    # Use version key for the release package naming
    version = manifest.get("version", {}).get("version", "unknown")
    date = manifest.get("version", {}).get("date", datetime.now().strftime("%d%b%Y"))

    platforms = {
        "macos": {"install": "Install_macos.command", "uninstall": "Uninstall_macos.command"},
        "macos_brew": {"install": "Install_macos_brew.command", "uninstall": "Uninstall_macos_brew.command"},
        "linux": {"install": "Install_linux.sh", "uninstall": "Uninstall_linux.sh"},
        "ubuntu": {"install": "Install_ubuntu.sh", "uninstall": "Uninstall_ubuntu.sh"},
        "windows": {"install": "Install_windows.bat", "uninstall": "Uninstall_windows.bat"}
    }

    # Directories to include
    include_dirs = ["program", "scripts", "docs", "installer_scripts"]
    if use_new_scripts:
        include_dirs.append("new_scripts")
        include_dirs.append("bootstrap_scripts")
    
    # Files to be moved into docs/ inside the ZIP
    docs_files = ["LICENSE.txt", "CHANGELOG.md"]

    # Help determine ignored files using .gitignore
    def ignore_patterns(path: str, names: List[str]) -> List[str]:
        rel_path = os.path.relpath(path, repo_root)
        if rel_path == ".":
            rel_path = ""
        
        # Whitelist specific directories to bypass .gitignore (binary dependencies)
        whitelist_prefixes = ["jartools", "FastQC", "yleaf", "reference", "base_reference"]
        # Check if we are inside or matching a whitelisted directory
        # rel_path might be "jartools" or "" (if matching "jartools" in names)
        
        ignored = []
        for name in names:
            full_rel_path = os.path.join(rel_path, name)
            
            # Start checks
            
            # Basic hardcoded ignores that should always be ignored for release
            if name.startswith('.') and name != ".": # . is not a name usually
                 pass # check specifically for .git, .DS_Store etc
            
            if name in ["download_tmp", "build", "__pycache__", ".git", ".DS_Store", ".venv", "venv", ".idea", ".vscode"]:
                ignored.append(name)
                continue
            
            if name.endswith(".pyc"):
                ignored.append(name)
                continue

            # Bypass gitignore for whitelisted paths
            is_whitelisted = False
            for wp in whitelist_prefixes:
                # If full_rel_path starts with whitelisted prefix
                # e.g. "jartools" or "jartools/haplogrep.jar"
                if full_rel_path == wp or full_rel_path.startswith(wp + os.sep):
                    is_whitelisted = True
                    break
            
            if is_whitelisted:
                continue

            # Use pathspec if available
            if spec:
                is_dir = os.path.isdir(os.path.join(path, name))
                if is_dir:
                    if spec.match_file(full_rel_path + '/'):
                        ignored.append(name)
                elif spec.match_file(full_rel_path):
                    ignored.append(name)
        return ignored

    for platform, scripts in platforms.items():

        print(f"Creating release for {platform}...")
        
        temp_dir = os.path.join(build_dir, f"temp_{platform}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        for d in include_dirs:
            src = os.path.join(repo_root, d)
            if os.path.exists(src):
                shutil.copytree(src, os.path.join(temp_dir, d), dirs_exist_ok=True, ignore=ignore_patterns, copy_function=copy_and_ensure_lf)

        # 2. Rename base_reference to reference in the package
        base_ref_src = os.path.join(repo_root, "base_reference")
        if os.path.exists(base_ref_src):
            shutil.copytree(base_ref_src, os.path.join(temp_dir, "reference"), dirs_exist_ok=True, ignore=ignore_patterns, copy_function=copy_and_ensure_lf)

        # 3. Handle documentation files
        zip_docs_dir = os.path.join(temp_dir, "docs")
        if not os.path.exists(zip_docs_dir):
            os.makedirs(zip_docs_dir)
            
        # Packaging the release.json
        if use_override:
            # When using override, the file we load from repo_root/release-override.json
            # should be packaged as release.json in the zip root
            copy_and_ensure_lf(manifest_path, os.path.join(temp_dir, "release.json"))
        else:
            # Original logic: copy from repo root release.json
            if os.path.exists(manifest_path):
                copy_and_ensure_lf(manifest_path, os.path.join(temp_dir, "release.json"))
        
        for f in docs_files:
            src = os.path.join(repo_root, f)
            if os.path.exists(src):
                copy_and_ensure_lf(src, os.path.join(zip_docs_dir, f))

        # README.md -> docs/dev_readme.md
        repo_readme = os.path.join(repo_root, "README.md")
        if os.path.exists(repo_readme):
            copy_and_ensure_lf(repo_readme, os.path.join(zip_docs_dir, "dev_readme.md"))

        # docs/installer_readme.md -> README.md (root)
        inst_readme_src = os.path.join(temp_dir, "docs", "installer_readme.md")
        if os.path.exists(inst_readme_src):
            shutil.move(inst_readme_src, os.path.join(temp_dir, "README.md"))

        # 4. Copy the main installer and uninstall scripts to the root
        for script_type in ["install", "uninstall"]:
            script_name = scripts[script_type]
            
            if use_new_scripts:
                src_script = os.path.join(repo_root, "bootstrap_scripts", script_name)
            else:
                src_script = os.path.join(repo_root, "installer_scripts", script_name)
                
            if os.path.exists(src_script):
                copy_and_ensure_lf(src_script, os.path.join(temp_dir, script_name))
            else:
                print(f"Warning: {script_type} script {script_name} not found")

        # Zip it up
        zip_name = f"WGSExtract-v{version}_{date}_{platform}_installer.zip"
        zip_path = os.path.join(build_dir, zip_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    
                    if file.endswith('.md'):
                        arcname = arcname[:-3] + '.txt'

                    if file.endswith(('.sh', '.bat', '.command')):
                        # Ensure scripts are executable in the ZIP
                        zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                        zinfo.create_system = 3  # Unix
                        # Set permissions to 755: (S_IFREG | 0o755) << 16
                        zinfo.external_attr = (0o100755 << 16)
                        if verbose:
                            print(f"  + {arcname} (script)")
                        with open(file_path, 'rb') as f:
                            zipf.writestr(zinfo, f.read())
                    else:
                        if verbose:
                            print(f"  + {arcname}")
                        zipf.write(file_path, arcname)

        print(f"Created {zip_name}")
        shutil.rmtree(temp_dir)

    print("All releases created in build/ directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create WGSExtract release packages.")
    parser.add_argument("-ro", "--release-override", action="store_true", help="Use release-override.json from repo root.")
    parser.add_argument("-n", "--new", action="store_true", help="Use new Python-based installers and bootstrap scripts.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose output (e.g., files added to ZIP).")
    args = parser.parse_args()
    
    if args.release_override:
        print("[!] Using release-override.json from repo root.")
    
    if args.new:
        print("[!] Using new Python-based installers.")

    create_release(use_override=args.release_override, use_new_scripts=args.new, verbose=args.verbose)

