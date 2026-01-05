#!/usr/bin/env python3
import sys
from pathlib import Path
from install_test_base import run_install_test

def run_brew_install_test(test_name: str, is_new_installer: bool):
    # macOS-specific configurations
    zip_glob_pattern = "*_macos_brew_installer.zip"
    
    if is_new_installer:
        installer_cmd = [sys.executable, "sandbox/python_scripts/install_macos_brew.py"]
    else:
        installer_cmd = ["bash", "Install_macos_brew.command"]
        
    expected_files = [
        Path("WGSExtract.command"),
        Path("program/wgsextract.py"),
        Path("jartools")
    ]
    
    launch_cmd = ["bash", "WGSExtract.command", "--auto"]
    launch_marker_text = "Starting WGS Extract"

    run_install_test(
        test_name=test_name,
        zip_glob_pattern=zip_glob_pattern,
        installer_cmd=installer_cmd,
        expected_files=expected_files,
        launch_cmd=launch_cmd,
        launch_marker_text=launch_marker_text,
        is_new_installer=is_new_installer
    )

