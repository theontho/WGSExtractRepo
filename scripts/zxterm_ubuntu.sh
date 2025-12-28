#!/usr/bin/env bash
#
# WGS Extract for Ubuntu Linux (Xterm startup script)
# Copyright (C) 2022-23 Randolph Harr
#

# Self-aborts if not being run on a Linux system, starts a new terminal window otherwise.
if [[ $OSTYPE =~ ^linux*$ ]] ; then
    echo "*** ERROR: Unknown OSTYPE of ${OSTYPE} for the Ubuntu xterm launcher."  ;  echo ""
    sleep 5
    exit 1
fi

# If not in a Terminal, start one so questions can be answered. Linux window managers
# do not allow you to set the terminal as the default way to open a shell script.
# Hints at https://unix.stackexchange.com/questions/233206/ , https://askubuntu.com/questions/72549/ ,
#  https://askubuntu.com/questions/46627/
# NOTE: Must be sourced from calling script so we can restart that script

if [ ! -t 1 ]; then     # Only for when not in a Terminal

  # Determine how to start a terminal based on the Window Manager.
  desktop=$XDG_CURRENT_DESKTOP
  [[ -z "$desktop" ]] && desktop=$(grep -o 'xfce|kde|gnome' <<< "$XDG_DATA_DIRS")
  desktop=${desktop,,}  # convert to lower case

  [[ ${0::1} == "/" ]] && cmd="$0" || cmd="./$0"    # Make command invoke-able directly

  # Open a terminal depending on the desktop type
  case $desktop in
    ubuntu*|gnome*)  gnome-terminal      -- "$cmd"   ;;
    xfce*)           xfce4-terminal      -e "$cmd"   ;;
    kde*)            konsole                "$cmd"   ;;
    *)               x-terminal-emulator -e "$cmd"   ;;
  esac
  exit 0    # Close this script/job as a new terminal window is running.
fi

clear           # Should be in a terminal window here
