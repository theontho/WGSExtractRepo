# Steps to make a release

### Prep for a new release; get and store cloud share links

For EACH package doing a new release for (installer, program, reflib, tools):

1. Update the package .json file with the NEW version and todays date or later.
   Likely bumping up the version # by one. Remember the version # stored there.

2. Duplicate the current ZIP archive file for the package in the cloud drive
   (OneDrive Pub) and rename it to the NEW release ZIP archive file name that
   will be created here shortly (new ver, new date). Add that file name to the
   URL field in the .json file by prepending with "https://get.wgse.io/".
   So now a new version number, date and URL in the package .json file.

3. Get the newly created ZIP archive Onedrive file share URL from the file just
   duplicated above.  In the https://get.wgse.io/ .httpaccess config file, add
   the name for the new file and the share URL there.  Being careful to only
   take the "key" from the share URL and paste it into an existing template
   as used by other files there.

4. When doing this for the installer package, only do it for the zip file in
   the track you are testing.  Still edit the new URL into the current
   `installer.json` file. `make_release.sh` will only override that URL when making
   each track installer ZIP when ALLTRACKS is selected.

   **FOR THE INSTALLER PACKAGE ONLY (only if updated; not if other package updated)**
   
   > NOTE: `make_release.sh` makes a `release.json` that points to `get.wgse.io`. Which
   > overrides the `installer.json` URL with the generic URL in `get.wgse.io` of:
   > `WGSExtract-<track>_latest_installer.zip`.
   > This `latest_installer.zip` URL is then stored in the `latest_release.json` file
   > created and put in the MS Onedrive folder. Only when the `latest_release.json`
   > file is overwritten will that tracks `latest_installer.zip` on be available.
   >
   > So, to test, make your own local `release.json` file that points to a local
   > `latest_release.json` file.  Copy the MS Onedrive `latest_release.json` file
   > to that test local location. This makes the new `latest_release.json`
   > available for testing whatever pacakge versions it points too. Only whe
   > you do a `make_release.sh` release will the correct `latest_release.json`
   > file (for that track) be created. If not making a new installer release
   > on a particular track, delete the new `installer.zip` for that track but use
   > the new track `latest_release.json` file)

5. Edit `dev/make_release.sh` for any changes in the `dev/` release folder (things
   to remove; things to keep).  If you discover something that the installer
   needs to handle, edit the common files to handle the change:
   `scripts/zinstall_common.sh` and `scripts/zuninstall_common.sh`
   (e.g. remove any old files that will not get overwritten, renamed, etc)

6. Do an incremental backup of the development directory for safety

### Loop until satisfied:

1. Run `./make_release.sh` alltracks allpacks (or a subset as desired) on a MacOS
   (only) in the `dev/` folder

2. If, before the release date, it will copy any created ZIP file(s) that need
   updated to the MS Onedrive Public area. By overwriting the just "duplicated
   and renamed" placeholder files made earlier, the captured share URL edited
   into the `.htaccess` file will not change. If you use "release", it will not
   only copy the new installer but replace the `latest_release` files (installer
   .zip and .json) and thus make the release available to everyone. If after
   the release date, then nothing will be copied out of the DEV folder.

3. If you have access to the Onedrive share folder, then as long as the local
   `release.json` points to the dated (not latest) `latest-release.json` file on
   the server (as redirected on `get.wgse.io`), then you can simply grab the
   installer from the `get.wgse.io/*installer.zip` for the unreleased date and
   version.

   Otherwise, if testing before making available there, unpack the
   installer and edit `release.json` to point to a local `latest-release.json`
   file. Then edit that local file with whatever URLs (including local
   `file://.....` path) that point to your under test packages. This private
   `release.json` will not get overwritten in an installer update UNLESS
   the `release-override.json` file is in that installer. If so, simply
   upack the installer and copy in your own `release.json` file over the
   one there and remove any `release-override.json` file.

4. Verify the new packages and URLs work and that the installers do a
   proper fresh AND update install on EACH PLATFORM (OS, CPU Arch)

> **do any regression testing on the WGS Extract program itself; loop until satisfied.** 

### Once Satisfied, Make a release:

