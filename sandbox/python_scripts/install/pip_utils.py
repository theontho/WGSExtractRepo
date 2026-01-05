import os
import sys
import subprocess
import platform
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from typing import List, Optional
from new_scripts.core.common import WGSE_FP, OSTYPE, CPU_ARCH
from new_scripts.core.logging import echo_tee, logger

def pip_install(cpu_arch: str, osver: str):
    """Installs or upgrades Python libraries (transliterated from pip_install in shell)."""
    echo_tee(f"\n*** Installing or Upgrading the Python 3.x libraries on {OSTYPE}")
    
    temp_dir = WGSE_FP / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.chmod(0o777)
    
    pip_log = temp_dir / "pip_install.log"
    pip_log.touch()
    pip_log.chmod(0o664)

    libs = [
        "Pillow", "pyliftover", "pyscreenshot", "openpyxl", "pandas", 
        "psutil", "multiqc", "wakepy>=0.8"
    ]
    
    os.environ["PIP_BREAK_SYSTEM_PACKAGES"] = "1"
    
    opts = ["--no-warn-script-location"]
    pip_cmd = []

    if OSTYPE == "darwin":
        libs.append("tkmacosx")
        opts = []
        custom_pip = Path("/usr/local/bin/pip3")
        arch_arg = "-arm64" if cpu_arch == "arm64" else "-x86_64"
        
        homebrew_base = Path("/opt/homebrew") if cpu_arch == "arm64" else Path("/usr/local/Homebrew")
        homebrew_pip = homebrew_base / "bin" / "pip3.11"
        
        if custom_pip.exists() and os.access(custom_pip, os.X_OK):
            pip_cmd = ["arch", arch_arg, str(custom_pip)]
        elif homebrew_pip.exists() and os.access(homebrew_pip, os.X_OK):
            pip_cmd = [str(homebrew_pip)]
        else:
            pip_cmd = ["pip3"]
    else:
        # Simplification for Linux
        if "linux" in OSTYPE:
            if os.environ.get("linux_type") == "micromamba":
                pip_cmd = ["pip3"]
                opts.extend(["--cache-dir", str(WGSE_FP / "micromamba" / "cache" / "pip")])
            else:
                pip_cmd = ["pip3"]
        elif "msys" in OSTYPE:
            pip_cmd = [str(WGSE_FP / "msys2" / "ucrt64" / "bin" / "python"), "-m", "pip"]
        elif "cygwin" in OSTYPE:
            pip_cmd = [str(WGSE_FP / "python" / "python.exe"), "-m", "pip"]
        else:
            pip_cmd = ["pip3"]

    if not pip_cmd:
        logger.error(f"Unknown OS:ARCH combination: {OSTYPE}:{cpu_arch}")
        return

    # Filter string for log output
    strip_prefixes = (
        "Requirement already satisfied", "Collecting", "Obtaining", "Preparing",
        "Running", "Downloading", "Installing", "Getting", "Using legacy",
        "Using cached", "Building", "Created", "Stored", "Successfully built",
        "━━━━", "-----"
    )

    def run_pip(args: List[str]):
        full_cmd = pip_cmd + args + opts
        with open(pip_log, 'a') as log_f:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                log_f.write(line)
                if not any(line.strip().startswith(p) for p in strip_prefixes):
                    print(line, end="", flush=True)
            process.wait()

    echo_tee("    ... updating pip")
    run_pip(["install", "--upgrade", "pip"])
    
    echo_tee("    ... installing libraries")
    run_pip(["install"] + libs)

    echo_tee("    ... finished upgrading the Python 3.x libraries")
