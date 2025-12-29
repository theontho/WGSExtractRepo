#!/usr/bin/env bash
# dev-launch.sh - Launch WGS Extract in development environment

case "$OSTYPE" in
    darwin*)
        echo "Launching WGS Extract for MacOS..."
        ./installer_scripts/WGSExtract.command
        ;;
    linux*)
        if grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
            echo "Launching WGS Extract for Ubuntu..."
            ./installer_scripts/WGSExtract_ubuntu.sh
        else
            echo "Launching WGS Extract for Linux..."
            ./installer_scripts/WGSExtract_linux.sh
        fi
        ;;
    msys*|cygwin*)
        echo "Launching WGS Extract for Windows..."
        cmd.exe /c "installer_scripts\WGSExtract.bat"
        ;;
    *)
        echo "Unsupported OS: $OSTYPE"
        exit 1
        ;;
esac