1. Run `./make_release.sh` but this time with "release" instead of "installer".
   Delete any `installer.zip` files you do not plan to make a release of. You
   have to run the installer .zip creation to get the updated
   `latest-release.json` file. Even if not updating the installer.

2. Notify TRACK testers of a new release in the Facebook group. Only ever
   distribute the generic `get.wgse.io/latest-installer.zip` link that is
   static and does not change.  Anyone simply runs their installer on an
   existing installation to get the new release.  New users get the new
   installer when they first download from the website.

TBD Update sha256 and md5 checksums on the main release page when the installer
is updated? Put other package chechsums there also? Make the installer
check the cheksums after downloading a package version?


## Background details on the new release and version control system in v4:

> (Make sure any links in the dev folder are hardlinks to directories. That is, junctions in windows terminology. NTFS
> volumes mounted to MacOS only follow junctions. MacOS bom creation will fail if symbolic. In windows cmd.exe:
> `mklink /j link_name target_path` to make a junction; `dir` to tell you which type of link is used; Windows explorer
> to safely remove a junction link without removing the target.  Under l/uinux, `find . -links +1` reports hardlinks
> whereas `ls -ls` will show softlinks.)

A version control system is in place.  The URL to a versioned ZIP archive is stored in a version file which are
themselves stored in the ZIP files created.  So you have to fake-create the new ZIP file and get its share URL,
edit the URL into the appropriate JSON file, and then make the actual release. Catch22. Note that the share URL
is to the actual file and not file name. So you can rename the target file and move it to a different folder and
the URL will not change. Currently, all share URLs are on the MS Onedrive archive as Google Drive makes it near
impossible to programatically download files larger than 25 MB.

All the 6 JSON version files are collected together into a `latest-release` JSON for each release track. That file
is only ever checked into the github repository location pointed to by a `release.json` file.  The `release.json`
file is stored in each installer and set with the appropriate track for that installer.  That is the only
difference between each installer file.  The `release.json` file in an installer will only be copied on new
installations.  If it already exists, it will not be overriden. (See special note on how to make the installer
force pick-up the new `release.json` in the ZIP archive.)

A top level file (`release.json`) in the installer package ZIP archive contains the "selected" release track of
either Beta, Alpha or Dev(eloper).  It also stores the URL to find the `latest-release` JSON file for each track.
The canonical `release.json` file is stored in the `make_release.sh` file here. As it creates each `release.json` from
scratch when making each installer. The default URL to the `latest-release` JSON stored there is to the github
check in of the `latest-release.json` file.

The `make_release.sh` file also has stored the default URL to be stored in each `install.json` file for each track.
When making a a track installer, the current `install.json` file is left as is with its stored URL.  When making
a release installer, the URL in the `install.json` file is overriden by that contained in the `make_release.sh`.
`make_release.sh` stores a URL that points to a "latest" installer for each track located on the MS Onedrive share.
So when making an installer release, the `install.json` file stored in the installer ZIP archive will be updated
with this new URL. So the "latest" installer file for the track on the MS Onedrive must be overwritten by the
newly created installer.

Each of the six mutex ZIP archive packages are independently version controlled with their own JSON files included
in their ZIP archive.  The package jsons have a version number, date created, and the URL to find the online ZIP
archive file (on MS Onedrive). This allows us to compare a current, installed release (JSON file) to the latest
available (online, `latest-release` JSON file) to decide whether the package needs to be updated. And if updating,
the new URLs are found in the online, latest release JSON file.

There are six versioned packages (four for everyone; two for just windows):

