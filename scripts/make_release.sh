#!/usr/bin/env bash
# WGS Extract script to make release ZIP Archives
# Copyright (C) 2021-24 Randolph Harr
#
# We create ZIPs using MacOS Ditto from BOM's to create the archives.  Apple only trusts ZIPs made with Ditto.
#
# There are two major steps to this process:
#   (1) Make a BOM for the particular package, then
#   (2) make the ZIP archive file from that BOM for that package
# Installer packages are special in that they include the release*json file(s) and make the latest-release file
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

# Todo move the reference/genomes folder up to the top level.  Make it created during the program package install.
#   the seed_genomes.csv is already in the program/ folder.  The reference library move and its corresponding setting
#   should only move the genomes/ folder. The reference library should stay in place.

jqURL="https://github.com/jqlang/jq/releases/download/jq-1.7/jq-macos-arm64"  # needed if MacPorts not installed

# releaseURLbase="https://raw.githubusercontent.com/WGSExtract/WGSExtract-Dev/master/" # v3, v4
releaseURLbase="https://get.wgse.io"   # Changed to wgse.io in v4.44 installer

# onedrive_smb="smb://randy-pc2/D/"
# onedrive_mnt="/Volumes/D"
onedrive_mnt="/Users/Randy"
onedrive_base="${onedrive_mnt}/Onedrive/WGSEReleases/WGSEReleasev4split/"

script=$(basename "${BASH_SOURCE[0]}")
scrspc="$( printf '%*s' ${#script} )"

print_usage() {
  {
    echo ""
    echo "Usage: $script { allpacks | release | installer | program | reflib | tools } "
    echo "       $scrspc [ alltracks | Dev | Alpha | Beta ]"
    echo "  Specify one of the packages to make (\"allpacks\" to make all). If making an"
    echo "  installer, then add a release track (\"alltracks\" to make all)."
    echo "  \"release\" implies \"installer\" and also makes the latest_release JSON and"
    echo "  ZIP files. The cygwin64 and msys2 package JSONs are needed."
  } > /dev/tty
}

onError() {
  [[ -n $1 ]] && echo "ERROR: $1"
  $2 && print_usage
  exit 1
}

usage=true
nousage=false


#---------------------------------- Setup common environment ------------------------------------------------------
export wgse_FP                                # Shellcheck needs (does not affect if already declared)
_wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
_wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
[[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

cd -P "$wgse_FP"  ||  true                    # cdx not yet available

declare currentVer currentDate zipdir wgse_FP
declare -f read_current_release_info rmrx rmx cpx cdx curlx sudox > /dev/null
source scripts/zcommon.sh "$wgse_FP" || onError 'Cannot source scripts/zcommon.sh' $nousage


#-------------------------------- General Script Checks ---------------------------------------------------------

# Specifically to be run on MacOS to use MacOS BOM and ZIP -- MacOS security raises issues at install time otherwise
[[ ! $OSTYPE =~ darwin ]] && onError 'Must be run from MacOS to get .zip set correctly' $nousage

# Need to make sure $zipdir directory does not exist; will not delete in case it contains important files
[[ -e "$zipdir" ]] && onError "Directory $zipdir already exists. Please delete before starting." $nousage

# Sanity check on number of parameters
(( $# < 1 || $# > 2 )) && onError "" $usage


#--------------------------------- Process Parameters -------------------------------------------------------------

make_installer=false  ;  make_program=false  ;  make_reflib=false  ;  make_tools=false  ;  make_release=false
make_Dev=false  ;  make_Alpha=false  ;  make_Beta=false

pack="$( awk '{print tolower($0)}' <<< "$1" )"
track="$( awk '{print tolower($0)}' <<< "$2" )"

case $pack in
  allpacks)  make_installer=true    # No longer generate a single, full ZIP. But can do all the packs at once
             make_program=true
             make_reflib=true
             make_tools=true     ;;
  release)   make_installer=true  ;  make_release=true  ;;
  installer) make_installer=true ;;
  program)   make_program=true   ;;
  reflib)    make_reflib=true    ;;
  tools)     make_tools=true     ;;
  *)         onError "Bad or missing package designator \"$1\"." $usage  ;;
esac

if $make_installer ; then
  case $track in
    alltracks)
            make_Dev=true
            make_Alpha=true
            make_Beta=true   ;;
    dev)    make_Dev=true    ;;
    alpha)  make_Alpha=true  ;;
    beta)   make_Beta=true   ;;
    *)      onError "Bad or missing track designator for installer package \"$2\"" $usage  ;;
  esac
fi

