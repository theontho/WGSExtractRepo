@echo off
REM WGS Extract v4 release
REM Copyright (c) 2021-24 Randy Harr
REM
REM Windows 10/11 native installer (initial, stage 1, universal package types)
REM
REM Install CygWin64 environment (instead of previous bootstrap only) or Msys2 bootstrap.  Latest versions DLLs
REM  will not match pre-compiled bioinformatic binary needs. Start BASH environment for stage 2 and beyond. Easier
REM  in BASH than BAT and have some in-common with other platforms.
REM

REM Stand-alone Windows 10/11 JQ binary to bootstrap before package install with JQ in it
set "jqURL=https://github.com/stedolan/jq/releases/download/jq-1.6/jq-win64.exe"

REM Cygwin64 Installer and Repository Mirror (only used on cygwin64 install; set here for visibility)
set "cygsetup=setup-x86_64.exe"
set "cygsetupURL=https://www.cygwin.com/%cygsetup%"
set "mirror=https://cygwin.mirror.constant.com/"              & REM Removed reliance on online mirror ;
set "mirenc=https%%3a%%2f%%2fcygwin.mirror.constant.com%%2f"  & REM rename to mirror\ after extracting from ZIP

REM Todo Cygwin has Python and Java. Maybe use? Ditto for Msys2 albeit already using its ucrt64 python
TITLE WGSE Installer

REM  Need to be in the installation as CWD could be anywhere
set "wgse_FP=%~dp0"
set "wgse_FP_noslash=%wgse_FP:~0,-1%"

cd /d "%wgse_FP%"

REM Default (no params) is a Cygwin64 installation. If %1 set to msys2, then do an msys2/ucrt64 installation
setlocal EnableDelayedExpansion
if "%~1" == "msys2" (
  set "pack=msys2"                         &  set "upack=Msys2"
  set "nixbin=%wgse_FP%!pack!\usr\bin"     &  set "biobin=%wgse_FP%!pack!\ucrt64\bin"
  if ";%PATH:msys=%;" == ";%PATH%;" ( set "PATH=!nixbin!;%PATH%" )

) else (
  set "pack=cygwin64"                      &  set "upack=Cygwin64"
  set "nixbin=%wgse_FP%!pack!\bin"         &  set "biobin=%wgse_FP%!pack!\usr\local\bin"
  if ";%PATH:cygwin=%;" == ";%PATH%;" ( set "PATH=!nixbin!;%PATH%" )
  set "cygstartx=!nixbin!\cygstart.exe"

)
REM Possible PATH variable additions: python, python\scripts, jre8\bin, jre17\bin,
REM                                   cygwin64\usr\local\bin, msys2\ucrt64\bin

set "zipdir=%pack%"                   &  REM Directory name stored in the toplevel of the ZIP file
set "reldir=%pack%"                   &  REM Directory name to put the release into on the local machine

set "curlx=%windir%\SysWOW64\curl.exe -k#LC -"  &  REM Use local windows curl (fairly up to date) -fkL?
set "bashx=%nixbin%\bash.exe"         &  REM Full path to pack bash
set "jqx=jq.exe"                      &  REM Purposeful file name only; not absolute path

