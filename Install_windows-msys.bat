@echo off
REM WGS Extract v4 release
REM Copyright (c) 2021-24 Randy Harr
REM
REM Windows 10/11 native installer (special patch msys installer startup)
REM
REM Simply used to call the original Cygwin64 Windows installer but with the msys2 directive set
REM

REM Todo Cygwin has Python and Java. Maybe use? Ditto for Msys2 albeit already using its python
TITLE WGSE Installer

REM  Need to be in the installation as CWD could be anywhere
set "wgse_FP=%~dp0%"
cd /d "%wgse_FP%"

Install_windows.bat "msys2"
