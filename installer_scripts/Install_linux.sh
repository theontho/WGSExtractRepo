#!/usr/bin/env bash
# shellcheck disable=SC1090
# WGS Extract Install Script for Linux x86_64 based on Micromamba (Conda/Mamba) bioinformatics tools
# Copyright (C) 2021-24 Aaron Ballagan
# Copyright (C) 2023-24 Randolph Harr
#
# Based on the original Install_ubuntu.sh using apt to install bioinformatic tools
# Copyright (C) 2020-23 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt
#
# See https://mamba.readthedocs.io/en/latest/ for more information

# Micromamba 2.0.0-0 was released on Sep 25th 2024, which introduced breaking changes
# The version of the micromamba binary being downloaded is now fixed at 1.5.10-0 to ensure compatibility with this script
# Todo re-work this script to work with Micromamba 2
case ${cpu_arch:-$(uname -m)} in
  x86_64)  mm_arch="linux-64" ;;
  aarch64|arm64) mm_arch="linux-aarch64" ;;
  *) mm_arch="linux-64" ;; # Fallback
esac
micromamba_url="https://github.com/mamba-org/micromamba-releases/releases/download/1.5.10-0/micromamba-${mm_arch}"

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" || $(basename "$_wgseabs") == "installer_scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/ or installer_scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

source scripts/zxterm_linux.sh "$wgse_FP"    || { echo "ERROR: Cannot source scripts/zxterm_linux.sh" ; exit 1 ; }

export linux_type="micromamba"                   # Only place we set before zcommon.sh; to indicate micromamba linux

declare -f rmrx readq curlx >/dev/null
declare microdir micromambax cpu_arch osver
source scripts/zcommon.sh "$wgse_FP"         || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

declare -f echo_tee echo_log echo_fnl askyesno error_exit >/dev/null
declare -f initialize_microdir delete_microdir micromamba_abort >/dev/null
declare log_short date_time
source scripts/zcommon_linux.sh "Install_linux"   || { echo "ERROR: Cannot source scripts/zcommon_linux.sh" ; exit 1 ; }


# Stubs for later: determine when in WSL; Get exact actual Linux type ; turn on GUI mode in SUSE
# if [ -e /proc/sys/fs/binfmt_misc/WSLInterop ] ; then    # [[ $(uname -r) =~ "WSL" ]] if want to detect WSL
# OSTYPE=$(cat /etc/os-release | grep ID= )               # gives type of Linux on most distributions
# sudo zypper in -t pattern wsl_gui                       # needed to enable GUI mode in SUSE

#-------------------------------------- Start of Actual Install -------------------------------------
#
initialize_microdir     # and logfile up front so we can start writing into it

# Start logfile with a time stamped header (that matches the external file name)
echo_log "Log of the WGS Extract Micromamba Linux installation executed on: ${date_time}"
echo_log ""

# Changed many of Aaron's original (verbose) informational messages to append to the logfile only; not stdout
echo_fnl
echo_log "\_/"
echo_log "/_\\"
echo_tee "*** WGS Extract v4 Linux Installer (64-bit x86, conda/bioconda packages)"
echo_log "\_/"
echo_log "/ \\"
echo_fnl

# Aborts script if script if *not* on a supported architecture. Customised messages for some architectures are given.
if [[ ${cpu_arch} != "x86_64" ]] && [[ ${cpu_arch} != "aarch64" ]] && [[ ${cpu_arch} != "arm64" ]]; then

  case ${cpu_arch} in
    arm*|aarch*) arch="ARM-based"       ;;
    i386|i486)   arch="32-bit x86"      ;;
    ppc*)        arch="PowerPC-based"   ;;
    s390*)       arch="IBM S/390-based" ;;
    *)           arch="unknown"         ;;
  esac

  error_exit "WGS Extract Linux (micromamba) works on 64-bit x86 architectures only, not $arch."
fi

# Aborts script if C standard library installed on the current distro is musl libc.
if ldd --version 2>/dev/stdout | head -1 | grep -q 'musl libc' ; then
  error_exit "Found the musl C standard library (as opposed to glibc) on your system." \
             "The micromamba bioinformatics tools require glibc. Consult your Linux" \
             "distribution docs for how to run glibc-based programs on your system" \
             "Enable glibc and then rerun the installer."
fi

