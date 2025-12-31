# WGS Extract

**Currently a WIP setup of the git repo for development**

Version: v4 DEV - 19Sep2025. Installer 52, Version 44.11

This git repo is for development of WGS Extract, if you would just like to install it, go to https://WGSE.bio/ and follow the instructions there.  The rest of this readme is for developers.

## Basic Dev Workflow

* Run `dev_init.py` to init your dev environment.
    * Windows: Doesn't work fully yet, run `uv run scripts/release.py`, take the windows installer zip, unzip it , run the installer script and edit the program folder there as a workaround for now.  Will make it workable soon.
    * MacOS: Works on an apple silicon mac.
    * Linux: Not tested yet, maybe works? 
* Edit - build - run: launch with `dev_launch.py`, edit in your text editor.  `dev_init.py` needs to work.
* Library updating: run `dev_launch_library.py`
* Build Release Installers: run `uv run scripts/release.py` , see outputs in the `build/` folder.
* Installer Status
    * Windows: Manually tested on a windows 11 machine to work
    * MacOS Brew: Manually tested on an apple silicon mac with homebrew
    * MacOS MacPorts: Not tested yet due to not getting the tart vm test working and macports being annoying to remove.
    * Linux (Ubuntu and not-ubuntu): Tested to work with `vm_test.py` in an arm64 tart vm, not tested manually yet.

Make branches, do standard git stuff, etc.

## Links

* [Docs](docs/)
* [Development Notes](docs/development.md)
* [Release](docs/release_process.md)
* [Changelog](docs/CHANGELOG.md)