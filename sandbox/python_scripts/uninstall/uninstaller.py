import sys
import shutil
import platform
import subprocess
from pathlib import Path
from new_scripts.core.common import WGSE_FP, OSTYPE, rmx, rmrx
from new_scripts.core.logging import echo_tee, askyesno

def run_uninstaller(reflibdir: Path):
    """Main uninstall logic (transliterated from zuninstall_common.sh)."""
    print('='*80)
    print('Now removing the WGS Extract program and reference library itself.')
    
    wgse_enclose = WGSE_FP.parent
    wgse_base = WGSE_FP.name

    if not WGSE_FP.exists() or not wgse_enclose.exists():
        print("\n*** ERROR: the installation base for the WGS Extract program is not defined.")
        return

    # User query
    remove_wgse = askyesno(f"Do you want to DELETE the WGS Extract program in {wgse_base}")

    if remove_wgse:
        rmx(HOME / ".wgsextract")
        rmx(HOME / ".wgsedebug")
        rmx(HOME / ".wgsewslbwa")
        print(f"... Removing the WGS Extract program in {wgse_base}")

    # Reference Library handling
    if reflibdir.exists() and remove_wgse:
        keep_reflib = askyesno(f"Do you want to KEEP the WGS Extract Reference Library ({reflibdir.name})")
        
        if keep_reflib:
            if reflibdir.parent == WGSE_FP:
                new_path = wgse_enclose / f"{reflibdir.name}_saved"
                mvx(reflibdir, new_path)
                print(f"... Saving the Reference Library to {new_path}")
        else:
            if reflibdir.parent != WGSE_FP:
                print(f"... Removing the Reference Library folder {reflibdir.name}.")
                rmrx(reflibdir)

    if not remove_wgse:
        input('Press Enter to close this window...')
        return

    # Final self-deletion logic
    print("\n" + '='*80)
    print("(Almost) Finished uninstalling WGS Extract and its programs.")
    input('Press Enter to finish deleting (close other apps first)...')

    # Change directory so we can delete the folder we are in
    os.chdir(wgse_enclose)

    if OSTYPE == "darwin" or OSTYPE == "linux":
        # Launch background process to delete
        subprocess.Popen(['nohup', 'rm', '-rf', wgse_base], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                         start_new_session=True)
    elif "msys" in OSTYPE or "cygwin" in OSTYPE:
        subprocess.Popen(['cmd.exe', '/d', '/c', 'start', '/b', 'rmdir', str(WGSE_FP.resolve()), '/s', '/q'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    
    sys.exit(0)

if __name__ == "__main__":
    # Usually passed from platform-specific uninstaller
    if len(sys.argv) > 1:
        run_uninstaller(Path(sys.argv[1]))
    else:
        # Default to standard location
        run_uninstaller(WGSE_FP / "reference")
