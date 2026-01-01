import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Union, List

def run_command(cmd: Union[str, List[str]], shell: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)

def get_cygwin_bash() -> str:
    """Returns the absolute path to cygwin bash.exe or just 'bash' if not on Windows."""
    if sys.platform == "win32":
        # Assume cygwin64 is in the current directory or a standard location
        # Prefer sh.exe as bash.exe is broken in some Cygwin versions
        for shell in ["sh.exe", "bash.exe"]:
            local_cyg = Path.cwd() / "cygwin64" / "bin" / shell
            if local_cyg.exists():
                return str(local_cyg)
        # Fallback to C:\cygwin64 if local doesn't exist
        for shell in ["sh.exe", "bash.exe"]:
            std_cyg = Path("C:/cygwin64/bin") / shell
            if std_cyg.exists():
                return str(std_cyg)
    return "bash"

def add_to_user_path_windows(directory: str) -> None:
    """
    Safely adds a directory to the persistent User PATH using the Registry.
    Does not use setx to avoid truncation.
    """
    try:
        import winreg
    except ImportError:
        print("Warning: winreg module not available.")
        return

    print(f"Checking persistent PATH for: {directory}")
    
    key_path = r"Environment"
    try:
        # Open Key
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        
        # Read current PATH
        try:
            current_path_val, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path_val = ""

        # Normalize for check
        path_parts = [p.strip() for p in current_path_val.split(";") if p.strip()]
        
        # Check if already present
        found = False
        for part in path_parts:
            if part.lower() == directory.lower():
                found = True
                break
        
        if not found:
            print(f"Adding {directory} to permanent User PATH...")
            # Append new path
            if not current_path_val.endswith(";"):
                 current_path_val += ";"
            new_path_val = current_path_val + directory
            
            # Write back
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_val)
            print("Successfully updated Registry PATH.")
            
            # Broadcast change mainly for other new windows, though usually requires restart
            # This is a bit "best effort" in Python without ctypes boilerplate, 
            # but usually script just reminds user.
            print("Note: You may need to restart your terminal for changes to take effect globally.")
        else:
            print("Path already in Registry.")

        winreg.CloseKey(key)

    except Exception as e:
        print(f"Warning: Failed to update persistent PATH in registry: {e}")

def cleanup_root_artifacts() -> None:
    """Clean up any temporary executables that might have landed in the root."""
    print("Performing final cleanup...")
    artifacts = ["setup-x86_64.exe"]
    for art in artifacts:
        p = Path(art)
        if p.exists():
            try:
                p.unlink()
                print(f"Removed {art} from root.")
            except Exception as e:
                print(f"Warning: Failed to remove {art}: {e}")
