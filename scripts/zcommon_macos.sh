#!/usr/bin/env bash
# WGS Extract v4 in-place common scipt startup (MacOS specific)
# Copyright (C) 2021-2024 Randolph Harr
#
# Mainly used for install_macos.command and uninstall_macos.command. Adds functions in common such as macports
# install and uninstall, python uninstall, etc.
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.
#

if (( $# != 1 )) || ! (return 0 2>/dev/null) || [[ ! -d "$wgse_FP" ]]; then
  printf "Usage: source %s { install_dir } \n" "${BASH_SOURCE[0]##*/}"   # basename may not be available
  printf "  This script should only be sourced from internal scripts after zcommon.sh.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
fi

#VERS=`defaults read loginwindow SystemVersionStampAsString`
_build_vers=$(sw_vers -buildVersion)
IFS="." read -ra _os_vers <<< "$osver"
if (( _os_vers[0] > 10 )) ; then
  _vers="${_os_vers[0]}.${_os_vers[1]}"       # New major.minor
  echo "MacOS Version: ${_vers}+build${_build_vers} on ${cpu_arch}"
elif (( _os_vers[0] = 10 )) ; then
  _vers="10.${_os_vers[1]}.${_os_vers[2]}"    # Old 10.major.minor
  echo "MacOSX Version: ${_vers}+build${_build_vers} on ${cpu_arch}"
else
  _vers="unknown"
  echo "MacOS Version unknown, build${_build_vers} on ${cpu_arch}"
fi
echo
export _os_vers     # Normally local as only used in routine below but treated like global in case not sourced

#------------------- MacOS Homebrew (un)Install  ------------------------

# Shared Homebrew package lists
# Todo pbmm2, a PacBio Minimap2 front-end  https://github.com/PacificBiosciences/pbmm2
export HOMEBREW_PKGS="bash grep gnu-sed coreutils zip unzip 7zip md5sha1sum jq python@3.11 python-tk@3.11 samtools bcftools htslib bwa minimap2 fastp bowtie2"
export HOMEBREW_CASKS="zulu@8 zulu@11"
export HOMEBREW_BIO_PKGS="brewsci/bio/bwa-mem2 brewsci/bio/hisat2"

install_homebrew() {
  # Check if Homebrew is installed
  if ! command -v brew &> /dev/null; then
      if [ -x "/opt/homebrew/bin/brew" ]; then
          eval "$(/opt/homebrew/bin/brew shellenv)"
      elif [ -x "/usr/local/bin/brew" ]; then
          eval "$(/usr/local/bin/brew shellenv)"
      fi
  fi

  if ! command -v brew &> /dev/null; then
      echo "Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      
      # Determine where Homebrew was installed
      if [ -d "/opt/homebrew" ]; then
          eval "$(/opt/homebrew/bin/brew shellenv)"
      else
          eval "$(/usr/local/bin/brew shellenv)"
      fi
  fi

  # echo "DEBUG: Homebrew prefix is $(brew --prefix)"
  # echo "DEBUG: Homebrew bin is $(brew --prefix)/bin"

  echo "Updating Homebrew and packages..."
  brew update

  echo "Installing required Unix utilities & bioinformatics tools..."
  brew install $HOMEBREW_PKGS
  brew install $HOMEBREW_CASKS
  brew install $HOMEBREW_BIO_PKGS

  echo "Homebrew setup completed successfully!"
}
export -f install_homebrew

uninstall_homebrew_packages() {
  # If $1 == "ask", then query the user whether to remove or not
  local ask remove
  [[ $1 == "ask" ]] && ask=true || ask=false

  remove=true
  if $ask ; then
    readq 'Do you want to uninstall Homebrew packages? [y/N]'
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false
  fi

  if $remove ; then
    $ask && echo " ... uninstalling Homebrew packages."
    brew uninstall $HOMEBREW_PKGS $HOMEBREW_BIO_PKGS
  elif $ask ; then
    echo ' ... Leaving Homebrew packages installed.'
  fi
}

export -f uninstall_homebrew_packages

uninstall_homebrew() {
  # If $1 == "ask", then query the user whether to remove or not
  local ask remove
  [[ $1 == "ask" ]] && ask=true || ask=false

  remove=true
  if $ask ; then
    readq 'Do you want to uninstall Homebrew? [y/N]'
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false
  fi

  if $remove ; then
    $ask && echo " ... uninstalling Homebrew."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
  elif $ask ; then
    echo ' ... Leaving Homebrew installed.'
  fi
}
export -f uninstall_homebrew

#------------------- MacOS Command Line Interface (language compilation) tools  (un)Install  ------------------------

_cli_old_version() {
  # MacPorts requires a minimum xcode CLI version depending on the MacOS version
  local cli_min minver cli_cur curver

  case ${_os_vers[0]} in
    10)   # Original MacOSX on x86_64 platform
      case ${_os_vers[1]} in
        15) cli_min=11.3   ;;
        14) cli_min=10.0   ;;
        13) cli_min=9.0    ;;
        12) cli_min=8.0    ;;
         *) Echo "***ERROR: WGS Extract and Macports cannot support older MacOS version 10.${_os_vers[1]}"
            exit 1   ;;
      esac   ;;

    # New MacOS versioning
    11) cli_min=12.2   ;;
    12) cli_min=13.1   ;;
    13) cli_min=14.1   ;;
    14) cli_min=15.0   ;;
    15) cli_min=16.0   ;;
    26) cli_min=26.0   ;;
    *)  Echo "***ERROR: WGS Extract / MacPorts support for MacOS Version: ${_os_vers[0]}.${_os_vers[1]} is not yet available"
        exit 1   ;;
  esac
  IFS="." read -ra minver <<<"$cli_min"

  cli_cur=$(pkgutil --pkg-info=com.apple.pkg.CLTools_Executables | grep "version" | cut -f2 -d' ')
  IFS="." read -ra curver <<<"$cli_cur"

  (( curver[0] < minver[0] || curver[1] < minver[1] )) && return 0 || return 1
}