echo ================================================================================
echo WGS Extract v4 Installer for Microsoft Windows Systems (%upack% version)
echo(
echo   Installing WGS Extract support programs (Python, Java, %upack%, yLeaf, etc)
echo     in %wgse_FP%
echo   The Bioinformatic tools will be available (for personal use also)
echo     in %biobin%
echo(

REM DEFAULT settings in case a release.json local file does not exist
set "track=Beta"
set "latestversion_url=https://get.wgse.io/latest-release-%track%.json"

set "latestZIP=%zipdir%.zip"           &  REM Name to give local ZIP file after the download via cURL

REM See https://stackoverflow.com/questions/16042339/os-name-variable
:: for /f "usebackq tokens=1,2 delims==|" %%I in (`wmic os get os_name /format:list`) do 2>NUL set "%%I=%%J"
REM was a parameter passed to zinstall_common.sh; now calculated inside zinstall_stage2windows.sh to pass from there

REM ----------------------------------------------------------------------------------
REM Check that JQ JSON processor is available and working (and download if needed)

where /q "%jqx%"                        & REM will search in PATH but not current directory
if ERRORLEVEL 1 if not exist %jqx% (
  echo *** Downloading JQ for Windows from %jqURL%"
  %curlx% -o %jqx% %jqURL%
  if not exist %jqx% (set "errmesg=JSON processor JQ failed to download" & goto onError)
)

%jqx% --help >nul
if ERRORLEVEL 1  (set "errmesg=JSON processor JQ is not available" & goto onError)

if exist release-override.json (
  if exist release.json ( move /y release.json release-overridden.json >nul )
  move /y release-override.json release.json >nul
)

REM ----------------------------------------------------------------------------------
REM Get the latest release JSON file pointed to by the release.json file

REM Process release.json file to find latest release JSON URL
if exist release.json (
  %jqx% -r .^"release^".^"track^"      release.json > temp.txt & set /p            track=<temp.txt  & del temp.txt
  %jqx% -r .^"release^".^"!track!URL^" release.json > temp.txt & set /p latestreleaseURL=<temp.txt  & del temp.txt

) else (
  set "track=Beta"
  set "latestreleaseURL=https://get.wgse.io/latest-release-%track%.json"

)
if not defined latestreleaseURL (set "errmesg=local release.json file is corrupt" & goto onError)

if exist latest.json (del /q latest.json)     & REM because if exists, curl may try to restart and append to it

echo(
echo *** Downloading the !track! track latest release JSON file

%curlx% -o latest.json !latestreleaseURL!
if not exist latest.json (set "errmesg=cannot download the latest release JSON file from !latestreleaseURL!" & goto onError)

findstr "URL" latest.json >nul
if ERRORLEVEL 1 (set "errmesg=corrupted release JSON file downlaoded from !latestreleaseURL!" & goto onError)

REM Cannot use variable %pack% in jq command line parameter; so replicate for each pack type
echo(
if "%pack%" == "cygwin64" (
  %jqx% -r .^"cygwin64^".^"version^" latest.json > temp.txt  &  set /p  latestVer=<temp.txt & del temp.txt
  %jqx% -r .^"cygwin64^".^"date^"    latest.json > temp.txt  &  set /p latestDate=<temp.txt & del temp.txt
  %jqx% -r .^"cygwin64^".^"URL^"     latest.json > temp.txt  &  set /p  latestURL=<temp.txt & del temp.txt

) else (
  %jqx% -r .^"msys2^".^"version^" latest.json > temp.txt  &  set /p  latestVer=<temp.txt & del temp.txt
  %jqx% -r .^"msys2^".^"date^"    latest.json > temp.txt  &  set /p latestDate=<temp.txt & del temp.txt
  %jqx% -r .^"msys2^".^"URL^"     latest.json > temp.txt  &  set /p  latestURL=<temp.txt & del temp.txt

)
if not defined latestURL (set "errmesg=latest release JSON file is corrupt" & goto onError)
echo *** %upack% package latest release is version !latestVer!, date !latestDate!, at
echo         URL !latestURL!

REM leave latest.json around for stage2 and common install scripts later on

REM ----------------------------------------------------------------------------------
REM Check if pack base already installed and the latest available; if not to either, install latest pack

set currentVer=1

if exist "%reldir%" (

  set "currentJSON=%reldir%\%pack%.json"
  if exist "!currentJSON!" (

    if "%pack%" == "cygwin64" (
      %jqx% -r .^"cygwin64^".^"version^" !currentJSON! > temp.txt & set /p  currentVer=<temp.txt & del temp.txt
      %jqx% -r .^"cygwin64^".^"date^"    !currentJSON! > temp.txt & set /p currentDate=<temp.txt & del temp.txt
      %jqx% -r .^"cygwin64^".^"URL^"     !currentJSON! > temp.txt & set /p  currentURL=<temp.txt & del temp.txt
    ) else (
      %jqx% -r    .^"msys2^".^"version^" !currentJSON! > temp.txt & set /p  currentVer=<temp.txt & del temp.txt
      %jqx% -r    .^"msys2^".^"date^"    !currentJSON! > temp.txt & set /p currentDate=<temp.txt & del temp.txt
      %jqx% -r    .^"msys2^".^"URL^"     !currentJSON! > temp.txt & set /p  currentURL=<temp.txt & del temp.txt
    )

    if not defined currentURL (set "errmesg=current %pack% JSON file is corrupt" & goto onError)
    if exist "%bashx%" (
      echo(
      echo *** %upack% package v!currentVer!, date !currentDate! installed
    )

    call :verComp !currentVer! !latestVer!    & REM returns errorlevel -1 for LSS, 0 for EQU, 1 for GTR
    if not %ERRORLEVEL% == -1 (
      if exist "%bashx%" (
        echo(
        echo *** %upack% package v!latestVer! is up to date ...
        goto postinstall                      & REM latest already installed; jump out of installation section
      )
    )

  )

  set "begin_mesg=Replacing the %upack% package environment ..."
  set "end_mesg=WGSE %upack% package v!latestVer! upgraded"
  rmdir /s /q %reldir%

) else (

  set "begin_mesg=Installing a new %upack% package v!latestVer! environment ..."
  set "end_mesg=WGSE %upack% package v!latestVer! newly installed"

)
echo(

REM ----------------------------------------------------------------------------------
REM Base %pack% package Install / Upgrade routine (just fall into; not called; label is not needed)
:install
echo ================================================================================
echo %begin_mesg%

REM note: Package often fails on first download attempt. But is immediately successful on restart. curlx does 5 retries
REM       internally.  We retry the curlx itself three times before giving up; using a slight delay between each retry

if "%pack%" == "cygwin64" (
  echo(
  echo *** Downloading the %upack% installer %cygsetup%
  if exist "%cygsetup%" (del /q "%cygsetup%")
  %curlx% -o "%cygsetup%" "%cygsetupURL%"
  if not exist "%cygsetup%" (set "errmesg=failed to download the %cygsetup% executable" & goto onError)
)

REM Exclamation in MS Onedrive URL causes issue if delayedexpansion in on; cannot escape exclamation
echo(
echo *** Downloading the %upack% v%latestVer% Install Package (WGS Extract specific)
set "firsttime=y"
set "secondtime=y"

:tryagain

REM Try to read the %pack% package ; un-escapable exclamation in MS Onedrive URL is issue if DelayedExpansion on
setlocal DisableDelayedExpansion
for /F "tokens=*" %%g IN ('%curlx% -w "%%{http_code}" -o "%latestZIP%" "%latestURL%"') do (set response=%%g)
setlocal EnableDelayedExpansion

REM Check HTML response code for failure; retry (twice) if failed
if !response! GEQ 300 (
  if defined secondtime (
    echo(

    if !response! == 503 (
      if defined firsttime (
        echo *** Waiting a little longer for the server to spin up; then retrying ...

      ) else (
        echo *** Waiting a little longer for the virus check to complete; then retrying ...

      )
    ) else (
      echo *** Unknown HTML response code !reponse! ; retrying after delay ...

    )

    del "%latestZIP%"       & REM let's not try to restart with the partial file as likely incorrect

    if defined firstime (
      set "firsttime="      & REM clear firsttime
      timeout /t 10         & REM Wait 10 seconds the first time

    ) else (
      set "secondtime="     & REM clear secondtime
      timeout /t 10         & REM Wait 10 seconds the second time

    )
    goto tryagain

  ) else (
    if exist "%latestZIP%" (
      FOR /F "usebackq" %%A IN ('%latestZIP%') DO set size=%%~zA

      if !size! LSS 10000 (
        move /y "%latestZIP" "%zipdir%.html" >nul
        echo(
        echo *** The detailed response to the %zipdir% cURL request is in %zipdir%.html

      ) else (
        del %latestZIP%     & REM remove partial latestZIP file after it failed to download on the second try

      )
    )

    echo "*** 2nd round failed. Upon restarting the installer, it will usually succeed."
    set "errmesg=bad HTML response code !response! during cURL on 2nd try"  &  goto onError

  )
)

if not exist "%latestZIP%" (set "errmesg=failed to download the %latestZIP% archive" & goto onError)
FOR /F "usebackq" %%A IN ('%latestZIP%') DO set size=%%~zA
if !size! LSS 25000000 (set "errmesg=incomplete download of the %latestZIP% archive" & goto onError)

REM del "%cygsetup%"   # when problem with latest setup use original by deleting new before expanding archive with orig
powershell Expand-Archive -LiteralPath "%latestZIP%" -DestinationPath "." -force -WarningVariable w -ErrorAction Stop
if not exist "%zipdir%"\ (set "errmesg=failed to expand the %latestZIP% archive into %zipdir%" & goto onError)
del "%latestZIP%"

REM The ZIP hard codes %zipdir% inside itself.  Need to rename if %reldir% is different
if not "%zipdir%" == "%reldir%" (
  if exist "%reldir%" (rmdir /q /s "%reldir%")
  rename "%zipdir%" "%reldir%"
)

REM ----------------------------------------------------------------------------------
REM Cygwin64 requires cygsetup to run and create an installation; msys2 simply unzip's into static dir structure
if "%pack%" == "cygwin64" (
  if exist "%mirenc%\" (rename "%mirenc%" mirror)     & REM rename mirror so online source not checked for updates

  echo(
  echo *** Starting the %upack% Base Setup -- takes 10 minutes -- see %reldir%\setup.log for a detailed log

  "%cygsetup%" --root "%reldir%" --site mirror --only-site --quiet-mode --no-shortcuts ^
    --no-admin --local-package-dir "!wgse_FP_noslash!" --local-install --categories base ^
    --packages jq,p7zip,unzip,zip,libbz2-devel,libzip-devel,liblzma-devel,libdeflate-devel,zlib-devel,^
libncurses-devel,libcurl-devel,libssl-devel > "%reldir%\setup.log

  if not exist "%cygstartx%" (set "errmesg=Failure in Cygsetup base installer task" & goto onError)

  del /q "%cygsetup%"
  rmdir mirror\ /s/q              & REM Remove the pre-install packages

  "%cygstartx%" /bin/ln.exe -s /cygdrive /mnt
  type %reldir%\etc.skel.bashrc >> %reldir%\etc\skel\.bashrc

  rmdir "%reldir%\usr\local" /s/q   & REM Empty directories there; should be missing for bioinfo version check later
)

echo(
echo *** %end_mesg%

REM ----------------------------------------------------------------------------------
:postinstall
REM jq.exe is installed with the %pack% base package so delete our temporary, local copy as no longer needed
if exist %jqx% (del /q %jqx%)
REM echo(

if not exist "%nixbin%" (set "errmesg=%pack% package failed to install" & goto onError)

REM Special v44p3 patch to cygwin64 for ACL issues (to avoid new cygwin64 release but fix an issue)
if "%pack%" == "cygwin64" (
  "%nixbin%\sed.exe" s/inary,posi/inary,noacl,posi/ "%reldir%\etc\fstab" > "%reldir%\etc\fstab.new"
  mv "%reldir%\etc\fstab.new" "%reldir%\etc\fstab"
)

REM Now that we have a working BASH, we install the bioinformatic tools, python, etc in the Stage2 BASH script.
REM We need to make sure we use our newly available BASH and not the Win10 supplied one
echo(
echo ================================================================================
echo Starting Stage 2 Windows install using the new %upack% BASH environment
echo(
"%bashx%" "%wgse_FP%scripts\zinstall_stage2windows.sh" "%wgse_FP_noslash%"

echo(
if %ERRORLEVEL% EQU 0 (
  echo ================================================================================
  echo(
  echo Congratulations!  You finished installing WGS Extract v4 on MS Windows.
  echo Start WGS Extract by clicking the WGSExtract.bat file. Make a softlink,
  echo rename it, and place it on your desktop to start the program there.
  echo(

) else ( if %ERRORLEVEL% EQU 10 (
  REM Restarted the install script due to an upgrade; so exiting silently from this one
  goto :EOF

) else (
  echo ================================================================================
  echo(
  echo Appears there was one or more ERRORS during the WGS Extract install on Windows.
  echo  Please scroll back through the command log and look for any errors.
  echo(

) )

:end
pause
exit /b

REM ----------------------------------------------------------------------------------
:onError errmesg
:: Error handler (pseudo function call except using goto; parameter passed in variable errmesg)
echo(
echo *** ERROR^: !errmesg!
echo *** FATAL^: Installer terminating
echo(
echo Please scroll back through the command log and look for any earlier uncaught errors.
goto end

REM ----------------------------------------------------------------------------------
:verComp  version1  version2
:: Multi-level version comparison -- see https://stackoverflow.com/a/15809139 for original idea
::
:: Compares two version numbers of type 1.2.3 and returns the result in the ERRORLEVEL
:: note: similar function in scripts/zcommon.sh and program/utilities.py
::
:: Returns 1 if version1 > version2
::         0 if version1 = version2
::        -1 if version1 < version2
::
:: Allows any number of levels. Each level is separated by a . (period) or p (letter). Level==Node==Token
:: A 'p' is a patch specifier and changed to a period delimiter (and cannot be used as a value)
:: A single alphabetic letter (sans p) is treated as a next level down specifier. 4a == 4.a
:: The shorter length version specifier is padded with trailing .0's to equalize the longer length (# levels) one.
:: Each level is compared numerically; so multiple digits are treated as a single numeric specifier.
:: This is like a string / character comparison of two version numbers if you padded left with 0's.
:: Leading zero's are stripped so they are not confused as Octal numbers in batch.
:: Each alphabetic letter is upcased and converted to its ASCII numeric value. So "A" and "a" become 65.
:: Best not to mix letters and numbers at the same level.
:: These are true: 0.9.3 > 0.1 , 1p2 == 1.2 , 1g > 1A , 4.44p3 > 4.44.2 , 4.44 > 4.5 , 44aB == 44.A.b , 4.9 < 4a
::
setlocal enableDelayedExpansion
set "v1=%~1"
set "v2=%~2"

REM Convert letters to individual tokens / nodes across the whole version specifier
call :divideLetters v1
call :divideLetters v2

REM Loop through each level / token doing the comparison at each level. Exit _verComp with code -1, 0 or 1
:loop

REM Strip off leading token to prepare for comparison. Remove leading zeros. Convert alpha to numeric string.
call :parseNode "!v1!" n1 v1
call :parseNode "!v2!" n2 v2

REM Actual comparison
if !n1! gtr !n2! exit /b 1
if !n1! lss !n2! exit /b -1

REM Equal at this point
if not defined v1 if not defined v2 exit /b 0  &  REM both equivalent at all levels; no remainder to check

REM Must be equal to and a remainder; so adjust remainder and loop to check it
if not defined v1 if defined v2 set "v1=0"     &  REM exit /b -1  REM push decision off to next level ...
if not defined v2 if defined v1 set "v2=0"     &  REM exit /b 1   REM  ... by padding shorter version with .0's

goto :loop                                     &  REM loop to check next level
::

:parseNode  version  nodeVar  remainderVar
::
:: Split version string into first level/node/token with remainder. Returns first token and remainder in the
:: calling variables.  The remainder is used to update the version specifier before the next level is processed.
::
:: 1* means 1st token and remaining tokens; "for" automatically generates additional variables if more tokens
:: "for" loop automatically removes successive (and leading) delimeters (so .. or pp does not specify a blank node)
::
for /f "tokens=1* delims=.p" %%A in ("%~1") do (
  set "temp=%%A"
  set "%3=%%B"
)

REM In first token, remove leading zero's; resetting to 0 if only 0's.
REM   Windows batch treats a leading zero as an octal base numeric indicator
for /F "tokens=* delims=0" %%I in ("!temp!") do set "temp=%%I"
if not defined temp set "temp=0"

REM Leave alphabetic as is; will compare as string, If alphabetic compared to numeric; alphabetic always greater.

set "%2=!temp!"
exit /b
::

:divideLetters  versionVar
:: Convert each letter (sans p) to a separate token (inserts delimeter before and after; remains a letter)
::  "for" match is case insensitive. So this does both upper and lower case.
for %%C in (a b c d e f g h i j k l m n o q r s t u v w x y z) do set "%1=!%1:%%C=.%%C.!"
exit /b
::
