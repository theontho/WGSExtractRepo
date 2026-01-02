import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from new_scripts.uninstall.uninstaller import run_uninstaller
from new_scripts.core.common import get_reflib_dir

if __name__ == "__main__":
    reflibdir = get_reflib_dir()
    run_uninstaller(reflibdir)
