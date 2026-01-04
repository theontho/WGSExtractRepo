import sys
import os
import shutil
# import tomllib # Not available in 3.10
from pathlib import Path
from typing import Dict

# Ensure we can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from install_test_base import run_install_test

def load_settings(repo_root: Path) -> Dict[str, str]:
    settings_path = repo_root / "devsettings.toml"
    if not settings_path.exists():
        print(f"[!] Error: {settings_path} not found.")
        sys.exit(1)
    
    data = {}
    with open(settings_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                data[key] = value
    return data

def test_wsl_ubuntu(manual_kill: bool = False):
    repo_root = Path(__file__).resolve().parent.parent
    settings = load_settings(repo_root)
    
    distro = settings.get("wslUbuntu")
    if not distro:
        print("[!] Error: 'wslUbuntu' not set in devsettings.toml")
        sys.exit(1)
        
    print(f"[*] Testing Ubuntu installer on WSL distro: {distro}")
    
    # Path inside ZIP -> install_test_base extracts to tmp_test_install_...
    # We want to run: wsl -d <distro> bash Install_ubuntu.sh
    # And input "n\n\n" (No update, wait, exit)
    
    installer_cmd = ["wsl", "-d", distro, "-u", "root", "bash", "Install_ubuntu.sh"]
    
    # Files expected to be created
    expected_files = [
        Path("WGSExtract.sh"),  # Created by installer
        Path("Library.sh"),
        Path("program/wgsextract.py") # Should exist if extracted and common script ran
    ]
    
    # Launch command: wsl -d <distro> script -q -c "bash WGSExtract.sh" /dev/null
    # This forces a TTY so zxterm_ubuntu.sh doesn't try to spawn a new terminal window
    launch_cmd = ["wsl", "-d", distro, "-u", "root", "script", "-q", "-c", "bash WGSExtract.sh --auto", "/dev/null"]
    
    success = run_install_test(
        test_name="wsl_ubuntu",
        zip_glob_pattern="*ubuntu_installer.zip",
        installer_cmd=installer_cmd,
        expected_files=expected_files,
        launch_cmd=launch_cmd,
        launch_marker_text="Starting WGS Extract",
        is_new_installer=False,
        installer_input="n\n\n",
        manual_kill=manual_kill
    )
    
    if success:
        print("[*] WSL Ubuntu Test PASSED")

def test_wsl_linux(manual_kill: bool = False):
    repo_root = Path(__file__).resolve().parent.parent
    settings = load_settings(repo_root)
    
    distro = settings.get("wslNotUbuntu")
    if not distro:
        print("[!] Error: 'wslNotUbuntu' not set in devsettings.toml")
        sys.exit(1)
        
    print(f"[*] Testing Linux (Micromamba) installer on WSL distro: {distro}")
    
    installer_cmd = ["wsl", "-d", distro, "bash", "Install_linux.sh"]
    
    # Files expected
    expected_files = [
        Path("WGSExtract.sh"),
        Path("micromamba/bin/micromamba")  # Micromamba installed locally
    ]
    
    launch_cmd = ["wsl", "-d", distro, "script", "-q", "-c", "bash WGSExtract.sh", "/dev/null"]
    
    success = run_install_test(
        test_name="wsl_linux",
        zip_glob_pattern="*linux_installer.zip",
        installer_cmd=installer_cmd,
        expected_files=expected_files,
        launch_cmd=launch_cmd,
        launch_marker_text="Starting WGS Extract",
        is_new_installer=False,
        installer_input="\n", # Might need customized input if it asks questions
        manual_kill=manual_kill
    )
    
    if success:
        print("[*] WSL Linux Test PASSED")

def main():
    if len(sys.argv) < 2:
        print("Usage: python install_test_wsl.py [ubuntu|linux|all] [--manual-kill]")
        sys.exit(1)
    
    mode = sys.argv[1]
    manual_kill = "--manual-kill" in sys.argv
    
    if mode in ["ubuntu", "all"]:
        test_wsl_ubuntu(manual_kill=manual_kill)
    
    if mode in ["linux", "all"]:
        test_wsl_linux(manual_kill=manual_kill)

if __name__ == "__main__":
    main()
