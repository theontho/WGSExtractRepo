#!/usr/bin/env bash
# WGS Extract Uninstall Script for Ubuntu Linux
# Copyright (C) 2022-23 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

# Check in Linux and a Terminal for this script; restart in a Terminal if needed; exit if not Linux
source scripts/zxterm_ubuntu.sh                   || { echo "ERROR: Cannot source scripts/zxterm_ubuntu.sh" ; exit 1 ; }

declare -f sudox sudox_rmx readq > /dev/null
declare reflibdir osver bashx
source scripts/zcommon.sh "$wgse_FP"              || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }


echo '================================================================================'
echo 'WGS Extract v4 Uninstaller for Ubuntu LTS'
echo
echo 'WGS Extract used "apt" to install most of the tools.  So not known who installed'
echo ' which tools.  Therefore,  we ask before uninstalling any group of tools so  you'
echo ' can decide which you want to keep or not.'
echo

# Check if reference library has been moved out of the installation directory (needs jq; so use before deleted)
find_reflibdir

echo '================================================================================'
echo '*** Get latest Ubuntu software library tables.'
readq 'Do you want to clean your OS first (recommended) (update and autoremove) [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # shellcheck disable=SC2024
  sudox apt -y update &> temp/uninstall.log
  sudox apt -y autoremove &>> temp/uninstall.log      # use "|& tee -a" for viewing in terminal as well
else
  echo " ... leaving OS as is.  You may see many more warning messages below. Especially about dangling packages."
  touch temp/uninstall.log
fi

echo '================================================================================'
readq 'Do you want to remove sed coreutils zip unzip bash grep curl p7zip jq [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  sudox apt -y remove sed coreutils zip unzip bash grep curl p7zip-full jq &>> temp/uninstall.log
  sudox apt -y autoremove &>> temp/uninstall.log
else
  echo ' ... Leaving sed coreutils zip unzip bash grep curl p7zip-full jq installed.'
fi
echo

echo '================================================================================'
readq 'Do you want to remove Python3 [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  sudox apt -y remove python3 python3-pip python3-tk python3-pil python3-pil.imagetk &>> temp/uninstall.log
else
  echo ' ... Leaving Python3 installed.'
fi
echo

echo '================================================================================'
readq 'Do you want to remove OpenJDK Java 17 & 8 JRE and its libraries [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  sudox apt -y remove openjdk-17-jre openjdk-8-jre &>> temp/uninstall.log
else
  echo ' ... Leaving OpenJDK 17 and 8 (Java) installed.'
fi
echo

echo '================================================================================'
readq 'Do you want to remove Bioinformatics packages (htslib, bwa, etc) [y/N]?'
if [[ $REPLY =~ ^[Yy]$ ]]; then
  sudox apt -y remove samtools bcftools tabix bwa bowtie2 &>> temp/uninstall.log
  if [[ ${osver} =~ ^18* ]]; then
    sudo_rmx /usr/bin/minimap2 /usr/bin/fastp
  else
    sudox apt -y remove minimap2 fastp &>> temp/uninstall.log  # bwa-mem2 (see below)
  fi
  sudo_rmx /usr/bin/bwa-mem2
else
  echo ' ... Leaving Bioinformatics packages (htslib, bwa, etc) installed.'
fi

# Todo Hisat2: https://cloud.biohpc.swmed.edu/index.php/s/oTtGWbWjaxsQ2Ho/download
# Todo pbmm2: a PacBio Minimap2 front-end  https://github.com/PacificBiosciences/pbmm2
echo

mvx temp/uninstall.log ..     # Save the log file outside the installation directory which will be removed
${bashx} "scripts/zuninstall_common.sh" "$reflibdir"
