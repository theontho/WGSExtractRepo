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
* Run unit tests: `uv run pytest`
* Library updating: run `dev.py library` (or `Library.*`)
* Build Release Installers: run `dev.py release` , see output zip files in the `out/installer_builds/` folder.  Use `release --release-override` or `release -ro` to use your local cache for the installer, makes things much faster for testing.  Users would download those zips and run the `Install*` scripts they see in the root.
* Installer Status
    * Test flow: install and download a genome (bash testing), MT Haplogroup (java testing), make a microarray file
    * Windows: Manually tested on a windows 11 machine to work
    * MacOS Brew: Manually tested on an apple silicon mac with homebrew
    * MacOS MacPorts: Manually tested on a UTM vm macOS 26.2
    * Ubuntu Linux: Manually tested on a UTM arm64 vm and x86 WSL to work
    * Micromamba Linux: Tested with archlinux and openSUSE tumbleweed WSL.  Needed to install system packages for python & tk manually to get the app to launch, but the installer said it was successful.  We got a WSL test vm working with this, so it might work with the next manual test. 


## Repository Structure

### Git Tracked
- `installer_scripts/`: Platform-specific scripts used during the (un)installation process.
- `scripts/`: The bash scripts side of `program/`.
- `program/`: Core Python source code for the WGSExtract application and GUI.
- `base_reference/` -> becomes `reference/`, since `program/` expects that the `reference/` folder also exists but we want to `.gitignore` it because it has downloaded data we don't want to commit to git.
- ⁠`dev/` -> handles all the non-user things like making release builds, dev init, dev util scripts, etc.  `dev.py` is the interface for that and it has a help with `./dev.py -h`
- ⁠`docs/` - centralizes the docs into one spot for the most part.  We also converted to markdown in a semi automated way but also is txt friendly.
- `sandbox/`: Experimental code and temporary development work you can ignore.
- `tests/`: Where unit tests live

### Git Ignored
- `out/`: Default output directory for build artifacts, download caches, tmp dirs for tests, etc.  Basically the output dir of dev actions.
- `reference/`: Where downloaded genomes for the `program/` and such live.
- `temp/`: Temporary files generated during execution of `program/` or `scripts/`.

### Installed Standalone Packages
- `FastQC/`: The FastQC quality control tool for sequence data.
- `jartools/`: Java utility tools (JAR files) like GATK, Picard, and HaploGrep.
- `yleaf/`: Integration with the Y-Leaf tool for Y-chromosome analysis.

## Links

* [Docs](docs/)
* [Development Notes](docs/development.md)
* [Release](docs/release_process.md)
* [Changelog](docs/CHANGELOG.md)