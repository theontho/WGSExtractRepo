import os
import sys
import json
import stat
import shutil
import subprocess
from pathlib import Path
from .utils import run_command, get_cygwin_bash, add_to_user_path_windows
from .constants import MANIFEST, TMP_DIR

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
            
            aptfile = Path("Aptfile")
            if aptfile.exists():
                print("Installing system packages from Aptfile...")
                update_needed = True # Always check for updates first? Or just run it.
                print("Updating apt...")
                subprocess.run(["sudo", "apt", "update"])
                
                with open(aptfile, "r") as f:
                    packages = [
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.strip().startswith("#")
                    ]
                
                if packages:
                    # Install all at once
                    cmd = ["sudo", "apt", "install", "-y"] + packages
                    run_command(cmd)
            else:
                print("Warning: Aptfile not found. Falling back to manual default list.")
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
    elif sys.platform == "win32":
        install_windows_dependencies()

def install_java():
    print("=== Installing Java JRE (8 and 17) ===")
    java_configs = {
        "jre8": {
            "url": "https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u345-b01/OpenJDK8U-jre_x64_windows_hotspot_8u345b01.zip",
            "rename_from": "jdk8u345-b01-jre"
        },
        "jre17": {
            "url": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.2%2B8/OpenJDK17U-jre_x64_windows_hotspot_17.0.2_8.zip",
            "rename_from": "jdk-17.0.2+8-jre"
        }
    }
    
    for jre_dir, config in java_configs.items():
        if Path(jre_dir).exists():
            print(f"{jre_dir} already exists, skipping...")
            continue
            
        url = config["url"]
        filename = url.split("/")[-1]
        dest_path = TMP_DIR / filename
        
        if not dest_path.exists():
            print(f"Downloading {jre_dir} from {url}...")
            run_command(["curl", "-L", "-o", str(dest_path), url])
            
        print(f"Extracting {jre_dir}...")
        # Use powershell for extraction on Windows
        run_command(["powershell", "-Command", f"Expand-Archive -Path '{dest_path}' -DestinationPath './' -Force"])
        
        rename_from = Path(config["rename_from"])
        if rename_from.exists():
            print(f"Renaming {rename_from} to {jre_dir}...")
            if Path(jre_dir).exists():
                shutil.rmtree(jre_dir)
            rename_from.rename(jre_dir)

def install_windows_dependencies():
    print("=== Checking Windows Dependencies ===")
    
    # Cygwin Installer (always fetch if missing, just in case)
    setup_exe = TMP_DIR / "setup-x86_64.exe"
    if not setup_exe.exists():
        print("Downloading Cygwin installer...")
        url = "https://www.cygwin.com/setup-x86_64.exe"
        run_command(["curl", "-L", "-o", str(setup_exe), url])

    install_java()

