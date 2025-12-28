#!/usr/bin/env bash
# WGS Extract Uninstall Script for Linux x86_64
# Copyright (C) 2020-23 Randolph Harr
# Copyright (C) 2023 Aaron Ballagan
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

source scripts/zxterm_linux.sh                  || { echo "ERROR: Cannot source scripts/zxterm_linux.sh" ; exit 1 ; }

export linux_type="micromamba"                  # Only place we set before zcommon.sh; to indicate micromamba linux

declare bashx reflibdir micromambax microdir wgse_FP
declare -f find_reflibdir >/dev/null
source scripts/zcommon.sh "$wgse_FP"            || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

declare -f micromamba_abort >/dev/null
source scripts/zcommon_linux.sh "Uninstall_linux"

echo '======================================================================================================'
echo 'WGS Extract v4 Uninstaller for Linux (micromamba edition)'
echo
echo 'WGS Extract used "micromamba" (a Mamba / Conda installer) to install the dependent tools in the'
echo ' main folder WGSExtract/.  Simpy removing the WGSExtract/ folder removes all these tools.'
echo

# Start the micromamba environment to gain access to its applications to find the reflibdir, in case it has been moved
# Initialize and activate the micromamba base environment (to enable finding reflibdir, in case it was moved)
# This code must be repeated wherever the WGS Extract Linux code is run
declare -f micromamba >/dev/null
eval "$( "$micromambax" shell hook -s bash --prefix "$microdir" )"
micromamba_abort "Failed to init micromamba shell"
micromamba activate --prefix "$microdir"  # 2>&1 | echo_tee      # does not seem to work?
micromamba_abort "Failed to activate micromamba"
micromamba update -y -a &>/dev/null

# Check if reference library has been moved out of the installation directory (needs jq; so use before deleted)
find_reflibdir

# No micromamba to remove as it is needed by the WGS Extract general uninstall below. Can simply be deleted with WGSE

${bashx} "scripts/zuninstall_common.sh" "$reflibdir"

{ # Preread this code in case the script is deleted before reaching here
  # In case they left the WGS Extract installation there; we still need to deactivate and leave the environment intact
  if [ -e "$microdir" ]; then
    micromamba deactivate
    # delete_microdir
  fi
}
