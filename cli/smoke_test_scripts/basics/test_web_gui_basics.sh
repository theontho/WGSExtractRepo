#!/bin/bash

# Load common functions
# shellcheck source=/dev/null
source "$(dirname "$0")/../common.sh"

if [[ "$1" == "--describe" ]]; then
    echo "Description: Tests that the Web GUI starts correctly and is accessible."
    echo "✅ Verified End Goal: Web server started and responding to HTTP requests; verified by curl on localhost:8081."
    exit 0
fi

OUTDIR="out/smoke_test_web_gui"
mkdir -p "$OUTDIR"

echo "--------------------------------------------------------"
echo "  WGS Extract CLI: Web GUI Basics Smoke Test"
echo "--------------------------------------------------------"

# 1. Test 'web-gui --help'
echo ":: Testing 'web-gui --help'..."
if uv run wgsextract web-gui --help > "$OUTDIR/web_gui_help.stdout" 2>&1; then
    echo "✅ Success: 'web-gui --help' completed."
else
    echo "❌ Failure: 'web-gui --help' failed."
    exit 1
fi

# 2. Start Web GUI in background
echo ":: Starting Web GUI in background..."
# We use a different port if needed, but the default is 8081.
# NiceGUI might take a while to start.
uv run wgsextract web-gui > "$OUTDIR/web_gui.log" 2>&1 &
GUI_PID=$!

# Cleanup function to kill the GUI on exit
cleanup() {
    echo ":: Cleaning up Web GUI (PID: $GUI_PID)..."
    kill "$GUI_PID" 2>/dev/null
    wait "$GUI_PID" 2>/dev/null
}
trap cleanup EXIT

echo ":: Waiting for Web GUI to start (up to 30 seconds)..."
MAX_RETRIES=30
COUNT=0
SUCCESS=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8081 > /dev/null; then
        SUCCESS=true
        break
    fi
    sleep 1
    COUNT=$((COUNT + 1))
    echo -n "."
done
echo ""

if [ "$SUCCESS" = true ]; then
    echo "✅ Success: Web GUI is up and responding on http://localhost:8081"
else
    echo "❌ Failure: Web GUI failed to respond within $MAX_RETRIES seconds."
    echo "--- Last 20 lines of log ---"
    tail -n 20 "$OUTDIR/web_gui.log"
    exit 1
fi

echo ""
echo "========================================================"
echo "Web GUI Basics Smoke Test: PASSED"
echo "========================================================"
