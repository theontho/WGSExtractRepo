#!/usr/bin/env bash
#
# WGS Extract Uninstall Script for All (common)
# Copyright (C) 2022-24 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

# NOTE: MUST be in old BASH form for MacOS as MacPorts with modern BASH has been deleted by time this is called

# Common environment setup for scripts here; sets some variables used later
if (( $# != 1 )) ; then
  printf "Usage: %s { reflibdir }\n" "${BASH_SOURCE[0]##*/}"
  printf "  reflibdir is the Reference Library location (possibly a user setting).\n"
  printf "  This should only be called from WGSE Uninstaller internal scripts.\n"
  exit
fi

# IMPORTANT: If any changes made here, need to propogate to every script that uses this before sourcing this one
declare -x wgse_FP                        # Shellcheck needs (does not affect if already declared)
if [[ ! $wgse_FP ]]; then                 # Already set when called from .bat script ; or a subscript call
  [[ -d $1 ]] && _wgsedir="$1" || _wgsedir=$(dirname "${BASH_SOURCE[0]}")   # Get install directory (possibly via $1)
  _wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases, relative and symlinks (readlink not available)
  [[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs"
fi

if ! declare -f _perform_rmx > /dev/null ; then
  declare home reflibdir
  declare -f cdx rmx mvx readq > /dev/null
  source scripts/zcommon.sh "$wgse_FP"          || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }
fi

reflibdir="$1"    # Override zcommon.sh setting. Pass in reflibdir as jq.exe needed by findreflib may be gone by now

echo '================================================================================'
echo 'Now removing the WGS Extract program and reference library itself.'


wgseenclose="$(dirname "$wgse_FP")"
wgsebase="$(basename "$wgse_FP")"

remove_wgse=false       # Default is to save the WGS Extract installation
if [[ -z $wgsebase || ! -d $wgse_FP || ! -d $wgseenclose ]] ; then
  echo
  echo '*** ERROR: the installation base for the WGS Extract program is not defined.'
  echo '           You will have to delete the WGS Extract program folder yourself."'

elif [[ "$wgsebase" == "/" || "$wgseenclose" == "$wgsebase" ]]; then  # Make sure we are not wiping the disk
  echo
  echo '*** WARNING: The WGSE installation appears in the root. We will not delete it.'

else
  readq "Do you want to DELETE the WGS Extract program in $wgsebase [y/N]?"

  if [[ $REPLY =~ ^[Yy]$ ]]; then
    remove_wgse=true
    rmx "${home}/.wgsextract" "${home}/.wgsedebug" "${home}/.wgsewslbwa"
    echo "... Removing the WGS Extract program in ${wgsebase}"

  else
    echo "... Leaving the WGS Extract program ${wgsebase} in place"

  fi
fi

# Todo separate the reflib from the genomelib.  Offer to relocate and/or save the genomelib only.
#  Genomelib is empty with a new installation.

# Reference Library may have moved and not be in $wgse_FP/reference/
refenclose=$(dirname "$reflibdir")
refbase=$(basename "$reflibdir")

if [[ -d $reflibdir ]] && $remove_wgse ; then
  readq "Do you want to KEEP the WGS Extract Reference Library ($refbase) [y/N]?"

  if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$refenclose" == "$wgse_FP" ]] ; then     # Reference Library in WGSE, want to save it, and WGSE being deleted
      mvx "$reflibdir" "${wgseenclose}/${refbase}_saved"
      echo "... Saving the Reference Library to ${wgseenclose}/${refbase}_saved."

    # else not located in the WGSE folder so will not be deleted when deleting WGSE so nothing to do; automatic save
    fi

  elif [[ "$refenclose" != "$wgse_FP" ]] ; then     # Reference Library moved and want to remove it
    if [[ "$refbase" == "/" || "$refenclose" == "$refbase" ]]; then  # Just make sure we are not wiping disk
      echo '*** WARNING: The library folder appears in the root. We will not delete it.'

    else
      echo "... Removing the Reference Library folder ${refbase}."
      rmrx "$reflibdir"

    fi

  # else do not want to keep the ref library and it is located in the WGSE folder; so reflib will get deleted with WGSE
  fi
fi

# Todo check if Temp moved and delete it from the moved location

if ! $remove_wgse ; then
  readq 'Press any key to close this window (maybe scroll up to review for errors) ...'
  exit
fi

# Actually remove the WGS Extract installation folder and its packages. Also Cygwin64 and Micromamba on
# those platforms.  Windows and Mimcromamba Linux are special because we are trying to delete bash while
# in a bash script. So windows drops out to a cmd.exe forked process to do the deletion after once we
# leave here.

{   # Critical code section; force pre-read as file may disappear
  echo
  echo '================================================================================'
  echo '(Almost) Finished uninstalling WGS Extract and its programs. '
  echo
  echo 'If you specified a Temp directory outside the WGS Extract  install  folder,  you'
  echo '  will need to remove that folder yourself.  If you asked  to  save  the  genome'
  echo '  library that is located in the installation folder,  it will  be  moved to the'
  echo '  folder above the installation.'
  echo
  echo 'The WGS Extract program folder will not delete if any application has any  files'
  echo '  or folders open in it.  For example,  Finder / Explorer where you clicked  the'
  echo '  Uninstall command script from. Make sure to close any application NOW that may'
  echo '  have an open file or folder in the installation.'
  echo
  echo 'Due to race conditions, a few files may be left. You can safely delete any files'
  echo '  and the installation folder left after finishing here.'

  readq 'Press any key to finish deleting (maybe scroll up to review for any errors) ...'

  cdx "$wgseenclose"     # Move out of the way so we can delete the folder we are running from
  [[ ! -d "$wgsebase" ]] && { echo "Cannot find the $wgsebase folder to delete" ; exit ; }  # One last check

  case $OSTYPE in

    darwin* | linux*)
      nohup rm -rf "$wgsebase" &>/dev/null & ;;   # Cannot use the rmrx function call here

    msys* | cygwin*)
      wgsebasedos=$(cygpath -w "$wgsebase")   # But is just a folder name; not a path. Why needed?
      # delcmd="start /b rmdir ""$wgsebasedos"" /s/q"
      nohup cmd.exe /d /c start /b rmdir "$wgsebasedos" /s/q &>/dev/null  ;;

  esac

  exit  # Need to force an exit inside the pre-read code section as the file may no longer exist to read further
}
