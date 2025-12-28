#!/usr/bin/env bash
# WGS Extract v4 in-place common scipt startup (all platforms)
# Copyright (C) 2021-2023 Randolph Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

# Todo move Aarons log-file capture routines here and reuse in all the other bash and python script files

# Todo although coding style is 120 chars, should limit screen messages to default terminal size of 80 chars

# set linux_type=micromamba in Linux scripts before calling this script until we deprecate the ubuntu installer

#---------------- Script sourced by all others; Shell independent (POSIX) code till verify BASH --------------------

[[ ":$PATH:" != *":/usr/bin:"* ]] && PATH="/usr/bin:${PATH}" && export PATH     # Cygwin starts with no environment

cursh="$(ps -p$$ | tail -1 | grep -o 'bash')"   # Get shell from process stats; determine if BASH (best solution)

if (( $# != 1 )) || ! (return 0 2>/dev/null) || [ "$cursh" != "bash" ] ; then
  printf "Usage: source WGSE_script { install_dir } \n"   # We cannot get a script name in a SHELL independent way
  printf "  WGSE scripts should be sourced and run from a BASH shell.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

# Check for a known OS
if [[ ! $OSTYPE =~ (msys|cygwin|darwin|linux) ]]; then
  echo "*** Error: unsupported OSTYPE: $OSTYPE"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

# Most of the declare and export statements are not needed as this file is sourced. We add them to document what is
# being set and used by scripts that source this file (functions, variables) and to satisfy shellcheck
# There could be instances of a sub-shell call that needs the exports so is a good idea to keep them.


#-------------------------------------- Refined Installation Directory ---------------------------------------------
# Set installation directory (use passed in value if not already set) ; refine it for cygwin
# IMPORTANT: Relies on scripts being in the installation folder or the scripts one below that. Click on GUI file works
#  even with aliases as long as the original file is kept in the same place. Only reliable way is to require ~/.wgse
declare wgse_FP                               # Shellcheck needs (does not affect if already declared)
if [[ -z $wgse_FP ]] ; then                   # Already set when called from .bat script
  [[ -d $1 ]] && _wgsedir="$1" || _wgsedir=$(dirname "${BASH_SOURCE[0]}")   # Get install directory (possibly via $1)
  _wgseabs=$( cd "$_wgsedir" || true ; pwd -P )   # Resolve any aliases, relative and symlinks (readlink not available)
  [[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs"
fi

# Refinement for Cygwin not done elsewhwere
if [[ $OSTYPE =~ (cygwin|msys) ]]; then
  newp=$(cygpath -u "$wgse_FP")       # pwd in Cygwin64 returns DOS style path
  wgse_FP="${newp%/}"                   # Remove trailing slash added by cygpath to be consistent with others
fi
export wgse_FP

# Note: wanted to escape embedded spaces also -- ${wgseabs/ /\\ } -- to be more robust whether quoted or not
# But BASH cd accepts "sp ace" and sp\ ace, but not "sp\ ace". So escaped space cannot be used.


#-------------------------------------- Common Globally Used Definitions ---------------------------------------------

# See SPECIAL NOTE at the end about BASH pseudo-boolean variables in all BASH scripts here
declare -irx success=0 fail=1                             # Make returns / exits clearer (int instead of true/false)
# (return 0 2>/dev/null) && return $fail || exit $fail    # Handles whether script called or sourced; not needed here

# Needed by make_release.sh and installer to setup and then process .zip package releases of WGSE system install
declare -rx zipdir="WGSExtractv4"       # Local directory to create content for zip file (and now stored in zipfile)
# declare -rx release="WGSExtractv4"      # Set toplevel folder inside release .zip (the same; no longer needed)

# Functions work better than variables or aliases in a wider range of uses (subshells, complex commands (pipe, braces)
# sudov called before sudo to verify not in cygwin64. Refreshes cached password if cached credentials are not valid.
enable -n alias unalias # Make sure aliases are turned off (even though default) as we cannot prepend sudo with \

#------------------------------------------------------------------------------------------------------------------
# PATH not fully set (yet); override builtin (ancient) BASH for some OSs.
declare bashx microdir micromambax PATH
case $OSTYPE in
  msys*)
    declare -rx bashx="/usr/bin/bash.exe"
    [[ ":$PATH:" != *":/ucrt64/bin:"* ]] && PATH="/ucrt64/bin:/usr/bin:${PATH}"
    ;;

  cygwin*)
    declare -rx bashx="/bin/bash.exe"
    [[ ":$PATH:" != *":/usr/local/bin:"* ]] && PATH="/usr/local/bin:/bin:${PATH}"
    ;;

  darwin*)
    declare -rx bashx="/opt/local/bin/bash"
    [[ ":$PATH:" != *":/opt/local/bin:"* ]] && PATH="/opt/local/bin:/opt/local/sbin:${PATH}"
    ;;

  linux*)
    # If the micromamba env has been activated, then the bash bin from that env will get priority on $PATH
    if [[ "$linux_type" == "micromamba" ]]; then # Special: linux_type defined before sourcing this script
      declare -rx microdir="${wgse_FP}/micromamba"
      declare -rx micromambax="${microdir}/bin/micromamba"
      declare -rx bashx="${microdir}/bin/bash"

    else
      declare -rx bashx="/bin/bash"
      # All tools installed in system release directories already on path by apt or our local installer

    fi
    ;;
esac
export bashx microdir micromambax # Just for clarity and convention here
export PATH                       # System wide (BASH) variable (here to satisfy shellcheck)

# Helpful advice on distinguishing unset, null and non-null values in a BASH variable
# https://www.geeksforgeeks.org/bash-scripting-how-to-check-if-variable-is-set/
# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash/16753536#16753536
# https://stackoverflow.com/questions/35006457/choosing-between-0-and-bash-source

