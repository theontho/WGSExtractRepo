#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

MANIFEST = "installer_scripts/release.json"
TMP_DIR = Path("download_tmp")

def run_command(cmd, shell=False, check=True):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)

def get_cygwin_bash():
    """Returns the absolute path to cygwin bash.exe or just 'bash' if not on Windows."""
    if sys.platform == "win32":
        # Assume cygwin64 is in the current directory or a standard location
        # Prefer sh.exe as bash.exe is broken in some Cygwin versions
        for shell in ["sh.exe", "bash.exe"]:
            local_cyg = Path.cwd() / "cygwin64" / "bin" / shell
            if local_cyg.exists():
                return str(local_cyg)
        # Fallback to C:\cygwin64 if local doesn't exist
        for shell in ["sh.exe", "bash.exe"]:
            std_cyg = Path("C:/cygwin64/bin") / shell
            if std_cyg.exists():
                return str(std_cyg)
    return "bash"

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


def install_windows_dependencies():
    print("=== Checking Windows Dependencies ===")
    
    # Cygwin Installer (always fetch if missing, just in case)
    setup_exe = TMP_DIR / "setup-x86_64.exe"
    if not setup_exe.exists():
        print("Downloading Cygwin installer...")
        url = "https://www.cygwin.com/setup-x86_64.exe"
        run_command(["curl", "-L", "-o", str(setup_exe), url])

    install_java()

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
    # Note: --local-install in batch might imply using what's in the zip? 
    # But batch also had --site mirror. We will try standard install.
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
        
        # Cleanup the mirror directory created by setup-x86_64.exe
        # The installer creates a directory named after the URL-encoded site
        # e.g., https%3a%2f%2fcygwin.mirror.constant.com%2f
        encoded_site = "https%3a%2f%2fcygwin.mirror.constant.com%2f"
        mirror_dir = Path(encoded_site)
        if mirror_dir.exists() and mirror_dir.is_dir():
            print(f"Cleaning up mirror directory: {mirror_dir}...")
            shutil.rmtree(mirror_dir)

    except Exception as e:
        print(f"Cygwin installation failed: {e}")


    try:
        if sys.platform == "win32":
            # Check host uv first
            run_command(["uv", "--version"])
        else:
            run_command(["uv", "--version"])
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("uv not found on host. Please install uv (see https://github.com/astral-sh/uv).")
        return False

def setup_venv():
    print("=== Setting up Virtual Environment ===")
    if not Path(".venv").exists():
        print("Creating virtual environment...")
        if sys.platform == "win32":
             run_command(["uv", "venv"])
        else:
            run_command(["uv", "venv"])
    else:
        print("Virtual environment already exists.")

def install_python_dependencies():
    print("=== Installing Python Dependencies with uv ===")
    if sys.platform == "win32":
        # Run uv on host
        run_command(["uv", "pip", "install", "-e", "."])
        
        # Create 'python' junction to .venv/Scripts for compatibility with WGSExtract.bat
        if not Path("python").exists():
            print("Creating 'python' junction to .venv/Scripts...")
            # Use cmd /c mklink /j to create a junction
            subprocess.run(["cmd", "/c", "mklink", "/j", "python", ".venv\\Scripts"], check=True)
    else:
        # Use uv pip install which is part of the venv workflow
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
        # Extract using 7zz if available, else unzip
        try:
            run_command(["7zz", "x", "-y", "-o" + dest, str(dest_path)])
        except FileNotFoundError:
            run_command(["unzip", "-o", str(dest_path), "-d", dest])
    elif sys.platform.startswith("linux"):
        try:
            run_command(["7z", "x", "-y", "-o" + dest, str(dest_path)])
        except FileNotFoundError:
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
            dest = Path(".") / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        shutil.rmtree(nested)

def install_uv():
    print("Installing uv...")
    if sys.platform == "win32":
        # Install uv inside Cygwin
        print("Installing uv inside Cygwin...")
        try:
            # bash -l -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
            # We use subprocess to call bash. 'bash' must be in PATH (which it should be if Cygwin bin is in PATH or we find it)
            # If bash is not in PATH, we might need to find it relative to Cygwin install.
            # But the user script flow implies we setup Cygwin first. 
            
            # For robustness, let's try to assume 'bash' is available if we set it up.
            # If not, we might need to look for it in C:\cygwin64\bin\bash.exe or similar
            
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
        else:
            print(f"Found existing uv installer at {installer_path}, skipping download.")

        try:
            run_command(["sh", str(installer_path)])
        except Exception as e:
            print(f"Failed to run uv installer: {e}")
            return False
    return True

def ensure_uv():
    print("=== Checking for uv ===")
    
    if sys.platform == "win32":
        # Check host
        try:
            run_command(["uv", "--version"])
            return "uv" 
        except (FileNotFoundError, subprocess.CalledProcessError):
             pass
    else:
        # Check if uv is already in PATH
        try:
            run_command(["uv", "--version"])
            return "uv"
        except FileNotFoundError:
            pass

    print("uv not found. Attempting to install...")
    if install_uv():
        if sys.platform == "win32":
            # Re-check in bash
            bash_exe = get_cygwin_bash()
            try:
                run_command([bash_exe, "-l", "-c", "uv --version"])
                return "uv"
            except:
                print("uv installed in Cygwin but check failed.")
                return None
        
        # Try to find it in standard locations if not yet in PATH
        # Windows: %USERPROFILE%/.cargo/bin/uv.exe or %LOCALAPPDATA%/uv/uv.exe
        # Unix: ~/.cargo/bin/uv or ~/.local/bin/uv
        
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

