import os
import subprocess
from pathlib import Path
from typing import List, Optional
from core.common import (
    WGSE_FP, OSTYPE, CPU_ARCH, SUCCESS, FAIL,
    get_latest_release_info, read_current_release_info,
    ver_comp, get_reflib_dir, rmx, rmrx, mvx, cpx,
    get_latest_json
)
from core.logging import echo_tee, logger
from install.pip_utils import pip_install

# Platform-specific imports
if OSTYPE == "linux":
    from core.linux import setup_micromamba, install_micromamba_tools, ubuntu_setup, install_manual_tools
elif OSTYPE == "darwin":
    from core.macos import apple_cli_install, java_setup, macports_setup, bwa_setup, homebrew_setup

def install_or_upgrade(package: str, verbose: bool = False):
    """Orchestrates install/upgrade for a specific WGSE package."""
    
    # Implement recursive copy helper locally or use shutil
    def cprx(src_dir: Path, dst_dir: Path):
        """Recursively copies content of src_dir to dst_dir (merging)."""
        if not dst_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            dst = dst_dir / item.name
            if item.is_dir():
                cprx(item, dst)
            else:
                cpx(item, dst)
                # Preserve execute permissions for scripts
                if item.suffix in ['.sh', '.command', '.bat', '.py']:
                    try:
                        dst.chmod(item.stat().st_mode)
                    except: pass

    from core.common import download_file, extract_zip, change_release_json

    echo_tee(f"\nChecking package: {package}")
    
    reflibdir = get_reflib_dir()
    
    ver_map = {
        "installer": {"dir": WGSE_FP / "scripts", "name": "Installer"},
        "program": {"dir": WGSE_FP / "program", "name": "Program"},
        "tools": {"dir": WGSE_FP / "jartools", "name": "Local Tools"},
        "reflib": {"dir": reflibdir, "name": "Reference Library"}
    }
    
    if package not in ver_map:
        logger.error(f"Unknown package type: {package}")
        return

    data = ver_map[package]
    verdir = data["dir"]
    longname = data["name"]

    # Get latest version info
    latest_ver, _ = get_latest_release_info(package, verbose)
    # Get current version info
    current_ver = "0"
    current_json = verdir / f"{package}.json"
    
    if current_json.exists():
        current_ver, _ = read_current_release_info(package, current_json, verbose)
    
    # Logic for update check
    replace = False
    if ver_comp(latest_ver, "<=", "0"):
       echo_tee(f"*** Missing WGSE package \"{longname}\" latest version file; no update possible.")
       return

    check_ver = current_ver
    # Special reflib logic from zcommon.sh
    if package == "reflib":
        # if 33 <= currentVer <= 35 and latestVer < 33: checkVer = 0
        if ver_comp("33", "<=", current_ver) and ver_comp(current_ver, "<=", "35") and ver_comp(latest_ver, "<", "33"):
             check_ver = "0"

    if ver_comp(check_ver, "<", latest_ver):
        echo_tee(f"*** WGS Extract \"{longname}\" v{current_ver} is installed but outdated used.")
        replace = True
    elif not verdir.exists():
         echo_tee(f"*** WGS Extract \"{longname}\" v{latest_ver} is not yet installed.")
         replace = True
    else:
        echo_tee(f"Status: Up-to-date for {longname} (v{current_ver})")

    if not replace:
        return

    # Perform Install / Upgrade
    echo_tee(f"... Started installing/upgrading {longname} v{latest_ver} ...")
    
    # Need latestURL
    # get_latest_release_info set globals in bash, here we need to re-retrieve or refactor.
    # The python function returns (ver, date). It should probably return URL too or we fetch it.
    # Let's fix get_latest_release_info in common.py or access get_latest_json() directly here.
    rel_data = get_latest_json()
    latest_url = rel_data.get(package, {}).get("URL")
    
    if not latest_url:
        echo_tee(f"*** ERROR: No URL for package {package}")
        return

    zip_file = WGSE_FP / f"{package}.zip"
    if not download_file(latest_url, zip_file):
        echo_tee(f"*** FAILURE downloading {longname}")
        return
        
    # Extract to temp dir
    lzipdir_name = package + "_extract" # simplified
    dest_path = WGSE_FP 
    if package == "installer": lzipdir_name = "installer_pkg" # arbitrary temp name
    
    # Extract
    
    # For safety with python zip extraction which might not be same as 7z (paths), 
    # let's extract to a temp folder then copy.
    temp_extract = WGSE_FP / "temp_install" / package
    if temp_extract.exists(): rmrx(temp_extract)
    temp_extract.mkdir(parents=True, exist_ok=True)
    
    if not extract_zip(zip_file, temp_extract):
         echo_tee(f"*** FAILURE extracting {longname}")
         rmx(zip_file)
         return
    rmx(zip_file)

    # Now copy from temp_extract to final destination
    # The zip content is in temp_extract.
    
    if package == "installer":
        # Handle release.json
        new_release_json = temp_extract / "release.json"
        if change_release_json(new_release_json):
             if (WGSE_FP / "release.json").exists():
                 mvx(WGSE_FP / "release.json", WGSE_FP / "release-saved.json")
             mvx(new_release_json, WGSE_FP / "release.json")
        else:
             rmx(new_release_json)
             
        if (temp_extract / "release-override.json").exists():
             if (WGSE_FP / "release.json").exists():
                 mvx(WGSE_FP / "release.json", WGSE_FP / "release-overridden.json")
             mvx(temp_extract / "release-override.json", WGSE_FP / "release.json")
        
        # Copy content
        cprx(temp_extract, WGSE_FP)
        rmrx(temp_extract)
        
        echo_tee("... Restarting installer ...")
        # Restart logic
        import sys
        # Re-exec python with same args
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    elif package == "program":
        cprx(temp_extract, WGSE_FP)
        
    elif package == "reflib":
        # Copy reference/* to reflibdir
        src_ref = temp_extract / "reference"
        if src_ref.exists():
            cprx(src_ref, reflibdir)
        # Handle 00README
        base_readme = reflibdir / "00README_genomes.txt"
        if base_readme.exists():
            mvx(base_readme, reflibdir / "genomes")
            
    elif package == "tools":
        cprx(temp_extract, WGSE_FP)
        # chmod FastQC
        if (WGSE_FP / "FastQC" / "fastqc").exists():
             (WGSE_FP / "FastQC" / "fastqc").chmod(0o755)

    rmrx(temp_extract)
    echo_tee(f"... finished installing {longname} v{latest_ver}.")