#------------------------------------------------------------------------------------------------------------------
# Get users home directory; if in Windows, their true user home and not cygwin BASH $HOME
declare home
[[ $OSTYPE =~ (cygwin|msys) ]] && home=$(cygpath.exe -u "$USERPROFILE") || home=~
export home

#------------------------------------------------------------------------------------------------------------------
# Get OS Release version info (1-3 parts usually; leave as sting here)

declare -x osver cpu_arch # Shellcheck wants declare before in this instance (and -x); it is confused

cpu_arch=$(uname -m) # Generally, always x86_64. But may be aarm64 for Apple M1/M2's

case $OSTYPE in
  msys2*)
    osver=$(uname -a | cut -d" " -f3)       # 4th element is cpu architecture
    # IFS="." read -ra osarr <<<"$osver"
    ;;

  cygwin*)
    # In Cygwin, the main cygwin DLL is the Unix kernel version.  base-cygwin is more a cygwin release version.
    # Presume we do not want a windows version which is useless in Cygwin64
    osver=$(cygcheck -c base-cygwin | grep base-cygwin | tr -s "[:space:]" | cut -d" " -f2)
    osver=${osver//-/.}
    ;;

  darwin*)
    # Pre BigSur, versions were 10.maj.min.  Since BigSur, version are maj.min with BigSur starting at 11.
    osver=$(sw_vers -productVersion)
    ;;

  linux*)
    # No OS version for micromamba (generic linux), so set osver to 0
    if [[ "$linux_type" == "micromamba" ]]; then
      osver="$linux_type"     # NHelps with case statement later using cpu_arch & osver smashed together

    else # Ubuntu
      # This only works for Ubuntu that has the lsb-release file
      [ -e /etc/lsb-release ] && IFS='=' read -ra elements <<<"$(grep "ION=\"Ubuntu [12]" /etc/lsb-release)"
      [ ${#elements[@]} -eq 2 ] && IFS=' ' read -ra parts <<<"${elements[1]}"
      [ ${#parts[@]} -gt 1 ] && osver=${parts[1]}
      if [[ ! ${osver} =~ ^(18|20|22|24) ]]; then
        echo '***Warning: Currently only support Ubuntu LTS 18 thru 24; setting to 18'
        osver="18.04.0"
      fi

    fi
    ;;
esac
export osver cpu_arch

#------------------------------------------------------------------------------------------------------------------
# Setup Python access (only used by installer; this file is sourced by the installer before installing Python)
# note: micromamba puts its python3 and BASH in the PATH variable
declare -x pythonx owgse_FP   # Bug in shellcheck (needs declare and -x here)
case $OSTYPE in
  msys*)
    pythonx="${wgse_FP}/msys2/ucrt64/bin/python.exe"
    owgse_FP=$(cygpath -m "$wgse_FP")
    ;;
  cygwin*)
    pythonx="${wgse_FP}/python/python.exe"
    owgse_FP=$(cygpath -m "$wgse_FP")
    ;;
  darwin*)
    pythonx="/usr/local/bin/python3"
    owgse_FP="$wgse_FP"
    ;;
  linux*)
    pythonx="python3"
    owgse_FP="$wgse_FP"
    ;;
esac
export pythonx owgse_FP

declare -rx process_refgenomes="${owgse_FP}/scripts/process_refgenomes.sh"      # locally used


#------------------------------- GLOBAL FUNCTION CALLS AND RETURN VALUES (as exports) -------------------------------
#  Any "returned" values are exported at the end with defaults set in declare before definition (for clarity)

