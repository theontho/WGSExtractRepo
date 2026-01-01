#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
from typing import Optional, Dict, Any, Union

# Paths relative to the repository root
REPO_ROOT = Path(__file__).parent.parent.resolve()
RELEASE_JSON_PATH = REPO_ROOT / "release.json"
LOCAL_RELEASE_DIR = REPO_ROOT / "local_release"
OUTPUT_JSON_PATH = REPO_ROOT / "release-override.json"


def download_file(url: str, dest: Union[str, Path]) -> None:
    """Downloads a file from a URL to a destination path using curl."""
    print(f"Downloading {url} to {dest}...")
    try:
        subprocess.run(["curl", "-k#LC", "-", "--retry", "5", "-o", str(dest), url], check=True)
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def fetch_json(url: str) -> Optional[Dict[str, Any]]:
    """Fetches JSON content from a URL using curl."""
    try:
        result = subprocess.run(["curl", "-k#LC", "-", "--retry", "5", url], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error fetching JSON from {url}: {e}")
        return None

def setup_local_release() -> None:
    if not RELEASE_JSON_PATH.exists():
        print(f"Error: {RELEASE_JSON_PATH} not found in repository root.")
        return

    print(f"Reading base configuration from {RELEASE_JSON_PATH}")
    with open(RELEASE_JSON_PATH, "r") as f:
        config = json.load(f)

    # Ensure local_release directory exists
    LOCAL_RELEASE_DIR.mkdir(exist_ok=True)

    track = config.get("release", {}).get("track", "Dev")
    track_url_key = f"{track}URL"
    latest_json_url = config.get("release", {}).get(track_url_key)

    latest_config = None
    if latest_json_url and latest_json_url.startswith("http"):
        print(f"Fetching latest release info from {latest_json_url}")
        latest_config = fetch_json(latest_json_url)

    if latest_config is None:
        print("Warning: Using local release.json as base.")
        latest_config = config

    # Use the latest config as a base for the new local config
    new_config = latest_config.copy()

    # Re-insert or ensure release and version sections are present from the original config
    if "release" in config:
        new_config["release"] = config["release"].copy()
    if "version" in config:
        new_config["version"] = config["version"].copy()

    # Iterate through all sections and update URLs to local file paths
    for key, value in latest_config.items():
        if isinstance(value, dict) and "URL" in value:
            url = value["URL"]
            if not url.startswith("http"):
                continue
                
            filename = os.path.basename(url)
            local_path = LOCAL_RELEASE_DIR / filename
            
            if not local_path.exists():
                download_file(url, local_path)
            else:
                print(f"File {filename} already exists in local_release/")
            
            # Update the URL to a local file:// path
            new_config[key]["URL"] = f"file://{local_path.absolute()}"
            
            # Handle optional buildURL (e.g., for cygwin64/msys2)
            if "buildURL" in value:
                build_url = value["buildURL"]
                if build_url.startswith("http"):
                    build_filename = os.path.basename(build_url)
                    build_local_path = LOCAL_RELEASE_DIR / build_filename
                    if not build_local_path.exists():
                        download_file(build_url, build_local_path)
                    new_config[key]["buildURL"] = f"file://{build_local_path.absolute()}"

    # Update the release section to make the local config self-consistent
    if "release" in new_config:
        # Point the current track URL to this generated file
        new_config["release"][track_url_key] = f"file://{OUTPUT_JSON_PATH.absolute()}"
        print(f"Updated {track_url_key} to point to {OUTPUT_JSON_PATH}")

    # Write the new local release JSON
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(new_config, f, indent=2)
    
    print(f"\nSuccess! Created local release override at: {OUTPUT_JSON_PATH}")
    print(f"\nThe installer scripts will now automatically use this local configuration.")
    print(f"To revert to the built-in release, simply delete the {OUTPUT_JSON_PATH.name} file.")

if __name__ == "__main__":
    setup_local_release()
