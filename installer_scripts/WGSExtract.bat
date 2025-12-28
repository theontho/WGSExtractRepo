@echo off
REM WGS Extract Program start script (Microsoft Windows))
REM Copyright (C) 2020-2024 Randolph Harr
REM
REM License: GNU General Public License v3 or later
REM A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

TITLE WGS Extract

REM  Need to be in the installation as CWD could be anywhere
set "wgse_FP=%~dp0%"
cd /d "%wgse_FP%"

if exist "cygwin64\" (
  echo Starting WGS Extract on cygwin64 ...
  python\python program\wgsextract.py

) else if exist "msys2\" (
  echo Starting WGS Extract on msys2 ...
  set "PATH=/ucrt64/bin;/usr/bin;%PATH%"
  msys2\ucrt64\bin\python program\wgsextract.py

) else (
  echo Cannot find a Windows binary tools release for WGS Extract. Exiting.

)

pause
