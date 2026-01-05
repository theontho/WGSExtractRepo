#!/usr/bin/env bash
# WGS Extract Minimal Bootstrap for macOS
# This script ensures a minimal Python environment exists and then 
# hands over control to the new Python-based installer.

echo "Starting WGS Extract Bootstrap (macOS)..."

# 1. Determine base path
WGSE_FP=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$WGSE_FP" || exit 1
export wgse_FP="$WGSE_FP"

# 2. Check for Python 3
# macOS usually comes with python3 (or triggers an install prompt)
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Triggers Xcode CLI install to get Python..."
    xcode-select --install
    echo "Please follow the on-screen instructions to install Xcode CLI tools, then run this script again."
    exit 1
fi

# 3. Launch the new Python installer
echo "Launching Python-based installer..."
export macos_type="macports"
python3 sandbox/python_scripts/install_macos.py "$@"
