import os
import sys
import platform
import shutil
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

# Global constants equivalent to success=0 fail=1
SUCCESS = 0
FAIL = 1

def get_wgse_fp() -> Path:
    """Returns the base WGS Extract directory."""
    # Logic from zcommon.sh: determine based on script location or passed in value
    res = Path(__file__).resolve().parent.parent.parent.parent
    return res

WGSE_FP = get_wgse_fp()

def get_ostype() -> str:
    """Returns a simplified OSTYPE equivalent."""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        # Check if we are in MSYS or Cygwin
        if "MSYSTEM" in os.environ:
            return "msys"
        return "windows"
    return system

OSTYPE = get_ostype()

def get_cpu_arch() -> str:
    """Returns the CPU architecture."""
    return platform.machine()

CPU_ARCH = get_cpu_arch()

def get_home() -> Path:
    """Returns the user's home directory."""
    return Path.home()

HOME = get_home()

if OSTYPE == "linux":
    BASHX = WGSE_FP / "micromamba" / "bin" / "bash"
else:
    BASHX = Path("/bin/bash")

def ver_comp(v1: str, op: str, v2: str) -> bool:
    """
    Compares two version strings.
    Supported ops: <, >, ==, !=, <=, >=
    """
    def filter_ver(v: str) -> List[int]:
        import re
        # Transliteration of _filterVer and _alpha_to_ASCII
        # Convert alphabets to ASCII, change 'p' to '.', collapse delimiters
        v = str(v).upper().replace('P', '.')
        # Convert any other alpha to .ASCII.
        v = re.sub(r'([A-Z])', r'.\1.', v)
        
        parts: List[int] = []
        for part in v.split('.'):
            if not part:
                continue
            if part.isdigit():
                parts.append(int(part))
            elif part.isalpha() and len(part) == 1:
                parts.append(ord(part))
            else:
                # Handle cases like 'v4' or other mixed strings if they occur
                # For simplicity, if we find a single char we use ord, if it's longer it might be an issue
                # But let's follow the shell script's spirit
                for char in part:
                    if char.isalpha():
                        parts.append(ord(char))
                    elif char.isdigit():
                        parts.append(int(char))
        return parts

    p1 = filter_ver(v1)
    p2 = filter_ver(v2)
    
    # Pad shorter one with zeros
    max_len = max(len(p1), len(p2))
    p1 += [0] * (max_len - len(p1))
    p2 += [0] * (max_len - len(p2))
    
    # Convert to tuples for easy comparison
    t1 = tuple(p1)
    t2 = tuple(p2)
    
    if op == '==': return t1 == t2
    if op == '!=': return t1 != t2
    if op == '<': return t1 < t2
    if op == '<=': return t1 <= t2
    if op == '>': return t1 > t2
    if op == '>=': return t1 >= t2
    
    raise ValueError(f"Unsupported operator: {op}")

def load_json(path: Path) -> Dict[str, Any]:
    """Safely loads a JSON file."""
    if not path.exists():
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def get_latest_json() -> Dict[str, Any]:
    """Retrieves/loads the latest release JSON."""
    release_json_path = WGSE_FP / "release.json"
    override_json_path = WGSE_FP / "release-override.json"
    
    # Logic from zcommon.sh:
    # 1. Determine track and URLs from local release.json (or override)
    local_path = release_json_path
    if override_json_path.exists():
        local_path = override_json_path
    
    local_data = load_json(local_path)
    release = local_data.get("release", {})
    track = release.get("track", "Beta") # Default to Beta
    
    # 2. Determine URL for latest json
    # baseURL = release.get("baseURL", "https://get.wgse.io/")
    # Format: latest-release-{track}.json usually
    latest_pkg_url = release.get(f"{track}URL")
    
    if not latest_pkg_url:
        # Fallback defaults
        base_url = "https://get.wgse.io/"
        latest_pkg_url = f"{base_url}latest-release-{track}.json"
    
    # 3. Download latest.json
    latest_json_path = WGSE_FP / "latest.json"
    # Always try to download? or only if missing? zcommon says:
    # "Retrieve a new ... if local one is missing or local has different url"
    # For now, let's always try to download to ensure freshness, logic in py installer
    # will call this.
    try:
        print(f"Retrieving latest info for track {track}...")
        if download_file(latest_pkg_url, latest_json_path):
             return load_json(latest_json_path)
    except Exception as e:
        print(f"Failed to download latest.json: {e}")
    
    # Fallback to existing latest.json or local release.json if download fails
    if latest_json_path.exists():
        return load_json(latest_json_path)
    
    # Fallback to local data (better than nothing, might be same as latest if fresh install)
    return local_data

