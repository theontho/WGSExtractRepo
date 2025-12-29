#!/usr/bin/env bash
# WGS Extract MacOSX Uninstall Script
# Copyright (C) 2020-24 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

export TERM=xterm       # Needed when run from Applescript
clear

export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

# Common environment setup for scripts here; sets some variables used later
declare reflibdir _localport
declare -f rmx mvx cpx rmrx sudo_rmrx readq > /dev/null
source scripts/zcommon.sh "$wgse_FP"              || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

declare -f macports_install macports_uninstall macports_wrong_OS python_uninstall java_uninstall > /dev/null
source scripts/zcommon_macos.sh "$wgse_FP"        || { echo "ERROR: Cannot source scripts/zcommon_macos.sh" ; exit 1 ; }

# Check if reference library has been moved (needs jq; so use before MacPorts jq is deleted)
find_reflibdir

echo '================== WGS Extract Uninstaller for Apple MacOS ====================='
echo

echo 'WGS Extract installed Python 3, MacPorts, Xcode CLI and openJDK along with'
echo '  associated modules like samtools, htslib, pyliftover and such.'
echo
echo 'This script will require a password to remove them from the system area.'
echo 'You will be asked to confirm each tool before uninstalling.'
echo

echo '===================== Removing Homebrew Installations ============================'
uninstall_homebrew_packages
uninstall_homebrew ask

echo '===================== Removing Python Installations ============================'
vers=( 3.8 3.9 3.10 3.11 )    # Versions from WGSE v2 through v4

for (( i=0; i< ${#vers[@]}; i++ )) ; do
  python_uninstall "${vers[$i]}" ask
done

echo

echo '===================== Removing Java Installations =============================='
jdkpacks=( "adoptopenjdk-11.jre"   "zulu-17.jre"        "zulu-8.jre" )    # Versions from WGSE v3 and v4
jdknames=( "openJDK v11 (WGSE v3)" "Azul v17 (WGSE v4)" "Azul v8 (WGSEv4)" )

for (( i=0; i< ${#jdkpacks[@]}; i++ )) ; do
  java_uninstall "${jdkpacks[$i]}" "${jdknames[$i]}" ask
done

echo

echo '=================== Removing MacPorts Installation ============================='
macports_uninstall ask
echo

echo '=================== Removing Apple XCode CLI ==================================='
apple_cli_uninstall ask
echo

# Our local MacPorts BASH is no longer available ... so use MacOS v3 that is built-in
bash "${wgse_FP}/scripts/zuninstall_common.sh" "$reflibdir"