echo_tee "--------------------------------------------------------------------------------"
echo_tee "Installing Micromamba package manager for Linux (Conda/Mamba)"
echo_fnl

# Todo move to start of scripts and set based on .wgsedebug file so available from the start (like in Python)
# verbose mode (default off) is a parameter to micromamba ; could use -q when not -v but want some messages in the log
export verbosem="-v" # Note: must NOT quote when a parameter to the micromamba function call ("" is forced param)
verbose=true         # clear verbosem string and set verbose to false if want normal (not completely quiet) to log file

# Changed to verbose to a logfile always on; quiet or "no setting" for stdout (fixed in echo_tee and echo_log)
# if [[ "$1" != "restart" ]] ; then
#   askyesno "Would you like to run verbose mode on the Mamba installer log file messages (y/N)?"
#   if [[ ! $REPLY =~ ^[yY]$ ]] ; then
#     verbosem="-q"     # Let's turn on more than default messaging for the log
#     verbose=false
#   fi
# fi

# Todo Do we want this?  Installers act as updaters. Does fully re-entrant work here? Use Uninstall_linux.sh?
# if [[ -d "${microdir}/bin" ]]; then
#   askyesno "Would you like to delete the previous Micromamba installation (or simply update) (y/N)?"
#   if [[ $REPLY =~ ^[yY]$ ]] ; then
#     delete_microdir           # Saves current logfile
#     initialize_microdir       # Restores current logfile
#   fi
# fi

# TODO: Compile a static micromamba binary and package it with the installer. Some micromamba release binaries
#  are dymanically linked to glibc so this does not work with musl-based distros. Ideally, the micromamba
#  environment should run on any Linux distro though. Ditto for arm arch as more are available and running Linux.
#  Purposely do not set the architecture "conda-forge/linux-64" in general as some packages are only in noarch

mkdir -p "${microdir}"/{bin,cache/pip,jdk8,jdk11}   # Prepare our major subdirectories

[ -f "$micromambax" ] && rmx "$micromambax"     # Neccessary?  Won't it just overwrite?

if command -v curl &>/dev/null; then
  curlx -o "$micromambax" "$micromamba_url"     # Note: using our function defined curl with more parameters set

elif command -v wget &>/dev/null; then
  wget  -O "$micromambax" "$micromamba_url"

else
  error_exit "Neither curl nor wget are available to download the micromamba executable." \
             "Use your OS Package Manager to install one of them and then rerun this installer"
fi

if [ ! -f "$micromambax" ] ; then
  error_exit "Unknown error downloding the micromamba release located at:" \
             "$micromamba_url"
fi
chmod 755 "$micromambax" || error_exit "Failed to set micromamba executable bit"
echo_fnl

# Initialize and activate the micromamba base environment
# This code must be repeated wherever the WGS Extract Linux code is run
# note: this eval defines a function called "micromamba" which is used everywhere after; not micromambax in the bin
declare -f micromamba >/dev/null
eval "$( "$micromambax" shell hook -s bash --prefix "$microdir" )"
micromamba_abort "Failed to init micromamba shell"
micromamba activate --prefix "$microdir"  # 2>&1 | echo_tee      # does not seem to work?
micromamba_abort "Failed to activate micromamba"
micromamba update -y -a &>/dev/null

$verbose && echo_log ""
$verbose && echo_log "Base Micromamba package installed and activated."
$verbose && echo_log ""

echo_tee "--------------------------------------------------------------------------------"
echo_tee "[1/5] Installing needed additional Linux utilities from Conda Forge into base."
echo_fnl

micromamba install $verbosem -y -r "$microdir" -c conda-forge \
             sed coreutils zip unzip bash gcc grep curl p7zip jq dos2unix 2>&1 | echo_tee
micromamba_abort "Failed to install the Linux utilities"

echo_tee "--------------------------------------------------------------------------------"
echo_tee "[2/5] Installing Python from Conda Forge into base."
echo_fnl

# Todo 3.12.* triggers new warnings on some constructs still in use (remove in v5)
micromamba install $verbosem -y -r "$microdir" -c conda-forge 'python=3.11.*' pip tk 2>&1 | echo_tee
micromamba_abort "Failed to install Python "

echo_tee "--------------------------------------------------------------------------------"
echo_tee "[3/5] Installing OpenJDK 8 and 11 from Conda Forge into separate sub-bases."
echo_fnl

