import os
import sys
import json
import shutil
from pathlib import Path

from .constants import MANIFEST, TMP_DIR
from .utils import (
    run_command, 
    get_cygwin_bash, 
    add_to_user_path_windows, 
    cleanup_root_artifacts
)
from .setup_env import (
    ensure_runtime_directories, 
    ensure_uv, 
    setup_venv, 
    install_python_dependencies, 
    download_and_extract, 
    run_cygwin_setup, 
    copy_launch_scripts
)

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
    
    # If we found an absolute path, we should probably add its dir to PATH
    if uv_cmd and os.path.isabs(uv_cmd):
        uv_dir = str(Path(uv_cmd).parent)
        
        # 1. Update current session
        if uv_dir.lower() not in os.environ["PATH"].lower():
            print(f"Adding {uv_dir} to PATH for this session...")
            os.environ["PATH"] = uv_dir + os.pathsep + os.environ["PATH"]
            
        # 2. Update persistent User PATH (Windows only)
        if sys.platform == "win32" and "cygdrive" not in uv_cmd:
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
            download_and_extract("bioinfo", manifest_data, dest="cygwin64/usr")
        elif choice == "2":
            download_and_extract("msys2", manifest_data)
            download_and_extract("bioinfo-msys2", manifest_data, dest="msys2")
        
        copy_launch_scripts()
    else:
        copy_launch_scripts()

    print("\n==========================================")
    print("Initialization Complete!")
    print("==========================================")
    
    cleanup_root_artifacts()
