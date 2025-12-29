#!/usr/bin/env bash
# WGS Extract Program Start Script (Apple MacOS)
# Copyright (C) 2020-2023 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

export TERM=xterm       # Needed when run from Applescript
clear

export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" || $(basename "$_wgseabs") == "installer_scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/ or installer_scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

declare pythonx
declare -f readq
source scripts/zcommon.sh "$wgse_FP"        || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

echo 'Starting WGS Extract ...'

"$pythonx" "${wgse_FP}/program/wgsextract.py"

readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
