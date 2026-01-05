#!/usr/bin/env bash
# WGS Extract Minimal Bootstrap for Ubuntu
# This script ensures a minimal Python environment exists and then 
# hands over control to the new Python-based installer.

echo "Starting WGS Extract Bootstrap (Ubuntu)..."

# 1. Determine base path
WGSE_FP=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
cd "$WGSE_FP" || exit 1
export wgse_FP="$WGSE_FP"

# 2. Ensure Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Attempting to install via apt..."
    if command -v sudo &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3
    else
        apt-get update && apt-get install -y python3
    fi
fi

# 3. Launch the new Python installer
echo "Launching Python-based installer..."
export linux_type="ubuntu"
python3 sandbox/python_scripts/install_ubuntu.py "$@"
