
import subprocess
import sys
from .core import SCRIPTS_DIR, BUILD_DIR

def run_release_script():
    print("[*] Running release.py to generate packages...")
    release_py = SCRIPTS_DIR / "release.py"
    subprocess.run([sys.executable, str(release_py)], check=True)

def find_release_zip(platform):
    """Find the latest release zip for a platform in the build directory."""
    patterns = {
        "ubuntu": "*_ubuntu_installer.zip",
        "fedora": "*_linux_installer.zip",
        "macos": "*_macos_brew_installer.zip"
    }
    pattern = patterns.get(platform)
    if not pattern:
        return None
    
    zips = list(BUILD_DIR.glob(pattern))
    if not zips:
        return None
    
    return sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)[0]

def cleanup_stale_vms():
    """Cleanup any leftover test VMs from previous runs."""
    print("[*] Cleaning up stale test VMs...")
    res = subprocess.run(["tart", "list"], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        if "wgse-test-" in line:
             name = line.split()[0] # Assuming first column is name
             if name.startswith("wgse-test-"):
                 print(f"[*] Found stale VM {name}, deleting...")
                 subprocess.run(["tart", "stop", name], capture_output=True)
                 subprocess.run(["tart", "delete", name], capture_output=True)

def create_repo_zip(output_path):
    """Create a zip archive of the current repository state, excluding git and release/build artifacts."""
    import zipfile
    import os
    from pathlib import Path
    from .core import REPO_ROOT
    
    print(f"[*] Packaging repository to {output_path}...")
    
    ignored_dirs = {'.git', 'build', 'tmp', 'download_tmp', '.venv', '__pycache__', 'disk_images', 'tests/vm_testing/__pycache__'}
    ignored_files = {'.DS_Store'}
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(REPO_ROOT):
            # Modify dirs in-place to filter ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file in files:
                if file in ignored_files or file.endswith('.pyc'):
                    continue
                    
                file_path = Path(root) / file
                arcname = file_path.relative_to(REPO_ROOT)
                zipf.write(file_path, arcname)
    
    return output_path