| Version control files | Package | Suffix of ZIP | Explanation |
|---|---|---|---|
| `scripts/installer.json` | installer | `_installer.zip` | WGS Extract Installer / Uninstaller with scripts/ |
| `program/program.json` | program | `_program.zip` | WGS Extract main Program release (python, etc) |
| `reference/reflib.json` | reflib | `_reflib.zip` | WGS Extract Reference Library subsystem |
| `jartools/tools.json` | tools | `_tools.zip` | WGS Extract Local tools (jartools/, yleaf/, FastQC) |
| `cygwin64/usr/local/bioinfo.json` | bioinfo | `_bioinfo.zip` | (Windows only) Cygwin64 port of Bioinformatic tools |
| `cygwin64/cygwin64.json` | cygwin64 | `_installer.zip` | (Windows only) Cygwin64 base release |
| (unversioned) | - | `_builder.zip` | (Windows only) Cygwin64 base release with compilation environment to make `_bioinfo` release. Not distributed. |
| `release.json` | release | (in installer) | Release track and base URLs to latest version jsons |
| `latest-release-Dev.json` | release | - | One for each track; generated in `make_release` and uploaded when appropriate to Github. |
| `make_release.sh` / `.txt` | program (but deleted) | | Used to create the packages and JSONs. |
| `cygwin64/make_cygwin64.sh` | cygwin64 | | Stores the URL and version for the new cygwin64 release and creates the `cygwin64.json` file. This because there is no development directory to store the JSON file in. |
| `cygwin64/usr/local/make_bioinfo.sh` | bioinfo | | Stores the URL and version for the new bioinfo tools release on Windows; creates `bioinfo.json` file. |

The first four JSONs are the source for that packages version, date and URL.  They are assumed current in the
development directory and simply copied from there into the appropriate package archive. The archive filename is
created from the version and date stored in the JSON.

The last two cygwin packages are created by the `make_cygwin64` and `make_bioinfo.sh` scripts. The scripts store the
version and URL and so must be edited to update the version. The generated zip file names start with `cygwin64_`.
There is a third, undistributed `_builder.zip` generated that contains the additional cygwin64 files needed to build /
compile the bioinformatics tools in the bioinfo package on Windows.

The installer consults the `release.json` file in the local installation to find the track type and the corresponding
base URL. It then pulls in the (online) `latest-release` json file with all 6 packages' version info. This latest
is used to compare to a currently installed package (determined by the local json files of the installed release
as shown above). The above 6 version jsons are concatenated into one file named `latest-release-TRACK.json` (created
here and must be uploaded to make the latest release available to users).

To check a development release BEFORE posting it as a new version, override / change the URL in the `release.json` to
a local location for the latest-available JSON file. This before running the installer but after unpacking the
ZIP archive. The installer will then take the new location to look for a latest-release json file locally. And thus
get the unreleased version numbers and URLs to the packages to test.  The local `release.json` file in the development
directory is never used to create a release. And the installer will never overwrite an existing `release.json` file
when installing. The `release.json` file stored in the installer is created from the stored content in `make_release.sh`
Examples you can use in the `release.json` file instead of the standard `https://raw.github.com/...` are:
- `file:///wgse/dev/latest-release-Dev.json`                (a local file)
- `file:////randy-pc2/wgse/dev/latest-release-Dev.json`     (a local network file using SMB)
- `file:///c:/wgse/dev/latest-release-Dev.json`             (a local file with specific disk on Windows)

Generally, during development, the command to run this script is `./make_release.sh program` which will create
the `_program.zip` package archive. Likely you will also run `./make_release.sh installer Dev` to create a new
`_Dev_installer.zip` archive (if there were updates to the installer). You can run `./make_release.sh allpacks alltracks`
to make everything and then only upload what has changed. Key is, you need to edit / confirm the content of each of
these 4 package version json files for the appropriate version number (bump by one?) and URL. And then the other 2
for Windows Cygwin must be changed in the make_ scripts before they are run. And if you run just `make_release program`,
you need to edit the `latest-release*json` file to have the URL for your new ZIP archive package.

Github stores the 3 different track `latest-release` JSON files for the latest release versions for each package of each
track.  The stored URLs are to the MS Onedrive copies.  The default `release.json` file in each installer package points
to this github location.  wgsextract.github.io has links to each of the release track "latest" installers. Currently,
these are Bitly links to the Google Drive copies of the "latest" installer files (not the MS Onedrive copy).  The URL
in the `install.json` file is never really used.  The one stored in the `latest-release.json` is always the generic
pointer to the MS Onedrive "latest" installer ZIP archive. This is the only one not used. Otherwise, the
`latest-release.json` file is the collected JSON files from each package directory / ZIP archive.
