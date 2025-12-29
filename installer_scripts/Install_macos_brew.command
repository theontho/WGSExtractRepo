#!/usr/bin/env bash
# WGS Extract Install Script (Apple MacOS) - Homebrew Edition
# Copyright (C) 2018-20 Marko Bauer
# Copyright (C) 2020-24 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt
#

# Todo Use Conda / BioConda / Micromamba for Python packages

export TERM=xterm       # Needed when run from Applescript
clear

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

declare cpu_arch osver
source scripts/zcommon.sh "$wgse_FP"         || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }
source scripts/zcommon_macos.sh "$wgse_FP"   || { echo "ERROR: Cannot source scripts/zcommon_macos.sh" ; exit 1 ; }


echo '=========================================================================================='
echo 'WGS Extract Installer for MacOS'
echo
echo 'WGS Extract needs Apple Xcode CLI, Homebrew'
echo 'We will also need to uninstall the macports packages to replace them with homebrew managed ones.'
echo 'You can also optionally uninstall old WGSE installed python, java and macports installs, since homebrew now covers all of it.'
echo 'They must install into password protected system directories and will need your password to install.'
echo

echo '========================== Install Xcode CLI Tools ======================================'
# Install Xcode CLI tools first as some Python PIP tool installs need it
apple_cli_install
echo

echo '===================== Removing Old WGSE Python Installations ============================'
vers=( 3.8 3.9 3.10 3.11 )    # Versions from WGSE v2 through v4

for (( i=0; i< ${#vers[@]}; i++ )) ; do
  python_uninstall "${vers[$i]}" ask
done

echo '===================== Removing Old WGSE Java Installations =============================='
jdkpacks=( "adoptopenjdk-11.jre"   "zulu-17.jre"        "zulu-8.jre" )    # Versions from WGSE v3 and v4
jdknames=( "openJDK v11 (WGSE v3)" "Azul v17 (WGSE v4)" "Azul v8 (WGSEv4)" )

for (( i=0; i< ${#jdkpacks[@]}; i++ )) ; do
  java_uninstall "${jdkpacks[$i]}" "${jdknames[$i]}" ask
done

# Check if macports is installed and uninstall it if it is
if command -v port &> /dev/null; then
    echo '========================= Uninstalling MacPorts Packages =============================='
    uninstall_macports_packages
    echo 'MacPorts Packages uninstalled successfully.'
    echo
    uninstall_macports ask
fi



echo '================================= Installing Homebrew ==================================='
install_homebrew


# Verify installations
if ! command -v samtools &> /dev/null || ! command -v bcftools &> /dev/null || ! command -v bwa &> /dev/null; then
    echo "ERROR: Failed to install required bioinformatics tools via Homebrew"
    exit 1
fi
echo

# Todo pbmm2, a PacBio Minimap2 front-end  https://github.com/PacificBiosciences/pbmm2


echo '================================================================================'
echo 'Common script to install the Python and WGS Extract packages'
"$bashx" "${wgse_FP}/scripts/zinstall_common.sh" "$cpu_arch" "$osver" "-"

case $? in
  0)
    echo
    echo 'Congratulations!  You finished installing WGS Extract on Apple MacOS with Homebrew!'
    echo 'You can start WGS Extract by clicking file WGSExtract.command. Make an alias,'
    echo 'rename it WGSExtract, and place it on your desktop to start the program there.'
    echo   ;;

  10)
    exit   ;;   # exit silently as restarted the Install script due to an upgrade

  *)
    echo
    echo 'Sorry. Appears there was a problem during the WGS Extract install on MacOS.'
    echo 'Please scroll back through the screen log here and look for any errors.'
    echo   ;;

esac

readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
