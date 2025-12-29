#!/usr/bin/env bash
# dev-init.sh - Initialize development environment for WGS Extract
# Downloads dependencies from release_manifest.json

MANIFEST="release_manifest.json"

if [ ! -f "$MANIFEST" ]; then
    echo "Error: $MANIFEST not found."
    exit 1
fi

# Create tmp directory
mkdir -p tmp

# Function to download and extract
download_and_extract() {
    local pack=$1
    local url=$(jq -r ."$pack".URL "$MANIFEST")
    if [ "$url" == "null" ] || [ -z "$url" ]; then
        echo "Warning: No URL found for $pack"
        return
    fi

    local filename=$(basename "$url")
    echo "Downloading $pack from $url..."
    curl -L -o "tmp/$filename" "$url"

    echo "Extracting $pack..."
    case "$OSTYPE" in
        darwin*)
            # Use 7zz if available, else unzip
            if command -v 7zz &> /dev/null; then
                7zz x -y "tmp/$filename"
            else
                unzip -o "tmp/$filename"
            fi
            ;;
        linux*)
            if command -v 7z &> /dev/null; then
                7z x -y "tmp/$filename"
            else
                unzip -o "tmp/$filename"
            fi
            ;;
        msys*|cygwin*)
            powershell -Command "Expand-Archive -Path 'tmp/$filename' -DestinationPath './' -Force"
            ;;
        *)
            unzip -o "tmp/$filename"
            ;;
    esac
}

# Always download reflib and tools
download_and_extract "reflib"
download_and_extract "tools"

# Platform specific
case "$OSTYPE" in
    msys*|cygwin*)
        echo "Detected Windows environment."
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
        echo "Detected MacOS. No additional dependencies needed from manifest."
        ;;
    linux*)
        echo "Detected Linux. No additional dependencies needed from manifest."
        ;;
esac

echo "Development environment initialized."
