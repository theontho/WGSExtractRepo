import os
import subprocess
from pathlib import Path
from typing import Optional, List
from new_scripts.core.common import WGSE_FP, rmx, rmrx, mvx, CPU_ARCH, OSTYPE
from new_scripts.core.logging import logger, echo_tee, echo_log

# Constants for Micromamba
MICRODIR = WGSE_FP / "micromamba"
MICROMAMBAX = MICRODIR / "bin" / "micromamba"
BASHX = MICRODIR / "bin" / "bash" if MICRODIR.exists() else Path("/bin/bash")

def get_mm_arch():
    arch = CPU_ARCH.lower()
    if arch == "x86_64":
        return "linux-64"
    elif arch in ["aarch64", "arm64"]:
        return "linux-aarch64"
    return "linux-64"

MICROMAMBA_URL = f"https://github.com/mamba-org/micromamba-releases/releases/download/1.5.10-0/micromamba-{get_mm_arch()}"

def initialize_microdir(logfile: str):
    """Sets up the micromamba directory and moves the logfile if necessary."""
    MICRODIR.mkdir(parents=True, exist_ok=True)
    log_fp = MICRODIR / logfile
    
    # If a previous run logfile exists in root, move it back in place
    old_log = WGSE_FP / logfile
    if old_log.exists():
        mvx(old_log, log_fp)
    elif not log_fp.exists():
        log_fp.touch()
    
    return log_fp

def setup_micromamba():
    """Downloads and initializes micromamba."""
    (MICRODIR / "bin").mkdir(parents=True, exist_ok=True)
    (MICRODIR / "cache" / "pip").mkdir(parents=True, exist_ok=True)
    (MICRODIR / "jdk8").mkdir(parents=True, exist_ok=True)
    (MICRODIR / "jdk11").mkdir(parents=True, exist_ok=True)
    
    if not MICROMAMBAX.exists():
        echo_tee("Downloading Micromamba...")
        subprocess.run(['curl', '-Lk', '-o', str(MICROMAMBAX), MICROMAMBA_URL], check=True)
        MICROMAMBAX.chmod(0o755)

    echo_tee("Initializing Micromamba environment...")
    # This part is highly dependent on being in a shell, but we can call it
    # For Python, we usually just run commands with the full path to the micromamba bin
    subprocess.run([str(MICROMAMBAX), 'update', '-y', '-a'], check=True)

def ubuntu_setup(apt_cmd: str = "install"):
    """Sets up Ubuntu environment using apt."""
    echo_tee(f"{apt_cmd.capitalize()}ing Ubuntu packages...")
    pkgs = [
        "sed", "coreutils", "zip", "unzip", "bash", "grep", "curl", "p7zip-full", "jq",
        "python3", "python3-pip", "python3-tk", "python3-pil", "python3-pil.imagetk",
        "openjdk-17-jre", "openjdk-8-jre", "samtools", "bcftools", "tabix", "bwa", "bowtie2"
    ]
    install_apt_packages(pkgs)

def install_manual_tools():
    """Installs tools not available in apt (minimap2, fastp, bwa-mem2)."""
    echo_tee("Installing manual tools (minimap2, fastp, bwa-mem2)...")
    
    # Example for bwa-mem2
    bwamem2_url = "https://github.com/bwa-mem2/bwa-mem2/releases/download/v2.2.1/bwa-mem2-2.2.1_x64-linux.tar.bz2"
    tgz_path = WGSE_FP / "bwa-mem2.tar.bz2"
    subprocess.run(['curl', '-Lk', '-o', str(tgz_path), bwamem2_url], check=True)
    subprocess.run(['tar', '-xf', str(tgz_path)], check=True)
    # Move to /usr/bin (requires sudo)
    # subprocess.run(['sudo', 'mv', ...])
    rmx(tgz_path)

def install_micromamba_tools():
    """Installs required tools into micromamba."""
    echo_tee("Installing Linux utilities into micromamba...")
    subprocess.run([str(MICROMAMBAX), 'install', '-y', '-r', str(MICRODIR), '-c', 'conda-forge',
                    'sed', 'coreutils', 'zip', 'unzip', 'bash', 'gcc', 'grep', 'curl', 'p7zip', 'jq', 'dos2unix'], check=True)
    
    echo_tee("Installing Python into micromamba...")
    subprocess.run([str(MICROMAMBAX), 'install', '-y', '-r', str(MICRODIR), '-c', 'conda-forge',
                    'python=3.11.*', 'pip', 'tk=*=xft_*'], check=True)

    echo_tee("Installing JDK 8 and 11 into sub-environments...")
    # jdk8
    subprocess.run([str(MICROMAMBAX), 'install', '-y', '-r', str(MICRODIR / "jdk8"), '-c', 'conda-forge', 'openjdk=8.0.332'], check=True)
    # jdk11
    subprocess.run([str(MICROMAMBAX), 'install', '-y', '-r', str(MICRODIR / "jdk11"), '-c', 'conda-forge', 'openjdk=11.0.15'], check=True)

    echo_tee("Installing bioinformatics tools...")
    packages = ['bwa', 'bwa-mem2', 'minimap2', 'hisat2', 'samtools', 'bcftools', 'tabix', 'fastp']
    if get_mm_arch() == "linux-64":
        packages.append('pbmm2')
    
    subprocess.run([str(MICROMAMBAX), 'install', '-y', '-r', str(MICRODIR), '-c', 'conda-forge', '-c', 'bioconda'] + packages, check=True)
