import sys
from pathlib import Path
from install_test_base import run_install_test

def test_windows_installer(is_new_installer: bool):
    test_name = "windows_new" if is_new_installer else "windows_legacy"
    
    # Windows-specific configurations
    zip_glob_pattern = "*_windows_installer.zip"
    
    # On Windows, we need to use 'cmd /c' to run .bat files properly from subprocess.run
    if is_new_installer:
        # Assuming new_scripts/install_windows.py might exist in the future, 
        # Assuming sandbox/python_scripts/install_windows.py might exist in the future, 
        installer_cmd = [sys.executable, "sandbox/python_scripts/install_windows.py"]
    else:
        installer_cmd = ["cmd", "/c", "Install_windows.bat"]
        
    expected_files = [
        Path("WGSExtract.bat"),
        Path("program/wgsextract.py"),
        Path("jartools")
    ]
    
    launch_cmd = ["cmd", "/c", "WGSExtract.bat", "--auto"]
    
    # Marker text that indicates successful launch
    # In Windows WGSExtract.bat, it shows: Starting WGS Extract on cygwin64 ...
    launch_marker_text = "Starting WGS Extract on cygwin64"

    run_install_test(
        test_name=test_name,
        zip_glob_pattern=zip_glob_pattern,
        installer_cmd=installer_cmd,
        expected_files=expected_files,
        launch_cmd=launch_cmd,
        launch_marker_text=launch_marker_text,
        is_new_installer=is_new_installer
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Windows installer tests.")
    parser.add_argument("-n", "--new", action="store_true", help="Test the new Python-based installer.")
    args = parser.parse_args()
    
    test_windows_installer(is_new_installer=args.new)
