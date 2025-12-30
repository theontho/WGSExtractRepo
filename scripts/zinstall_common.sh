#!/usr/bin/env bash
# WGS Extract v4 in-place common install script (all platforms; was Upgrade_UbuntuLinux.sh in v3)
# Copyright (C) 2021-2023 Randolph Harr
# Copyright (C) 2023 Aaron Ballagan
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

# We try to do OS specific stuff in the OS main installer before calling this common installer.
# Serves as a first-time install, upgrade from v2 to v3 to v4, as well as minor release updater (re-entrant)
# Cleans out old release files from v3 and v2 that are no longer used.
# Will fill in any missing reference genomes by user request at the end IF a Fresh install

# echo Using Shell `ps -p $$ | grep -v PID | xargs | cut -d" " -f4`

# sourcing zcommon below will likely override these values passed in
cpu_arch="$1"
osver="$2"

# We purposely pass in some parameters that we could easily figure out; just to keep user from running by accident
if (( $# != 3 )) ; then
  printf "Usage: %s arch maj.min\n" "${BASH_SOURCE[0]##*/}"
  printf "  arch is either arm64 or x86_64.  maj.min is the major & minor OS release version.\n"
  printf "This should only be called internally from a WGSE OS-specific install script.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

[ -d micromamba ] && linux_type="micromamba" || linux_type="ubuntu"
# Note: not needed with cygwin64/msys2 because the OSTYPE indicates that properly.

if ! declare -f _perform_rmx > /dev/null ; then
  # Common environment setup for scripts here; sets some variables used later so we declare first so shellcheck knows set
  declare cpu_arch osver replace upgrade reflibdir bashx process_refgenomes
  declare -i fail success
  declare -f rmrx rmx mvx cdx install_or_upgrade > /dev/null
  source scripts/zcommon.sh "$wgse_FP"            || { echo "ERROR: Cannot source scripts/zcommon.sh" ; exit 1 ; }
fi

# ------------------------------------------- PYTHON PIP CALLS --------------------------------------------
# Setup Python libraries we need (universal except for way to invoke pip)
# On MacOS, we are finding some cases where PIP uses the wrong arch; so have to explicitely set to override

pip_install() {
  # Setup as a function now so can more easily bypass when not needed

  echo
  # '======================================================================================================'
  echo "*** Installing or Upgrading the Python 3.x libraries on ${OSTYPE}:$1"
  echo '    ... see the file temp/pip_install.log for details'

  # List of modules / packages / libraries to install and use in Python
  libs=( Pillow pyliftover pyscreenshot openpyxl pandas psutil multiqc "wakepy>=0.8" )
  # bio (brings biopython, numpy, requests urllib3), pyfaidx, pysocks, pySam (python v2 only), elevate
  # note: tkinter must be installed at an OS package level and not via PIP here

  export PIP_BREAK_SYSTEM_PACKAGES=1    # New in Python 3.11+ to allow for local and system environment like MacOS

  # Any command line options needed ; setup pip command for the particular OS / Architecture
  opts=( --no-warn-script-location )
  pip=()

  # Check for /usr/local/bin/pip3 first, otherwise use platform-specific paths
  if [[ "${OSTYPE}" == darwin* ]]; then
    libs+=( tkmacosx ) # MacOS extra package for tkinter colored buttons
    opts=()
      custom_pip_path="/usr/local/bin/pip3"
      arch_arg=$([ "${cpu_arch}" = "arm64" ] && echo "-arm64" || echo "-x86_64")
      homebrew_pip_path=$([ "${cpu_arch}" = "arm64" ] && echo "/opt/homebrew/bin/pip3.11" || echo "/usr/local/Homebrew/bin/pip3.11")
      chosen_pip_path=$([ -x "${custom_pip_path}" ] && echo "${custom_pip_path}" || echo "${homebrew_pip_path}")
      
      if [ -x "${custom_pip_path}" ] ; then
        pip=( arch "${arch_arg}" "${chosen_pip_path}" )
      elif [ -x "${homebrew_pip_path}" ]; then
        pip=( "${homebrew_pip_path}" )
      else
        # Last resort: just try pip3
        pip=( pip3 )
      fi
  else
    case "${OSTYPE}:${cpu_arch}:${osver}" in    # MacOS passes arch as first arg; major/min version as 2nd; Ubuntu major as first
      darwin*) ;; # Do nothing since we dealt with MacOS above
      linux*:x86_64:18*)        pip=( sudo -H python3 -m pip )      # 18.x Ubuntu pip errors; cannot use sudox function call
                                  opts=()  ;;                       # no-warn... not recognized in 18.x Ubuntu pip
      linux*:x86_64:20* | \
      linux*:x86_64:22* | \
      linux*:x86_64:24*)        pip=( pip3 )  ;;
      linux*:aarch64:20* | \
      linux*:aarch64:22* | \
      linux*:aarch64:24* | \
      linux*:arm64:20* | \
      linux*:arm64:22* | \
      linux*:arm64:24*)        pip=( pip3 )  ;;
      linux*:x86_64:micromamba) pip=( pip3 )        # Make sure to save cache files within micromamba environment directory
      # shellcheck disable=SC2206
      opts+=( --cache-dir "${wgse_FP}/micromamba/cache/pip" $VERBOSE )  ;;
      linux*:aarch64:micromamba | \
      linux*:arm64:micromamba) pip=( pip3 )        # Make sure to save cache files within micromamba environment directory
      # shellcheck disable=SC2206
      opts+=( --cache-dir "${wgse_FP}/micromamba/cache/pip" $VERBOSE )  ;;
      msys*:x86_64:* )          pip=( msys2/ucrt64/bin/python -m pip ) ;;   # In bioinfo folder; not on main path
      cygwin*:x86_64:*)         pip=( python/python.exe -m pip )  ;;  #  pip3 requires python/, python/scripts be on PATH
      *)  echo "*** Error: unknown OS:ARCH:VER combination of ${OSTYPE}:${cpu_arch}:${osver}"
          (return 0 2>/dev/null) && return 1 || exit 1  ;;
    esac
  fi

  # Make sure temp/ folder and pip_install.log file are there and ready (permission issues on cygwin64 again)
  [ ! -e temp ]  &&  mkdir temp  &&  chmod 777 temp
  piplog="./temp/pip_install.log"  &&  touch "$piplog"  &&  chmod 664 "$piplog"

  # We use GREP to remove the common success strings on the many packages and dependencies.  Slims down the output.
  # Note: BRE as cannot get ERE / PRE in all platforms (most notably MacOS without MacPorts version)
  strip='^Requirement already satisfied\|^Collecting\|Obtaining\|Preparing\|Running\|Downloading\|Installing\|Getting'
  strip+='\|Using legacy\|Using cached\|Building\|Created\|Stored\|Successfully built\|━━━━\|-----'

  # Start by updating PIP if needed (cannot use single array or string)
  "${pip[@]}" install --upgrade pip "${opts[@]}" | tee -a "$piplog" | grep -v "$strip"

  # Now process list of modules / packages / libraries
  "${pip[@]}" install "${libs[@]}"  "${opts[@]}" | tee -a "$piplog" | grep -v "$strip"

  # Todo MultiQC has bug with Windows release; cannot run from different disk than files it operates on
  #   so need to patch the python code in the library to get around / enable.
  #   See https://gitter.im/ewels/MultiQC?at=622591f9ddcba117a20d53d4

  echo '    ... finished upgrading the Python 3.x libraries'
}

