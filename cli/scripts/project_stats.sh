#!/bin/bash

# Simple script to run cloc with appropriate exclusions for this project.
# Requires 'cloc' to be installed on the system.

if ! command -v cloc >/dev/null 2>&1; then
    echo "❌ Error: 'cloc' is not installed. Please install it (e.g., brew install cloc or apt install cloc)."
    exit 1
fi

echo "========================================================"
echo "  WGS Extract CLI: Project Statistics"
echo "========================================================"

echo ""
echo "--- Full Project (Excluding generated data and external deps) ---"
cloc . --fullpath --not-match-d='\.git|\.venv|out|tmp|\.pixi|\.mypy_cache|\.pytest_cache|\.ruff_cache|external/yleaf' --vcs=git

echo ""
echo "--- Production Code (src/wgsextract_cli) ---"
cloc src/wgsextract_cli --vcs=git

echo ""
echo "--- Test Code (tests/ and smoke_test_scripts/) ---"
cloc tests smoke_test_scripts --vcs=git

echo ""
echo "========================================================"
