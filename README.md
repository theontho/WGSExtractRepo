# WGS Extract

**Currently a WIP setup of the git repo for development**

Version: v4 DEV - 19Sep2025. Installer 52, Version 44.11

This git repo is for development of WGS Extract, if you would just like to install it, go to https://WGSE.bio/ and follow the instructions there.  The rest of this readme is for developers.

## Basic Dev Workflow

* Run `dev_init.py` to init your dev environment.
    * Windows: Works on an windows 11 machine.
    * MacOS: Works on an apple silicon mac.
    * Linux: Not tested yet, maybe works? 
* Run `setup_release_local.py` to create a local release override cache so you don't have to redownload packages from the internet repeatedly during testing & development.
* Edit - build - run: launch with `dev_launch.py`, edit in your text editor, quit and launch again, etc.
* Library updating: run `dev_launch_library.py`
* Build Release Installers: run `uv run scripts/release.py` , see output zip files in the `build/` folder.  Use `--release-overide` to use your local cache for the installer, makes things much faster for testing.  Users would download those zips and run the `Install` scripts they see in the root.
* Installer Status
    * Test flow: install and download a genome (bash testing), MT Haplogroup (java testing), make a microarray file
    * Windows: Manually tested on a windows 11 machine to work
    * MacOS Brew: Manually tested on an apple silicon mac with homebrew
    * MacOS MacPorts: Manually tested on a UTM vm macOS 26.2
    * Ubuntu Linux: Manually tested on a UTM arm64 vm and x86 WSL to work
    * Micromamba Linux: Tested with archlinux and openSUSE tumbleweed WSL.  Needed to install system packages for python & tk manually to get the app to launch, but the installer said it was successful. 
* `vm_test.py`: Buggy, doesn't work correctly, WIP.

## Links

* [Docs](docs/)
* [Development Notes](docs/development.md)
* [Release](docs/release_process.md)
* [Changelog](docs/CHANGELOG.md)