if [[ ! $OSTYPE =~ "msys" ]] ; then
  pip_install "$1"
fi


# ----------------------------------- WGSExtract Package Installs / Upgrades -------------------------------------
# NOTE: in v4, pulled the Reference Library out to a seperately installed, versioned ZIP. No longer use a full ZIP.
#  Microarray templates moved into the Reference Library as well. Also moved yLeaf, Haplogrep and FastQC to a
#  seperate tools ZIP to further conserve downloads on updates.  The reference library and tools tend to be more
#  static. Each ZIP has its own version json file to control when it gets updated. Finally, the installer itself
#  is given a version file so we can restart the installer if the installer is updated.

# '======================================================================================================'
# Check and Upgrade WGS Extract installer scripts; if needed
install_or_upgrade installer "false"

# '======================================================================================================'
# Check and Install or Upgrade WGS Extract Reference Library templates and scripts files; if needed
install_or_upgrade reflib "false"

# '======================================================================================================'
# Check and Install or Upgrade WGS Extract local tools (yLeaf, FastQC, jartools/haplogrep, etc); if needed
install_or_upgrade tools "false"

# '======================================================================================================'
# Check and Install or Upgrade main WGS Extract program scripts; if needed
# run_library=false
install_or_upgrade program "false"
# $replace && ! $upgrade && run_library=true
# replace, upgrade and run_library are our special pseudo-boolean types. See note in zcommon.sh