def main_installer(cpu_arch: str, osver: str):
    """Main entry point for unified installer."""
    echo_tee("="*80)
    echo_tee("WGS Extract Unified Installer")
    echo_tee("="*80)

    # 1. Platform-specific Setup
    if OSTYPE == "linux":
        if os.environ.get("linux_type") == "micromamba":
            setup_micromamba()
            install_micromamba_tools()
        else:
            ubuntu_setup()
            install_manual_tools()
    elif OSTYPE == "darwin":
        if os.environ.get("macos_type") == "homebrew":
            homebrew_setup()
        else:
            apple_cli_install()
            java_setup()
            macports_setup()
            bwa_setup()

    # 2. Pip Installation
    if "msys" not in OSTYPE:
        pip_install(cpu_arch, osver)

    # 2. Package Updates
    for pkg in ["installer", "reflib", "tools", "program"]:
        install_or_upgrade(pkg)

    # 3. Cleanup from Previous Releases
    echo_tee("\nCleaning up from any previous releases")
    
    # Legacy v2/v3 cleanup logic
    to_remove = [
        "Install_MacOSX.app", "Start_MacOSX.app", "Uninstall_MacOSX.app",
        "Install_MacOSX.scpt", "Start_MacOSX.scpt", "Uninstall_MacOSX.scpt",
        "Install_MacOSX.sh", "Start_MacOSX.sh", "Uninstall_MacOSX.sh",
        "Windows_START.bat", "MacOS_START.sh", "Linux_START.sh",
        "00README.txt", "WGSE Betav3 Release Notes.txt", "set_WGSEpath.bat",
        "Upgrade_v2tov3.command", "Upgrade_v2tov3.sh", "Upgrade_v2tov3.bat"
    ]
    for item in to_remove:
        rmrx(WGSE_FP / item)

    # 4. Final Platform-specific Cleanup/Setup
    if OSTYPE == "darwin":
        cpx(WGSE_FP / "installer_scripts" / "WGSExtract.command", WGSE_FP / "WGSExtract.command")
        cpx(WGSE_FP / "installer_scripts" / "Library.command", WGSE_FP / "Library.command")
        if (WGSE_FP / "WGSExtract.command").exists():
            (WGSE_FP / "WGSExtract.command").chmod(0o755)
        if (WGSE_FP / "Library.command").exists():
            (WGSE_FP / "Library.command").chmod(0o755)
    elif "linux" in OSTYPE:
        suffix = "_linux" if os.environ.get("linux_type") == "micromamba" else "_ubuntu"
        cpx(WGSE_FP / "installer_scripts" / f"WGSExtract{suffix}.sh", WGSE_FP / "WGSExtract.sh")
        cpx(WGSE_FP / "installer_scripts" / f"Library{suffix}.sh", WGSE_FP / "Library.sh")
        if (WGSE_FP / "WGSExtract.sh").exists():
            (WGSE_FP / "WGSExtract.sh").chmod(0o755)
        if (WGSE_FP / "Library.sh").exists():
            (WGSE_FP / "Library.sh").chmod(0o755)
    elif "msys" in OSTYPE or "cygwin" in OSTYPE:
        cpx(WGSE_FP / "installer_scripts" / "WGSExtract.bat", WGSE_FP / "WGSExtract.bat")
        cpx(WGSE_FP / "installer_scripts" / "Library.bat", WGSE_FP / "Library.bat")

    echo_tee("\nUnified Installation Complete.")

if __name__ == "__main__":
    # In practice, these would come from arguments
    import platform
    main_installer(platform.machine(), platform.release())