def get_reflib_dir() -> Path:
    """Finds the reference library directory."""
    default_reflib = WGSE_FP / "reference"
    settings_path = HOME / ".wgsextract"
    
    if settings_path.exists():
        settings = load_json(settings_path)
        new_reflib = settings.get("reflib.FP")
        if new_reflib:
            return Path(new_reflib)
            
    return default_reflib

# Utility file operations
def rmx(target: Union[str, Path]):
    """Safe remove file (equivalent to rm -f)."""
    p = Path(target)
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass

def rmrx(target: Union[str, Path]):
    """Safe recursive remove (equivalent to rm -rf)."""
    p = Path(target)
    if p.exists():
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError:
            pass

def cpx(src: Union[str, Path], dst: Union[str, Path]):
    """Safe copy (equivalent to cp -fp)."""
    try:
        shutil.copy2(src, dst)
    except OSError:
        pass

def mvx(src: Union[str, Path], dst: Union[str, Path]):
    """Safe move (equivalent to mv -f)."""
    try:
        shutil.move(str(src), str(dst))
    except OSError:
        pass

def read_current_release_info(package: str, json_path: Path, verbose: bool = False):
    """Transliteration of read_current_release_info from zcommon.sh."""
    data = load_json(json_path)
    version = data.get(package, {}).get("version", "0")
    date = data.get(package, {}).get("date", "01Jan2020")
    return version, date

def get_latest_release_info(package: str, verbose: bool = False):
    """Transliteration of get_latest_release_info from zcommon.sh."""
    data = get_latest_json()
    version = data.get(package, {}).get("version", "0")
    date = data.get(package, {}).get("date", "01Jan2020")
    return version, date

def download_file(url: str, dest: Path) -> bool:
    """
    Downloads a file from a URL to a destination path.
    Uses curl if available for better progress bars/resiliency, falls back to urllib.
    """
    if shutil.which("curl"):
        try:
            # -L follows redirects, -f fails on HTTP errors, -o output file
            # --retry 3 for transient errors
            cmd = ["curl", "-L", "-f", "--retry", "3", "-o", str(dest), url]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            pass # Fallback to urllib or return False
            
    # Fallback to python native
    import urllib.request
    try:
        with urllib.request.urlopen(url) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    """
    Extracts a zip file to a destination directory.
    Uses 7z/7zz if available (faster/more robust), else python zipfile.
    """
    # Try 7z/7zz first as per original scripts logic preferred 7zip
    seven_z = shutil.which("7zz") or shutil.which("7z")
    if seven_z:
        try:
            # x: extract, -y: yes to all, -o: output dir
            cmd = [seven_z, "x", "-y", f"-o{dest_dir}", str(zip_path)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            pass

    # Fallback to python zipfile
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        return True
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return False

def change_release_json(new_json_path: Path) -> bool:
    """
    Checks if the release track has changed in the new release.json.
    Returns True if track changed or local release.json missing.
    """
    if not (WGSE_FP / "release.json").exists():
        return True
        
    if not new_json_path.exists():
        return False

    current_data = load_json(WGSE_FP / "release.json")
    new_data = load_json(new_json_path)

    curr_track = current_data.get("release", {}).get("track")
    new_track = new_data.get("release", {}).get("track")
    
    return curr_track != new_track
