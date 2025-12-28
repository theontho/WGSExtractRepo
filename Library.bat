@echo off
REM WGS Extract Reference Library start script (Microsoft Windows)
REM Copyright (C) 2022-2024 Randolph Harr
REM
REM License: GNU General Public License v3 or later
REM A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

TITLE WGSE Library

REM  Need to be in the installation as CWD could be anywhere
set "wgse_FP=%~dp0%"
cd /d "%wgse_FP%"

REM echo Starting WGS Extract Library program ...

if exist cygwin64 (
  cygwin64\bin\bash scripts\library_common.sh "%wgse_FP%"

) else if exist msys2 (
  msys2\usr\bin\bash scripts\library_common.sh "%wgse_FP%"

) else (
  echo Cannot find a Windows binary tools release for WGS Extract. Exiting.

)

pause
