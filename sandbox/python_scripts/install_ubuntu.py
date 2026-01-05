import platform
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from install.installer import main_installer

if __name__ == "__main__":
    cpu_arch = platform.machine()
    os_ver = platform.release()
    os.environ["linux_type"] = "ubuntu"
    main_installer(cpu_arch, os_ver)
