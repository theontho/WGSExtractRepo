#!/usr/bin/env bash
# WGS Extract Install Script for Linux x86_64
# Copyright (C) 2021-23 Aaron Ballagan
# Copyright (C) 2020-23 Randolph Harr
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

declare pythonx micromambax microdir wgse_FP
declare -f readq >/dev/null
source scripts/zcommon.sh "$wgse_FP"            || { echo "ERROR: Cannot source scripts/zxterm_linux.sh" ; exit 1 ; }

echo 'Starting WGS Extract ...'

# Start micromamba environment so we have access to its applications
declare -f micromamba >/dev/null
eval "$( "$micromambax" shell hook -s bash --prefix "$microdir" )"
micromamba activate --prefix "$microdir"

"$pythonx" "${wgse_FP}/program/wgsextract.py"

readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
