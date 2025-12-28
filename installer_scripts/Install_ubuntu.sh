#!/usr/bin/env bash
# WGS Extract Install Script for Ubuntu Linux
# Copyright (C) 2020-24 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

# Note: Although we bring the URLs to the header here, there are versioned directory names below - edit both places
minimap2URL=https://github.com/lh3/minimap2/releases/download/v2.17/minimap2-2.17_x64-linux.tar.bz2
bwamem2URL=https://github.com/bwa-mem2/bwa-mem2/releases/download/v2.2.1/bwa-mem2-2.2.1_x64-linux.tar.bz2
fastpURL=http://opengene.org/fastp/fastp

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

source scripts/zxterm_ubuntu.sh "$wgse_FP"   || { echo "ERROR: Cannot source scripts/zxterm_ubuntu.sh" ; exit 1 ; }

declare -f sudox readq curlx
declare cpu_arch osver bashx
source scripts/zcommon.sh "$wgse_FP"         || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

clear
echo '================================================================================'
echo 'WGS Extract v4 Installer for Ubuntu LTS'
echo
echo 'This installer has only been tested on Ubuntu LTS 18 thru 24. If you are using'
echo '  a different version, then you have to adapt this script and others it calls.'
echo 'For a detailed installation log, see the file temp/install.log'
echo

if [ ! -e temp ]; then
  mkdir temp
fi

echo '================================================================================'
echo '*** Get latest Ubuntu software library tables.'
readq 'Do you want to update your OS (recommended) (update/upgrade/autoremove) [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # shellcheck disable=SC2024
  sudox apt -y update &> temp/install.log
  sudox apt -y upgrade &>> temp/install.log
  sudox apt -y autoremove &>> temp/install.log
else
  echo " ... leaving OS as is.  You may see more warning messages below."
  touch temp/install.log
fi

# Check if already installed WGS Extract v4; plan on upgrade instead of install then
aptcmd="install"  ;  message="Installing"
if [ -f program/program.json ]; then  # Just doing an upgrade and not install; this folder was introduced in v4
    aptcmd="upgrade"  ;  message="Upgrading"
fi
echo

echo '================================================================================'
echo "${message} missing Unix utilities."
# shellcheck disable=SC2024
sudox apt -y $aptcmd sed coreutils zip unzip bash grep curl p7zip-full jq &>> temp/install.log # dos2unix
sudox apt -y autoremove &>> temp/install.log    # Always seems to outdate some libraries
echo

# Note: keeping the standard python3 install for the Ubuntu OS version. Just make sure our code can deal with it.
echo '================================================================================'
echo "${message} Python3 and its support libraries."
# shellcheck disable=SC2024
sudox apt -y $aptcmd python3 python3-pip python3-tk python3-pil python3-pil.imagetk &>> temp/install.log
echo

echo '================================================================================'
echo "${message} Java 17 JRE and its libraries."
# shellcheck disable=SC2024
sudox apt -y $aptcmd openjdk-17-jre openjdk-8-jre &>> temp/install.log # picard-tools
echo

echo '================================================================================'
echo "${message} needed bioinformatics packages (htslib, bwa, etc)."
# shellcheck disable=SC2024
sudox apt -y $aptcmd samtools bcftools tabix bwa bowtie2 &>> temp/install.log

# These programs are not in the apt release; must direct install from other sources
if [[ ${osver} =~ ^18* ]]; then
  if [[ ! -f /usr/bin/minimap2 ]]; then
    # Simply take version that is in UB 20.04; we know there is a later version but that is OK
    curlx -o minimap2.tar.bz2 "${minimap2URL}"
    if [ -e minimap2.tar.bz2 ]; then
  tar -xf minimap2.tar.bz2
  # shellcheck disable=SC2086
  sudo_mvx minimap2-2.17_x64-linux/minimap2 /usr/bin
  rmrx minimap2.tar.bz2 minimap2-2.17_x64-linux
else
  echo "ERROR - failed to download minimap2!"
fi
  fi
  if [[ ! -f /usr/bin/fastp ]]; then
    curlx -o fastp "$fastpURL"
    if [ -e fastp  ]; then
      chmod a+x fastp
      # shellcheck disable=SC2086
      sudo_mvx fastp /usr/bin
    else
      echo "ERROR - failed to download fastp!"
    fi
  fi
else
  # shellcheck disable=SC2024
  sudox apt -y $aptcmd minimap2 fastp &>> temp/install.log  # bwa-mem2 (see below)
fi

if [[ ! -f /usr/bin/bwa-mem2 ]]; then
  curlx -o bwa-mem2.tar.bz2 "${bwamem2URL}"
  if [ -e bwa-mem2.tar.bz2 ]; then
    tar -xf bwa-mem2.tar.bz2
    # shellcheck disable=SC2086
    sudo_mvx bwa-mem2-2.2.1_x64-linux/bwa-mem2* /usr/bin
    rmrx bwa-mem2.tar.bz2 bwa-mem2-2.2.1_x64-linux
  else
    echo "ERROR - failed to download bwa-mem2!"
  fi
fi

# Todo Hisat2: https://cloud.biohpc.swmed.edu/index.php/s/oTtGWbWjaxsQ2Ho/download
# Todo pbmm2: a PacBio Minimap2 front-end  https://github.com/PacificBiosciences/pbmm2
echo

# Handling WGS Extract program, Python Library and Java programs via the Common script
echo '================================================================================'
echo 'Calling the Common script to install the Python and WGS Extract packages'
${bashx} "${wgse_FP}/scripts/zinstall_common.sh" "$cpu_arch" "$osver" "-"

case $? in
  0)
    echo
    echo 'Congratulations!  You finished installing WGS Extract v4 on Ubuntu Linux!'
    echo 'See more detail in the temp/install.log file.'
    echo 'You can start WGS Extract by clicking the WGSExtract.sh file. Make a softlink,'
    echo 'rename it to WGSExtract, and place on your desktop to start the program there.'
    echo   ;;

  10)
    exit   ;;   # exit silently as restarted the Install script due to an upgrade

  *)
    echo
    echo 'Sorry. Appears there was a problem during the WGS Extract install on'
    echo ' Ubuntu Linux. Please scroll through the temp/install.log for errors.'
    echo   ;;

esac

readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
