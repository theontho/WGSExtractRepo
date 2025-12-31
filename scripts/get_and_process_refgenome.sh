#!/usr/bin/env bash
#
# Subset of function previously in get_and_process_refgenomes.sh. Simplified to be just download and process one
#  reference genome model. Parameter must match init/final filename listed in reference/genomes/genomes.csv
#  Interactive, menu query to support Library command moved to library_common.sh.
#  Main functionality moved to get_and_process_refgenome() function in zcommon.sh
#
# Only used in python reference_library.py now. Library_common uses get_and_process_refgenome() function.
#
# Todo Change to a Python function and make a Reference Library manager tab in the main program.
#
# Part of the Reference Genome package in WGS Extract (https://wgsextract.github.io/)
# Copyright (c) 2021-23 Randy Harr
#

if (( $# < 1 || $# > 2 )) ; then
  printf "Usage: %s RefGenomeFile [NIH|EBI]\n" "${BASH_SOURCE[0]##*/}"
  printf "  Downloads and processes the requested reference genome file listed in genomes.csv\n"
  printf "  Allows a preferred reference model server to be specified."
  printf "  Normally only called internally by the WGS Extract program.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

#---------------------------------- Setup common environment ------------------------------------------------------

[[ ":$PATH:" != *":/usr/bin:"* ]] && PATH="/usr/bin:${PATH}" && export PATH     # Cygwin starts with no environment

if [[ -z $wgse_FP ]] ; then
  # Find the installation directory
  declare -x wgse_FP
  _wgsedir=$(dirname "${BASH_SOURCE[0]:-$0}")       # Get the (calling) script location to determine the install directory
  _wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
  [[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

fi

cd "$wgse_FP" || true

if ! declare -f _perform_rmx > /dev/null ; then
  declare pythonx owgse_FP
  declare -f cdx mvx rmx readq _perform_rmx > /dev/null
  source scripts/zcommon.sh "$wgse_FP"        || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

fi

# -----------------------------------------------------------------------------------------------------------------
# Sets reflib with value from settings or the default installation location if not set
find_reflibdir

cdx "${reflibdir}/genomes/"

# -----------------------------------------------------------------------------------------------------------------
# Read in genomes.csv file and transpose rows to columns; sets one array variable per column
declare -a source finalf     # First pytcode[]; last initf[], gurl[], menopt[], sncnt[], snnam[], descr[] not meeded
read_genomes_file

# -----------------------------------------------------------------------------------------------------------------
# The second parameter is the preferred server (NIH vs EBI).  Reference Genomes with an alternate will be marked with
#  a source[] field of NIH-Alt or EBI-Alt. The idea is, if we prefer NIH, then do not select an EBI-Alt model. If EBI,
#  then do no select an NIH-Alt model.  Any other value of source is a unique server and acceptable.
notsource="none"
if (( $# == 2 )) ; then
  [[ "$2" == "NIH" ]] && notsource="EBI-Alt"
  [[ "$2" == "EBI" ]] && notsource="NIH-Alt"
fi

# -----------------------------------------------------------------------------------------------------------------
# Go through all the file names in genomes.csv looking for this file (from the preferred server; if applicable)
for ((j=1 ; j<${#finalf[@]} ; j++)); do
  if [[ "$1" == "${finalf[$j]}" && "$notsource" != "${source[$j]}" ]]; then
    # If we find the match and the preferred source, use the index to get other array variables
    get_and_process_refgenome "$j"
    (return 0 2>/dev/null) && return || exit
  fi
done

echo "***ERROR Reference Genome File $1 not found in genomes.csv"
