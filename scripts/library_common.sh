#!/usr/bin/env bash
# WGS Extract v4 Library implementation scipt (all platforms)
# Copyright (C) 2021-2023 Randolph Harr
#
# Subset of function previously in get_and_process_refgenomes.sh. Simplified to be just the UI portion of the Library
#  command now. Rest of old script in get_and_process_refgenome.sh (singular). Reads in (relies on being available) the
#  genomes.csv file in the reference/genomes/ (library) folder.
#
# Part of the Reference Genome management in WGS Extract (https://wgsextract.github.io/)
#

#---------- Script called by OS dependent wrapper; Shell independent (POSIX) code till verify BASH --------------------
[[ ":$PATH:" != *":/usr/bin:"* ]] && PATH="/usr/bin:${PATH}" && export PATH     # Cygwin starts with no environment

cursh="$(ps -p$$ | tail -1 | grep -o 'bash')"   # Get shell from process stats; determine if BASH (best solution)

if (( $# != 1 )) || (return 0 2>/dev/null) || [ "$cursh" != "bash" ]; then
  printf "Usage: %s { install_dir }\n" "${BASH_SOURCE[0]##*/}"
  printf "  The Library command to download and process Reference Genomes.\n"
  printf "  Only called internally by OS specific wrappers.\n"
  (return 0 2>/dev/null) && return || exit
fi

#---------------------------------- Setup common environment ------------------------------------------------------

if [[ -z $wgse_FP ]] ; then
  # Find the installation directory
  declare -x wgse_FP
  _wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
  _wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
  [[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

fi

cd "$wgse_FP" || true

if ! declare -f _perform_rmx > /dev/null ; then
  declare reflibdir currentVer
  declare -f cdx find_reflibdir get_and_process_refgenome >/dev/null
  source scripts/zcommon.sh "$wgse_FP"        || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }

fi


find_reflibdir  # Sets reflib with value from settings or the default installation location if not set
cdx "${reflibdir}genomes/"

read_current_release_info reflib "${reflibdir}reflib.json"  > /dev/null   # Supress found message

# Read in genomes.csv file and transpose rows to columns; sets one array variable per column
declare -a menopt   # pytcode[], source[], finalf[], initf[], gurl[] ; last sncnt[], snnam[], descr[] not used
read_genomes_file
# menopt[] has the Library menu options (first entry is header / title to be ignored)

# We have added the options for both USA NIH and EU EBI server access. Some have better luck with one or the other.
# Suspect it is jitter / latency; especially on a wireless connections.  But not enough data to characterize it yet.
echo
echo "--------------------------------------------------------------------------------"
echo "WGS Extract Reference Library REFERENCE GENOME Installation and Update"
echo "--------------------------------------------------------------------------------"
echo "Version ""${currentVer}"" located at ""${reflibdir}"""
echo "[See the Users Manual for more information about these Reference Genomes]"
echo "You can run the WGS Extract program while a Reference Genome is downloading."
echo

PS3='Choose which Reference Genome(s) to process now (1 to Exit): '
option=( "Exit" "Recommended (@US NIH)" "Recommended (@EU EBI)" "${menopt[@]:1}" )

#  We only redisplay the menu after every 3 downloads; when menu will likely scroll off the screen. So keep track.
declare -i menu_cnt
menu_cnt=0

select rg in "${option[@]}"; do
  case $rg in
    "Exit")
      echo "Exiting the WGS Extract Reference Genome Library script."
      break
      ;;

    "Recommended (@US NIH)")
      for ((i=1 ; i<${#menopt[@]} ; i++)); do    # Go through all the menu options added by genomes.csv
        if [[ "hs38 (Nebula) (@NIH) (Rec)" == "${menopt[$i]}" ||
              "hs37d5 (Dante) (@NIH) (Rec)" == "${menopt[$i]}" ||
              "T2T_v2.0 (PGP/HPP chrN) (Rec)" == "${menopt[$i]}" ]]; then
          get_and_process_refgenome "$i"
          menu_cnt+=1
        fi
      done
      echo "Finished with Recommended (@US NIH)."
      ;;

    "Recommended (@EU EBI)")
      for ((i=1 ; i<${#menopt[@]} ; i++)); do    # Go through all the menu options added by genomes.csv
        if [[ "hs38 (Nebula) (@EBI) (Rec)" == "${menopt[$i]}" ||
              "hs37d5 (Dante) (@EBI) (Rec)" == "${menopt[$i]}" ||
              "T2T_v2.0 (PGP/HPP chrN) (Rec)" == "${menopt[$i]}" ]]; then
          get_and_process_refgenome "$i"
          echo
          menu_cnt+=1
        fi
      done
      echo "Finished with Recommended (@EU EBI)."
      ;;

    *)    # Main menu is not static (read from genomes.csv) so need to loop through list to find match (if at all)
      found=false
      for ((i=1 ; i<${#menopt[@]} ; i++)); do    # Go through all the menu options added by genomes.csv
        if [ "$rg" == "${menopt[$i]}" ]; then    # If we find the match, use the index to call script to process
          get_and_process_refgenome "$i"
          menu_cnt+=1
          found=true
          break
        fi
      done

      if [ "$found" == false ]; then
        echo
        echo "Please enter a valid option (emter 1 to exit)"
      fi
      ;;
  esac

  echo

  if (( menu_cnt > 2 )); then
    # Cause the menu to be redisplayed again before the prompt
    REPLY=""
    menu_cnt=0
  fi

done
echo "Finished installing and processing Reference Genomes."