apple_cli_uninstall() {
  # note: Apple instructs to simply remove the folder to unintall xcode cli tools. Simply removing the folder
  #       sometimes causes later reinstalls of the tools to fail.  No real workaround.
  # If $1 == "ask", then query the user whether to remove or not
  local ask remove
  [[ $1 == "ask" ]] && ask=true || ask=false

  [ ! -d /Library/Developer/CommandLineTools ]  && return 0

  remove=true
  if $ask ; then
    readq 'Do you want to remove Apple Xcode CLI [y/N]?'
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false
  fi

  if $remove ; then
    $ask && echo " ... removing Apple Xcode CLI."
    sudo_rmrx  /Library/Developer/CommandLineTools
    $ask && echo 'Running: mdfind -name "xcode" may help you find more to uninstall'

  elif $ask ; then
    echo ' ... Leaving the Apple Xcode CLI tools installed.'

  fi
}
export -f apple_cli_uninstall

# Homebrew installs xcode cli tools, but just incase...
apple_cli_install() {
  (( ${_os_vers[0]} > 14 )) && cli_min="^version: 16" || cli_min="^version: 15"

  if xcode-select -p &> /dev/null; then
    if ! _cli_old_version ; then
      echo "Apple Xcode CLI tools already installed (minimum version for MacPorts met)"
      return
    fi

    echo "Uninstalling an older version of Xcode CLI tools as a newer version is needed."
    apple_cli_uninstall noask
  fi

  echo 'Installing Apple Xcode CLI; needed for the MacPorts packages and Python PIP modules'
  # ${sudox} xcode-select --install.  # only schedules installer; below touch does the same
  touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress;
  _prod=$(softwareupdate -l | \
      grep "\*.*Command Line" | \
      head -n 1 | awk -F"Command" '{print $2}' | \
      sed -e 's/^ *//' | \
      tr -d '\n')
  softwareupdate -i "Command $_prod" --verbose;		# Do the scheduled install

}
export -f apple_cli_install

