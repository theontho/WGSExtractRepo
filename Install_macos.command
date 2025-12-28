#!/usr/bin/env bash
# WGS Extract Install Script (Apple MacOS)
# Copyright (C) 2018-20 Marko Bauer
# Copyright (C) 2020-24 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt
#

# Todo Macports has Python and likely Java; may be an easier way to install, maintain and remove those later
# Todo Use Conda / BioConda / Micromamba instead of MacPorts; seems to be keeping up-to-date better than when we started

export TERM=xterm       # Needed when run from Applescript
clear

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

declare cpu_arch osver
declare _localport bashx
declare -f curlx readq sudo_mvx > /dev/null
source scripts/zcommon.sh "$wgse_FP"         || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

declare -f macports_install macports_uninstall macports_wrong_OS python_install > /dev/null
source scripts/zcommon_macos.sh "$wgse_FP"   || { echo "ERROR: Cannot source scripts/zcommon_macos.sh" ; exit 1 ;}


echo '================================================================================'
echo 'WGS Extract Installer for MacOS'
echo
echo 'WGS Extract needs Apple Xcode CLI, Python3, Macports, and Java v11+ / v8.'
echo 'They must install into password protected system directories.'
echo

echo '================================================================================'
# Install Xcode CLI tools first as some Macports and Pythin PIP tool installs need it
apple_cli_install
echo

echo '================================================================================'
python_install "3.11.7"
echo

echo '================================================================================'
# Apple has shadow-execs so /usr/bin/java is fake; need java --version to truly check is working
# But command -v java -v returns true but is not a jvm; instead a dummy executable by Apple
# Need to avoid Oracla Java as it requires interactive license pop-up during install
# Azul is the only site with M1 and x86 code bases; so utilize them.
jdkpacks=( "zulu-17.jre"                              "zulu-8.jre" )
jdknames=( "Azul v17 (WGSE v4)"                       "Azul v8  (WGSE v4)" )
jdk_x86=(  "zulu17.32.13-ca-jre17.0.2-macosx_x64"     "zulu8.64.0.15-ca-fx-jre8.0.342-macosx_x64" )
jdk_arm=(  "zulu17.32.13-ca-jre17.0.2-macosx_aarch64" "zulu8.64.0.15-ca-fx-jre8.0.342-macosx_aarch64" )
for (( i=0; i< ${#jdkpacks[@]}; i++ )) ; do
  java_install "${jdkpacks[$i]}" "${jdknames[$i]}" "${jdk_x86[$i]}" "${jdk_arm[$i]}"
done
echo

echo '================================================================================'
# Now install MacPorts as a way to get additional Unix executables and many of the bioinformatic tools
# NOTE: See zcommon_macos.sh for MacPorts routines.  Pushed there as also needed in uninstall.

# If Macports installed but for the wrong OS; then must uninstall and reinstall
if _macports_wrong_OS ; then
  echo "Uninstalling Macports from an earlier MacOS version ..."
  macports_uninstall noask
fi

# If Macports not installed; simply install
if [ ! -f "$_localport" ]; then
  macports_install "2.11.5"

# else Update Macports and any packages as necessary
else
  echo 'Updating Macports and its packages ...'
  sudox "$_localport" selfupdate
  sudox "$_localport" upgrade outdated

fi
echo

# Filter prolific warnings going to stderr but meant for developers (on MacOS 13 Ventura with new 2.8.0)
# Then filter out detailed stdout messages except Configuring; want to leave unusual / unexpected messages but ...
if [ ! -f /opt/local/bin/7zz ]; then
  echo 'Macports is installing the Unix utilities (can take 5 to 60 minutes) ...'
  sudox "$_localport" -N install bash grep gsed coreutils zip unzip 7zip md5sha1sum jq \
    2> >(grep -v "^Warning: Configuration logfiles" 1>&2) | grep "^--->  Configuring"
  sudox ln -s /opt/local/bin/7zz /opt/local/bin/7z    # New 7zip only installs as 7zz
fi

if [ ! -f /opt/local/bin/samtools ]; then
  echo 'MacPorts is installing the bioinformatic packages (can take 5 to 60 minutes) ...'
  sudox "$_localport" -N install samtools bcftools htslib \
   2> >(grep -v "^Warning: Configuration logfiles" 1>&2) | grep "^--->  Configuring"
fi
echo 'Finished installing MacPorts base with Unix and bioinformatic packages.'
echo

# BWA is not in MacPorts! BWA is on homebrew if we decide to switch
# So grab compiled versions from https://github.com/smikkelsendk/bwa-for-arm/tree/master/bin
if [ ! -f /opt/local/bin/bwa ]; then
  echo 'Adding BWA ...'
  case "$cpu_arch" in
    x86_64*)  _bwaf=bwa0717-mac-x64  ;;
    arm*)     _bwaf=bwa0717-mac-aarch64  ;;
    *)        echo "*** Error: Unknown MacOS Architecture ${cpu_arch}"  ;  exit  ;;
  esac
  _bwap="https://raw.githubusercontent.com/smikkelsendk/bwa-for-arm/master/bin/${_bwaf}.tar.gz"
  # BWAP="https://github.com/smikkelsendk/bwa-for-arm/raw/master/bin/${BWAF}.tar.gz"
  curlx -o bwa.tgz "$_bwap"
  if [ -e bwa.tgz ]; then
    tar xf bwa.tgz && rmx bwa.tgz
    chmod +x $_bwaf
    # shellcheck disable=SC2086
    sudo_mvx $_bwaf /opt/local/bin/bwa    # Not part of MacPorts but put bwa in its bin for convenience

  else
    echo '***ERROR downloading compiled BWA from smikkelsendk.'
  fi
fi
echo

# Todo bowtie2 -- in Macports but errors on install
# Todo bwa-mem2, minimap2 and fastp install; not in Macports nor Homebrew. Only Linux release on github master.
# Todo HiSat2.2.1 OSX x86 64bit  https://cloud.biohpc.swmed.edu/index.php/s/zMgEtnF6LjnjFrr/download
# Todo pbmm2, a PacBio Minimap2 front-end  https://github.com/PacificBiosciences/pbmm2

echo '================================================================================'
echo 'Common script to install the Python and WGS Extract packages'
"$bashx" "${wgse_FP}/scripts/zinstall_common.sh" "$cpu_arch" "$osver" "-"

case $? in
  0)
    echo
    echo 'Congratulations!  You finished installing WGS Extract on Apple MacOS!'
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
