@echo off
setlocal EnableDelayedExpansion

echo Starting WGS Extract Uninstall Bootstrap (Windows)...

REM 1. Determine base path
set "WGSE_FP=%~dp0"
cd /d "%WGSE_FP%"

REM 2. Check for Python
where python >nul 2>&1
if ERRORLEVEL 1 (
    where python3 >nul 2>&1
    if ERRORLEVEL 1 (
        echo Python not found in PATH.
        pause
        exit /b 1
    ) else (
        set "py=python3"
    )
) else (
    set "py=python"
)

REM 3. Launch the new Python uninstaller
echo Launching Python-based uninstaller...
%py% new_scripts\uninstall_windows.py %*
if ERRORLEVEL 1 (
    echo Uninstallation failed.
    pause
    exit /b 1
)

pause
