#!/usr/bin/env bash
# WGS Extract Reference Library Management (Apple MacOS)
# Copyright (C) 2022-23 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

export TERM=xterm       # Needed when run from Applescript
clear

# Find the installation directory (normally part of zcommon.sh but when run standalone, cannot find that script)
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" || $(basename "$_wgseabs") == "installer_scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/ or installer_scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

declare bashx wgse_FP
source scripts/zcommon.sh "$wgse_FP"          || { echo "ERROR: Cannot source scripts/zzcommon.sh" ; exit 1 ; }

"$bashx" scripts/library_common.sh "$wgse_FP"