def main():
    print("==========================================")
    print("WGS Extract Development Environment Init")
    print("==========================================")

    TMP_DIR.mkdir(exist_ok=True)
    ensure_runtime_directories()

    if not os.path.exists(MANIFEST):
        print(f"Error: {MANIFEST} not found.")
        sys.exit(1)

    with open(MANIFEST, "r") as f:
        manifest_data = json.load(f)

    # On Windows, we need to ensure Cygwin is installed BEFORE checking for uv
    if sys.platform == "win32":
         # Force Cygwin setup first
         download_and_extract("cygwin64", manifest_data)
         run_cygwin_setup("cygwin64")
         # We need to make sure bash is in path. 
         # Assuming c:\cygwin64\bin or the local cygwin dir.
         cygwin_bin = Path("cygwin64/bin").resolve()
         if cygwin_bin.exists() and str(cygwin_bin).lower() not in os.environ["PATH"].lower():
             print(f"Adding {cygwin_bin} to PATH...")
             os.environ["PATH"] = str(cygwin_bin) + os.pathsep + os.environ["PATH"]

    uv_cmd = ensure_uv()
    if not uv_cmd:
        print("Error: uv is required but could not be found or installed.")
        print("Please install uv manually: https://github.com/astral-sh/uv")
        sys.exit(1)
    
    # Monkey-patch run_command or pass uv_cmd?
    # Simplest is to just put the new uv path at front of PATH for this process, 
    # OR wrap subsequent calls. 
    # But wait, subsequent calls use `run_command(["uv", ...])`.
    

    # If we found an absolute path, we should probably add its dir to PATH
    if uv_cmd and os.path.isabs(uv_cmd):
        uv_dir = str(Path(uv_cmd).parent)
        
        # 1. Update current session
        if uv_dir.lower() not in os.environ["PATH"].lower():
            print(f"Adding {uv_dir} to PATH for this session...")
            os.environ["PATH"] = uv_dir + os.pathsep + os.environ["PATH"]
            
        # 2. Update persistent User PATH (Windows only)
        # Note: In Cygwin mode, we might not need to update Windows PATH for uv, 
        # but usage of 'uv' from Windows CMD would require it.
        # Since we are hiding it in Cygwin, maybe we skip this for Windows?
        # But let's leave common logic if not specific.
        if sys.platform == "win32" and "cygdrive" not in uv_cmd:
             # Only add if it's a windows path. If it's a cygwin path (unlikely to be returned as abs path from bash check), skip.
             add_to_user_path_windows(uv_dir)

    setup_venv()
    install_python_dependencies()

    download_and_extract("reflib", manifest_data)
    download_and_extract("tools", manifest_data)

    # Merge base_reference into reference
    base_ref = Path("base_reference")
    ref = Path("reference")
    if base_ref.exists():
        print("Merging base_reference into reference...")
        ref.mkdir(exist_ok=True)
        for item in base_ref.iterdir():
            dest = ref / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    if sys.platform in ["cygwin", "msys", "win32"]:
        print("\nDetected Windows environment. Defaulting to Cygwin64.")
        # choice = input("Enter choice [1-2]: ")
        choice = "1"
        if choice == "1":
            # download_and_extract("cygwin64", manifest_data) # Already done at start
            # run_cygwin_setup("cygwin64") # Already done at start
            download_and_extract("bioinfo", manifest_data, dest="cygwin64/usr")
        elif choice == "2":
            download_and_extract("msys2", manifest_data)
            # run_msys2_setup() # Not implemented
            download_and_extract("bioinfo-msys2", manifest_data, dest="msys2")
        else:
            print("Invalid choice. Skipping platform-specific dependencies.")

    print("\n==========================================")
    print("Initialization Complete!")
    print("==========================================")
    
    cleanup_root_artifacts()

def add_to_user_path_windows(directory):
    """
    Safely adds a directory to the persistent User PATH using the Registry.
    Does not use setx to avoid truncation.
    """
    try:
        import winreg
    except ImportError:
        print("Warning: winreg module not available.")
        return

    print(f"Checking persistent PATH for: {directory}")
    
    key_path = r"Environment"
    try:
        # Open Key
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        
        # Read current PATH
        try:
            current_path_val, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path_val = ""

        # Normalize for check
        path_parts = [p.strip() for p in current_path_val.split(";") if p.strip()]
        
        # Check if already present
        found = False
        for part in path_parts:
            if part.lower() == directory.lower():
                found = True
                break
        
        if not found:
            print(f"Adding {directory} to permanent User PATH...")
            # Append new path
            if not current_path_val.endswith(";"):
                 current_path_val += ";"
            new_path_val = current_path_val + directory
            
            # Write back
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_val)
            print("Successfully updated Registry PATH.")
            
            # Broadcast change mainly for other new windows, though usually requires restart
            # This is a bit "best effort" in Python without ctypes boilerplate, 
            # but usually script just reminds user.
            print("Note: You may need to restart your terminal for changes to take effect globally.")
        else:
            print("Path already in Registry.")

        winreg.CloseKey(key)

    except Exception as e:
        print(f"Warning: Failed to update persistent PATH in registry: {e}")


def cleanup_root_artifacts():
    """Clean up any temporary executables that might have landed in the root."""
    print("Performing final cleanup...")
    artifacts = ["setup-x86_64.exe"]
    for art in artifacts:
        p = Path(art)
        if p.exists():
            try:
                p.unlink()
                print(f"Removed {art} from root.")
            except Exception as e:
                print(f"Warning: Failed to remove {art}: {e}")

if __name__ == "__main__":
    main()
