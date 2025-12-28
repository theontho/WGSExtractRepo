#!/usr/bin/env bash
#
# WGS Extract terminal emulator startup script for Linux operating systems
# Copyright (c) 2022-23 Aaron Ballagan
# Copyright (C) 2022-23 Randolph Harr
#
# Based on zxterm_ubuntu.sh in the original WGS Extract release with some portions copied in

# Self-aborts if not being run on a Linux system, starts a new terminal window otherwise.
if [[ ! $OSTYPE =~ linux ]] ; then
    echo "*** ERROR: Unknown OSTYPE of ${OSTYPE} for the Linux xterm launcher."  ;  echo ""
    sleep 5
    exit 1
fi

# If not in a Terminal, start one so questions can be answered. Linux window managers
# do not allow you to set the terminal as the default way to open a shell script.
# Hints at https://unix.stackexchange.com/questions/233206/ , https://askubuntu.com/questions/72549/ ,
#  https://askubuntu.com/questions/46627/
# NOTE: Must be sourced from calling script so we can restart that script

if [ ! -t 1 ]; then     # Only for when not in a Terminal
  # This is similar to the method "neofetch" uses to find the terminal in which it is run.
  term=$(ps -p ${PPID} -o comm=)

  [[ ${0::1} == "/" ]] && cmd="$0" || cmd="./$0"    # Make command invoke-able directly

  # Find the terminal this script is being run in, so we can start a new window with the same terminal.
  case ${term} in
    gnome-terminal- )   gnome-terminal      -- "$cmd"   ;;     # GNOME, GNOME Flashback and Cinnamon.
    konsole |yakuake )  konsole             -e "$cmd"   ;;     # KDE Plasma, Yakuake
    sakura )            sakura              -x "$cmd"   ;;     # Minimal terminal no dependencies.
    kitty | st )        ${term}                "$cmd"   ;;     # Minimalist desktops (i3, bspwm, dwm)
    xfce4-terminal | \
    mate-terminal | \
    tilix | qterminal | \
    deepin-terminal | \
    lxterminal | \
    termit | roxterm | \
    guake | alacritty | \
    xterm | rxvt | \
    urxvt | mlterm |\
    terminator )        ${term}             -e "$cmd"   ;;     # Misc terminals
    * )                 x-terminal-emulator -e "$cmd"   ;;     # Fallback for terminals not found above.
  esac
  exit 0    # Close this script/job as a new terminal window is running.
fi

clear           # Should be in a terminal window here