# If making an installer, we need the jq JSON file parser. Normally in Macports. If not available, grab it from the net
if $make_installer && ! command -v jq &> /dev/null ; then
  curlx -o jq "$jqURL"
  sudo_mvx jq /usr/local/bin
  if ! command -v jq &> /dev/null ; then
    onError 'JQ is needed by this script and not found.' $nousage
  fi
fi

# Assure correct permissions for key files and ensure LF line endings for shell scripts
chmod 0755 ./*.bat ./*.command ./*.sh scripts/*.sh
chmod 0644 ./*.txt

# Ensure shell scripts have LF line endings (in case they were edited on Windows)
if command -v sed &> /dev/null; then
  for f in ./*.sh ./*.command scripts/*.sh; do
    [ -f "$f" ] && sed -i '' 's/\r$//' "$f" 2>/dev/null || sed -i 's/\r$//' "$f" 2>/dev/null
  done
fi

#------------------------------------------------------------------------------------------------------------------
# We create up to three regular package and three Installer .zip files. One Installer .zip for each release track type.
# The three package scripts are: Reference Library, Local Tools, and everything else (Program).
# The reference library package is a large, binary blob and has been most of the release size.  The Library
# does not update often.  So this allows for separate versioning and a quick, reliable upgrade of just the Program
# independent of the more static reference library elements.  The microarray templates are now in the reference library.
# yleaf with its templates are kept together and redistributed with jartools/Haplogrep and FastQC; the three
# as the tools package. The tools package is now the largest after including the GATK programs in the jartools.
# The Program package is mainly the program/ folder of python code as well as the user-initiated WGSExtract and
# Library scripts at the top level. Some scripts/ files are common but included in the installer package solely.
# The regular ZIP archive package contents along with an Installer package are mutually exclusive.  The Installer,
# Program, Reference Library and Tools ZIP archives, when merged, create the old Full ZIP archive (sans cygwin64
# and bioinfo which was included for Windows machines). Early v1 and v2 releases also have 5 reference genome models.
#
# NOTE: The latest-release-track.json file is only made with the respective installer when in "release" mode.
#       So if you need that file updated, you will have to make the installer package to create a new
#       latest-release-track.json file.  Even if you do not plan to use the new installer package created.

# Todo TECHNICALLY, the BOM is just a list of files to include in the packages / release.  So we really only need to
#  check if any file has been added or removed.  And recreate the listing if so.  But not easy to do that.
#  Originally just checked if any directory was newer than BOM.  But the directory updates just for editing a file
#  in it.  So now just check if any file has a newer time stamp than the BOM. But this will not catch file deletions
#  or files copied in keeping their old time stamps. So need to come up with a better way.
bom_outdated() {    # $1 bom file to check
  local -i bom_time dir_time  # bom_latest dir_latest bom_file dir_file
  local bom="$1"

  [[ ! -f $bom ]] && return 0
  echo "Checking dates on pre-existing BOM"

  # Below is only a second to complete
  # bom_latest="$(lsbom -ptf dev.bom | sort -nr | head -1 )"   # time in seconds & file name of latest file (tab)
  # bom_time="$(cut -f1 "$bom_latest" )"    # ; bom_file="$(cut -f2 "$bom_latest" )"
  bom_time=$( stat -f "%m" "$bom" )

  # Below is about 1/5th the time of making a new BOM -- 17 vs 94 seconds -- so worth it if multiple succesive runs
  # dir_latest="$( lsbom -s dev.bom | tr '\n' '\0' | xargs -0 ls -ld -D '%s' 2> /dev/null | \
  #               grep -v '^d\|^t\|:$' | tr -s ' ' | cut -s -d" " -f6- | sort -nr | head -1 )"
  # dir_time="$(cut -f1 "dir_latest" )"     # ; dir_file="$(cut -f2 "dir_latest" )"
  dir_time="$( lsbom -sf "$bom" | tr '\n' '\0' | xargs -0 stat -f "%m" 2> /dev/null | sort -nr | head -1 )"

  # Check if the BOM file is older than the newest file from the local directory that is listed in the BOM
  (( bom_time < dir_time ))

}

#--------------------------------- Create BOM(s) of needed package(s) -------------------------------------
# Use BOM tools to create lists of files we want.  We first create a list of everything in the development directory.
# Then remove what we know we do not want.  Must be careful as could snare unintended temporary or not-ready-for-release
# files.  Therefore must use a clean development directory or exceptions must be explicitely listed here.
# grep -v gets rid of files and directories equally well.  -s Dev gives IO error if a mounted volume in vmware

echo
echo '================================================================================'
# We leave dev.bom around for multiple runs.  BOM is just a listing of the directory tree.  Not version
#  stamped (file or dir). Check if any included files have been updated since created. If so, recreate BOM
if bom_outdated dev.bom ; then
  echo
  echo 'Making new BOM listing of directory' "$(basename "$wgse_FP")"
  echo '  (Note: this takes longer as the Python cache, Windows tools, etc are scanned)'
  rmx dev_all.bom
  mkbom -s . dev_all.bom

  echo
  echo 'Trimming new BOM listing to just release files (drop python/, cygwin64/, etc)'
  lsbom dev_all.bom \
    | grep -v "^./yleaf_3\|^./jre\|^./python\|^./cygwin64\|^./msys2\|^./IGV\|^./WGSExtract-\|./latest\|.bom" \
    | grep -v "^./reference/genomes/\|^./temp/\|.idea\|__pycache__\|DS_Store\|samtools.exe.stackdump" > dev.lst
    # Strip out content of temp/ and reference/genomes/ but leave empty directory name. GATK in jartools now left in.
    # | grep -v "^./jartools/gatk-\|^./jartools/picard\|^./jartools/GenomeAnalysisTK.jar\|^./jartools/DISCVRSeq.jar"\

  mkbom -s -i dev.lst dev.bom
  rmx dev.lst dev_all.bom

else
  echo
  echo 'Reusing BOM (release listing) of' "$(basename "$wgse_FP")"

fi

if "$make_installer"; then
  echo
  echo 'Making Installer BOM with (un)install* scripts, readme, scripts/z*'
  lsbom dev.bom | grep "^./Install_\|^./Uninstall_\|^./00README\|^./scripts\|^.$" \
    | grep -v "refgenome\|bwa-kit\|library" > dev_installer.lst   # Things to remove from scripts/: Ref Lib scripts

  mkbom -s -i dev_installer.lst dev_installer.bom
  rmx dev_installer.lst
fi

if "$make_program"; then
  echo
  echo 'Making Program BOM with program, open_source; WGSExtract.* and Library.* scripts'
  lsbom dev.bom | grep "^./program\|^./open_source_licenses\|^./Betav4_Rel\|^.$" > dev_program.lst
  lsbom dev.bom | grep "^./Library\.\|^./Library_\|^./WGSExtract\.\|^./WGSExtract_\|^./scripts" \
    | grep -v "installer.json\|00README\|make_release\|^./scripts/z" >> dev_program.lst
  {
    echo "./reference"
    lsbom dev.bom | grep "seed_genomes.csv\|hg38ToHg19"
  } >> dev_program.lst # Special for 44p3 (reflib patch; to remain until update reflib version)

  mkbom -s -i dev_program.lst dev_program.bom
  rmx dev_program.lst
fi

if "$make_reflib"; then
  echo
  echo 'Making Reference BOM using only the reference subdirectory and Library scripts.'
  lsbom dev.bom | grep "^./reference\|^.$" > dev_reflib.lst    # Removed genomes/* when making dev.bom
  # Moved Library* and scripts/*refgenome scripts to program package; leaving reflib to be just the reference/ blob

  mkbom -s -i dev_reflib.lst dev_reflib.bom
  rmx dev_reflib.lst
fi

if "$make_tools"; then
  echo
  echo 'Making Local Tools BOM using only the yLeaf, FastQC and jartools folders.'
  lsbom dev.bom | grep "^./jartools\|^./yleaf\|^./FastQC\|^.$" > dev_tools.lst
  # yLeaf has major bug fixes by us.  Haplogrep is easier to distribute and use this way.
  # FastQC is unreliable to retrieve from the BAbraham servers. So we simply distribute it here.
  # https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.11.9.zip
  # https://downloads.sourceforge.net/project/fastqc.mirror/v0.11.9/v0.11.9.zip

  mkbom -s -i dev_tools.lst dev_tools.bom
  rmx dev_tools.lst
fi


#-------------------- Local Functions to support ZIP file creation (often called only once) --------------------

# Release.json is generated from scratch and stored in the root folder of the installer ZIP archive.
# The baseURL is a historic artifact and no longer used.  Complete URL's for each track should be used.
# We always ignore the release.json file in the current folder
make_release_json() {     # parameter $1 is release track, $2 is releaseURLbase defined at top ; output to stdout
  printf '{ \n'
  printf '  "release": { \n'
  printf '    "track": "%s", \n' "$1"
  printf '    "__comment0": "WGS Extract Installer release track control", \n'
  printf '    "__comment1": "Set release.track above to choose the URL below to find the latest release json file.", \n'
  printf '    "__comment2": "Edit to change the track before (re)running the installer.", \n'
  printf '    "baseURL":"%s/", \n' "$2"
  printf '    "DevURL": "%s/latest-release-Dev.json", \n' "$2"
  printf '    "AlphaURL": "%s/latest-release-Alpha.json", \n' "$2"
  printf '    "BetaURL": "%s/latest-release-Beta.json", \n' "$2"
  printf '    "__comment3": "Developers, you can replace URLs above with file:///path to test before release." \n'
  printf '   } \n'
  printf '} \n'
}

# make_release_override_json() {
# Developers can edit in a local URL to a locally created release_override.json file that points to a test
# lastest.json file for testing. Local test URLs can be file URLs like:
#   file:////randy-pc2/wgse/dev/latest-release-Dev.json
#   file:///c:/wgse/dev/latest-release-Dev.json
#   file:///wgse/dev/latest-release-Dev.json
#   smb://randy-pc/ and cifs://randy-pc/ fo not work in MacOS.
# We expect a developer to hand edit and update this file internal URL pointer to their needs. Eventually using a
#   https://get.wgse.io/latest-release-Dev_DATE.json file for final testing before removing the release_override
#}

# IMPORTANT: When making an "installer", we update the zipdir scripts/install.json embedded URL to reflect the
#   track being created.  A call to "alltracks" causes the file to be updated for each track processed.
update_installer_json() {   # $1 is the release track being worked on, $2 the json file to update ; output to stdout
  jq --arg REL "$1" '."installer"."URL" |= sub("(Dev|Alpha|Beta)";$REL)' "$2"
}

make_latest_release_json() {  # $1 is zipdir install.json (that has an updated track field) ; output to stdout
  # We simply concatenate the individual JSON files into a latest-release JSON file
  # Assumes a Windows cygwin64 and msys2 installation with JSONs to copy in also
  jq -s '.[0] + .[1] + .[2] + .[3] + .[4] + .[5] + .[6] + .[7]' \
    "$1" program/program.json reference/reflib.json jartools/tools.json \
    cygwin64/cygwin64.json cygwin64/usr/local/bioinfo.json msys2/msys2.json msys2/ucrt64/bioinfo-msys2.json

}

get_package_version() {   # $1 is package name
  local pack=$1 packjson

  case $1 in
    # full)       packjson="program/program.json" ; pack="program"  ;;    # Combined, single pack not made anymore
    installer)  packjson="scripts/$1.json"    ;;
    program)    packjson="program/$1.json"    ;;
    reflib)     packjson="reference/$1.json"  ;;
    tools)      packjson="jartools/$1.json"   ;;
    # Remember, Cygwin64 and bioinfo packages are handled in special, separate Windows release scripts for each
    *) onError "(internal) -- illegal package name $1" $nousage  ;;
  esac

  # cver=0  ;  cdate=$(date +"%d%b%Y")                    # defaults
  read_current_release_info "$pack" "$packjson" "false"   # from scripts/zcommon; sets currentVer and currentDate

  export cver="$currentVer"
  export cdate="$currentDate"
}

make_zip() {     # parameter $1 is the package name; $2 the release track if installer package
  local -i size nowsec packsec
  local track package ver install_pack archive json rarchive rjson onedrive_dest hash mesg

  package="$1"
  track="$2"

  onedrive_dest="${onedrive_base}${package}"     # onedrive_base set at head of script

  [[ "$package" == "installer" ]] && install_pack=true || install_pack=false

  # Setup names with track, version, and date info
  get_package_version "$package"                          # Sets $cver and $cdate

  [[ "$track" == "Dev" ]] && ver="${cver}_$cdate" || ver="v${cver}_$cdate"  # duplicated v looks odd for Dev

  if $install_pack ; then
    archive="WGSExtract-${track}${ver}_$package.zip"
    json="latest-release-${track}-${cdate}.json"          # Historical; should really be same as archive w/ json suffix
    mesg="$track installer"

    if $make_release ; then
      rarchive="WGSExtract-${track}_latest_$package.zip"
      rjson="latest-release-${track}.json"
    fi

  else 							  # any package other than the installer
    archive="WGSExtract-${ver}_$package.zip"
    mesg="package $package"

  fi
  echo "*** Making WGSE $mesg ZIP ($archive) ***"

  # Construct the folder of the package release (content of ZIP archive to make) from the BOM
  #  Do using a DITTO ZIP instead of simply copy to create new files / directories with MacOS flags attached to each
  ditto -c -k --bom "dev_$package.bom" . "temp_$package.zip"   		# Create .zip from our release bom
  ditto -x -k "temp_$package.zip" "$zipdir"              	        # Unzip into $zipdir directory

  # When installer, rewrite track in created release.json and existing installer.json
  if $install_pack; then

    # Create release.json file in zipdir (ignore local copy); copy override file if there
    make_release_json "$track" "$releaseURLbase" > "${zipdir}/release.json"   # Create release.json with track in zipdir
    [ -e "release-override.json" ] && cpx "release-override.json" "${zipdir}/release-override.json"

    # Replace track in local installer.json and overwrite zipdir copy already there
    update_installer_json "$track" "scripts/installer.json" > "${zipdir}/scripts/installer.json"

    # The combined json file for a track (does not go into zipdir) (have to use zipdir installer.json that was updated)
    make_latest_release_json "${zipdir}/scripts/installer.json" > "$json"

  fi

  # Create the actual, final ZIP archive from the constructed zipdir with MacOS flags in each file
  ditto -c -k --keepParent --norsrc "$zipdir" "$archive"

  # Print stats of the created archive in a pretty format (note: specific to MacOS versions) (file name given earlier)
  hash=$( md5 "$archive" | awk '{print $4}' )  ;            echo "MD5    = $hash"
  hash=$( shasum -a 256 "$archive" | awk '{print $1}' )  ;  echo "SHA256 = $hash"
  size=$(stat -f %z "$archive")  ;                          echo "Size   = $size bytes"

  # final cleanup of temporary files
  rmrx "$zipdir" "temp_$package.zip" || true
  [ "$package" != "installer" ] && rmx "dev_$package.bom"       # Have to leave dev_installer.bom in case multiple calls

  # If successfully made, copy to Onedrive archive (disabled for now)
  nowsec=$(date -j +%s)                               # find now in seconds
  packsec=$(date -j -f "%d%b%Y" "$cdate" +%s)         # adds the current hh:mm:ss to retrieved date seconds

  echo
  # If package creation success (sanity size check before release date), then copy to cloud server
  if (( 25000 < size  && nowsec <= packsec )); then

    # Make sure OneDrive is there and ready for us to copy the files
    if df "${onedrive_base}$" > /dev/null 2>&1 ; then
      # [[ -d "$onedrive_mnt" ]] || sudox mkdir -p "$onedrive_mnt"    # changed to use Onedrive cloud app
      # sudox mount -t smbfs "$onedrive_smb" "$onedrive_mnt"
      $? && onError "Failed to mount Onedrive filesystem to accept new package" $nousage
    fi

    echo "Installing package $package to Onedrive $onedrive_base"

    if $install_pack; then
      onedrive_dest+="_$track"      # Installer packages are unique per track (could mix in the same folder)

      echo "Copying package $package for track $track to $onedrive_dest"
      cpx "$archive" "$onedrive_dest"
      cpx "$json" "$onedrive_dest"

      # If making a release, copy release files to generic latest to make available to all users
      if $make_release ; then      # Turn off for now; manually verify and copy later
        echo "Copying latest release $package for track $track to $onedrive_dest"
        cpx "$archive" "${onedrive_dest}/$rarchive"
        cpx "$json" "${onedrive_dest}/$rjson"

      fi

    else
      echo "Copying package $package to $onedrive_dest"
      cpx "$archive" "$onedrive_dest"

    fi
  else
    echo "NOT updating Onedrive with \"$package\" (error creating or after release date)"

  fi
}

#------------------------------------- Make ZIP archive file(s) ----------------------------------------------
# Now that we have the BOMs and functions, we can create the actual ZIP archives.

echo
echo '================================================================================'
echo 'Making ZIP file(s) from created BOM list(s)'

# make_zip full               # no longer created
if "$make_installer" ; then   # Recall that alltracks simply sets all three make_track variables to true
  "$make_Dev"   && echo '' && make_zip installer Dev
  "$make_Alpha" && echo '' && make_zip installer Alpha
  "$make_Beta"  && echo '' && make_zip installer Beta
  rmx dev_installer.bom       # Had to leave it in case of multiple calls
fi
"$make_program" && echo '' && make_zip program
"$make_reflib"  && echo '' && make_zip reflib
"$make_tools"   && echo '' && make_zip tools

echo
echo '================================================================================'
echo 'Do not forget to run:'
echo '  1) cygwin64-port/{make_cygwin64, make_bioinfo}.sh to get new Windows packages.'
echo '  2) regression/run_tests.sh to run regression tests on the new release.'
echo
