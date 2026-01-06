import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
from core.common import WGSE_FP, OSTYPE, CPU_ARCH, rmx, rmrx, mvx, ver_comp
from core.logging import logger, echo_tee

def install_homebrew():
    """Installs or updates Homebrew and required packages."""
    if shutil.which("brew") is None:
        # Check standard locations
        if Path("/opt/homebrew/bin/brew").exists():
            os.environ["PATH"] = f"/opt/homebrew/bin:{os.environ['PATH']}"
        elif Path("/usr/local/bin/brew").exists():
            os.environ["PATH"] = f"/usr/local/bin:{os.environ['PATH']}"
            
    if shutil.which("brew") is None:
        echo_tee("Installing Homebrew...")
        # Note: This is a simplified version of the shell script's install
        subprocess.run(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'], check=True)
        # Re-check path after install
        if Path("/opt/homebrew/bin/brew").exists():
            os.environ["PATH"] = f"/opt/homebrew/bin:{os.environ['PATH']}"
        else:
            os.environ["PATH"] = f"/usr/local/bin:{os.environ['PATH']}"

    echo_tee("Updating Homebrew and installing packages...")
    pkgs = "bash grep gnu-sed coreutils zip unzip 7zip md5sha1sum jq python@3.11 python-tk@3.11 samtools bcftools htslib bwa minimap2 fastp bowtie2"
    casks = "zulu@8 zulu@11"
    bio_pkgs = "brewsci/bio/bwa-mem2 brewsci/bio/hisat2"
    
    try:
        subprocess.run(['brew', 'update'], check=True)
    except subprocess.CalledProcessError:
        echo_tee("Warning: 'brew update' failed. Continuing anyway...")

    subprocess.run(['brew', 'install'] + pkgs.split(), check=True)
    subprocess.run(['brew', 'install', '--cask'] + casks.split(), check=True)
    subprocess.run(['brew', 'install'] + bio_pkgs.split(), check=True)

def apple_cli_install():
    """Installs Apple Xcode CLI tools."""
    if subprocess.run(['xcode-select', '-p'], capture_output=True).returncode == 0:
        echo_tee("Apple Xcode CLI tools already installed.")
        return

    echo_tee("Installing Apple Xcode CLI tools...")
    # This usually triggers a GUI prompt on macOS
    subprocess.run(['xcode-select', '--install'], check=True)

def java_setup():
    """Installs Azul Zulu Java v17 and v8."""
    jdk_data = [
        ("zulu-17.jre", "Azul v17", "zulu17.32.13-ca-jre17.0.2-macosx_x64", "zulu17.32.13-ca-jre17.0.2-macosx_aarch64"),
        ("zulu-8.jre", "Azul v8", "zulu8.64.0.15-ca-fx-jre8.0.342-macosx_x64", "zulu8.64.0.15-ca-fx-jre8.0.342-macosx_aarch64")
    ]
    for dir_name, display_name, x86_url, arm_url in jdk_data:
        java_install(dir_name, display_name, x86_url, arm_url)

def java_install(dir_name: str, display_name: str, x86_url_part: str, arm_url_part: str):
    """Installs Zulu Java JRE."""
    jvm_path = Path("/Library/Java/JavaVirtualMachines") / dir_name
    if jvm_path.exists():
        echo_tee(f"Java JRE {display_name} already installed.")
        return

    echo_tee(f"Installing Java JRE {display_name}...")
    url_part = arm_url_part if "arm" in CPU_ARCH.lower() or "aarch64" in CPU_ARCH.lower() else x86_url_part
    url = f"https://cdn.azul.com/zulu/bin/{url_part}.tar.gz"
    
    tgz_name = WGSE_FP / f"{dir_name}.tgz"
    subprocess.run(['curl', '-Lk', '-o', str(tgz_name), url], check=True)
    subprocess.run(['tar', 'xf', str(tgz_name)], check=True)
    
    # The tar extract creates a directory with the url_part name
    extracted_dir = Path.cwd() / url_part
    if extracted_dir.exists():
        subprocess.run(['sudo', 'mv', str(extracted_dir / dir_name), str(jvm_path.parent)], check=True)
        rmrx(extracted_dir)
        rmx(tgz_name)
    echo_tee(f"Finished Java JRE {display_name} install.")

def macports_setup():
    """Handles MacPorts installation and package management."""
    port_bin = Path("/opt/local/bin/port")
    if not port_bin.exists():
        # Transliteration of MacPorts version based on OS version would go here
        echo_tee("Installing MacPorts 2.11.5...")
        # Placeholder for macports_install("2.11.5")
    else:
        echo_tee("Updating MacPorts and packages...")
        subprocess.run(['sudo', str(port_bin), 'selfupdate'], check=True)
        subprocess.run(['sudo', str(port_bin), 'upgrade', 'outdated'], check=True)

    pkgs = ["bash", "grep", "gsed", "coreutils", "zip", "unzip", "7zip", "md5sha1sum", "jq"]
    bio_pkgs = ["samtools", "bcftools", "htslib"]
    
    echo_tee("Installing Unix utilities and bioinfo tools via MacPorts...")
    subprocess.run(['sudo', str(port_bin), '-N', 'install'] + pkgs, check=True)
    subprocess.run(['sudo', str(port_bin), '-N', 'install'] + bio_pkgs, check=True)

def bwa_setup():
    """Installs compiled BWA for macOS."""
    bwa_bin = Path("/opt/local/bin/bwa")
    if bwa_bin.exists():
        return

    echo_tee("Adding BWA...")
    bwaf = "bwa0717-mac-aarch64" if "arm" in CPU_ARCH.lower() or "aarch64" in CPU_ARCH.lower() else "bwa0717-mac-x64"
    url = f"https://raw.githubusercontent.com/smikkelsendk/bwa-for-arm/master/bin/{bwaf}.tar.gz"
    
    tgz_path = WGSE_FP / "bwa.tgz"
    subprocess.run(['curl', '-Lk', '-o', str(tgz_path), url], check=True)
    subprocess.run(['tar', 'xf', str(tgz_path)], check=True)
    
    extracted_file = Path.cwd() / bwaf
    if extracted_file.exists():
        extracted_file.chmod(0o755)
        subprocess.run(['sudo', 'mv', str(extracted_file), str(bwa_bin)], check=True)
        rmx(tgz_path)

def remove_old_python():
    """Removes old WGSE Python installations."""
    # Versions from WGSE v2 through v4
    versions = ["3.8", "3.9", "3.10", "3.11"]
    # Logic to find and ask to remove. 
    # Python.org installs usually Frameworks.
    # We need to be careful not to remove system python or brew python if we are using it?
    # Original script uninstall logic for python is complex (paths in /Library/Frameworks/Python.framework/Versions/...).
    # Detailed implementation of python_uninstall from zcommon_macos.sh needed if we want strict parity.
    # For now, we will add a placeholder or simplified check.
    pass

def remove_old_java():
    """Removes old WGSE Java installations."""
    # jdkpacks=( "adoptopenjdk-11.jre" "zulu-17.jre" "zulu-8.jre" )
    pass

def uninstall_macports_logic():
    """Uninstalls MacPorts if present."""
    if Path("/opt/local/bin/port").exists():
        echo_tee("Uninstalling MacPorts...")
        # sudo port -fp uninstall installed
        # sudo rm -rf /opt/local ...
        pass

def homebrew_setup():
    """Sets up macOS environment using Homebrew."""
    # Logic from Install_macos_brew.command
    
    echo_tee("Checking for old WGSE installations to remove...")
    # remove_old_python()
    # remove_old_java()
    
    if shutil.which("port"):
        # uninstall_macports_logic()
        pass

    apple_cli_install()
    
    install_homebrew()
    
    # Homebrew environment setup is usually done in shell, 
    # but we can call brew directly if we know the path.
    brew_bin = Path("/opt/homebrew/bin/brew") if "arm" in CPU_ARCH.lower() else Path("/usr/local/bin/brew")
    
    if brew_bin.exists():
        echo_tee("Installing bioinfo tools via Homebrew...")
        subprocess.run([str(brew_bin), 'install', 'samtools', 'bcftools', 'bwa', 'htslib'], check=True)