micromamba deactivate 2>&1 | echo_tee                            ; micromamba_abort "Failed deactivating base"
micromamba activate --prefix "${microdir}/jdk8" 2>&1 | echo_tee  ; micromamba_abort "Failed activating sub-base jdk8"
micromamba install $verbosem -y -r "${microdir}/jdk8" -c conda-forge 'openjdk=8.0.332' 2>&1 | echo_tee
micromamba_abort "Failed to install JDK8"
micromamba update -y -a &>/dev/null

micromamba deactivate 2>&1 | echo_tee                            ; micromamba_abort "Failed deactivating sub-base jdk8"
micromamba activate --prefix "${microdir}/jdk11" 2>&1 | echo_tee ; micromamba_abort "Failed activating sub-base jdk11"
micromamba install $verbosem -y -r "${microdir}/jdk11" -c conda-forge 'openjdk=11.0.15' 2>&1 | echo_tee
micromamba_abort "Failed to install JDK11"
micromamba update -y -a &>/dev/null

micromamba deactivate 2>&1 | echo_tee                            ; micromamba_abort "Failed deactivating sub-base jdk11"
micromamba activate --prefix "$microdir" 2>&1 | echo_tee         ; micromamba_abort "Failed activating base"

echo_tee "--------------------------------------------------------------------------------"
echo_tee "[4/5] Installing bioinformatics tools from Conda Forge and Bioconda into base."
echo_fnl

# Todo Bowtie2 omitted due to incompatibility with Python 3.11
# Conda-forge needed to install dependencies of some bioconda packages
packages=( bwa bwa-mem2 minimap2 hisat2 samtools bcftools tabix fastp )
[[ ${mm_arch} == "linux-64" ]] && packages+=( pbmm2 )

micromamba install $verbosem -y -r "$microdir" -c conda-forge -c bioconda \
  "${packages[@]}" 2>&1 | echo_tee
micromamba_abort "Failed to install the bioinformatic tools"

# Todo do we really need this?  Or should we simply do it every time? Disabled for now
# if [[ $1 != "restart" ]]; then
#   askyesno "Would you like to delete any micromamba caches (slightly delays reinstall later) (y/N)?"
#   if [[ $REPLY =~ ^[yY]$ ]]; then
#     $verbose && { echo_tee "Deleting caches."  ;  echo_log "" ; }
#
#     micromamba clean $verbosem -y -a
#     [ -f "$HOME/micromamba/pkgs/urls.txt" ] && rmrx "$HOME/micromamba/"
#     [ -f "$HOME/.mamba/pkgs/urls.txt"     ] && rmrx "$HOME/.mamba/"
#     [ -f "${microdir}/cache/pip/"         ] && rmrx "${microdir}/cache/pip/"
#
#     $verbose && { echo_tee "Caches deleted."  ;  echo_log "" ; }
#
#   else
#     $verbose && { echo_tee "Keeping caches."  ;  echo_log "" ; }
#
#   fi
# fi

echo_fnl
echo_tee "Finished initializing needed tools from Conda Forge and Bioconda."
echo_fnl
echo_tee "Micromamba detailed installation logfile at: $log_short"
echo_fnl

# Handles Python Library Modules and WGS Extract packages via the Common script
echo_tee "----------------------------------------------------------------------------"
echo_tee "[5/5] Common script to install the Python and WGS Extract packages"
echo_fnl
if [ -e "$bashx" ] ; then
  "$bashx" "scripts/zinstall_common.sh" "$cpu_arch" "$osver" "$linux_type" # "$verbose"  # Todo pass verbose down

else
  error_exit "Cannot find the Conda / Mamba bash program to start the common install script."
fi

case $? in
  0)
    echo_fnl
    echo_tee 'Congratulations!  You finished installing WGS Extract on Linux (Micromamba)!'
    echo_tee 'You can start WGS Extract by clicking the WGSExtract.sh file. Make a softlink,'
    echo_tee 'rename it to WGSExtract, and place on your desktop to start the program there.'
    echo_fnl   ;;

  10)
    exit       ;;   # exit silently as restarted the Install script due to an upgrade

  *)
    echo_fnl
    echo_tee 'Sorry. There was a problem during the WGS Extract install on Linux (Micromamba).'
    echo_tee 'Please scroll back through the log here or view the micromamba/ folder logfile '
    echo_tee 'to look for any errors.'
    echo_fnl   ;;

esac

readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
