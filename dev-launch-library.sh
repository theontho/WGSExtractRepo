#!/usr/bin/env bash
# dev-launch-library.sh - Launch WGS Extract Library in development environment

case "$OSTYPE" in
    darwin*)
        echo "Launching WGS Extract Library for MacOS..."
        ./installer_scripts/Library.command
        ;;
    linux*)
        if grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
            echo "Launching WGS Extract Library for Ubuntu..."
            ./installer_scripts/Library_ubuntu.sh
        else
            echo "Launching WGS Extract Library for Linux..."
            ./installer_scripts/Library_linux.sh
        fi
        ;;
    msys*|cygwin*)
        echo "Launching WGS Extract Library for Windows..."
        cmd.exe /c "installer_scripts\Library.bat"
        ;;
    *)
        echo "Unsupported OS: $OSTYPE"
        exit 1
        ;;
esac
