#!/usr/bin/env bash
# WGS Extract Minimal Uninstall Bootstrap for Ubuntu

echo "Starting WGS Extract Uninstall Bootstrap (Ubuntu)..."

# 1. Determine base path
WGSE_FP=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$WGSE_FP" || exit 1

# 2. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required to start the uninstallation."
    exit 1
fi

# 3. Launch the new Python uninstaller
echo "Launching Python-based uninstaller..."
python3 sandbox/python_scripts/uninstall_linux.py "$@"
