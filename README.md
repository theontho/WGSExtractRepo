# WGS Extract

> ⚠️ **Currently a WIP setup of the git repo for development**

Version: v4.45 DEV - 19Sep2025. Installer 52, Version 44.11

This git repo is for development of WGS Extract, if you would just like to install it, go to https://WGSE.bio/ and follow the instructions there.  The rest of this readme is for developers.

## Basic Dev Workflow

You might need to install python and uv in your local environment before this works.  You also might need to do `uv run dev.py` or `python dev.py` to run this flow.

* Run `dev.py init` to init your dev environment.
    * Windows: Works on an windows 11 machine.
    * MacOS: Works on an apple silicon mac.
    * Linux: Not tested yet, maybe works? 
* Run `dev.py release-cache` to create a local release override cache so you don't have to redownload packages from the internet repeatedly during testing & development.
* Edit - build - run: launch with `dev.py launch` (or `WGSExtract.*`), edit in your text editor, quit and launch again, etc.
* Library updating: run `dev.py library` (or `Library.*`)
* Build Release Installers: run `dev.py release` , see output zip files in the `build/` folder.  Use `release --release-override` or `release -ro` to use your local cache for the installer, makes things much faster for testing.  Users would download those zips and run the `Install*` scripts they see in the root.
* Installer Status
    * Test flow: install and download a genome (bash testing), MT Haplogroup (java testing), make a microarray file
    * Windows: Manually tested on a windows 11 machine to work
    * MacOS Brew: Manually tested on an apple silicon mac with homebrew
    * MacOS MacPorts: Manually tested on a UTM vm macOS 26.2
    * Ubuntu Linux: Manually tested on a UTM arm64 vm and x86 WSL to work
    * Micromamba Linux: Tested with archlinux and openSUSE tumbleweed WSL.  Needed to install system packages for python & tk manually to get the app to launch, but the installer said it was successful. 

## Testing

### Unit Tests
We use `pytest` for unit testing. To run the tests, use:
```bash
uv run pytest
```
Note: Ensure you have `uv` installed and have run `dev.py init` first.

### VM Installation Tests

> ⚠️ **Currently a non  functional / buggy WIP**

The `tests/vm_test.py` script allows you to test the installer in clean VM environments (Ubuntu, Fedora, macOS).

**Prerequisites:**
* MacOS: Requires `tart` (installed automatically via brew if missing).
* Windows: Requires WSL2.

## Links

* [Docs](docs/)
* [Development Notes](docs/development.md)
* [Release](docs/release_process.md)
* [Changelog](docs/CHANGELOG.md)