set -a                                      # All below will be set as if "declare -fx"
sudox() { sudov ; sudo -H "$@" || true; }   # sudov checks that sudo available; sudox does the || true for shellcheck
cpx() { \cp -fp "$@" || true; }             # preserve timestamps (--preserve=timestamps not on MacOS)
sudo_cpx() { sudox cp -fp "$@"; }           # Cannot sudo a function; so replicate
cprx() { cpx -R "$@"; }
sudo_cprx() { sudox cp -fp -R "$@"; }
rmx() { _perform_rmx "nosudo" "$@"; }
sudo_rmx() { _perform_rmx "sudo" "$@"; }
rmrx() { _perform_rmrx "nosudo" "$@"; }
sudo_rmrx() { _perform_rmrx "sudo" "$@"; }
mvx() { \mv -f "$@" || true; }
sudo_mvx() { sudox mv -f "$@"; }
cdx() { \cd -P "$1" || true; }               # built-in; but helps ignore the error shellcheck reports
readq() { echo ; read -n1 -r -p "$@" ; echo ; }  # For 1 char answer from user; $1 query string, optional $2 var to set
# reada() { read -ra "$@"; }                # For reading into am array variable
curlx() { curl -k#LC - --retry 5 "$@"; }     # -Z not in curl < v7.66 (Monterey-11 and earlier; Ubuntu 18.04)
# sudov, _perform_rmx and _perform_rmrx defined below; more than a single line
set +a

#---------------------------------------- SPECIAL RM -RF and SUDO SUPPORT --------------------------------------------
# We try to avoid "rm -rf"; especially if in a sudox state.  But since we sometimes need it, we make a special routine
# to do sanity checks before implementating the call.  PLEASE ALWAYS USE THIS ROUTINE INSTEAD OF "rm -rf"

sudov() {
  # Use as function call in a statement like "sudov ; sudo -H cmd_of_interest ...."
  # Created to catch improper use of sudo in Cygwin64; simply refreshes the cache or creates a valid cache entry
  if [[ $OSTYPE =~ (msys|cygwin) ]]; then
    echo "*** internal ERROR: sudo not supported in Windows"
    return 1
  fi
  sudo -v
}


_perform_rmx() {
  # $1 is "sudo" or "nosudo", $2 onward are the parameters to the rm -f command
  # Perform guarded, checked "rm -f"; check that -r is not the first parameter that bypasses rm -rf checks
  local dosudo target

  if [[ $1 != "sudo" && $1 != "nosudo" ]] ; then
    echo '*** ERROR (internal): Call _perform_rmx without the sudo/nosudo first parameter'
    return 1
  fi
  [[ "$1" == "sudo" ]] && dosudo=true || dosudo=false   # Shift removes current $1
  shift

  for target in "$@"; do
    [[ ! -f "$target" ]] && continue            # If not a file; skip
    # shellcheck disable=SC2015
    $dosudo && sudox rm -f "$target" || rm -f "$target"
  done
}
export _perform_rmx


# Disallowed directories to do a rm -rf on (root, and key OS directories) ; in case script has an error
not_allowed='/|/bin|/dev|/etc|/home|/lib|/mnt|/opt|/proc|/sbin|/tmp|/usr|/var|/share'
not_allowed+='|/Applications|/Library|/System|/Users|/Volumes'
not_allowed+='|/usr/local|/usr/share|/opt/local'
# e.g. require /usr/local/* to get around disallowing /usr/local (which is needed by cygwin64 and macports)

_perform_rmrx() {
  # $1 is "sudo" or "nosudo", $2 onward are the parameter(s) to the rm -rf command
  # Perform guarded, well checked "rm -rf" command on the list of files and/or directories
  local target filen dirn absdir dosudo

  if [[ $1 != "sudo" && $1 != "nosudo" ]] ; then
    echo '*** ERROR (internal): Call _perform_rmrx without the sudo/nosudo first parameter'
    (return 0 2>/dev/null) && return 1 || exit 1
  fi
  [[ "$1" == "sudo" ]] && dosudo=true || dosudo=false   # shift removes current $1
  shift

  for target in "$@"; do
    # If a file; strip the filename leaving only the directory in obj (filename only gets the "." directory)
    if [[ -f "$target" ]]; then
      dirn="$(dirname "$target")"  ;  filen="$(basename "$target")"
    else
      dirn="$target"               ;  filen=""
    fi

    # If not a directory; skip (want cd below to work; avoids any options like -r, etc)
    [[ ! -d "$dirn" ]] && continue

    # Change to absolute directory; remove . ~ .. etc (similar as done for wgse_FP)
    absdir=$( cdx "$dirn" ; pwd -P )
    [[ "$(basename "$absdir")" != "$(basename "$dirn")" && "$dirn" != "." ]] && continue

    # If not a directory now; skip (extra cautious)
    [[ ! -d "$absdir" ]] && continue

    # Recreate target but now with absolute path (avoid trailing slash if no filename)
    [[ -f "$target" ]] && target="${absdir}/${filen}" || target="$absdir"

    # Skip if is root or one of the other key OS directories (whether sudo or not)
    [[ ${target} =~ ^($not_allowed)$ ]] && continue

    # Final check as whether still valid, finally do rm -r but hopefully well guarded now
    if [[ -d "$target" || -f "$target" ]]; then
      # shellcheck disable=SC2015
      $dosudo && sudox rm -rf "$target" || rm -rf "$target"
    fi

  done
}
export _perform_rmrx


#----------------------------------------- REFERENCE LIBRARY SUPPORT ---------------------------------------------

# Reference Genome Library support (global for use by many routines to find a redirected reference library)
# Need to check wgse settings in case the user moved the reference library; relies on other settings in this file
# Needed in uninstall_windows.bat before deleting jq so replicated this code in cmd.exe using .bat script
export reflibdir=""
find_reflibdir() {
  local newreflib tempref

  reflibdir="${wgse_FP}/reference/" # Default location is in installation directory

  if [[ -e "${home}/.wgsextract" ]]; then
    # In case called before jq installed (during WGSE installation; by Library command before full install, etc)
    if command -v jq &>/dev/null; then                        # Should have been installed already ...
      newreflib="null"                                        # If command below fails; then returns "null", not ""
      newreflib=$(jq -r '."reflib.FP"' "${home}/.wgsextract") # Return string from settings (else "null")

      if [[ "$newreflib" != "null" ]]; then
        case $OSTYPE in
          msys* | cygwin*)  tempref=$(cygpath.exe -u "$newreflib") ;; # Massage Windows version
          darwin* | linux*) tempref="$newreflib" ;;
        esac
        # printf "Reference Library was at %s\n but moved to %s in settings.\n" "$reflibdir" "$tempref"
        reflibdir="$tempref" # From settings file -- reference library was moved
      fi

    else
      # See https://github.com/stedolan/jq/ for more information.
      echo "*** ERROR (internal): JQ is needed by find_reflibdir but not found."

    fi
  fi

  # echo "find_reflibdir: $reflibdir"
}
export -f find_reflibdir


#------------------------------------ REFERENCE GENOME LIBRARY SUPPORT --------------------------------------------
#  Seed genomes.csv has one row per genome. Columns are:
#   Python Genome Code, Final File Name, Downloaded File Name, URL, Library command menu string, SN Cnt, SN Name, Descr
# Note: very order dependent here and in the genomes.csv file.  Note based on reading genomes.csv headers to get order.
#   Also, true CSV with each field in double quotes and comma separated (no commas or double quotes allowed in fields).