#------------------------------------ OLD METHODS (un)INSTALLERS  --------------------------------------------

#------------------------------------ MacOS MacPorts (un)Install  --------------------------------------------
#  Needed here as Installer may have to uninstall and then do a fresh install

declare -rx _localport="/opt/local/bin/port"

_macports_wrong_OS() {
  # If not installed; then cannot be wrong_OS so return false (1)
  [ ! -f "$_localport" ] && return 1

  # If _localport is for the wrong OS; exit / return code is true (0)
  "$_localport" info samtools 2>&1 >/dev/null | head -1 | grep -q "Error: Current platform"
}

# Function to uninstall MacPorts packages
uninstall_macports_packages() {
  # If not installed, simply return true (0) as successful
  [ ! -f "$_localport" ] && return 0
  echo 'Starting MacPorts packages uninstallation...'
  
  # Remove 7z symlink if it exists
  if [ -L /opt/local/bin/7z ]; then
    echo 'Removing 7z symlink...'
    sudo rm -f /opt/local/bin/7z
  fi

  # Uninstall bioinformatic packages
  if [ -f /opt/local/bin/samtools ]; then
    echo 'Uninstalling bioinformatic packages...'
    sudo "$_localport" -N uninstall samtools bcftools htslib
  fi

  # Uninstall Unix utilities
  if [ -f /opt/local/bin/7zz ] || [ -f /opt/local/bin/gsed ] || [ -f /opt/local/bin/jq ]; then
    echo 'Uninstalling Unix utilities...'
    sudo "$_localport" -N uninstall bash grep gsed coreutils zip unzip 7zip md5sha1sum jq
  fi
}

export -f uninstall_macports_packages

