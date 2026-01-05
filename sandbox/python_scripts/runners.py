import sys
import os
import subprocess
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from new_scripts.core.common import WGSE_FP, OSTYPE, BASHX
from new_scripts.core.logging import echo_tee, logger
from new_scripts.core.library import main_menu

def run_wgsextract():
    """Launches the WGS Extract main program."""
    echo_tee("Starting WGS Extract...")
    
    # Path to the main python entry point or legacy bash runner
    # For now, we still likely rely on the bash logic if we haven't ported the main app
    # But we can at least set the environment and launch.
    
    app_py = WGSE_FP / "program" / "WGSExtract.py"
    if app_py.exists():
        subprocess.run([sys.executable, str(app_py)], check=True)
    else:
        # Fallback to legacy
        legacy_sh = WGSE_FP / "scripts" / "zcommon.sh" # Not really a runner, just an example
        logger.error("Main app entry point not found in new system.")

def run_library():
    """Launches the Reference Library menu."""
    library_menu()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "library":
        run_library()
    else:
        run_wgsextract()
