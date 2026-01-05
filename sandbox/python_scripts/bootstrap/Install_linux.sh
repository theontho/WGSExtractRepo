#!/usr/bin/env bash
# WGS Extract Minimal Bootstrap for Linux
# This script ensures a minimal Python environment exists and then 
# hands over control to the new Python-based installer.

echo "Starting WGS Extract Bootstrap (Linux)..."

# 1. Determine base path
WGSE_FP=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
cd "$WGSE_FP" || exit 1
export wgse_FP="$WGSE_FP"

# 2. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Attempting to use bundled Micromamba..."
    # If we are in a fresh install, we might need to bootstrap Micromamba first 
    # to get a Python version we can use.
    # However, for Linux, the goal is often to use the new_scripts/core/linux.py 
    # setup which downloads Micromamba itself.
    
    # We'll try to use a simple approach: if python3 is missing, 
    # try to install it or tell the user. Most modern Linux have it.
    echo "Error: Python 3 is required to start the installation."
    echo "Please install python3 (e.g., 'sudo apt install python3' or 'sudo dnf install python3') and try again."
    exit 1
fi

# 3. Launch the new Python installer
echo "Launching Python-based installer..."
export linux_type="micromamba"
python3 new_scripts/install_linux.py "$@"