declare -a pytcode server finalf initf gurl menopt sncnt snnam descr
# shellcheck disable=SC2086
read_genomes_file() {
  local -i i
  # Start with seed file from release if non-existent
  [ ! -f "${reflibdir}genomes/genomes.csv" ] &&
    cpx -f "${reflibdir}seed_genomes.csv" "${reflibdir}genomes/genomes.csv"

  # Read in Genomes.csv and transpose into array of column strings
  declare -a row cols
  while IFS="," read -ra row ; do
    for ((i = 0; i < ${#row[@]}; i++)); do
      cols[i]+="${row[i]}," # Rebuild rows by appending to column array strings; reinsert comma separator
    done
  done <"${reflibdir}genomes/genomes.csv"

  # This order (of array index / columns) must match the order in the genomes.csv file; first row is header / titles
  IFS="," read -ra pytcode <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[0]}\")"  # Python Ref Gen Code eg hs37
  IFS="," read -ra server  <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[1]}\")"  # Server with file (NIH, EBI, etc)
  IFS="," read -ra finalf  <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[2]}\")"  # Final reference file name
  IFS="," read -ra initf   <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[3]}\")"  # Initial, downloaded file name
  IFS="," read -ra gurl    <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[4]}\")"  # URL to download ref genome
  IFS="," read -ra menopt  <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[5]}\")"  # BASH Library menu option
  IFS="," read -ra sncnt   <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[6]}\")"  # Seq Name Count (# SNs)
  IFS="," read -ra snnam   <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[7]}\")"  # Seq Name Format (Chr, Num, Acc)
  IFS="," read -ra descr   <<<"$(sed -e 's/\"//g' -e 's/,$//' <<<\"${cols[8]}\")"  # Description
  export pytcode server finalf initf gurl menopt sncnt snnam descr
}
export -f read_genomes_file


# Implements the body of get_and_process_refgenome.sh call
get_and_process_refgenome() {
  # Parameter: index to genomes.csv arrays

  _filesizebad() { # parameters: file name, min size ; returns true if smaller than min size (or does not exist)
    local size=0    # size of 0 if file does not exist; so returns true
    [[ -f "$1" ]] && { [[ $OSTYPE =~ darwin ]] && size=$(stat -f %z "$1") || size=$(stat -c %s "$1") ; }
    ((size < $2))   # Trick, returning result of test as function return status
  }

  echo
  echo "Downloading and Processing ${descr[$1]}"
  cdx "${reflibdir}genomes/"

  [ -f "${finalf[$1]}" ] && rmx "${finalf[$1]}"
  [ -f "${initf[$1]}"  ] && rmx "${initf[$1]}"

  # To get around exclanations embedded in MS Onedrive URLs; no spaces in params so no escaped double quotes needed
  IFS=" " read -ra cmd <<<"curlx -o ${initf[$1]} ${gurl[$1]}"
  "${cmd[@]}"

  if _filesizebad "${initf[$1]}" 500000000; then
    echo "*** Error downloading ${initf[$1]}"
    [ -f "${initf[$1]}" ] && rmx "${initf[$1]}"
    return
  fi

  chmod 774 "${initf[$1]}"                        # Cygwin64 BASH is occassionally setting 060 permissions for genomes?
  ${bashx} "$process_refgenomes" "${initf[$1]}"

  if _filesizebad "${finalf[$1]}" 500000000; then
    echo "*** Error processing ${finalf[$1]}"
    [ -f "${finalf[$1]}" ] && rmx "${finalf[$1]}"
    [ -f "${initf[$1]}"  ] && rmx "${initf[$1]}"
    return
  fi

  echo "${finalf[$1]}: Finished installing ${pytcode[$1]}, SN Cnt: ${sncnt[$1]}, SN Style: ${snnam[$1]}"
}
export -f get_and_process_refgenome


#---------------------------------------- VERSION CHECK SUPPORT -------------------------------------------------
# Version check system support
#  Similar _verComp function in install_windows.bat in cmd.exe form. Also in program/utilities.py.
#  This _verComp implementation only needed in this script. Utility functions before main _verComp function.
# _verComp followed by JSON file reading functions for extracting the version numbers to check
# WGS Extract Version setting was integer only.  We added patch numbers (e.g v44.3) so changed to interpreted string

_alpha_to_ASCII() {
  # Take in version string $1 and replace each delimited alpha character with its ASCII code numeric string
  # Also, easiest to remove any leading delimiter here (array read later sets 1st element to null if leading delimiter)
  # Output the transformed string to stdout (to be captured from there)
  local ver chr alpha result
  local -i i j vlen

  ver="$1"
  vlen="${#ver}"

  result=""

  # Loop through each character in the string
  for ((i=0;i<vlen;i++)) ; do
    chr="${ver:$i:1}"

    if [[ $chr =~ [A-Z] ]] ; then                   # If alphabetic then convert to ASCII numeric
      j=65                                          # ASCII value of "A" ; j used to track the alphabetic characters

      for alpha in {A..Z} ; do                      # Find alphabetic character (no function in BASH for this)
        if [[ $chr == "$alpha" ]] ; then
          result+=$j                                # append string value of character ASCII numeric of character
          break
        fi
        ((j++))                                     # if not found, increase alphabet counter for next letter in loop
      done

    elif (( i == 0 )) && [[ $chr == "." ]] ; then   # Remove any leading delimiter
      continue

    else                                         # else simply append the character to the result
      result+="$chr"

    fi
  done
  echo "$result"
}


_filterVer() {
  # Take version string $1, filter it, and put it back out on stdout as a string
  # Filters applied: uppercase, change each letter to a ASCII code (surrounded by delimeters),
  #   change "p" delimeter to ".", and finally collapse successive delimeters to one.

  [[ ! $1 =~ ^[0-9a-zA-Z.]+$ ]] && echo "0" && return    # If not a valid version string; return string 0

  # gensub not on MacOS
  #_alpha_to_ASCII "$( awk -vv1="$1" 'BEGIN {     # change letters to ASCII numeric equivalent string
  #  print gensub(/\.+/, ".", "g",                # change successive delimeters to single delimeter
  #          gensub(/([A-Z])/, ".\\1.", "g",      # change each letter to a deliminated single letter
  #            gensub(/P/, ".", "g",              # change any P to a period (.) delimiter
  #              toupper(v1)))) }' )"             # Upcase any letters
  _alpha_to_ASCII "$( echo "$1" | awk '{print toupper($0)}' | sed "s/P/./g;s/\([A-Z]\)/.\1./g;s/\.\.*/./g" )"
}