macports_uninstall() {
  # If $1 == "ask", then query the user whether to remove or not
  local ask remove
  [[ $1 == "ask" ]] && ask=true || ask=false

  # If not installed, simply return true (0) as successful
  [ ! -f "$_localport" ] && return 0

  remove=true
  if $ask ; then
    readq 'Do you want to remove Macports and all its programs [y/N]?'
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false
  fi

  if $remove ; then
    # See https://guide.macports.org/chunked/installing.macports.uninstalling.html

    # Can only run "macports uninstall" if MacOS has not been upgraded since macports was installed
    if ! _macports_wrong_OS ; then
      echo "   Deleting Macports installed packages ..."
      sudox "$_localport" -fp uninstall installed | grep -v "Cleaning\|Deactivating\|Uninstalling"
    fi

    echo "   Deleting MacPorts login credentials ..."
    sudox dscl . -delete /Users/macports 2> /dev/null
    sudox dscl . -delete /Groups/macports 2> /dev/null

    # NOTE: Cannot use our rmrx on /opt/local. So use /opt/local/* with hope MacPorts is the only installation there
    # MacPorts creates too many directory names to give as an explicit list (bin, lib, etc). But many are common as it is.
    # MacPorts assumes it was the only thing installed in /opt/local which does not seem kosher.
    echo "   Deleting MacPorts installation folders ..."
    sudo_rmrx /opt/local/* \
      /Applications/DarwinPorts \
      /Applications/MacPorts \
      /Library/LaunchDaemons/org.macports.* \
      /Library/Receipts/DarwinPorts*.pkg \
      /Library/Receipts/MacPorts*.pkg \
      /Library/StartupItems/DarwinPortsStartup \
      /Library/Tcl/darwinports1.0 \
      /Library/Tcl/macports1.0 \
      ~/.macports

    elif $ask ; then
      echo ' ... Leaving the MacPorts application installed.'

    fi
}
export -f macports_uninstall

macports_install() {
  # todo Macports requires a specific version number and OS name for each MacOS version.  Not known ahead of release.
  #      Need to install the latest release for a given / latest OS version. Read a config file from the server?
  local ver="$1"   # MacPorts version (latest at time of release; e.g. 2.10.1)
  local _macportSP="https://github.com/macports/macports-base/releases/download"
  # _macportSP="https://distfiles.macports.org/MacPorts/${_macportSF}"  # requires _macportSF
  local _macportSF
  local strip

  echo "Installing MacPorts v${ver} on MacOS version ${_os_vers[0]}.${_os_vers[1]} in /opt/local."

  case ${_os_vers[0]} in
    10)   # Original MacOSX on x86_64 platform
      case ${_os_vers[1]} in
        15) _macportSF="MacPorts-${ver}-10.15-Catalina.pkg"     ;;
        14) _macportSF="MacPorts-${ver}-10.14-Mojave.pkg"       ;;
        13) _macportSF="MacPorts-${ver}-10.13-HighSierra.pkg"   ;;
        12) _macportSF="MacPorts-${ver}-10.12-Sierra.pkg"       ;;
         *) Echo "***ERROR: MacPorts cannot support older MacOS version 10.${_os_vers[1]}"
            exit 1   ;;
      esac   ;;

    # New MacOS versioning (requires name as well like before)
    11) _macportSF="MacPorts-${ver}-11-BigSur.pkg"     ;;
    12) _macportSF="MacPorts-${ver}-12-Monterey.pkg"   ;;
    13) _macportSF="MacPorts-${ver}-13-Ventura.pkg"    ;;
    14) _macportSF="MacPorts-${ver}-14-Sonoma.pkg"     ;;
    15) _macportSF="MacPorts-${ver}-15-Sequoia.pkg"    ;;
    26) _macportSF="MacPorts-${ver}-26-Tahoe.pkg"      ;;
    *)  Echo "***ERROR: MacPorts support for MacOS Version: ${_os_vers[0]}.${_os_vers[1]} not yet available in WGS Extract"
        exit 1   ;;
  esac

  curlx -O "${_macportSP}/v${ver}/${_macportSF}"  # MacOS has issues with MacPorts SSL; so curl -k.
  # See https://github.com/WGSExtract/WGSExtract.github.io/discussions/9#discussioncomment-2923858

  strip='^--->  Computing\|^--->  Attempting\|^--->  Fetching\|^--->  Verifying\|^--->  Extracting\|^--->  Applying\|'
  strip+='\|^--->  Configuring\|^--->  Building\|^--->  Staging\|^--->  Cleaning\|^--->  Deactivating\|^--->  Activating'
  # Automatically puts it in _localport area which is /opt/local
  sudox installer -package "$_macportSF" -target /  |  grep -v "$strip"
  rmx "$_macportSF"
}
export -f macports_install


#------------------------------------ MacOS Python (un)Install  --------------------------------------------

_python_rmdeflinks() {
  # Removes default links for python3 installation. $1 = force means to force delete whether target exists or not
  local file fp force
  [[ $1 == "force" ]] && force=true || force=false

  for file in idle3 pip3 pydoc3 python3 python3-config python3-intel64 ; do
    fp="/usr/local/bin/$file"
    [[ -h "$fp" ]] && [[ $force || ! -e "$fp" ]] && sudo_rmx "$fp"
  done
}

python_install() {
  local newver=$1   # e.g. 3.11.7
  local arrver=()  strver=""  curver="0.0.0"
  declare -i minver=0 majver=0
  local _pythonf _pythonp

  # Check if current version is older than newver; if so, unlink default version to force install of the newer version
  # shellcheck disable=SC2154
  if [ -f /usr/local/bin/python3 ]; then

    # We presume the alias for python3 will be to the latest version installed
    strver=$(/usr/local/bin/python3 --version)                                                    # python 3.11.7

    IFS=" " read -ra arrver -d '' <<<"$strver"  ;  curver=${arrver[1]//[$'\r\n']/}                # 3.11.7
    IFS='.' read -ra majmin -d '' <<<"$curver"  ;  majver=${majmin[0]}  ;  minver=${majmin[1]}    # 3 , 11

    if _verComp "$curver" "<" "$newver" ; then
      echo "Default Python v$curver is out of date."
      echo "  Resetting the default from v$curver to v$newver."
      _python_rmdeflinks force

      echo "  Removing the old v$curver before installing the new $newver."
      python_uninstall "${majver}.${minver}" noask   # Todo Could just remove default links and leave it at that

    else
      echo "Python v$curver already installed and up-to-date."
    fi
  fi

  # Install when either python is not installed at all or the default installation is older than what we want.
  if [ ! -f /usr/local/bin/python3 ]; then
    echo "Installing Python $newver" '(ignoring labotomized Python in MacOS).'
    case "$cpu_arch" in
    x86_64*) _pythonf=python-${newver}-macos11.pkg ;;    # No longer separate arch installs needed
    arm*)    _pythonf=python-${newver}-macos11.pkg ;;    # Universal installer with native code per arch
    *)       echo "*** Error: Unknown MacOS Architecture ${cpu_arch}"
             exit 1 ;;
    esac
    _pythonp="https://www.python.org/ftp/python/${newver}/${_pythonf}"
    curlx -o "$_pythonf" "$_pythonp"
    sudox installer -package "$_pythonf" -target /
    rmx "$_pythonf"
  fi
}
export -f python_install

python_uninstall() {
  # Allows for one or more versions of python3 to be uninstalled. $1 is majmin like 3.8. optional $2 is ask / noask
  local ask remove
  [[ $2 == "ask" ]] && ask=true || ask=false

  [ ! -d "/Library/Frameworks/Python.framework/Versions/$1" ] && return 0

  remove=true
  if $ask ; then
    readq "Do you want to remove Python that we potentially installed? v$1 [y/N]?"
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false

  fi

  if $remove ; then
    echo " ... removing Python v$1 libraries and modules ..."
    sudo_rmrx "/Library/Frameworks/Python.framework/Versions/$1"
    echo " ... removing Python v$1 application"
    sudo_rmrx "/Applications/Python $1"

    # Remove version specific symlinks
    # shellcheck disable=SC2086
    sudo_rmrx /usr/local/bin/{idle$1,python$1*,pip$1,pydoc$1}

    # Remove default symlinks if no longer valid (target is removed)
    _python_rmdeflinks noforce

  elif $ask ; then
    echo " ... Leaving the Python $1 Application installed."

  fi
}
export -f python_uninstall


#------------------------------------ MacOS Java (un)Install  --------------------------------------------

java_install() {
  # Parameters: dir name, text name, x86 name, arm name
  local _javaf _javap

  if ! (ls "/Library/Java/JavaVirtualMachines/$1" >/dev/null 2>&1 ); then
    echo "Installing Java JRE $2 ..."
    case "$cpu_arch" in
      x86_64*)  _javaf="$3"  ;;
      arm*)     _javaf="$4"  ;;
      *) echo "*** Error: Unknown MacOS Architecture ${cpu_arch}" ; exit 1 ;;
    esac
    _javap="https://cdn.azul.com/zulu/bin/${_javaf}.tar.gz"
    curlx -o "$1.tgz" "$_javap"
    #/opt/local/bin/7z x -tzip -y $1.tgz >/dev/null && rmx $1.tgz
    tar xf "$1.tgz"
    # shellcheck disable=SC2086
    sudo_mvx "${_javaf}/$1" /Library/Java/JavaVirtualMachines
    rmrx "$_javaf" "$1.tgz"
    echo " ... finished Java JRE $2 install."

  else
    echo "Java JRE $2 already installed."

  fi
}
export -f java_install

java_uninstall() {
  # Parameters: dir name, text name, ask
  local ask remove
  [[ $3 == "ask" ]] && ask=true || ask=false

  [ ! -d "/Library/Java/JavaVirtualMachines/$1" ] && return 0

  remove=true
  if $ask ; then
    readq "Do you want to remove Java JRE that we potentially installed? $2 [y/N]?"
    [[ $REPLY =~ ^[Yy]$ ]] && remove=true || remove=false
  fi

  if $remove ; then
    $ask && echo " ... removing Java JRE $2 ."
    sudo_rmrx "/Library/Java/JavaVirtualMachines/$1"

  elif $ask ; then
    echo " ... Leaving Java JRE $2 installed."

  fi
}
export -f java_uninstall
