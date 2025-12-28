#!/usr/bin/env bash
# WGS Extract v4 in-place common scipt startup (Linux specific)
# Copyright (C) 2021-2024 Randolph Harr, Aaron xxx
#
# Mainly used for install_macos.command and uninstall_macos.command. Adds functions in common such as macports
# install and uninstall, python uninstall, etc.
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

if (( $# != 1 )) || ! (return 0 2>/dev/null) || [[ ! -d "$wgse_FP" ]]; then
  printf "Usage: source %s { logfile_prefix } \n" "${BASH_SOURCE[0]##*/}"   # basename may not be available
  printf "  This script should only be sourced from internal scripts after zcommon.sh.\n"
  printf "  Logfile name is logfile_prefix after adding the underscore date and .log suffix.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

# Local setup for the Micromamba Linux install
date_time=$(date +%d%m%y_%H%M%S)
logfile="$1_${date_time}.log"

log_FP="${microdir}/${logfile}"

microbase="$(basename "$microdir")"
log_short="$microbase/$logfile"

export log_short log_FP logfile date_time

# Initialize and activate the micromamba base environment.
# This code must be repeated in all WGSE linux scripts that use micromamba
# The micromamba start cannot be done here as the installer needs this script before micromamba is installed
#
# declare -f micromamba >/dev/null
# eval "$( "$micromambax" shell hook -s bash --prefix "$microdir" )"
# micromamba_abort "Failed to init micromamba shell"
#
# micromamba activate --prefix "$microdir"  # 2>&1 | echo_tee      # redirection does not seem to work here?
# micromamba_abort "Failed to activate micromamba"
#
# micromamba update -y -a &>/dev/null


#-------------------------------------- Common Functions Defined -------------------------------------
# Todo move to zcommon and use in other scripts (have pip log to a file in zinstall_common.sh already)
echo_tee() {      # if $* exists, echo each to stdout. Otherwise echo stdin. If logfile exists, tee to there.
  # Prints message(s) to stdout AND appends them to a logfile.  Input is either via parameters or stdin (pipe)
  # Presumes stderr has been redirected into stdout to capture errors into the logfile

  # We filter out common lines going to stdout that are generated in micromamba verbose mode; only sending to a logfile
  # Note: we are not trying to filter out legitimate error messages; just the verbose status ones
  # Use BRE; not ERE or PRE which is not available everywhere (MacOS in particular). Spaces important.
  local mambafilter
  mambafilter='^$\|^───\|^info\|^Trans\|^Link\|^To \|^Or \|^Pinn\|^Chan\|^conda\|^bioconda'
  mambafilter+='\|^  + \|^  -\|^  Pref\|^  Up\|^  Pack\|^  Inst\|^  Summ\|^  Tot\|^   - \|^    micro'

  # if $# == 0, then use tee to read stdin.  Otherwise, message in args: echo $*
  # could use grep -f - instead of tee when no logfile, but chose tee for a consistent look

  if [[ -e "$log_FP" ]] ; then        # Log file exists, tee there first before filtering to put back out to stdout
    # shellcheck disable=SC2015
    (( $# == 0 )) && { tee -a "$log_FP" | grep -v "$mambafilter" || true ; } || \
                     { echo "$*" | tee -a "$log_FP" | grep -v "$mambafilter" ; }

  else                                # No logfile, so just filter and put to stdout
    # shellcheck disable=SC2015
    (( $# == 0 )) && { tee | grep -v "$mambafilter" || true ; } || \
                     { echo "$*" | grep -v "$mambafilter" ; }

  fi
}
export echo_tee


echo_log() {
  # Like echo_tee except only to the logfile; not to stdout also. No filter. Allows reporting strictly to logfile.
  if [[ -e "$log_FP" ]] ; then
    # shellcheck disable=SC2015
    (( $# == 0 )) && { tee >> "$log_FP" || true ; } || \
                     { echo "$*" >> "$log_FP" ; }

  fi
}
export echo_log


echo_fnl() {
  # We are filtering blank lines from the stdout in echo_tee. So need a way to force newlines
  echo_log ""  ;  echo
}
export echo_fnl


askyesno() {
  # May be called before logfile setup (early stages of setup); more than just readq as echos Q&A to logfile
  readq "$1"    # readq does all query output to the users terminal only (stdout)

  if [[ -e "$log_FP" ]] ; then        # Q&A already in stdout; just need into the logfile (if exists)
    echo_log ""
    echo_log "$1  $REPLY"
    echo_log ""

  fi
}
export askyesno


error_exit() {
  # General exit on error. Prints all messages to stderr instead of stdout (and tee to the logfile)
  # Prints first parameter / string prepended by *** ERROR:. Rest as supplied each on their own line
  # Waits for query answer from the user before finally exiting.
  local mesg

  # shellcheck disable=SC2015
  [ -z "$1" ] && { mesg="internal -- error_exit without message" || true ; } || { mesg="$1" ; shift ; }

  echo_tee   "" 1>&2
  echo_tee   "*** ERROR: $mesg" 1>&2

  while [ -n "$1" ] ; do
    echo_tee "           $1" 1>&2       # Spaces important to indent remaining lines after first ***ERROR:
    shift
  done

  echo_tee   "" 1>&2

  askyesno "Hit any key to exit ..."    # Query to user goes to stdout (and log file); not stderr
  exit 1
}
export error_exit


#--------------------------- Common Functions Defined (Micromamna specific) ---------------------------
#
initialize_microdir() {
  # setup microdir if not already there
  mkdir -p "${microdir}/" # Want it to exist for logfile

  # Initialize log file in microdir if not already there
  if [[ -e "${wgse_FP}/${logfile}" ]] ; then      # If a previous run logfile then move it back in place
    mvx "${wgse_FP}/${logfile}" "$log_FP"

  else
    touch "$log_FP"

  fi
}
export initialize_microdir


delete_microdir() {
  cdx "$wgse_FP"            # Make sure not in the microdir
  mvx "$log_FP" "$wgse_FP"  # move the logfile out of the micromamba directory before deleting
  rmrx "$microdir"          # remove the micromamba directory (fully)

}
export delete_microdir


micromamba_abort() {
  # Aborts script if an error is found in the logfile or returned by the last called commaned before entry here
  # Presumes stderr is redirected into logfile to find issues
  local abort=false

  (( $? == 1 )) && abort=true
  [[ -e $log_FP ]] && grep -qP 'numpy/[core,typing]/tests|error|critical|problem|aborting' "$log_FP" && abort=true

  if $abort ; then
    micromamba deactivate

    # delete_microdir     # prevents renetrant installer on error; desired?

    if [[ -n "$1" ]] ; then
      error_exit "$1"

    else
      error_exit "A problem occured in the $1 script. Aborting further activity." \
                 "Check the log file for specifics if not displayed above."

    fi
  fi
}
export micromamba_abort
