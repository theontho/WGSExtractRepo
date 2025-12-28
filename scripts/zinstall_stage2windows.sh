#!/usr/bin/env bash
# WGS Extract v4 Win10 install script (after Cygwin64 installed via Install_windows.bat)
#
# Copyright (C) 2021-2023 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

# Because we want to spend minimal effort in CMD.EXE BAT file, we have most of the Windows install
# happening here in this BASH script.  Called once a base CygWin64 environment is set up.

# Todo Originally Cygwin64 Python was too old.  They seem to have caught up now. Consider simply
#  installing python and java with the cygwin release.

# Check for required parameter (mainly to verify called internally and not directly)
if (( $# != 1 )) ; then
  printf "Usage: %s { install_dir }\n" "${BASH_SOURCE[0]##*/}"
  printf "  install_dir is the WGSE installation folder.\n"
  printf "This script should only be called from the internal Windows install script.\n"
  exit
fi

#---------------------------------- Setup common environment ------------------------------------------------------
wgse_FP="$1"          # No need to figure out location; it was passed in from .bat caller
export wgse_FP

cd "$wgse_FP" || true

declare osver cpu_arch wgse_FP bashx
declare -f cdx mvx rmx rmrx curlx > /dev/null
source scripts/zcommon.sh "$wgse_FP"              || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

# The Windows Install script intalls cygwin64 or msys2. Make sure we are only called by that installer.
case $OSTYPE in
  darwin* | linux*)
      echo '*** ERROR: This is an installer for MS Windows systems only!' && exit 1  ;;

  msys*)
    if [ ! -d msys2/ ]; then
      echo '*** ERROR: Cannot find the Windows Msys2 tools previously installed.' && exit 1
    fi
    pack="bioinfo-msys2"   ;;

  cygwin*)
    if [ ! -d cygwin64/ ]; then
      echo '*** ERROR: Cannot find the Windows Cygwin64 tools previously installed.' && exit 1
    fi
    pack="bioinfo"          ;;

esac


echo
# ======================================================================================================
# WinPython standalone Python release
# todo cygwin64 release: use cygwin64 python now that it is up to date. PIP libraries from cygwin installer?
# todo msys2 release: use WinPython and generic pip library installs instead of built-in with msys2 release
if [[ $OSTYPE =~ "cygwin" ]] && [ ! -d python ]; then
  echo '*** Installing Python 3.10.2 ...'

  # https://github.com/winpython/winpython/releases/download/4.6.20220116/Winpython64-3.9.10.0dot.exe  3.9.10.0
  # https://github.com/winpython/winpython/releases/download/4.6.20220116/Winpython64-3.10.2.0dot.exe  3.10.2
  curlx -o Winpython64.exe "https://github.com/winpython/winpython/releases/download/4.6.20220116/Winpython64-3.10.2.0dot.exe"

  if [ -e Winpython64.exe ]; then
    chmod a+x Winpython64.exe && ./Winpython64.exe -y && rmx Winpython64.exe    # 7Zip self-extracting archive
    # Only need the Python interpreter; not all the IDE that comes with it
    mvx WPy64-31020/python-3.10.2.amd64 python  &&  rmrx WPy64-31020
    echo "... finished installing Python 3.10.2"

  else
    echo "*** ERROR - failed to download Python 3 release."

  fi
else
  echo '*** Python already installed.'    # Included in bioinfo-msys2 package; so not yet installed but will be there

fi

echo
# ======================================================================================================
# We check to see if Java command is already available; or if we have locally installed it already
# GATK3 / Picard / VariantQC require JDK8; GATK4, FASTQC, etc require openJDK11+. openJDK17 LTS came out in 2021.
# OpenJDK stopped delivering binaries; switched to adoptium. Maybe should go to Azul like for Mac due to M1.
# Now first number updated with every release (e.g. 17) instead of the second (1.8.xx)

# See if java already on the PATH; if so, determine the version so we can avoid installing it and simply use
unset jre  jre8  jre17

jre=$( command -v java 2>/dev/null )   # Returns path to command if it exists (possible spaces in path)

if [[ -n "$jre" ]] ; then
  IFS='.'
  # Check the version: take first line, 3rd grouping, strip double quote and dots to read into array of numerals
  read -ra ver <<<"$("$jre" -version 2>&1 >/dev/null | head -1 | cut -d" " -f3 | sed -e 's/"//g')"
  if (( ver[0] == 1 && ver[1] == 8 )); then
    jre8="$jre"
  elif (( ver[0] >= 11 )); then
    jre17="$jre"
  fi
fi

# Check if ver 11+ installed either found via command or in our release but not on the path; install jre17 if not found
if [ -z "$jre17" ] && ! [ -f jre17/bin/java.exe ]; then
  echo '*** Installing Java JRE v17'

  # We do not need a standalone Java release but easier to setup that way on Windows from a script
  openjdk="https://github.com/adoptium/temurin17-binaries/releases/download/"
  curlx -o jre17.zip "${openjdk}/jdk-17.0.2%2B8/OpenJDK17U-jre_x64_windows_hotspot_17.0.2_8.zip"

  if [ -e jre17.zip ]; then
    powershell Expand-Archive -LiteralPath "jre17.zip" -DestinationPath "." -Force && rmx jre17.zip
    mvx jdk-17.0.2+8-jre jre17
    chmod a+x jre17/bin/*.exe jre17/bin/*.dll
    # Program does two similar checks; either simply available or if Win10, in the jre subdirectory
    echo "... finished installing Java JRE v17"

  else
    echo "*** ERROR - failed to download Java JRE 17 release from Adptium."

  fi
else
  echo '*** Java v17 already installed.'

fi

echo
# Check if ver 8 installed; if not install jre8 now
if [ -z "$jre8" ] && ! [ -f jre8/bin/java.exe ] ; then
  echo '*** Installing Java JRE v8'

  # We do not need a standalone Java release but easier to setup that way on Windows from a script
  openjdk="https://github.com/adoptium/temurin8-binaries/releases/download/"
  curlx -o jre8.zip "${openjdk}/jdk8u345-b01/OpenJDK8U-jre_x64_windows_hotspot_8u345b01.zip"

  if [ -e jre8.zip ]; then
    powershell Expand-Archive -LiteralPath "jre8.zip" -DestinationPath "." -Force && rmx jre8.zip
    mvx jdk8u345-b01-jre jre8
    chmod a+x jre8/bin/*.exe jre8/bin/*.dll
    # Program does two similar checks; either simply available or if Win10, in the jre subdirectory
    echo "... finished installing Java JRE v8"

  else
    echo "*** ERROR - failed to download Java JRE 8 release from Adoptium."

  fi
else
  echo '*** Java v8 already installed.'

fi

# ======================================================================================================
# Grab our own bioinformatics release to add to the existing cygwin64 Unix tools already installed
# Was simply redestributed in v2 to everyone; in v3 only installed with Win10 users. Was mixed in with /bin
# in v3, now installed in /usr/local so can be easily replaced
echo
install_or_upgrade "$pack" "false"     # leaves the latest.json file for use in later package installs

echo
echo '================================================================================'
echo 'Calling the common script to install the Python and WGS Extract packages'
"$bashx" "scripts/zinstall_common.sh" "$cpu_arch" "$osver" "-"
# Propogate the exit code back to the Windows Batch file that called this script
exit $?

