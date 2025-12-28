@echo off
REM WGS Extract Uninstaller (Microsoft Windows)
REM Copyright (c) 2021-24 Randy Harr
REM
REM Uninstall a Cygwin64 or Msys2 release of WGS Extract. Both install in the main WGS Extract folder.
REM  So everything done in the zuninstall_common.sh call.  But we need to find reflib dir via the call first.
REM

set "jqURL=https://github.com/stedolan/jq/releases/download/jq-1.6/jq-win64.exe"

TITLE WGSE Uninstaller

REM  Need to be in the installation as CWD could be anywhere
set "wgse_FP=%~dp0%"
cd /d "%wgse_FP%"

setlocal enableDelayedExpansion
if exist "%wgse_FP%\cygwin64" (
  set "nixbin=%wgse_FP%\cygwin64\bin"
  if ";%PATH:cygwin=%;" == ";%PATH%;" ( set "PATH=!nixbin!;%PATH%" )

) else if exist "%wgse_FP%\msys2" (
  set "nixbin=%wgse_FP%\msys2\usr\bin"
  if ";%PATH:msys=%;" == ";%PATH%;" ( set "PATH=!nixbin!;%PATH%" )

) else (
  set "errmesg=Cannot find a Windows base BASH environment for WGS Extract. Installed yet?"
  goto onError

)

set "curlx=%windir%\SysWOW64\curl.exe -k#LC -"  &  REM Use local windows curl (fairly up to date) -fkL?
set "bashx=%nixbin%\bash.exe"

echo ======================================================================================================
echo WGS Extract v4 Uninstaller for Microsoft Windows Systems
echo(
echo   Windows uninstall is simple as all dependent programs are in the WGS Extract installation folder.
echo   So we simply have to delete the install directory and maybe the relocated Reference Library.
echo(
echo(

set "jqx=jq.exe"

where /q "%jqx%"      & REM will search on path but not current directory
if ERRORLEVEL 1 if not exist %jqx% (
  echo *** Downloading JQ for Windows from %jqURL%"
  %curlx% -o %jqx% %jqURL%
  if not exist %jqx% (set "errmesg=JSON processor JQ failed to download" & goto onError)
)

%jqx% --help >nul
if ERRORLEVEL 1  (set "errmesg=JSON processor JQ is not available" & goto onError)

echo ======================================================================================================
echo Finding Reference Library (in case moved in application settings)
echo(
set newreflib=
if exist "%USERPROFILE%\.wgsextract" (
  %jqx% -r .^"reflib.FP^" "%USERPROFILE%\.wgsextract" > temp.txt & set /p newreflib=<temp.txt & del temp.txt
)

set "reflib=%~dp0%reference"
if exist "%newreflib%\\" (
  echo Original Reference Library in %reflib% but using new Reference Library of %newreflib%
  set "reflib=%newreflib%
)

REM We need to make sure we use our BASH and not the Win10 supplied one
"%bashx%" scripts\zuninstall_common.sh "%reflib%

REM If user chose not to delete the installation, then program.json will still exist and we simply exit.
if not exist %wgse_FP%program\program.json (
  REM Sometimes, due to race condition, BASH keeps the nixbin from being deleted. If so, pause then delete again.
  if exist %nixbin% (
    sleep 5
    rmdir %wgse_FP% /s/q
  )
)
exit /b

:onError errmesg
:: Error handler (pseudo function call except using goto; parameter passed in variable errmesg)
echo(
echo *** ERROR^: !errmesg!
echo(
pause
exit /b