# Version compare $1 to $3 using op $2
#   $1 and $3 are alphanumeric version values ( e.g. 3.44.2 or 2.4 or 0.0.1 or 4.44p3)
#   $2 a pseudo arithmetic comparison operator given as a string (<. <. ==, !=, <=, and >=)
#   Allows any number of levels. Each level is separated by a . (period) or p (letter). Level==Node==Token
#   A 'p' is a patch specifier and changed to a period delimiter (and cannot be used as a value)
#   A single alphabetic letter (sans p) is treated as a next level down specifier. 4a == 4.a
#   The shorter length version specifier is padded with trailing .0's to equal the longer length one.
#   Each Level is compared numerically; so multiple digits are treated as a single numeric specifier.
#   Leading zero's are stripped so they are not confused as Octal numbers in BASH.
#   Each alphabetic letter is upcased and converted to its ASCII numeric value. So "A" and "a" become 65.
#   Best not to mix letters and numbers at the same Level.
#   These are true: 0.9.3 > 0.1 , 1p2 == 1.2 , 1g > 1A , 4.44p3 > 4.44.2 , 4.44 > 4.5 , 44aB == 44.A.b , 4.9 < 4a
#
# An example use in an if conditional:
#   if _verComp 2.34 "<" 3.45.1 ; then ... but more likely will see:  if _verComp "$cur" "<" "$new" ; then ...
# Inspired by https://stackoverflow.com/a/25845393

