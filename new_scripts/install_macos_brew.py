import platform
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from new_scripts.install.installer import main_installer

if __name__ == "__main__":
    cpu_arch = "arm64" if "arm" in platform.machine().lower() else "x86_64"
    os_ver = platform.mac_ver()[0]
    os.environ["macos_type"] = "homebrew"
    main_installer(cpu_arch, os_ver)
