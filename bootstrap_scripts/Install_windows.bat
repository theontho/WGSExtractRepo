@echo off
setlocal EnableDelayedExpansion

echo Starting WGS Extract Bootstrap (Windows)...

REM 1. Determine base path
set "WGSE_FP=%~dp0"
cd /d "%WGSE_FP%"
set "wgse_FP=%WGSE_FP%"

REM 2. Check for Python
where python >nul 2>&1
if ERRORLEVEL 1 (
    where python3 >nul 2>&1
    if ERRORLEVEL 1 (
        echo Python not found in PATH.
        echo Please install Python 3 from python.org or the Microsoft Store.
        pause
        exit /b 1
    ) else (
        set "py=python3"
    )
) else (
    set "py=python"
)

REM 3. Launch the new Python installer
echo Launching Python-based installer...
%py% new_scripts\install_windows.py %*
if ERRORLEVEL 1 (
    echo Installation failed.
    pause
    exit /b 1
)

pause
