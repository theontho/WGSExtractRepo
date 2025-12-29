#!/usr/bin/env bash
# dev-init.sh - Initialize development environment for WGS Extract
# Downloads dependencies from release_manifest.json

MANIFEST="installer_scripts/release.json"

# 1. Check for JQ
if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' is not installed. Please install 'jq' to continue.  macos: brew install jq , linux: sudo apt install jq, windows: choco install jq"
    exit 1
fi

# 2. Check for Manifest
if [ ! -f "$MANIFEST" ]; then
    echo "Error: $MANIFEST not found."
    exit 1
fi

# 3. Create tmp directory
mkdir -p tmp

# Function to download and extract
download_and_extract() {
    local pack=$1
    local url=$(jq -r ."$pack".URL "$MANIFEST")
    if [ "$url" == "null" ] || [ -z "$url" ]; then
        echo "Warning: No URL found for '$pack' in $MANIFEST"
        return
    fi

    local filename=$(basename "$url")
    echo "--- Preparing $pack ---"
    
    if [ -f "tmp/$filename" ]; then
        echo "Found existing tmp/$filename, skipping download..."
    else
        echo "Downloading $pack from $url..."
        curl -L -o "tmp/$filename" "$url"
    fi

    echo "Extracting $pack..."
    case "$OSTYPE" in
        darwin*)
            if command -v 7zz &> /dev/null; then
                7zz x -y "tmp/$filename" > /dev/null
            else
                unzip -o "tmp/$filename" > /dev/null
            fi
            ;;
        linux*)
            if command -v 7z &> /dev/null; then
                7z x -y "tmp/$filename" > /dev/null
            else
                unzip -o "tmp/$filename" > /dev/null
            fi
            ;;
        msys*|cygwin*)
            powershell -Command "Expand-Archive -Path 'tmp/$filename' -DestinationPath './' -Force"
            ;;
        *)
            unzip -o "tmp/$filename" > /dev/null
            ;;
    esac
    
    # Check for nested WGSExtractv4 folder and move contents to root
    if [ -d "WGSExtractv4" ]; then
        echo "Cleaning up nested extraction folder..."
        cp -rn WGSExtractv4/* .
        rm -rf WGSExtractv4
    fi

    echo "Finished $pack."
}

echo "=========================================="
echo "WGS Extract Development Environment Init"
echo "=========================================="

# Always download reflib and tools
download_and_extract "reflib"
download_and_extract "tools"

# Merge base_reference into reference
if [ -d "base_reference" ]; then
    echo "Merging base_reference into reference..."
    mkdir -p reference
    cp -rv base_reference/* reference/ > /dev/null
fi

# Platform specific
case "$OSTYPE" in
    msys*|cygwin*)
        echo ""
        echo "Detected Windows environment (Cygwin/MSYS2)."
        echo "Choose environment to initialize:"
        echo "1) Cygwin64"
        echo "2) MSYS2"
        read -p "Enter choice [1-2]: " choice
        if [ "$choice" == "1" ]; then
            download_and_extract "cygwin64"
            download_and_extract "bioinfo"
        elif [ "$choice" == "2" ]; then
            download_and_extract "msys2"
            download_and_extract "bioinfo-msys2"
        else
            echo "Invalid choice. Skipping platform-specific dependencies."
        fi
        ;;
    darwin*)
        echo ""
        echo "Detected MacOS. No additional dependencies needed from manifest."
        ;;
    linux*)
        echo ""
        echo "Detected Linux. No additional dependencies needed from manifest."
        ;;
esac

echo ""
echo "=========================================="
echo "Initialization Complete!"
echo "=========================================="