def copy_launch_scripts():
    print("=== Copying Launch Scripts to Root ===")
    source_dir = Path("installer_scripts")
    
    scripts_map = {}
    if sys.platform == "darwin":
        scripts_map = {
            "WGSExtract.command": "WGSExtract.command",
            "Library.command": "Library.command"
        }
    elif sys.platform.startswith("linux"):
        # Distinguish between Micromamba (generic Linux) and Ubuntu
        if Path("micromamba").exists():
            scripts_map = {
                "WGSExtract_linux.sh": "WGSExtract.sh",
                "Library_linux.sh": "Library.sh"
            }
        else:
            scripts_map = {
                "WGSExtract_ubuntu.sh": "WGSExtract.sh",
                "Library_ubuntu.sh": "Library.sh"
            }
    elif sys.platform in ["win32", "cygwin", "msys"]:
        scripts_map = {
            "WGSExtract.bat": "WGSExtract.bat",
            "Library.bat": "Library.bat"
        }
    
    for src_name, dest_name in scripts_map.items():
        src = source_dir / src_name
        dest = Path(dest_name)
        if src.exists():
            print(f"Copying {src_name} to {dest_name}...")
            shutil.copy2(src, dest)
            # Make executable
            try:
                st = os.stat(dest)
                os.chmod(dest, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                print(f"Made {dest_name} executable.")
            except Exception as e:
                print(f"Warning: Failed to make {dest_name} executable: {e}")
        else:
            # Only warn if neither version of a expected script exists
            if not dest.exists() and "ubuntu" not in src_name: 
                print(f"Note: {src} not found, skipping.")

def ensure_runtime_directories():
    print("=== Ensuring Runtime Directories ===")
    dirs = ["temp", "reference"]
    for d in dirs:
        p = Path(d)
        if not p.exists():
            print(f"Creating {d} directory...")
            p.mkdir(parents=True, exist_ok=True)
        else:
            print(f"{d} directory already exists.")

def run_cygwin_setup(cygwin_dir_name="cygwin64"):
    print("=== Running Cygwin Setup ===")
    setup_exe = TMP_DIR / "setup-x86_64.exe"
    cygwin_dir = Path(cygwin_dir_name)
    
    if not setup_exe.exists():
        print("Error: setup-x86_64.exe not found.")
        return

    # Packages from Install_windows.bat
    packages = [
        "curl", "jq", "p7zip", "unzip", "zip", 
        "libbz2-devel", "libzip-devel", "liblzma-devel", 
        "libdeflate-devel", "zlib-devel", "libncurses-devel", 
        "libcurl-devel", "libssl-devel"
    ]
    package_list = ",".join(packages)
    site = "https://cygwin.mirror.constant.com/"
    
    print("Running Cygwin setup (this may take a while)...")
    cmd = [
        str(setup_exe),
        "--root", str(cygwin_dir.resolve()),
        "--local-package-dir", str(TMP_DIR.resolve()),
        "--site", site,
        "--quiet-mode",
        "--no-shortcuts",
        "--no-admin",
        "--packages", package_list
    ]
    
    try:
        run_command(cmd)
        print("Cygwin installation complete.")
        
        encoded_site = "https%3a%2f%2fcygwin.mirror.constant.com%2f"
        mirror_dir = Path(encoded_site)
        if mirror_dir.exists() and mirror_dir.is_dir():
            print(f"Cleaning up mirror directory: {mirror_dir}...")
            shutil.rmtree(mirror_dir)

    except Exception as e:
        print(f"Cygwin installation failed: {e}")

def setup_venv():
    print("=== Setting up Virtual Environment ===")
    if not Path(".venv").exists():
        print("Creating virtual environment...")
        run_command(["uv", "venv"])
    else:
        print("Virtual environment already exists.")

def install_python_dependencies():
    print("=== Installing Python Dependencies with uv ===")
    if sys.platform == "win32":
        run_command(["uv", "pip", "install", "-e", "."])
        
        if not Path("python").exists():
            print("Creating 'python' directory for wrapper...")
            Path("python").mkdir(exist_ok=True)
            
        python_bat = Path("python/python.bat")
        print(f"Creating {python_bat} wrapper...")
        with open(python_bat, "w") as f:
            f.write("@uv run python %*\n")
    else:
        run_command(["uv", "pip", "install", "-e", "."])
        if sys.platform == "darwin":
            run_command(["uv", "pip", "install", "-e", ".[macos]"])

def download_and_extract(pack, manifest_data, dest="./"):
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
        try:
            run_command(["7zz", "x", "-y", "-o" + dest, str(dest_path)])
        except Exception:
            run_command(["unzip", "-o", str(dest_path), "-d", dest])
    elif sys.platform.startswith("linux"):
        try:
            run_command(["7z", "x", "-y", "-o" + dest, str(dest_path)])
        except Exception:
            run_command(["unzip", "-o", str(dest_path), "-d", dest])
    elif sys.platform in ["win32", "cygwin", "msys"]:
        run_command(["powershell", "-Command", f"Expand-Archive -Path '{dest_path}' -DestinationPath '{dest}' -Force"])
    else:
        run_command(["unzip", "-o", str(dest_path), "-d", dest])

    # Clean up nested folder if it exists
    nested = Path("WGSExtractv4")
    if nested.exists() and nested.is_dir():
        print("Cleaning up nested extraction folder...")
        for item in nested.iterdir():
            target_dest = Path(".") / item.name
            if item.is_dir():
                if target_dest.exists():
                    shutil.rmtree(target_dest)
                shutil.copytree(item, target_dest)
            else:
                shutil.copy2(item, target_dest)
        shutil.rmtree(nested)

def install_uv():
    print("Installing uv...")
    if sys.platform == "win32":
        print("Installing uv inside Cygwin...")
        try:
            bash_exe = get_cygwin_bash()
            print(f"Using bash: {bash_exe}")
            bash_cmd = [bash_exe, "-l", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
            run_command(bash_cmd)
        except Exception as e:
            print(f"Failed to install uv in Cygwin: {e}")
            return False
    else:
        installer_url = "https://astral.sh/uv/install.sh"
        installer_path = TMP_DIR / "uv_install.sh"
        
        if not installer_path.exists():
            print(f"Downloading uv installer to {installer_path}...")
            try:
                run_command(["curl", "-L", "-o", str(installer_path), installer_url])
            except Exception as e:
                print(f"Failed to download uv installer: {e}")
                return False
        
        try:
            run_command(["sh", str(installer_path)])
        except Exception as e:
            print(f"Failed to run uv installer: {e}")
            return False
    return True

def ensure_uv():
    print("=== Checking for uv ===")
    
    try:
        run_command(["uv", "--version"])
        return "uv"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    print("uv not found. Attempting to install...")
    if install_uv():
        if sys.platform == "win32":
            bash_exe = get_cygwin_bash()
            try:
                run_command([bash_exe, "-l", "-c", "uv --version"])
                return "uv"
            except Exception:
                print("uv installed in Cygwin but check failed.")
                return None
        
        candidates = []
        home = Path.home()
        candidates.append(home / ".cargo" / "bin" / "uv")
        candidates.append(home / ".local" / "bin" / "uv")
        
        for cand in candidates:
            if cand.exists():
                print(f"Found uv at {cand}")
                return str(cand)
        
        print("uv installed but not found in expected paths. You may need to restart your shell.")
        return None
    else:
        print("Failed to auto-install uv.")
        return None