# shellcheck disable=SC2211 disable=SC1102 disable=SC2046 disable=SC1105 disable=SC2086
_verComp() {
  # Main body of version compare set of functions; takes in the v1 op v2 parameters
  # Calls _filterVar which itself calls _alpha_to_ASCII
  local -a vlarr vrarr
  local -i vllen vrlen max i a b

  IFS="." read -ra vlarr <<<"$(_filterVer "$1")"  ;  vllen=${#vlarr[@]}
  IFS="." read -ra vrarr <<<"$(_filterVer "$3")"  ;  vrlen=${#vrarr[@]}

  (( vllen == 0 || vrlen == 0 )) && return $fail        # If both null / empty, return false
  max=$(( vllen > vrlen ? vllen : vrlen ))          # Find the max level of the two version strings

  for (( i=0; i<max; i++ )) ; do
    a=$(( 10#${vlarr[i]} ))  ;  b=$(( 10#${vrarr[i]} ))  # Automatically converts null's to zero's; drops leading zero's
    if (( a != b )) ; then
      (( a "$2" b )) && return $success || return $fail      # If not equal; perform the op. Else go to the next level
    fi
  done
  (( a "$2" b )) && return $success || return $fail          # Both were identical.  Perform op on equal value each side
}


declare release_track base_url latest_package_url
get_latest_json() {
  # Update local latest.json file from the online latest-release (does not check version numbers; may regress)
  # Reads track from release.json file if not yet set from a previous call
  # Processes new install by replacing release.json with release-override.json if latter exists; saves old release.json

  local -r saved_package_url="$latest_package_url"
  local -r release_json="${wgse_FP}/release.json"
  local -r override_json="${wgse_FP}/release-override.json"
  local -r saved_json="${wgse_FP}/release-saved.json"

  # Read release.json for the first time to set release_track, latest*url (and replace release.json if needed)
  if [[ -z "$release_track" ]]; then

    # If the installer has an override json, replace the current release.json with it
    # Note that a user overlaying an installer.zip content over an existing installation replaces the release.json
    if [ -e "$override_json" ]; then
      [ -e "$release_json" ] && mvx "$release_json" "$saved_json"
      mvx "$override_json" "$release_json"
    fi

    # If jq is available and there is a release.json file then extract the content
    if command -v jq &>/dev/null && [ -e "$release_json" ]; then
      release_track=$(jq -r .\"release\".\"track\" "$release_json")
      base_url=$(jq -r .\"release\".\"baseURL\" "$release_json")
      latest_package_url=$(jq -r .\"release\".\""${release_track}"URL\" "$release_json")

    fi    # Silent if jq or release.json do not exist
  fi      # Note: release_track could still be null

  # If a release.json file not found; then set defaults.  Should never occur but just in case
  if [[ -z ${latest_package_url:+set} ]]; then
    release_track="Beta"
    base_url="https://get.wgse.io/"
    latest_package_url="${base_url}latest-release-Beta.json"

  fi

  # Retrieve a new (package) json file if the local one is missing or the local has a different url
  #   not checking date or version so can regress if desired (Dev to Beta; for example)
  if [[ ! -e latest.json || "$latest_package_url" != "$saved_package_url" ]]; then
    echo "*** Retrieving the WGS Extract latest release json file (track ${release_track})."
    [[ -e latest.json ]] && rmx latest.json   # We are forcing the download; curl tries to recover if file sizes diff
    curlx -o latest.json "$latest_package_url"
    echo ""

  fi

  export release_track base_url latest_package_url # Provides source definition for latest.json file content
}
export -f get_latest_json


_fancypack() {
  # Center name $1 in a fixed width field $2 using spaces. Left padding greater than right if uneven padding required.
  # Return packed name to stdout. If name larger than fixed width field, just return name.
  local -r name="$1"
  local -i fieldlen=$2 namelen=${#1} lpad rpad padding

  if (( namelen > fieldlen )) ; then
    printf "%s" "$name"

  else
    padding=$(( fieldlen - namelen ))
    rpad=$((         padding / 2  ))
    lpad=$(( rpad + (padding % 2) ))
    printf "%${lpad}s%s%${rpad}s" "" "$name" ""

  fi
}


declare latestVer latestDate latestURL
get_latest_release_info() {
  # From the local latest.json file, read in the settings for the passed in package $1 (key in json); $2 if to print
  local -r pack=$1  verbose="$2"
  local fpack flver

  get_latest_json # Sets global release_track and gets latest-release.json file with all packages defined

  latestDate=""
  if [[ -e latest.json ]]; then
    latestVer=$(jq -r .\""$pack"\".\"version\" latest.json)
    latestDate=$(jq -r .\""$pack"\".\"date\" latest.json)
    latestURL=$(jq -r .\""$pack"\".\"URL\" latest.json) # Actual pointer to this package ZIP archive for version

  fi

  if [[ -z ${latestDate:+set} ]]; then    # jq above may return "" if error in file content and format
    latestVer=-1
    latestDate="unk"
    latestURL="URL_unknown"
    echo "*** ERROR: No latest version info available for package $pack in track $release_track"

  else
    fpack=$( _fancypack "$pack" 9 )
    flver=$( _fancypack "v$latestVer" 3 )
    $verbose && echo "Found $fpack  latest available version is ${flver}, date $latestDate for track $release_track"

  fi

  export latestVer latestDate latestURL
  # echo "get_latest_release: ver $latestVer, date $latestDate, URL $latestURL"
}
export -f get_latest_release_info


declare -x currentVer currentDate currentURL
read_current_release_info() {
  # Read in the current package $1 local json file found at $2 ; for example package program gets program/program.json
  # $1 is the package name (key in json), $2 is the json file, $3 is true if should print (verbose)
  local -r pack=$1  jfile="$2"  verbose="$3"  special="$4"
  local fpack fcver

  # Special for old Alpha 4m / 4.33 release that introduced version.json files but had different file naming convention
  if [[ $special == "4m" ]] ; then
    case "$pack" in
      program) pack="wgse"       ;;
      tools)   pack="localtools" ;;
    esac
  fi

  currentDate=""
  if [ -e "$jfile" ]; then # May assign "" if error in file content or format
    currentVer=$(jq -r .\""$pack"\".\"version\" "$jfile")
    currentDate=$(jq -r .\""$pack"\".\"date\" "$jfile")
    currentURL=$(jq -r .\""$pack"\".\"URL\" "$jfile")

  fi

  if [[ -z ${currentDate:+set} ]]; then
    currentVer=0
    currentDate="unk"
    currentURL="URL_unknown"
    echo "*** ERROR: No current version info for package $1 in local file $2"

  else
    fpack=$( _fancypack "$pack" 9 )
    fcver=$( _fancypack "v$currentVer" 3 )
    $verbose && echo "Found $fpack current installed version is ${fcver}, date ${currentDate}"

  fi

  export currentVer currentDate currentURL
}
export -f read_current_release_info


change_release_json() {   # $1 is a new release.json file, current/existing is found in ./release.json
  # Return true if track has changed from installed in new downloaded one OR local release.json does not (yet) exist
  local currentTrack newTrack

  if [ -e release.json ] && [ -e "$1" ]; then
    currentTrack=$(jq -r .\"release\".\"track\" release.json)
    newTrack=$(jq -r .\"release\".\"track\" "$1")
    [[ "$currentTrack" == "$newTrack" ]] && return "$fail"

  fi
  return "$success"
}
export -f change_release_json


#------------------------------------------- INSTALL AND UPGRADE SUPPORT ------------------------------------------
# Install / Upgrade WGSE package system(s). May cause a restart of the installer itself.
#  Needed by zinstall_common.sh and zinstall_stage2windows.sh so included in zcommon here

declare replace upgrade     # Using as our special boolean type
install_or_upgrade() {
  # $1 is package, $2 is verbose messaging (true or false)
  local -r zipfile="$1.zip"   # Temporary zip file name after download amd before extract
  local -r verbose="$2"
  local lzipdir=$zipdir destpath="." verdir longname current_json alpha4m_json vmesg checkVer start_mesg end_mesg

  echo

  # In install directory so paths relative to that
  case $1 in
    installer)  verdir=scripts/             ;  longname="Installer"           ;;
    program)    verdir=program/             ;  longname="Program"             ;;
    tools)      verdir=jartools/            ;  longname="Local Tools"         ;;

    reflib)     find_reflibdir
                verdir="$reflibdir"         ;  longname="Reference Library"   ;;

    bioinfo)    # Windows stage2 installer only; path local to the cygwin environment
                lzipdir="local"             ;  destpath=$(cygpath -u cygwin64/usr)    # Override defaults
                verdir=cygwin64/usr/local/  ;  longname="Bioinformatic Tools (cygwin)" ;;

    bioinfo-msys2)    # Windows stage2 installer only; path local to the msys2 environment
                lzipdir="ucrt64"            ;  destpath=$(cygpath -u msys2)           # Override defaults
                verdir=msys2/ucrt64/        ;  longname="Bioinformatic Tools (msys2)" ;;

    cygwin64)   # Windows only (not handled here, set as a reminder; See install_windows.bat)
                verdir=cygwin64/            ;  longname="Cygwin64"            ;;

    msys2)      # Windows only (not handled here, set as a reminder; See install_windows.bat)
                verdir=msys2/               ;  longname="Msys2"               ;;

    *)          echo "ERROR -- unknown package type $1"  ;  return            ;;
  esac

  latestVer=0
  currentVer=0 # Zero out for safety from previous runs

  # Get latest available version info
  get_latest_release_info "$1" "false"  # Sets three latest* variables for the package (& release_track if not yet set)

  # if (( latestVer <= 0 )); then
  if _verComp "$latestVer" "<=" 0 ; then
    echo "*** Missing WGSE package ""$longname"" latest version file; no update possible."
    export replace=false
    export upgrade=false # defaults going in; do / did nothing
    return

  fi
  # So latestVer valid at 1 or greater; so latestURL must be good and pointing to a valid package

  # Compare current to latest release info; decide what needs to be done.
  replace=false
  upgrade=false # defaults going in; do / did nothing
  if [[ -d "$verdir" ]]; then
    current_json="${verdir}$1.json"      # Originally named version.json, now $package.json
    alpha4m_json="${verdir}version.json" # Special for Alpha 4m only that has version.json files

    # Sets three current* variables based on JSON version file
    if [[ -e "$current_json" ]]; then
      read_current_release_info "$1" "$current_json" "$verbose" "-" # new package.json file

    elif [[ -e "$alpha4m_json" ]]; then
      read_current_release_info "$1" "$alpha4m_json" "$verbose" "4m"  # older version.json file

    else
      $verbose && echo "Updating Package ""$1"" (no JSON version file found)."
      currentVer=0   # Must be previous WGS Extract v3, v2, etc with no json file; so force upgrade

    fi

    # (( currentVer != 0 )) && vmesg="v${currentVer}" || vmesg="older release"
    _verComp "$currentVer" "!=" 0 && vmesg="v${currentVer}" || vmesg="older release"

    # Note: when user copies latest installer over existing release; it adds scripts/installer.json and release.json

    # Note: We changed reflib version numbering because we pulled its scripts out and put them into the program pack.
    # So version now reflects actual blob content of the reference/ folder; not previous program pack version.  Reflib
    # Version 35 is now known as version 5.  So specially handle its versions so upgrade performed as expected.

    # if (( 33 <= currentVer <= 35 && latestVer < 33 )); then
    if [[ "$1" == "reflib" ]] && _verComp 33 "<=" "$currentVer" && _verComp "$currentVer" "<=" 35 &&
       _verComp "$latestVer" "<" 33 ; then
      checkVer=0 # Force upgrade to lower version number that is actually newer

    else
      checkVer=$currentVer

    fi

    # if (( checkVer < latestVer )); then
    if _verComp "$checkVer" "<" "$latestVer" ; then
      echo "*** WGS Extract ""$longname"" v${currentVer} is installed but outdated."

      start_mesg="...  Started upgrading WGS Extract ""$longname"" from ${vmesg} ..."
      end_mesg="... finished upgrading WGS Extract ""$longname"" to v${latestVer}."
      replace=true
      upgrade=true

    else
      echo "*** WGS Extract ""$longname"" v${currentVer} is installed and the latest available."

    fi
  else
    echo "*** WGS Extract ""$longname"" v${latestVer} is not yet installed."

    # We assume that if no json file then no "upgrade"; only new / "replace" (Installer will be latest)
    start_mesg="...  Started installing WGS Extract ""$longname"" v${latestVer} ..."
    end_mesg="... finished installing WGS Extract ""$longname"" v${latestVer}."
    replace=true

  fi
  export replace upgrade    # Passing back state in globals

  # If no package to replace (no newer version), then can exit now
  ! $replace && return

  # Now upgrade / install a package
  echo
  echo "$start_mesg"

  curlx -o "$zipfile" "$latestURL" # Get the package from the internet to a local .zip

  # If package did not download properly, then exit now
  if [[ ! -e $zipfile ]] ; then
    echo "*** FAILURE when trying to download the package ""$longname"" v${latestVer}"
    return
  fi

  # Uncompress package (OS Specific)
  case $OSTYPE in
    msys* | cygwin*)
      powershell Expand-Archive -LiteralPath "$zipfile" -DestinationPath "$destpath" -Force  ;;
    darwin*) 7zz x -tzip -y "$zipfile" >/dev/null  ;;
    linux*)  7z  x -tzip -y "$zipfile" >/dev/null  ;;
  esac
  rmx "$zipfile"

  # If package did not uncompress properly, then exit now
  if [ ! -d "${destpath}/${lzipdir}" ]; then
    echo "*** ERROR: ${lzipdir} directory not created when expanding"
    echo "           ${zipfile} during package ""$1"" install"
    return
  fi

  # Package specific installation process (sometimes more than simply copying the contents)
  case $1 in

  installer)
    # We have a new installer but need to overlay it onto existing installer.

    # Handle release.json file (use new if we change tracks (or it does not exist yet); use override if it exists)
    if change_release_json "${lzipdir}/release.json" ; then
      [ -e release.json ] && mvx release.json release-saved.json # Preserve old file in case dev changed
      mvx "${lzipdir}/release.json" .

    else
      rmx "${lzipdir}/release.json"         # do not want to clobber local copy when we copy the whole lzipdir

    fi      #  guaranteed "${lzipdir}/release.json" no longer exists

    # If override release json exists, force a new release.json with it (even if the same track)
    if [ -e "${lzipdir}/release-override.json" ]; then
      [ -e release.json ] && mvx release.json release-overridden.json # Preserve old file in case user changed
      mvx "${lzipdir}/release-override.json" release.json

    fi
    #  Now guaranteed release.json exists and "${lzipdir}/release{,-override}.json" files no longer exist

    # *** Critical code area ; this script changes after cprx. So force a pre-read of critical section script code
    {
      cprx "$lzipdir"/* .                             # Simply copy everything including this script (overwrite)
      chmod a+x ./*.bat ./*.sh ./*.command scripts/*.sh # Should be set in zip; but just in case

      # Ending this current installer script as we are about to restart in a new script
      rmrx "$lzipdir"
      echo "$end_mesg"

      echo
      echo '*******************************************************************************'
      echo '*** Need to restart the WGSE v4 installer with the upgraded installer script.'
      echo '*******************************************************************************'

      readq 'Press any key to restart the WGSE installer ...'
      case $OSTYPE in

      msys* | cygwin*)
        $(cygpath "$COMSPEC") /c Install_windows.bat
        ;;

      darwin*)
        ${bashx} Install_macos.command
        ;;

      linux*)
        if [[ "$linux_type" == "micromamba" ]]; then
          ${bashx} Install_linux.sh "restart"
        else
          ${bashx} Install_ubuntu.sh
        fi
        ;;

      esac
      exit 10 # Exit this script with status 10 as we already restarted the new one
    }         # *** End of critical code area
    ;;        #  end of installer case / esac sub-section

  program)
    cprx "$lzipdir"/* . # Includes program/, open_source_licenses/, WGSExtract*, Library*, addtl scripts/ entries
    chmod a+x ./*.bat ./*.sh ./*.command scripts/*.sh
    ;;

  reflib)
    # Used to simply copy reference/ created from zipdir. But if user moved reflib, they may have renamed it, so ...
    mkdir -p "${reflibdir}/genomes"                     # Only makes reflibdir and subdir genomes if it does not exist
    cprx "${lzipdir}"/reference/* "$reflibdir"          # Copy content because dest may no longer be called reference/
    mvx "${reflibdir}00README_genomes.txt" "${reflibdir}genomes/"
    ;;

  tools)
    # Simply copy everything; easy addition of additional top level folders (current is yleaf, fastqc, jartools, etc)
    cprx "$lzipdir"/* .
    chmod a+x FastQC/*.bat FastQC/fastqc
    ;;

  bioinfo)              # Expanded zip file content directly into cygwin64/usr/local already; nothing more to do
    ;;

  bioinfo-msys2)        # Expanded zip file content directly into msys2/ucrt64 folder already
    mvx msys2/ucrt64/ucrt64* msys2      # Move the mintty driver shell into the top-level
    ;;

  cygwin64 | msys2 | *)   # cygwin64/msys2 is handled in the Install_windows.bat file; should not be seen here
    echo "*** ERROR (internal): Unexpected package type $1 during Install or Upgrade"
    ;;

  esac

  rmrx "$lzipdir"
  echo "$end_mesg"

  export replace upgrade
  #  echo "install or upgrade $1 $2: replace $replace, upgrade $upgrade"
}
export -f install_or_upgrade


#------------------------ SPECIAL NOTE ON UNCONVENTIONAL USE OF BASH pseudo-boolean technique -----------------------
# We employ an UNCONVENTIONAL use of a BASH pseudo-boolean technique
#  We can create pseudo boolean variables by assigning variables the strings "true" or "false".
#  We can then use the variables in an if statement as COMMANDS and or passed to "test", "[", or "[[ ]]"
#  Key is you are executing the commands "true" or "false" by expanding the string variable in a command
#  context; so the true or false command is executed.  e.g. bool="true" ; if $bool ; then ....
#  Strings "true" and "false" or the $variable can be double quoted or not; does not affect the result
#  One caveat: to pass the true or false string as a parameter to a function call it MUST be quoted to
#  not get evaluated and passed as a numeric. BASH built-in true is the same as a function defined as
#  "true() { exit 0 }". Ditto for for false built-in except it has an exit code of 1.
#
#  Simple if-then-else works as expected:
#     bool=true  ;  $bool && echo true || echo false   # prints true
#     bool=false ;  $bool && echo true || echo false   # prints false
#
#  So use variables such as: success, exists, upgrade etc as booleans without an explicit comparison.  For example:
#    sucess=true
#    if $success ; then ...
#    $success && do_on_success
#    ! $success && do_on_fail

#  This allows us to use the shortcut statements of BASH more clearly and effectively; as shown above.
#
#  If more than one test to do, use brackets or braces:
#     [[ $bool1 && $bool2 ]] && do_true || do_false  yields do_true if both bool's true; else yields do_false
#     { $bool1 || $bool2 ; } && do_true || do_false  yields do_true if a bool is true; else yields do_false
#  Just remember that the if test in if-then-else must be treated as one group to get the if-then-else behavior
#  Same goes for do_true and do_false; enclose multiple commands in braces or use a traditional if-then-else
#  Remember that when using braces, even if only a single command, you always need a trailing semicolon (;).
#  Semicolon is a terminator, not a separator in BASH. Ditto in if conditional tests, for loops on one line, etc.
#
#  Another more complicated form (if-then with embedded if-then-else):
#     $bool && { $bool2 && do_true || do_false ; }  will not do anything if $bool is false else do simple if-then-else
#  Remember, you always need a semicolon before a closing brace. Even when only a single statement like here.
#
#  Braces can be embedded in braces:
#   false && { false && {  true && echo true2 || echo false2 ; } || echo false1 ;}   does nothing
#    true && { false && {  true && echo true2 || echo false2 ; } || echo false1 ;}   prints false1
#    true && {  true && {  true && echo true2 || echo false2 ; } || echo false1 ;}   prints true2
#    true && {  true && { false && echo true2 || echo false2 ; } || echo false1 ;}   prints false2

# There is much written about the incorrect use or limitation of a && b || c instead of an if-then-else.  Namely,
# if the "then" part of the if-then-else results in a false return value, then the "else" will be executed.  Which is
# not a desired behavior.  If doing a code block with the potential for a bad return call in the "then" section,
# then just end the code block with a "|| true" statement to assure the block always succeeds. Shellcheck requires this
# for commands like cd, mv, cp, etc anyway.
#
# Another variation is using numeric values instead of strings:
#    strue=1; sfalse=0; bool=$strue ; if ((bool)); then do_true
#  But this can be confusing as the process return value is opposite the falsey / truthy. ((0)) is false but process
#  return on success is 0 which is true.  So must think of $? being the equivalent of true if "failed". So not a very
#  good solution; in our opinion.
#
