#!/usr/bin/env -S uv run python3
import os
import shutil
import json
import zipfile
from datetime import datetime
import pathspec

def create_release():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    build_dir = os.path.join(repo_root, "build")
    manifest_path = os.path.join(repo_root, "installer_scripts", "release.json")

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
    
    # Files to be moved into docs/ inside the ZIP
    docs_files = ["LICENSE.txt", "CHANGELOG.md"]

    # Help determine ignored files using .gitignore
    def ignore_patterns(path, names):
        rel_path = os.path.relpath(path, repo_root)
        if rel_path == ".":
            rel_path = ""
        
        ignored = []
        for name in names:
            full_rel_path = os.path.join(rel_path, name)
            
            # Basic hardcoded ignores that should always be ignored for release
            if name.startswith('.') or name in ["tmp", "build", "__pycache__", ".git"]:
                ignored.append(name)
                continue
            
            # Use pathspec if available
            if spec:
                # Check if it's a directory to help pathspec match directory-only patterns
                is_dir = os.path.isdir(os.path.join(path, name))
                if is_dir:
                    # pathspec matches directories if they end with / or if is_dir is handled
                    # For pathspec.match_file, we can append a / to simulate directory matching if needed,
                    # but match_file often handles it if the pattern is simple.
                    # Best practice for pathspec is to use match_file with the path.
                    if spec.match_file(full_rel_path + '/' if is_dir else full_rel_path):
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
                shutil.copytree(src, os.path.join(temp_dir, d), dirs_exist_ok=True, ignore=ignore_patterns)

        # 2. Rename base_reference to reference in the package
        base_ref_src = os.path.join(repo_root, "base_reference")
        if os.path.exists(base_ref_src):
            shutil.copytree(base_ref_src, os.path.join(temp_dir, "reference"), dirs_exist_ok=True, ignore=ignore_patterns)

        # 3. Handle documentation files
        zip_docs_dir = os.path.join(temp_dir, "docs")
        if not os.path.exists(zip_docs_dir):
            os.makedirs(zip_docs_dir)
            
        # Copy release.json to root if it exists in installer_scripts/
        release_json_src = os.path.join(temp_dir, "installer_scripts", "release.json")
        if os.path.exists(release_json_src):
            shutil.copy2(release_json_src, os.path.join(temp_dir, "release.json"))
        for f in docs_files:
            src = os.path.join(repo_root, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(zip_docs_dir, f))

        # README.md -> docs/dev_readme.md
        repo_readme = os.path.join(repo_root, "README.md")
        if os.path.exists(repo_readme):
            shutil.copy2(repo_readme, os.path.join(zip_docs_dir, "dev_readme.md"))

        # docs/installer_readme.md -> README.md (root)
        inst_readme_src = os.path.join(temp_dir, "docs", "installer_readme.md")
        if os.path.exists(inst_readme_src):
            shutil.move(inst_readme_src, os.path.join(temp_dir, "README.md"))

        # 4. Copy the main installer and uninstall scripts to the root
        for script_type in ["install", "uninstall"]:
            script_name = scripts[script_type]
            src_script = os.path.join(repo_root, "installer_scripts", script_name)
            if os.path.exists(src_script):
                shutil.copy2(src_script, os.path.join(temp_dir, script_name))
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
                    zipf.write(file_path, arcname)

        print(f"Created {zip_name}")
        shutil.rmtree(temp_dir)

    print("All releases created in build/ directory.")

if __name__ == "__main__":
    create_release()

