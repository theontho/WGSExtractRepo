# WGS Extract

**Currently a WIP setup of the git repo for development**

Version: v4 DEV - https://WGSE.bio/

This git repo is for development of WGS Extract, if you would just like to install it, go to https://WGSE.bio/ and follow the instructions there.  The rest of this readme is for developers.

## Current Development System

Since this toolkit app has a bunch of bundled packages, programs, libraries, etc that isn't a good idea to put in a git repo, it used a json manifest file system to help downloading these and composing these packages together.  This is refrenced in release_manifest.json. 

There is the main cross platform set of packages:

- installer : this contained the install scripts made by the release process, which downloaded and set up the packages for each platform refrencing `release.json`
- program : this is the main python program code that put all of this stuff together, shows the user interface, etc.
- reflib : this contains a whole bunch of genetic reference data for the program to use
- tools : this contains a set of cross platform python and java tools like FastQC

And there is there is the bioinformatics (`bioinfo`) tools.

- macos: uses macports and some custom scripts to install needed dependencies.  There is a new beta homebrew version that is significantly simpler to maintain and install vs. the old macport version.
- linux: uses apt and some custom scripts to install needed dependencies (ubuntu) or micromamba if not the main repo
- windows: provides some prebuilt bioinformatics tools which it runs via a prebuilt cygwin or msys2 environment. These are downloaded as binary packages from the release_manifest.json file (bioinfo & cygwin64 or msys2 & bioinfo-msys2).  My guess is it's way more painful to do the linux / macos method on windows, thus the prebuilt need.

The platform installer script would download the set of packages it needs, installs them and then deletes the other cross platform installer scripts to clean up the root directory.  The user would then run the {wgsextract,library}.{bat,sh,command} to start the python tkinter UX.  

The release process is fairly manual and extensive, and you can see it specified in [docs/release_process.md](docs/release_process.md).

Since it was a pretty complicated system to maintain, it wasn't under a git repo, just this custom process.

## Proposed New Interm Development System

I wanted to improve the app, so I'm proposing a new development situation.  

- merge installer & program packages into the github repo as a single source of truth since they are where most new source code is edited here.  Put development back into a git repo for our sanity.
- keep the `release_manifest.json` manifest system for `reflib`, `tools` & the windows `bioinfo` packages since they are all third party software & data for now and mostly large binaries that don't change as much.
- make `release_manifest.json` only exist in the github repo, and we use release tags to differentiate versions of this url for installer scripts that we create.
- create an automated release process that uses github actions & releases to create an end user installer script package for each platform.  Each installer package will also include the contents of the git repo to reduce the amount of `release_manifest.json` managed packages.  Host these on the releases page of the github repo and have it update the github page with these latest releases automatically.  Refer people to the releases page if they want to download older versions, only show one stable version on the website.
- make an `dev-init.sh` script that will download what is needed from `release_manifest.json` to enable full development of the app based on the platform of the user.

## Eventual Goals:

- Move todos into github issues
- Merge v5 changes into the main branch
- Make macos homebrew the default
- Update a bunch of out of date tooling
- Have a CI github action, somehow, per commit?
- One day, in the far future, make it a one click app, have a windows installer, etc.