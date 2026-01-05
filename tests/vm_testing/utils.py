
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
    
    if sys.platform == "win32":
        # Windows / WSL cleanup
        try:
            # wsl --list --quiet returns names only, but might need encoding handling
            # Using -v is more robust to parse if needed, but -q is better for names loops.
            # But -q might output unicode.
            res = subprocess.run(["wsl", "--list", "--quiet"], capture_output=True, text=True, encoding='utf-16')
            # WSL list output is often utf-16
            if res.returncode != 0:
                 # Try default encoding if utf-16 fails or returns empty
                 res = subprocess.run(["wsl", "--list", "--quiet"], capture_output=True, text=True)
            
            if res.returncode != 0:
                return # WSL might not be enabled or error
            
            for line in res.stdout.splitlines():
                name = line.strip()
                if not name: continue
                # Remove null bytes if any (common in wsl output decoding issues)
                name = name.replace('\x00', '')
                
                if "wgse-test-" in name or "wgse-apt-test-" in name or "wgse-dev-test-" in name:
                     print(f"[*] Found stale WSL distro {name}, unregistering...")
                     subprocess.run(["wsl", "--unregister", name], capture_output=True)
                     # Also try to clean up the dir if we know it
                     # But we don't know the path easily without querying.
                     # WSLVM.delete logic handles it, but here we just do best effort unregister.
                     # The directory cleanup is harder to do blindly reliably.
        except Exception as e:
            print(f"[!] Error during WSL cleanup: {e}")

    else:
        # Mac/Linux (Tart)
        res = subprocess.run(["tart", "list"], capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "wgse-test-" in line or "wgse-apt-test-" in line or "wgse-dev-test-" in line:
                     name = line.split()[0] # Assuming first column is name
                     if name.startswith("wgse-"):
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
    
    ignored_dirs = {'.git', 'out', '.venv', '__pycache__', 'disk_images', 'tests/vm_testing/__pycache__'}
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