rmx latest.json    # Now retained between calls to install_or_upgrade as a common file between packages


# -------------------------------- WGSExtract Clean-up from Previous Releases ----------------------------------

echo
echo '================================================================================'
echo 'Cleaning up from any previous releases'


# =============================================================================================================
# WGS Extract v2 to v3 upgrade special operations

# Handle removing old start / install scripts: 2b release and patches

# Avoiding compiled Applescript due to Translocation issues and Apple not allowing distribution outside signed app
rmrx Install_MacOSX.app Start_MacOSX.app Uninstall_MacOSX.app
rmx Install_MacOSX.scpt Start_MacOSX.scpt Uninstall_MacOSX.scpt

# renamed to just MacOS due to BigSur 11 and renamed .sh to .command for easier click-start
rmx Install_MacOSX.sh Start_MacOSX.sh Uninstall_MacOSX.sh

# Changed all OS specific START files to WGSExtract.xxx and changed from .sh to .command on MacOS
rmx Windows_START.bat MacOS_START.sh Linux_START.sh

rmx 00README.txt "WGSE Betav3 Release Notes.txt" set_WGSEpath.bat
rmx Upgrade_v2tov3.command Upgrade_v2tov3.sh Upgrade_v2tov3.bat

rmx WGSExtractv2b_Francais_Patch.zip WGSExtractv2b_MacOSX_Patchv3.zip WGSExtractv2b_MacOSX_Patchv4.zip

# Finished with saving files from the old 2b programs/ folder; we can now remove it
[ -d programs ] && rmrx programs    # Removes old Win10 binaries as well

# Some old releases delivered corrupted ACLs for temp; so lets try to correct for that
[ -d temp ] && rmrx temp
mkdir temp || true
chmod a+rwx temp

#
# In v2 to v3, change from reference_genomes folder to reference/genomes as default. But we also use the relocated
# reference library location if it exists (should not if v2 to v3 but would if v2 to v4 or later)
#

# Move v2 Reference Genomes to new v3 area (the only reference items saved from v2 release)
# Should be guaranteed reference/genomes in installation. But just in case v4 settings file exists to change it ...
newlib="${reflibdir}/genomes/"      # As opposed to simply reference/genomes
if [[ -d reference_genomes && -d "$newlib" ]]; then
  (
    cdx reference_genomes || echo '***Internal ERROR: cd reference_genomes'
    echo '*** Saving existing reference genomes from v2 release ...'
    [ -f hg38.fa.gz ] && [ ! -f "${newlib}hg38.fa.gz" ] && \
      echo Moving hg38 && mvx hg38.fa.gz "$newlib"
    [ -f hs37d5.fa.gz ] && [ ! -f "${newlib}hs37d5.fa.gz" ] && \
      echo Moving hs37d5 && mvx hs37d5.fa.gz "$newlib"
    [ -f GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz ] && [ ! -f "${newlib}hs38.fa.gz" ] && \
      echo Moving hs38 && mvx GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz "${newlib}hs38.fa.gz"
    [ -f human_g1k_v37.fasta.gz ] && [ ! -f "${newlib}human_g1k_v37.fasta.gz" ] && \
      echo Moving human_g1k_v37 && mvx human_g1k_v37.fasta.gz "$newlib"
    [ -f hg19.fa.gz ] && [ ! -f "${newlib}hg19_wgse.fa.gz" ] && \
      echo Moving hg19_wgse && mvx hg19.fa.gz "${newlib}hg19_wgse.fa.gz"
  )
  rmrfx reference_genomes
  echo '... saved needed reference files. Removing v2 release reference genomes directory.'


  echo '*** Processing reference genomes for new reference library format'
  (
  cdx "$newlib" || echo "***Internal ERROR: cd $newlib"
  "$bashx" "$process_refgenomes" hg38.fa.gz hs37d5.fa.gz hs38.fa.gz human_g1k_v37.fasta.gz hg19_wgse.fa.gz
  )
  echo

fi


# =============================================================================================================
# WGS Extract v3 to v4 upgrade special operations (and mid-v4 changes)

# Rename of actual Reference Genomes files between versions v3, v4, etc
(
  cdx "${reflibdir}genomes"
  if [ -f "${reflibdir}genomes/chm13_v2.0.fna.gz" ]; then # Location can be changed by user
    echo '*** Renaming T2T CHM13 reference genome to new standard'
    mvx chm13_v2.0.fna.gz chm13v2.0.fa.gz
    rmx chm13_v2.0*
    "$bashx" "$process_refgenomes" chm13v2.0.fa.gz
  fi
  if [ -f "${reflibdir}genomes/hg19_wgse.fa.gz" ]; then
    echo "*** Deleting hg19_wgse reference genome as in error and outdated"
    rmx hg19_wgse*
  fi
)

# Cleanup any v3 to v4 file changes

rmx WGSE_Betav3_Release_Notes.txt 00README_WGSEv3.txt     # Was left hanging around in v3 release by accident
rmx samtools.exe.stackdump                                # Accidently left in an early Alpha v4 release
# rmx jartools/GenomeAnalysisTK.jar jartools/picard.jar   # Distributed in v3 but never used. Will leave for now.
rmx Start_* Upgrade_* Install_UbuntuLinux.sh Install_Win10.bat
rmrx win10tools program/microarray               # Replaced with cygwin64 and reference/microarray; respectively
rmx WGSE_Betav4_Release_Notes.txt                # Dropped WGSE_ prefix on 27 June 2022 (mid-Alpha 4l)
rmx zcommon.sh zinstall_common.sh zinstall_stage2windows.sh zxterm.sh          # moved on 27 June 2022 to scripts/
rmx program/version.json reference/version.json jartools/version.json          # renamed to $package.json
rmx cygwin64/version.json cygwin64/usr/local/version.json                      # renamed to $package.json
rmx make_release.txt                                       # Accidently left in v3 top level after install
rmx WGSExtract.sh Library.sh                               # Old Ubuntu scripts before dual ubuntu / linux
rmx ./*_Linux.sh scripts/*_Linux.sh                        # Original generic Linux scripts (upper case L)

(
  cdx scripts
  rmx zprocess_refgenomes.sh zget_and_process_refgenomes.sh zcompare_refgenomes.sh  # removed added z from name
  # rmx get_and_process_refgenome.sh        # back to v3 name for script; new will overlay old
  rmx make_release.sh make_release.txt      # Only needed by developers; not end users
)

(
  cdx "$reflibdir"
  rmx genomes/*.sh           # Moved to scripts/ or deleted
  rmx TruSeq_Exome_TargetedRegions_v1.2_GRCh.bed xgen_plus_spikein.GRCh38.GRCh.bed  # renamed
)


# -------------------------------- WGSExtract Final Clean-up ----------------------------------
# We now remove files for OSs that are not installed here; leaving only one OS set of scripts
case $OSTYPE in
  darwin*)
    cpx installer_scripts/WGSExtract.command installer_scripts/Library.command .
    rmx ./*_ubuntu.sh scripts/*_ubuntu.sh
    rmx ./*_linux.sh scripts/*_linux.sh
    rmx ./*.bat scripts/zinstall_stage2windows.sh  ;;

  linux*)
    # Only the linux releases have overlapping extensions and so need WGSExtract and Library files renamed
    if [[ "$linux_type" == "micromamba" ]]; then
      cpx installer_scripts/WGSExtract_linux.sh installer_scripts/Library_linux.sh .
      rmx ./*_ubuntu.sh scripts/*_ubuntu.sh
      for file in Library_linux.sh WGSExtract_linux.sh; do [ -f $file ] && mvx $file ${file/_linux} ; done
    else    # Our historic Ubuntu release (before we had the generic Linux release)
      cpx installer_scripts/WGSExtract_ubuntu.sh installer_scripts/Library_ubuntu.sh .
      rmx ./*_linux.sh scripts/*_linux.sh
      for file in Library_ubuntu.sh WGSExtract_ubuntu.sh; do [ -f $file ] && mvx $file ${file/_ubuntu} ; done
    fi
    rmx ./*.bat scripts/zinstall_stage2windows.sh
    rmx ./*command ;;

  msys*)
    cpx installer_scripts/WGSExtract.bat installer_scripts/Library.bat .
    # rmrx cygwin64 python
    rmx ./*_ubuntu.sh scripts/*_ubuntu.sh
    rmx ./*_linux.sh scripts/*_linux.sh
    rmx ./*command scripts/*_macos.sh ;;

  cygwin*)
    cpx installer_scripts/WGSExtract.bat installer_scripts/Library.bat .
    # Leave msys installer in case user wants to switch
    # rmrx msys2
    rmx ./*_ubuntu.sh scripts/*_ubuntu.sh
    rmx ./*_linux.sh scripts/*_linux.sh
    rmx ./*command scripts/*_macos.sh ;;
esac

# Return to the OS platform specific master installer that called this scrupt for any final word
