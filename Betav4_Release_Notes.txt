# Release notes Beta v4.
These notes here are in the `WGSE_Betav4_Release_Notes.txt` file installed with the software. They give you the most comprehensive list of changes since Beta v2.

Your installed v4 and later release is dated and displayed in the banner when you start the program.  Rerunning the installer will update your software to the latest available for your release track.

Releases are shown latest first and back to the initial **Beta v2 release of 18 Feb 2020**. (Previous years alpha releases not individually catalogued.)
v3 Alpha was first released Jun 2020, V2 from Dec 2019-Feb 2020, and v1 was first released in May 2019.

Version 4 release:

# **19 Sep 2025 (52 Installer, 4.44 patch 11 Program)
* Minor (bug) fixes; internal updates
  * Added TypeError to exception checks on module loads. A temporary Python release library error was not getting caught.
  * Fixed typo in languages.xlsx that prevednted file name from being included in error report on missing AllSNPs file in Microarray CombinedKit processing.
  * Fixed tools.json URL that was still pointing to old MS Onedrive instead of latest get.wgse.io folder area
  * Minor tweaks to languages.xlsx to fix relocation of HGP references
  * Minor tweaks in settings.py for MGI T7 sequencer ID (v1, v2, v2.5 etc)
  * Extended support for MacOS 26 Tahoe (note: not 16), MacPorts 2.11.5 (from 2.10.x), xcode CLI to 26.0 min (zcommon_macos.sh, Install_macos.command)
  
# **08 Oct 2024 (51 Installer, 4.44 patch 10 Program)
* Minor (bug) fixes; internal updates
  * Fixed typo in last minute edit to zinstall_common.sh that only caused problems with Linux installs (both micromamba and Ubuntu). Was a fix to fix a previous typo that would not leave the WGSExtract.sh and Library.sh files; and still wouldn't.
  * Fixed introduced error in DEBUG mode font change.  Was dropping change before setting it on redraw after removing the globals a few releases ago.
  * Added recognition of Novaseq X sequencer
  * Teemu fixed the microarray generator per company (aconv.py) to be oblivious to out of order coordinates in the template file.  Seems a few templates have that issue in a few places. Improves the generated file.

# **30 Sep 2024 (50 Installer)
* Fix for Micromamba 2 update that breaks current Linux installer. Fix for TK library that is portable across OSs to allow font sizing.
* Fix for MacOS v15 Sequoia to check Apple xcode CLI version. Macports on Sequoia requires v16 whereas older OSs have v15.

* Minor (bug) fixes; internal updates
  * Updated make_release to utilize onedrive app connection to cloud drive; instead of mounting local network storage version (preparing for MacOS stand alone, primary development)
  * Generalized zcommon_macos.sh install/uninstall routines and added ones for xcode cli. Cleans up the install / uninstall _macos scripts and makes the code more maintainable.
  * Fixed a nit in the Linux / Ubuntu common installer to only try to rename the file if it exists

# **23 Sep 2024 (4.44 patch 9 Program, 49 Installer)
* Minor (bug) fixes; internal updates
  * Enable MacOS v15 Sequoia for MacPorts on install. Did not attempt to update the MacPorts nor Python version. Save for v5 release major update still in progress. As it is, need to upgrade Cygwin release to get later htslib/samtools and python to even catchup to msys, ubuntu and macports releases now being used. Note that the change to these release notes causes a change to the program package and thus overall program version given.

# **30 Jun 2024 (4.44 patch 8 Program, 48 Installer)
* Minor (bug) fixes; internal updates
  * WES Coverage stats display corrected to use "Poz" instead of "WES" in the title when a Y only BAM.
  * Fixed bug introduced in Install_windows.bat that always reinstalls cygwin64 no matter what the version already installed is.
  * Clean up sequencer ID in settings to not mention BGI, Riga and now clearly mark v1 versus v2 chemistry of T7 and T10 models. What is Dante 2500 model (versus 1000 and 2000 from others)?
  * Fixed microarray combinedkit shell script generator for tab separator on sort. Left backquoted single quotes in extracted string assigned using raw string technique. Duh.

# **24 Jun 2024 (4.44 patch 7 Program, 47 Installer)
* Minor (bug) fixes; internal updates
  * Ubuntu 24.04 explicit support added. Is in v5 code but not back ported. One line in zinstall_common.sh but other implications due to newer Python.
  * Added "export PIP_BREAK_SYSTEM_PACKAGES=1" for PIP install to bypass new python venv setup (for now; not all releases to a higher python version to accept general code changes needed for venv)
  * Fixed Python 3.12 warnings regarding escapes in strings.  Either combined f-string and raw, or pulled needed escapes for shell commands into separate raw string variable. Some strings with warnings were simply multi-line comments ;( Ubuntu 24.04 has Python 3.12 default.

# **20 Jun 2024 (4.44 patch 6 Program)
* Cleanup to allow unaligned BAMs.  Somehow lost this feature over time. Key is their header is missing all SQ fields.  And certain calculations will fail (determining reference genome, paired end type, etc). Added new "Align" state (in addition to Sort and Index ones) to capture issue and then use that to disable user buttons like "To CRAM", "To WES", "Index", "Sort". Required fixes in other areas to detect if unaligned BAM and thus avoid anomolous calculations (paired-end type, etc). FYI, Unaligned BAMS are used in place of FASTQs in Broad Institutes true Best Practices pipeline. As this is an "off label" use of the SAM file spec, there is no specific definition of how to detect an unaligned BAM.

* Minor (bug) fixes; internal updates

# **13 Jun 2024 (4.44 patch 5 Program, v46 Installer)
* Minor (bug) fixes; internal updates
  * Rewrote wakepy use in commandprocessor.py due to change in program UI with v0.8 and greater. Forced version requirement in Python PIP installer for wakepy (scripts/zinstall_common.sh).

# **30 Mar 2024 (4.44 patch 4 Program. v45 Installer)
* Proof of Concept MSYS2 implementation for Windows 10/11 systems. To replace Cygwin64 with more easily maintained Windows ports of the bioinformatics tools.  With eventual goal to pull in Windows micromamba to have a universal bioconda installer everywhere that utilizes ucrt64 (minGW executables). Even better will be if the MSVC compiler effort works to compile all so there is no dependencies on UNIX-like libraries. This work caused cleanup of Windows .bat files and script/stage2windows.sh to handle alternate Windows environments (cygwin64 or msys2). And updates to settings.py for the alternate paths for the two installations that are both Windows.  Added Install_windows_msys2.bat which simply calls the original Install_windows.bat with an "msys2" parameter set.  Other .bat files are universal. Requires updates to make_release.sh for two additional packages in the latest-release.json file. Python and PIP library installations for Windows is only for cygwin64 as Teemu has it prebuilt into msys2. First OS/arch specific install in zinstall_common.sh (arggh). No windows_type selection variable is needed in .sh files.  Can simply look for cygwin64/ or msys2/ folder in installation.  Default is to always select / look for cygwin64 first.

* Minor (bug) fixes; internal updates
  * Minor fix to countingNs.py. Had incorrect start location for every run of N's bin due to an additional missing value in the calculation.
  * Minor fixes for unquoted path variables found in scripts/zcommon.sh and the Windows .bat files

# **30 Oct 2023 (4.44 patch 3 Program, v44 Installer)  (initial target date; not finally released until the following mid-March)
Minimal new functionality pulled in from the v5 release that has been internally developing and releasing for 12 months. Just fixes, mostly in the installer, for issues that have cropped up over the last 12 months. But because it took 8 months to get just this patch out, this has a lot more tweaking of functionality from v5 (installer, library manager) pulled in than we planned to do for a quick patch. Minor fixes / changes to the Python code to accomodate.
* Added Aaron's Micromamba linux installer (rewritten) to replace the _Linux.sh script. Will eventually deprecate the _ubuntu.sh scripts. Added the uninstaller, Library and WGSExtract scripts. Required updates to zcommon.sh and zinstall_common.sh to accomodate.  Will wait for more testing in a DEV release before replacing _ubuntu.sh for Ubuntu.  Uses Conda/Mamba/Micromamba packages and installer.  Makes Linux install more like the Windows release. The Bioinfo and other support tools are isolated to the WGSE Install directory. Making it easier to maintain consistency by not installing in the system area.  MacOS still uses MacPorts which installs everything in /opt/local. Maybe we can switch that to Conda also?
* Beginning the long awaited command line capability.  Made microarray.py callable from the command line with the outdir and bam file as parameters. Used to create the CombinedKit file from the command line. Not robust for other parameters or parameter errors yet.
* Tuned the command script output to only come on when the GUI is enabled, and the SHELL commands echoed only with the DEBUG mode on. Cleans up the user script in non-DEBUG GUI mode and removes everything when in command line mode.
* Now that DEBUG toggle is in the main GUI, made that button create or remove the .wgsedebug file in the users home directory as well.  So DEBUG is truly enabled from the start if left on at the last program exit. Still keep it as a file so it can be effective before reading in the stored settings file.
* Added version interpretation logic in the installer and program to handle multi-level version (that is, 4.44p2 instead of just 44). Is enough to allow existing installed program patches to update accordingly without a reported error. Will allow the installer to be patched in the future as well.
* Patched settings.py to: (a) recognize a new MGI T7 sequencer (or v2 flow plate version) that Dante Labs started using Summer 2023 (E200); and subsequently seeing in Nebula in Fall as well. Specifically report as BAD the T7 with the flow plate ID E2000006xxx from Dante as has been delivering nonsense results (many runs August through October 2023), (b) recognize a new MGI T10 sequencer (flow plate ID) of FP270.... Previously had only seen FP200. Used by the Riga, Latvia lab hired by ySeq and new Nebula/ProPhase runs. and (c) (re)recognize Dante's fourth Illumina Novaseq 6000.  Somehow lost recognizing it along the way.  Added back in.
* Changed all ftp URLs to https in seed_genomes.csv (except JHU who do not seem to have an https interface).  FTP protocol is no longer working in many curls; just as it has been removed from browsers. Avoids a 450 error that occurs after downloading all data when using ftp://. Changed ftp-trace.ncbi.nih.gov to ftp.ncbi.nlm.nih.gov in the 3 1K Genome files in reference/seed_genomes.csv. Made a special change to make_release.sh to include reference/seed_genomes.csv in the program package so it will update with the new release. Normally, in the past releases, is part of the reference package.  No need to update that just for this one file.  v5 already has it moved to the program package.
* Changed most embedded URLs in python programs and shell scripts to use new get.wgse.io site / server.  Allows us to update physical links without changing scripts. Furthering the JSON file URL functionality introduced earlier. Even the latest release json files are found on the new server as pointed to by release.json. Using github as the location will be deprecated.  Because we specifically avoided updating release.json in case someone locally edited it (like using it to change tracks), we used the hidden capability to force an update of the release.json file to install these updated pointers.  We can only check dates of files on our own server; not github nor our MS Onedrive cloud server. So this will help with non-versioned files that we will start downloading automatically when updated in the future.  Such as genomes.csv, language.xlsx and similar.  Helps us avoid doing releases (or waiting for releases) when all we need to do is update those files.  Will start adding more to loaded, independently updated files that we pull out of the code such as the mapping of sequence names found in reference models to the primary chromosome nomenclature.  And the sequencer name recognition and regex to pull out that key information. Note that the updated URLs in the tools and reflib packages will appear in the latest release JSONs but not in all the actual distributed JSONs in the packages until the next update.  Which is OK because only the latest release JSON URL's are used to grab the latest package.
* Major cleanup of installers to better detect errors, report them and then stop immediately.  Reduced messages during installation to make it easier to find any anomolies.  Changed cURL to use a progress bar instead of progress meter.  Used a more succinct and standard way to report activity from the install scripts themselves.  Eventually will add Aaron's technique used in the linux installer to "tee" the installation log into a file as well as to the terminal. And maybe get that working for the main python program itself so we can drop its terminal window all together.
* Fixed the hg38tohg19 liftover chain from UCSC that is used in the microarray generator.  It has actually been converting rCRS to Yoruba mito models all this time.  Essentially but a noop in the liftover chain for mito now as an effective, easy fix.  Instead of requireing a whole new reference library creation and download for users, I added it to the 4.44p3 program ZIP file (which happens to simply copy everything so I could put a reference/ folder entry there). Thanks to Wilhelm HO for pointing out this glaring error there since v1. Only applies to generating a microarray file from a build 38 model; as is the case for Nebula customers by default.

* Minor (bug) fixes; internal updates
  * Minor bug fix (syntax error) when trying to run a Y extraction on a Y only BAM (tries to simply rename the file but used the wrong variable name)
  * 503 error (server unavailable) starting to pop-up for some when doing a Windows Cygwin64 install. Put a specific, additional retry for that error in the installer. Basically run it anytime a non-2xx return code is detected.
  * Further checks for successful downloads in installer so more gracefully exit early when things go wrong. Some pulled in from already rewritten installer from March 2025 v5 pre-Dev release.
  * Modified keep_awake to work when GUI not turned on (mostly for command line tasks)
  * Removed unguarded, general exceptions in try's
  * Restoring a BAM file setting without an output directory already set (or in settings) caused installation directory to be used as if outdir.  Turned off trying to restore BAM if an output directory is not set.  Happens because v5 has a default outdir and so saves the BAM without a saved outdir.
  * Disabled the VCF section buttons; been active with a pop-up "coming soon" for over a year!
  * Added Sonoma to MacPorts installation on MacOS.  Improved MacPorts installer to recognize when an OS change occured since installed. Will then do an uninstall first. Ditto for Python upgrade.  Required updating MacPorts from release 2.8.7 to 2.9.1 (2.8 not available on Sonoma).
  * Cleaned-up (re)align command to fail more gracefully when intermediate errors.  Was sloppily falling through rest of stages and failing. Had fixed in v5 release last winter but pulled code in for this patch.
  * Long needed cleanup of BASH scripts for common commands like mv, cp, rm, and rmdir. Especially needed where rmdir done under sudo. New rm -rf has many checks to avoid deleting system areas (especially when under sudo)
  * Added titles to shell command windows
  * Major cleanups of scripts to pass shellcheck and new, stricter rules required by MacOS of all scripts in the distributed installer (whether MacOS targeted or not). Shellcheck has not been fully run for a year.
  * preloads jq in installer if not available yet.  Full install loads it eventually. But need it for new early version check. Ditto in make_release.sh if missing on MacOS platform.
  * reintroduced bug in windows installer that did not allow spaces in a path. Fixed.
  * clarified select reference genome pop-up text to indicate for current BAM (in BAM determination code) or new BAM (in (re)align command). Fixed opposite logic for when to include Unknown button in Reference Genome selector pop-up
  * improved make_release.sh to parameterize inclusion of release_override.json, That way can just edit that to create an installer that overrides the old release.json. And we do not have to worry about editing make_release.sh first. Eases testing.
  * Catch exceptions for trying to import multiqc, tkinter, and pyscreenshot.  Either set flags or handle appropriately in the code when then used (try - except guard block). Running into mixed support in the generic micromamba Linux installer. If pyscreenshot is not available, use PIL.imagegrab
  * Tuned common uninstaller logic to first ask if want to remove the WGS Extract program. Only if you want to remove it will it ask if you want to save the reference library. Keeps one from moving the reference library between disks if it was moved to another location outside the main program install area.
  * Minor word tweaking on some pop-up messages to clarify the intent better.
  * Refined make_release.sh to more accurately determine file updates (and indicate a BOM rebuild.  Also added "release" to create the final, user latest release files when building an installer; not just the developer ones.
  * Started a general fix to shorten terminal messages to 80 characters or less. So fits nicely on default terminal windows of that width. Fixed in most scripts. Python code not yet touched.
  * discovered cygwin64 ACL problem rearing its head on some installations using a mounted (not system) disk.  Added the noacl flag to the /etc/fstab file in the release. Done before the first call to BASH so permissions can be set appropriately.  Note, this does not fix an installation already experiencing problems. Only new installations; not updates.
  * reordered package installation so the program package is last.  Allows us to have simple file patch updates to the larger reference and tools packages in the program update
  * Added Ubuntu 24.04 recognition in the installer since it took us 7 months to get this "simple" patch out! Tools in that release may be delayed further but hopefully they will automatically fill in without further script changes.
  * Fixed reported typo in seed_genomes.csv using httos:// instead of https://
  * Removed is_legal_path check (now returns true always) as has never been correct.  A quick fix using pathvalidate does not seem to work with Windows path designators.  Need to investigate more. Also corrected report of Temp Directory error by not crashing on a null value setting (which is what was returned if is_legal_path returned false).

# **28 Feb 2023 (4.44 patch 2 Program)
* Minor (bug) fixes; internal updates
  * Introduced with v4.44 an error where hg38to19 script includes settings.py to use the command processor but settings and command processor try to use fonts when not in GUI mode. Slight tweeks to fix.
  * Needed quotes around library.bat and process_refgenomes calls with python executable for when WGS Extract is installed with a path with spaces in the folder name(s) (all part of Program; not Installer)

# **30 Jan 2023 (4.44 patch 1 Program, v43 Installer)
* Minor (bug) fixes; internal updates
  * Patched settings.py to recognize new Nebula/Prophase sequence names. Now the sequencer is properly recognized again.  Changed all Nebula IDs to ProPhase as they were all introduced by ProPhase changeover and have ProPhase in the sequence name.
  * Removed -Z option to curl in zcommon.sh as it is not supported on Ubuntu 18.04 and some other Linux variants with an old Curl (only change to installer; should have been a "patch")

# **07 Dec 2022 (4.44 Program, v42 Installer)
* Minor (bug) fixes; internal updates
  * Upgraded MacOS Python install to 3.11.0 for both archs.  Seems to behave better for MacOS Ventura. The installer is universal but specific for each arch (not using Rosetta).
  * Made WSL BWA button in DEBUG frame only enabled in Windows (has no effect in other OS's but why keep available). Reordered the DEBUG frame items to a more logical one.
  * Changed (new) base font size for MacOS to 13. Brings it visually inline with Windows (@ 12) and Linux (@ 8) (implemented last release).
  * Added base font point size and typeface to the DEBUG_MODE frame. Settings are stored (or cleared if set to default).  Settings may be unique per platform and are ignored if not available on that platform (default used).  You can experiment and let us know what you think a better font and size to use is.
  * Finally added a vertical scroll bar to the header pop-up window. Actually to all simple results including haplogroup results and unmapped reads.

# **03 Dec 2022 (4.43 Program, v41 Installer, v4 Cygwin64-bioinfo)
* Minor (bug) fixes; internal updates
  * User reported problem during installation where package downloaded succesfully but WGSExtractv4/ package folder was not created. Added extra error check for folder after the unzip. But had to add the path as the bioinfo package is not unzipped into the current directory like the others. Getting real work done is tough to deal with all the edge cases.
  * Added buttons in DEBUG frame for setting user overrides on (maximum) number of threads and total memory available to WGSE.  Had allowed the setting in the .wgsextract file previously (had to be hand edited in; undocumented).  Now allows it to be dynamically set and changed during the run (and user override value takes immediate effect). Ss saved and restored like other settings.
  * Discovered bug in htslib on the cygwin64 platform for windows which caused samtools sort to take 10x or more longer.  Corrected by turning off libdeflate option during compile.  Created new cygwin64 Bioinfo package release using same cygwin64 release of before but new binaries.  Thanks to Teemu for diagnosing and developing the solution.
  * Discovered MacOS UI cannot support colored buttons directly and so tkinter does not either. But package tkmacosx has been written, can be installed, and implements a colored Button class in place of Tkinter's default one. Fixes colored buttons on MacOS. Also had to fix restoring buttons to background color as MacOS changes the default background when the OS is in dark mode.
  * Fixed background color on Ubuntu/Linux GUI introduced when fixing similar issue in MacOS earlier.  Now inquire the default background color of the main window when created.  And use that for Frames and Notebook tabs. Ditto for initial button (get defaults and use that). Finally makes all platforms the same regarding coloring.
  * Reworked fonts system into a utilities module subsystem that is initialized in mainwindow_init.  This allows us to determine what fonts are available at the time of the first window creation and modify the program action accordingly. It cannot be determined before creating the first window.  As a result, WSLG Ubunutu use of WGSE is now the same as the other platforms (WSLg has a very limited font set). Touched just about every python code file as it changed the global settings where font defaults were initially defined.
  * Nit bug in installer for reference library package install.  Checked if directory exists using file parameter. Fixed to check that it not exist as a directory. Duh. Was just generating an inocuous error message when the directory already existed (like in an upgrade). But correct behavior otherwise.
  * As a result of these fixes, all three platforms appear the same (from the UI viewpoint); finally.  Still the clunky, old fashioned Tk GUI but at least the same now. Also, with the latest WSLg fixes to the file system over the last year, WSLg with Ubuntu is outperforming the Cygwin64 "native" win10/11 executables.

# **29 Nov 2022 (4.42 Program)
* Minor (bug) fixes; internal updates
  * Fixed code for early Dante (MGI) result files that have sequencer ID's starting with CL100 instead of C100 or V100.
  * Reduced minimum bam header size from 1000 bytes to 600 as a BAM aligned to the old WGSE v1 HG19 model has only primaries in the header (minimal header size).
  * Fixed typo for hg19_WGSE file name (was lower case in some places)
  * Fixed bug for when a root directory specified in win10 systems for the output directory was reported as in error (need to check for linux/unix systems)
  * Cleaned up Align button logic when input query window(s) cancelled; added hs38d1 to reference genome selection and renamed hs38s to hs38d1s in UI
  * UI colored the buttons only after the (first) BAM file selected. Fixed to happen when window is first setup as the Align and other buttons are available before then.
  * Changed pop-up about needed disk space for sort to be an OK / Cancel option selection (instead of just OK to continue).
  * Clarified CRAM use pop-up to simply state Stats is not automatically run but needed for other buttons to be enabled. Was already changed to only appear if CRAM selected and stats not run.

# **06 Nov 2022 (4.41 Program, v40 Installer, v7 RefLib)
* Added code to handle the (what we are calling) hs38d1 and hs38d1a models.  Nebula has switched delivering CRAMs aligned to a hs38d1 model. Although it existed on the NCBI server, it has never been used before that we are aware of. This updates the Program and Reference Library code and so both are updated in this release. For completeness, added the Verily hs38d1 model as well as the hg19 WGSE (25 SNs).
* Added (back) the sub-identification of internal lab sequencers -- not just the sequencer model. So Illumina NS 6000 (Dante), Illumina MS 6000 (FTDNA), etc. Had simplified it out in the last release when revamping the sequencer ID list. But now becomes more important for the new Nebula / ProPhase sequencer names being used.

* Minor (bug) fixes; internal updates
   * Cleaned up zcommon.sh and how the installation directory is found; when it is cd'ed into, etc.  So process_refgenomes.sh could be called standalone and from get_and_process_refgenome.sh; and make a call to python from within
   * Discovered reference library installer was checking settings changed location for version file but always installing into the default release location. Fixed and added installation items like removing genomes.csv.
   * Updated MacPorts to 2.8.0 and added MacOS 13 Ventura option to install list; changed source of Macports to Github URL instead of their previous release site of distfiles.macports.org
   * Commented out the call to the Library command at the end of Installers (only called for new installs). With auto-load of missing reference genome files, not really needed and confuses new users.

# **01 Nov 2022 (4.40 Program, v39 Installer, v6 RefLib) (patched 02 Nov 2022 with threads/totmem change)
* Added functionality so that when a missing reference genome is discovered and needed, allows the user to have the program download and process it before proceeding.  NEED NIH vs EBI option yet. Library command still exists for users wanting that option.
* Added hs37, hs38a, GRCh37- (base EBI 37 model), GRCh38-, T2T v1.1, T2T v1.0 and T2T v0.9 models to the Library manager and understood in the WGS Extract program now. Brings it up to 29 models. As we dropped the hg19_wgse model from v1/v2. Note that Build 38 Patch 14 still has not filtered into Gencode, Ensembl, etc. But none of the models in the Library have any patches anyway.
* Added os_threads and os_totmem to the saved settings; allowing a user to override them downwards from the measured values. Will be restored on restart.  Note that if you run when the CPU is very busy and not as much memory is available to the program, it will set a lower value that will stick.  The GUI to adjust the value will come later. User has to edit the .wgsextract JSON file for now to change.

* Minor (bug) fixes; internal updates
   * Minor updates to sequencer identification related to HWI-x. Still not sure about HWI-ST and -SN. Flow cells indicate HiSeq 1000-4000 but which Solexa model are they?
   * Cleaned up error reporting and checking for ref genome. Make clear (and fully implmenent) that can run Library command and then hit OK to missing RefGenome error dialog. Include RefGenome code with filename for user understanding of link in Library menu. Do not report double error when trying to load CRAM with missing RefGenome file.
   * Dramatically shortened and cleaned up previous get_and_process_refgenomes.sh file.  Split into zlibrary_common.sh for GUI menu implementation of Library command and get_and_process_refgenome.sh (singular) for actual work one one file. Greatly simplified code because created a reference/seed_genomes.csv file with the 19 entries currently defined. Eventually will expand with MD5sum of DICT entries and files themselves for further error checking. Also to make reference genome checker use the file to determine appropriate reference genomes.
   * Added generation of chromosome length and name to process_refgenomes.sh per reference.

# **11 Oct 2022 (4.39 Program and v38 Installer, v5 Tools)
* Added JRE v8 to all installers and uninstallers; setup settings.py to allow for the separate specification of jre8 versus jre 11-2x? only previously (jre17 is the actual installed). VariamtQC requires JRE8 (as does GATK3 and Picard). JRE11+ are really Java 2. 10 and lower are Java 1 (e.g. 1.8).
* Modified Oral Microbiome Frame and Unmapped Reads button to reflect Oral and Blood; and Kaiju and CosmosID tools. Modified final result frame accordingly as well.  Tool was not checking for existence of files before running; added that check and bypass so as not to recreate if already exist.
* Added single-end FASTQ generation to unmapped extraction command.  Also modified the command to not run and only show the result if the file(s) exists already.
* 665 MB added to the jartools folder versus only 10MB previously. Added DISCVRSeq.jar (VariantQC), gatk-package-4.1.9.0-local.jar (GATK4), GenomeAnalysisTK (GATK3) and Picard to the release im preparation for buttons utilizing them. DISC* is 320 MB and GATK4 is 310 MB. They include everything they includimg duplicate copies of other libraries. Most of which we do not need for our uses.
* Aaron added a more universal Linux installer and startup for more than just Ubuntu.  Uses microMamba to install locally like we do on Windows with Cygwin64. Better than apt for bringing in known versions and easier uninstall (like on Windows). Dumped in 4.39 DEV release with no documentation.

* Minor (bug) fixes; internal updates
   * Updated haplogrep.jar to the latest (2.4.0) from Github (https://github.com/seppinho/haplogrep-cmd/releases/tag/v2.4.0). Could switch to being installed by installer.  But as so small, will just keep the redistribuion in the tools package in place. Modified version # in manual and languages.xlsx
   * Added M_ as optional start for the Illumina Novaseq 6000 and HiSeq X sequencers ID / SNs.  Used in a number of ENA BAM / FASTQ files. Determined there is no sequencer ID and other info in the Ultima Genomics sequencer output (https://www.facebook.com/groups/consumerwgs/posts/1119975175264307/) and so cannot identify that sequencer at this time.
   * Added columns of primary chromosome names (SNs) to .wgse files and WGSE.csv table; in prep for creating seed table of SNs for python and BASH to read in
   * Fixed missing translation text in languages.xlsx for FastqFileBad error message -- used in Align button when requesting the paired-end FASTQ Files.
   * Found an ancient DNA BAM with (mistaken?) extra sample in the same BAM.  Modified the Microarray generation to cut out all after the first sample column so the CombinedKit remains a legal microarray RAW file format (was including extra columns for the extra sample values).
   * FINALLY, found a workaround for the askopenfilenames MacOS library bug. Kept getting fixed then reintroduced by Apple.  Determined that if we only include single-dot suffixes, it works in all cases.  So instead of allowing .fq, .fastq, .fq.gz and .fastq.gz; not only specify .gz instead of .fastq.gz and .fq.gz.  This is only in the MacOS version.  Makes unusable files selectable but does allow multi-file selection.  This plural open files was needed for the new VCF procesing button as well. Backported MacOS askopenfilenames() workaround into a new patched Beta v3 that is still active.
   * Expanded recognized Illumina sequencer IDs (and thus XY coordinate extraction). Discovered Illumina entries had it as X:Y:Tile and should have been Tile:X:Y (corrected).
   * Fixed bug when redisplaying WES Coverage stats after already created previopusly; stats result had no rows other than the title row
   * Decided was calculating WES mapped / raw ARD incorrectly. Was making WES mapped / raw ARD be opposite WGS one (mapped value larger) whereas with WGS the raw value is larger. There are no unmapped gbases in WES as we look at only the primary, filtered areas. So make the two ARD the same in WES and based on the RAW calculation. Was calculating mapped as total gbases / non-zero WES areas.
   * Restored and expanded 00README.txt in reference/ folder that was somehow dropped during Alpha release cycles; did not bump version so will no be reflected until the next Reference library update.
   * Fixed problem in determine_reference_genome() call. Was returning 0 instead of (0, "unknwn") in an assignment statement if the mitochondrial model could not be determined.
   * Fixed check for bam header return check to look for file size less than 1000 bytes instead of 0 bytes (empty). Now catches the bam header creation fail earlier.
   * Renamed sheet in languages.xlsx to v4 (was still v3)
   * Removed the weird hg19 model from WGSExtract v1 that was unique / not found anywhere else. Replaced with hs38a @ NIH for completeness of the 1K Genome Build 38 models. Expanded (R) to (Rec) for clarity in the selection labels.
   * Updated copyright header to include 2022.  Even though October and should probably just update from 2021 to 2023!
   * Never added to 25 Jul release notes that patched MyHeritage_v2 body file. Daniel discovered it was missing double quotes around the first column (rsID) entries. As v5 was first release in new version system, did not need to bump version (nor date)
   * Added check for liftover file existing before use. Changed DEBUG error messages for other liftover issues to typical error pop-ups and returns

# **23 Aug 2022 (4.38; and v.37 Installer)
* Minor (bug) fixes; internal updates
    * Bug in process_refgenomes.sh _uniq_ChrLNM5.csv generation; had wrong column selected.  Also removed redundant first column in _dict.csv generation.
    * Fixed adding new MacOS samtools sort fix to the button unalign (to FASTQs). Also had to add adjustment of 50% more temp file space required for a Name sort than a coordinate one (samtools sort is weird). Assume FASTQ files to be created are roughly equal in size to the BAM (or 2x the CRAM).
    * Verified caught all uses of samtools sort in the code now including in generating unmapped BAM. Assume unmapped file is 1/3 the size of the BAM. Should be rare when over 33%% of entries are unmapped.
    * Now provides a pop-up when doing samtools sort indicating the total temporary file space needed for the sort. Asking the user to assure it is available before proceeding. This after discovering Name Sort requires 50% more space than a Coord sort in the temporary directory.
    * Detects if asked for fastp on MacOS and app is not available; reports app is missing instead of reporting it cannot find the output file after the run failed.

# **17 Aug 2022 (4.37; and v.36 Installer)
* Fix for MacOS using samtools sort. MacOS has a limit of 256 open files per process; which samtools sort regularly exceeds for large BAMs (100GB and larger). So we now adjust the amount of memory available per thread so less than 250 temp files will be created. Must correspondingly drop the number of available threads. Potentially report error and do not do the sort if not enough memory available. Issue mostly on M1/M2 Apple machines with low memory and performance processor count.
* Minor (bug) fixes; internal updates
    * Changed Ubuntu JRE 17 install from -headless to full.  MultiQC required access to an X library only available in the desktop version even though GUI functions are never called.
    * Slight cleanup of README file for clarity (per Facebook posts / complaints by Alex)
    * Typo fixed in Library command (get_and_process_refgenomes) "(10) hg38 (ySeq)" which prevented hg38 from being processed after selecting

# **7 Aug 2022** (4.36)
* Filled in SNP and InDel buttons with standard code already used internally for microarray, y SNP, etc buttons.  Still have never seen bcftools generate an InDel though.  Know this is not correct code but part of the Developer release as we push forward.
- Added VCF stats capability. Relying on bcftools stats for now (really need a bcftools idxstats capability but they do not store the info in the TBI file like the BAI; although near identical).

# **31 Jul 2022** (4.35)
* Properly recognize human_g1k reference model BAMs now (call it hs37- for short). Human_g1k is already in the Library manager and delivered since v2. Just never usable. Invitae delivers sparse gene-panel tests in BAMs with this model. Old Nebula 0.4x tests used it also. Oddly, was already a selection in the pop-up reference model selector. So just more automatic in recognizing it and properly handling it everywhere internally.

* Minor (bug) fixes; internal updates
    * "wgse_FP" setting on some Win10 systems was returning DOS format. Added a cygpath -u call in zcommon.sh to fix.
    * FIXED Windows 4.34 installer was sometimes installing the bioinformatics tools into \usr\local on the current disk (instead of wgse_FP/cygwin64/usr/local).
    * Modifed get_and_process_refgenomes.sh to redirect the stdout of get_current_release_info to /dev/null to surpress its informational message output. Appeared above banner and dup of message in banner.
    * Added check in zcommon.sh for being run inside BASH; sourced by most scripts otherwise so makes it more universal.
    * Changed returns to return/exit in zcommon and zinstall ; just in case called dircetly and not sourced. zcommon is sourced by WGSE scripts so return was fine
    * Modified install_or_upgrade function in zcommon.sh to handle Alpha release 4m/4.33 version.json files. 4.34/4n changed them to package.json and the internal naming so they could be merged.
    * Errantly had the check of valid $OSTYPE after first use. Moved up appropriately.
    * Gave up on trying to fool the 4m release to autoupgrade to the new 4n release and installer. Asked people to overlay the new 4n installer on 4m to upgrade.
    * Moved make_release files into the scripts/ folder and thus part of the Installer archive (removed during installation still)
    * Moved Library* and scripts/*refgenomes.sh script files from Reference Library to Program package. Thus isolating all scripts into Installer or Program. And making the large reference library more stable and less prone to needing updates. As a result, changed the version number and date of the reference library back to reflect what just its content represents (instead of version 35 it is now 5).  Patches in installer code to handle this special case of version number regression.
    * Fixed introduced error. If RefLib redirected with a setting at installation then the default reference/ directory will not exist in the installation directory.  So delay reporting error of an unset or bad reference library until after trying to set default and restore saved settings.

# **25 Jul 2022** (4.34; would have been 4n in old style)
* Completed T2T model recognition / integration by bringing in the HG01243 PR1 "Puerto Rican with African ancestry"; Updated library installer, process_reference_genomes, referencelibrary.py, etc. All models used by the Y phylogeny commmunity should be covered now. "Realign" from any goes to the final T2T v2 release.
* Greatly expanded on the version json file and release management files and processing.  Added concept of release track (Beta, Alpha, Dev) to formalize the process.  Split out more, versioned packages that are now all mutex. Added a scripts/installer.json and release.json file.  The installer is versioned itself; and only it being updated causes a restart of the installer. The program package no longer has the installer scripts in it. The release.json file specifies the URLs of a base directory and files to find the latest available combined package version file, and specifies the release track to use of either Beta, Alpha or Dev(eloper). No longer have to mimix the installed directory structure for the individual latest release files to check.

* Minor (bug) fixes; internal updates
    * If Coverage stats already calculated and displayed in main Stats window, then do not destroy main stats window to regenerate.  Causes a needless flash (regenerate) of the main Stats window when no data is updated / added
    * Fixed common installer displays error of Library.* file(s) not found when trying to chmod after moving them
    - Windows installed into "Program Files" is causing Windows to require Admin privileges to run WGS Extract
    * Cygwin64 mirror.constant.com caused issues for user in Finland. As doing local install, can simply use a local dir name as the mirror.  Adjusted installer script to do so.
    * Adjusted the main program to pick up its version and date (and user manual link) from the program/program.json and release.json files.
    * Minor reformatting of 5 version.json files to be multiline and easier to read and edit; added two more. Renamed from version.json to $package.json
    - Windows uninstaller always still leaves the WGSExtractv4/cygwin64/bin/bash.exe file and its folders to it on the path
    * Fixed windows uninstaller ending with message "# was unexpected at this time"
    * Added version and location info into the banner for the Reference Library manager
    * cut-and-paste (widely) bug on the installation directory was fixed; caused problems when there was a space in the path (which it was supposed to fix).

# **05 Jul 2022**  (versions 4a-4m, or 4.15-4.33) (~1 year)
* Added VCF Frame to the last tab with buttons to modify and generate VCF files (similar to completing functionality for FASTQs during March minor update).  Hid buttons not yet implemented (InDel, CNV, SV, Filter) so only SNP and Annotated there now but functionality still in development.
* Added WES BAM generation to BAM file frame (routine was already there internally; just not added to the GUI yet). Moved Realign button to accommodate. WES BED files only available for Build 37 and 38.
* Replaced (WGS) Breadth of Coverage and WES Coverage buttons in Stats display with dedicated buttons in Summary column.  Both now run new Bin Coverage commands using samtools depth.  Summary values still displayed as before in main Stats page if data found.  But now hitting buttons, beside running Coverage if not yet run, will bring additional Stats window pop-up that gives Bin Coverage for primary sequences across multiple defined bins: -0, 1-3, 4-7, and 8-.  Previous (WGS) Coverage ran the samtools coverage command. That button has been removed.  Now all coverage results are due to custom processing the samtools depth command.
* Changed Avg Read Depth to Mean Read Depth; added Standard Deviation calculation and reporting.  Added mean Insert / Fragment size and standard deviation reporting (for paired-end only). Simply modified Wei Lei's getinsertsize.py script.
* Tuned Stats Breadth of Coverage Total row to (a) not include Other (alt contigs) (was already dropping unmapped and EBV), and (b) to not include Y when a known Female sample.  Was affecting final result by 1-2%. Brings better conformance with expected results.  Note the dropping of Other has an equal impact no matter the gender.  But is varied depending on the reference model chosen (hs38dh having the largest impact).
- Changed (re)Align (when BWA) to process messages and provide updating progress bar message in command script window. Replaces about 15 status messages every 1 million segment reads which makes the command script log useless.
* Changed (re)Align command to save _raw BAM file output from aligner in Output Directory and then only delete it after successfully creating a final BAM file. Ditto for new intermediate file _sorted. Helps for when (rare) markdup error is encountered after sorting. When DEBUG_MODE was not turned on, the previous output in the temp directory was wiped.  Saves considerable time to recreate the RAW file when stopping the program due to the markdup error.  _sorted file can then simply be used (and renamed) as final output with _raw then being deleted by hand. Files were in Temp directory before.
* Now handle the Telomere-to-Telomere DRAFT reference model of chm13 Autosomal and the HG002XY reference models.  Calling it build 99 for now. Note that there are many DRAFT versions with different model lengths per chromosome.  Set N adjust values to 0 per chromosome for now. Cleaned-up to handle advanced Illumina, PacBio HiFi and Oxford Nanopore advanced BAMs there with tens of thousands of base pairs per read segment. Required adding new reference genomes to Install Scripts, Reference Library module and BAM File module. Realign selects primary T2T v2 if Build 99, hs38 if already T2Tv2.
* Cleaned up Reference Genome Library installer to promote Recommended (3) reference genomes, added T2T model selection (6 in total), and dropped human_g1k_v37 and hg19_WGSE models from base 9 in All option. Also added EBI version selection option to new Recommended and to All option. Added new WGSE.dict generation.
* Modified WES button when a Y (or Y and MT) only BAM to use a CombBED / McDonald / Poznik merged BED file instead of WES one.  Buttons, labels and file names modified to use Poz instead of WES in those instances.
* Added fastp button and operation. Not yet available on MacOS (Intel and M1) or Ubuntu 18.04 as have not found binaries for those platforms (ditto for minimap2 there)
* Added fastqc button and operation.  New to v4 and requires install of FastQC Java program and MultiQC Python (pip). Currently using patched FastQC code as it has limitation when script and data files are not on the same drive in Windows systems.
* After building code to analyze runs of N's in the reference models, modified the code to account for differences in N counts between Major Builds AND Minor Classes (or analysis model types). See the updated Reference Model Study for more details.
* Added logic to remove button options for Build 18/26 and T2T Build 99 model BAM / CRAM's where VCF and liftover files are not available. Need similar for EBI-based reference model BAMs.
* Modified Realign button action to still work when automatic matching of a paired ref model is not found; simply defaults back to unalign / align action and asks user for reference file to use
* Added 23andMe v3 & 5 (merged) button generation and made it additional recommended option.  Reformatted Microarray selection screen to 2 column. In preperation for adding more output formats / vendors.
* Removed Microarray generation warning when not hs37d5 (too small an issue to really warn about); modified displaying CRAM warning to only when stats not run yet; modified text to reflect need to run stats to enable buttons instead of dire warning of time issues
* Added BAM Unselect button so can changed stored setting before exiting. Only other way, once one selected, was to edit or remove the .wgsextact saved settings file.
* Added support for sequencing.com 30x WGS output. Although using Nebula Genomics (AKESOgen / MGI) for kit / lab work, they are doing their own bioinformatics.  Recognize FASTQ file names (relative to BAM name) for align command. Recreated custom Sequencing.com reference model being used (GCA_000001405.15_GRCh38_no_alt_plus_hs38d1.fna.gz with numeric names and 22_KI270879v1_alt from hs38DH added) and stored on servers.  Added its recognition and handling in the python code and installer shells.
* Added Library_xxxxx.xxx scripts to run Reference Library Load and Process system directly. Is now the last call in Install_Common script (Install_Common last call in Install) to reference/genomes/get_and_process_refgenomes.sh.
* Added subdirectory to temp/ directory based on Process ID (pid) so can run multiple copies of the program at the same time with the same settings. Settings adjusted to save the non-pid root path.
* Added capability to PleaseWait to keep host processor from going to sleep (not available on Linux as requires sudo)
* Updated merged installer / updater scripts to check version installed versus available online and update if needed.  Split bulk of previous release out into a separate Reference Library subsystem release with separate versioning.
* Added uninstaller scripts for Ubuntu and Windows; added deletion of the WGS Extract install directory to all uninstall scripts (via zuninstall_common.sh)
* Pulled all Upgrade_ material either into the main Install_ or the former Upgrade_Universal.sh. Renamed Upgrade_Universal.sh to zInstall_Common.sh. Renamed all Start_* to WGSExtract.* . Created Library_* scripts to allow the reference/genomes/get_and_process_refgenomes.sh script to be run indepedently of the install. Preparing to move the Library_* and Install_* functionality mostly into Python. Leaving just the base Installer to bootstrap getting Python (and CygWin / MacPorts Base).
* Moved functionality of Upgrade scripts into either a common portion or the base Installer for that OS.  Dropped OS names from script files as extension unique identifies them (.sh for Linux, .command for MacOS, .bat for MS Windows). Renamed Upgrade_Universal to Install_common.sh. Created special Install_windowsstage2.sh for 2nd half of Windows install that can be done in BASH.
* Changed Windows install functionality to simply do a command-line cygwin64 full "base" install (with 7Zip and some other needed libraries included). Saves us releasing a sub-set environment that did not fully work.  Let's user more easily have a full Cygwin / BASH environment to run the tools.  The bioinformatic tools now naturally sit in the /usr/local/ area and are still separately downloaded from our server. The install is made from our own release capture of a stable set of versions from the time the bioinformatic tools were last compiled.
* Added a BAM Subset button (specify percent) to the DEBUG tab.
- Added a #Cpus and Mem per CPU override setting to lower these values from the read ones.  To see if gets around samtools v1.15.1 sort issues being seen.
* Added a DEBUG_MODE toogle button to the Settings Frame in the Settings tab. Same line as language selector.  Note that this causes the fourth DEBUG tab to appear or disappear.  And the Reload button on the language line to toggle as well. Initial state at startup is still not from saved settings but from the separate .wgsedebug file set by the user before program start.
* Improved recognition of sequence naming type by expanding list of accession types checked for and understood (both in the bamfile reference model determination code and the reference library installer shell script)
* Reference library installer now more formalized.  Added Library.xxxx for each OS to make the call to the installation script.  Scripts and installer picks up if the reference library has been moved in the stored settings and adjusts accordingly (putting the new files there; previously scripts only worked on original installation directory location.) New Library* script calls the get_and_process_refgenomes to get to that function directly. Installer only calls now IF a new installation with no previous reference library.  get_and_process_refgenomes script is parameterized for EBI vs NIH install sources on call.  Modified to reprint menu on each loop iteration. So took out exit on ALL / First-9. Only (1) Exit will exit now. Moved the scripts from reflib/genomes to scripts/ installation directory. (Removes issue of scripts run stand-alone not knowing where the WGSE installation is.)  Removed requirement in code when setting new reference library for it to be already populated.  So user can set new location of reference library and then either move the directory and content OR rerun the installer to install the latest in the new location. get_reference_genomes.sh functionality moved into get_and_process_refgenomes.sh file. process_reference_genomes.sh modified to handle more model types properly (accession names, T2T).
* As continuation of above (reference library formalization), moved microarray template files from program/ to reference/ library.  Split the release ZIP file into two.  Main program/ directory, (new) scripts/ and tag-along programs (haplogrep, yleaf and new FastQC). Then separate reference/ with its new Library* scripts and any additions in the scripts/ directory for this module. This new ZIP / reflib module is separately version tagged with a JSON file.
* Split the yleaf, jartools, and fastqc releases out from the Program ZIP release / version file.  Update dicated by the jartools/version.json file.  Even though a change of any will likely cause some program/ python changes and an update there, the changes to these large blobs are infrequent.
* Udpated Windows cygwin64 bioinformatic tools to the latest (samtools 1.15.1)

* Minor (bug) fixes; internal updates:
    * Cleaned up Align, Unalign and Realign for internal vs external calls; resuming main window. Error reporting pop-ups enhanced and expanded.
    * Corrected confused logic to make primary file input buttons only become available AFTER the Output Directory is set (BAM file select, FASTQ Align, Fastp. FastQC, VCF Annotate, VCF Filter)
    * Fixed invalid reference bug when one clicked the Align button before any BAM file selected. Now allows Align before / without a BAM loaded. Cleaned up bugs that still reference a BAM file if it existed when hitting the Align button directly (loaded BAM not correct).
    * Fixed misocnfigured error message triggered during startup settings restore for when temporary file directory no longer exists
    * Cleaned automatic stats run logic for intended action of only running when button hit directly or is quick & easy (BAM with index). Auto run Stats (not button direct) from Index button to save user one more step.
    * Split internal button routines for BAM and Outdir settings into separate user query and internal process routines; preparing to push more function into BAM file class and out of mainwindow GUI to more cleanly separate the two functions.
    * Refactored language i18n indices names to be more explicit when used as frame and tab labels
    * Added Monterey option to MacOS Install script for Macports. Updated links to Macports 2.7.1 from 2.6.2. Cleaned up to properly report error when major MacOS version is not available for MacPorts in MacOS Install script.
    * Updated MS Windows release to handle Win11 and Win10
    * Added Ubuntu 22 handling to Ubuntu installer
    * Ubuntu 18* does not have minimap2 or fastp in the apt repository (only minimap); fixed so load line does not error out and prevent other loads. Found releases to install directly when on Ubuntu 18.
    * Fixed error when unrecognized Build model in a BAM / CRAM (non 19/37 or 38) was generating python error instead of querying to select the likely model
    * Added error to report when missing a Refgenome file if trying to process a CRAM file (for stats, for example)
    * Added file name error report when not able to find various stats CSV files during processing due to creation errors along the way
    * Added more file name exist checks for reference library elements (due to many such files missing for T2T model files)
    * Sort somal and Mito entries in stats table before displaying; MT is not always last in a reference model. Now makes listing consistent and independent of the model order like for the Autosomes already. But should MT always be after X and Y?
    * Added default, dummy RG tag to BWA alignment command; similar to dummy done by Dante and Nebula now.  At very start, both had real RG's based on flowcell and lane.  That would be much harder as would have to split FASTQs by lane, align, then merge.
    * Changed functionality of process_reference_genomes.sh so when processing whole directory, deletes WGSE.csv, WGSE.dict, and *wgse files first.  So causes reprocessing there.
    * Fixed single-end FASTQ generation from a BAM file
    * Fixed microarray CombinedKit file generation for numeric named build 38 models; had M and not MT in the tab file passed to BCFTools and so mito was not getting generated (how did this get past testing all these years?)
    * Fixed stats so Y is not included in total for female samples (was enough to throw it off); moved Other row beyond Total to clarify that it is not included in Stats total (but is included in summary values to the right)
    * MacOS, in an update, changed the 50 year old "wc" program to add spaces before the count when printed with the file name. This has broken scripts in the old v2 and v3 releases.  Corrected now in v4.
    * Modified host processor determination on Apple MacOS with M1 processors to use the Performance Processor count only; not the "all" returned by traditional commands.
    * Changed all BASH shebangs to '/usr/bin/env bash' to try and avoid the bad BASH executables in MacOS and Windows OS bins (defaults).
    * Moved ref library T2T install source from our local WGSE MS OneDrive to the T2T AWS source after they finally added a chr name version (backup is at UCSC server for same).  MS OneDrive was throttling our link due to too many downloads.
    * Added clean and clean_all options to process_reference_genomes to clean out files created by that script or even downloaded by the user after initial release. Created more analysis files when processing a directory with many reference genomes.
    * Refined code in prep for batch mode (non GUI) to process -h (--help) and -v (--version) properly now; so python wgsextract.py -v will return the current version
    * Cleaned up installers to be less verbose. Saving long logs (python PIP, Cygwin64 setup) to text files for later perusal.  Added header bars for each major section of installation.
    * Consolidated the internal, common scripts into a scripts/ subdirectory of the release.  Moved the Reference Library genomes processing scripts there as well.  Pulled out common functions in each to a zcommon.sh script to include in them all. Updated installers, etc to accomodate.
    * Renamed this file to remove WGSE_ start to it. Simplifies directory so only file (starting) with WGSE is the start command / script to start the program.

BETA version 3 Final release (v3.12-3.14)
* A patch file replacement for mainwindow.py was provided in Sept 2021 to fix an error caught in regression testing but not fixed in the final 10 Jul 2021 release. Basically prevented the Align button from working at all.

# **10 Jul 2021**:
* Reworked Upgrade_UbuntuLinux.sh (all platforms) and reference/genomes/get*sh to create single new script (get_and_process_refgenomes.sh) with 17 choices instead of just yes/no in old Upgrade*sh script. Removed all the individual get_ref*sh scripts introduced in the 30 Jun 2021 release.
* Restructured install of WGS Extractv3 to create, from scratch, the win10tools/tmp and temp/ folders (even though in release .zip) so bad ACLs on previous installs do not propagate.
* Fixed minor bug in process_reference_genomes.sh that prevented handling multiple file parameters correctly
* Added -y option to win10 python self-extracting archive command in Upgrade_UbuntuLinux.sh so it does not give the user an option of changing the download location
* Minor refactoring of some internal names

# **30 June 2021**:
* Align and Unalign button added to GUI **Analysis** tab in new FASTQ frame.  This adds new request pop-ups for needed parameters and generalizes the sub-functions of the BAM Realign button.  Align works off any FASTQ file(s) specified and allows any of the 10 reference genomes to be chosen to make the target BAM or CRAM.
* Reference Genome selector window expanded and cleaned-up; Build number added to description string; mainly for the Unknown Reference Genome.
* Oxford Nanopore BAM / CRAM / FASTQ processing finished.  Mainly, added the minimap2 alignment command for the Align FASTQs button. Minimap2 is already part of Win10tools; added to the Ubuntu Upgrade script.  Minimap2 is not available in MacOS (not in any package manager we have found)
* Added individual get_and_process scripts for each of the 10 reference genomes in the reference/genomes folder. For when you do not want to run option (1) to download all ten files. Can run the individual script for a particular reference genome for when the tool reports the file is missing. Eventually this will all be moved into Python code and be done dynamically on demand. Also added -EBI versions of scripts for the 4 1K Genome models located on NIH servers.  The EBI script uses the EBI copy.  NIH servers seem to give problems to some in the EU.  EBI servers tend to be problematic for most others.  Gives one the option to try one or the other now.
* Refined the memory calculator for the samtools sort command to use 10% less of the available memory; then divided by the number of OS CPU processors available. Required adding psutil to the Python PIP library and as part of the install / upgrade.
* Reduced valid CombinedKit (zip'ped) metric from 5 MB to 500 KB (to better support Teemu doing ad-mixture analysis on aDNA samples)
* Numerous minor refactoring (e.g. in mainwindow names) and latent introduced bugs (e.g. in DEBUG_MODE unsort command) completed.

# **15 June 2021**:
Initial Beta v3 release.  List of major changes from Beta v2 (18 Feb 2020) through ALPHA v3.3 to v3.11 and this initial Beta v3.12.

A key new feature is the tool can take in a BAM or CRAM and all functionality works with either specification.  Also, you can use the tool to convert from one file format to the other. By any BAM, we include subset ones.  Not just WGS. FamilyTreeDNA BigY-500 and -700 BAMs.  Like Y- or mtDNA-only BAMs you create with the tool. All are accepted and used.

Another key feature is the ability to realign your BAM to a new reference model.  Results may not be as robust and complete as delivered by your WGS test vendor.  But is a start at offering comparable files with more options. Key is, it allows you to convert from Build 37 to 38 or back. Microarray file generation works best from Build 37. Y Haplogroup work from Build 38. Now you can do both in the tool.

The stats area has been dramatically reworked and added to.  Measures are made without including the 'N' values in the reference model.  This represents around 5% in both Build 37 and 38; and is over 50% of the Y chromosome itself.  So the values are now more accurate to what is really possible from the reference model.  Y now appears more accurate for the read depth actually available.  Additionally, the initial stats are delayed if not taking just a second to run (for an un-indexed BAM or any CRAM). And two new additional stats buttons are in the stats page itself. One to calculate the breadth of coverage and one to calculate stats for the WES (Exome) portion of the BAM / CRAM.  The latter is important for WGZ testers from Dante Labs.

There are many performance improvements.  For example, where possible, we look to see if a key intermediate file is available.  And if so, reuse it so significant time can be saved from having to regenerate it.  The CombinedKit with the microarray file generator is one key place this occurs.  We have also added functionality to determine the number of processor cores and specify the use of them if a benefit can be gained. Another area is creating the FASTQ from the BAM for realignment. Or the reference model index needed for alignment.

A save button has been added to all results screens (copy-paste of text is still not possible).  And they are all labeled with the BAM / CRAM file used to generate them as well as tool versions used to create them.

Settings are now saved and restored when restarting the tool. Saving time in operating the tool after a break.

Proper, more complete and robust installers have been built for the three platforms.  It is a constant catch-up with Apple as they keep changing what tools like this from outside their Apple Store are allowed to do.  So much so it becomes near impossible to have a single program / script that works on multiple OS versions. Please be patient if you discover one of these changes before we have a chance to diagnose and fix it. We removed the use of pre-compiled Applescripts and added .command "single click" files for MacOS.

The previous release was a 5 GB download. The actual Python and Bash shell script source code is only a little over a megabyte.  With reference data files for the Microarray generator and yleaf needing another 80 megabytes (compressed).  The vast majority of that download was the human genome reference models (5 at just over 1 gigabyte each).  And the Win10 bioinformatic and python tool release.  We now download as much of this as possible either during install or only on demand.  We also have a script to take your old installation and transfer any of these large files that may be needed so they do not have to be downloaded again. The initial download is simply the installer scripts.

Here is a mapping of the basic, standard reference genomes between the v2 and v3 releases:
| Beta v2b (18 Feb 2020) | Beta v3 (15 Jun 2021)           | Notes
| ---------------------- | ------------------------------- | --------------------------------------------
|hs37d5.fa.gz            | `*`                             | (no change)
|human_f1k_v37.fasta.gz  | `-`                             | (no change) ; not ever used
|GCA_000...set.fna.gz    | `*` hs38.fa.gz                  | renamed
|`-`                     | `-` hs38dh.fa.gz                | added, aka GRCh38_full_analysis...hla.fa.gz
|hg19.fa.gz              | `-` hg19_wgse.fa.gz             | renamed, in error and should not be used
|`-`                     | `*` hg19_yseq.fa.gz             | added, replaces earlier hg19.fa.gz
|`-`                     | `*` hg19.fa.gz                  | added, only true Yoruba hg19 model
|hg38.fa.gz              | `*`                             | (no change)
|`-`                     | `**` Homo_sapiens.GRCh37...fa.gz| added, only true EBI numeric-SN / GRCh models
|`-`                     | `**` Homo_sapiens.GRCh38...fa.gz| added, only true EBI numerc-SN  / GRCh models

`*` marked v3 models are the core, base ones that should be used most often.  `-` dash marked ones are there but likely not needed unless dealing with some ancientDNA that used them.  `**` marked models are new and the only numeric-Sequence-named models that some historically called 'GRCh'.

This adds 5 new models and nearly 5 GB more of space.  Two of the old models should not be used. They need only be saved if you used them outside of the WGS Extract v2 program (your own tool runs with samtools directly).

Although the UI appears very similar, the tool has, for the most part, been rewritten underneath. This to dramatically improve performance, remove spurious bugs throughout, and is more robust with an expansion of functionality.  We hope to improve the UI in the next release. The program went from 1600 Source Lines of Code (SLoC) to well over 6500 now. All the old code was refactored or rewritten.

This release started the day the old Beta v2 release was delivered on 18 February 2020.  And includes the patches made to that release over the next few months.  While we had hoped for a v3 release in June 2020 (and we did make an internal one), inevitable delays made us take another 12 months.  The largest issue was working to expand the code to handle any BAM (or CRAM) thrown at it. Many have started processing AncientDNA samples; which come in all varieties of formats and reference models.  We scoured the Internet and found well over 150 different reference models that BAMs have been aligned too.  We had to work to catalogue and characterize them. This is still a work in progress.

More detailed bullet notes on changes in this Beta v3 15 June 2021 release since Beta v2 18 Feb 2020:
(Taken from the Beta v3 manual forked on 15 June 2020 with ~~strike-through~~ suggested changes listed at the end. Removed from there once added here.)
* Added programs/tmp folder to Win10tools release to resolve BASH not finding /tmp error.
* Downloaded yleaf original .py's and undid many unneeded changes.  Also incorporated yleaf v2.2 upgrade to handle CRAMs. We still have many changes; some of which can be back ported into the yleaf master.
* Modified MacOS install to not check for dot, not install graphviz, and auto install python3 and macports
* Heavily modified MacOSX and Ubuntu Linux start scripts; renamed to Install_xxxxx.sh
* All files and paths are quoted everywhere. So embedded spaces are now allowed everywhere.
* The tool incorrectly identified BAMs based on the GCA*fna.gz reference model (aka hs38.fa.gz) as being GRCh38 (meaning, EBI Numeric naming) when it in fact is HG "chrN" naming.
* Pop-up warning on non-hs37d5 based models in microarray generation adjusted for clarity
* Stats adjusted for the N's in the reference model. (note: N's in the BAM file itself are not yet analyzed and reported on)
* As part of generalization for CRAM use, determine and specify the CRAM reference model where needed.  Also know about and create the CRAM Index file (.crai). Note that the .crai is not the same as a .bai. In particular, samtools idxstats cannot operate off the .crai and so takes scanning the full CRAM to generate results.
* Added a BAM to CRAM and CRAM to BAM button
* Generalized and fixed BAM to FASTQ unaligner. No longer using deprecated samtools bam2fq feature and instead samtools fastq one.
* Changed use of samtools mpileup (deprecated) to bcftools mpileup.
* Moved haplogrep jar file from standalone folder to new jartools folder (similar to parallel win10tools folder for Windows 10 executables). For future expansion to add GATK, etc. Updated to v2.2 as well.
* Updated yleaf v2.1 to 2.2 and back ported many changes and fixes added here
* Generalized all result windows to use common form. Added a Save and Close button to all.  Added a BAM file name, WGS extract tool version and current time/date stamp to all.
* Major cleanup of Y Haplogroup output page.  Added ISOGG tree button.  Cleaned up pop-up for more than 3 SNPs to more compactly present long lists of SNPs.
* Major cleanup on stats pages.  Added LOCALE numeric printing, scale factors on values (K, M).  Added Other to capture the rest of the sequences.  Fixed many bugs; especially when subsetted BAMs are supplied. Added more newly determined stats like number of sequences, reference model refinement, size of file, content of file (Auto, X, Y, Mito, unmapped). Clarified RAW versus MAPped values.
* Added tool version and release date to main banner at top. Added button to get to WGS Extract manual.  Moved the Exit button there instead of at the bottom of the screen.
* Cleaned up and created Class for handling temp directory. Fixed deletion of entries; especially for directories like the yleaf one. 
* Added DEBUG feature to provide more robust reporting, prevent deletion of TEMP directory entries when on, etc. 
* All windows have explicit close / exit buttons and handle cleanup in such cases consistently
* Tried to clarify and reduce amount of text, in general, to be more precise
* Added, more explicitly, the recommended files in the Microarray tool (Renamed from Autosomal to Microarray tool also.)  Added "select recommended" button and explicit close button.
* added -B option to mpileup calls to support Nanopore Long read files
* French language translation / form added (thanks François Boucher for translation). Portugese and Finnish also in process.
* Major rewrite and expansion to create new install scripts.  Simplified start scripts to just tool invocation
* Detects and indicates when a BAM is not sorted nor indexed.  Add buttons to sort and/or index the BAM. Removed automatic invocation. Do give a pop-up warning if not in his state.
* Cleaned up settings tab (first, main tab) to bifurcate settings BAM file support into separate frames.  Expanded data reported on BAM.  Added many BAM-specific buttons such as STATS (moved from last tab Analysis), Sort, Index, To/From CRAM, realign and show header.
* Settings now saved and restored with each run.  So language is remembered and restored without asking.  Added language button to settings frame of main tab to change language once set.  Added Reference Library and Temporary Files buttons to change from default installation location; if user wishes to move to more optimum location.  Last used BAM file and Output directory saved and restored; including any stats on the BAM.
* Added button to generate Yonly VCF file (from BAM; not the simpler subset from existing VCF). Add annotation although not required for feeding Cladefinder or yFull.
* Upgraded to newer 3.7.7 Python (from 3.7.3). Still using standalone WinPython "zero" release that does not require Windows installer. Removed from general release and handled directly by Win10 installer. Still retained 32 bit version (found issue with 64 bit portability still). Also found issues with 3.8 and 3.9 on Win10 (partly with PIP libraries) and so stayed with 3.7 Issues during Alpha testing with 3.7.7 and some libraries that were since upgraded force a Win10 upgrade to 3.8.9.
* Re-ported HTSLib tools (at first 1.10, then 1.11 and now) 1.12. All are 64bit now (new requirement for handling CRAMs).  Was v1.6 and v1.4 on Cygwin32 and MinGW64 before (using htslib 1.9 though).
* PIP upgrades to all packages relied on (Pillow 6.0.0 to 7.2.0, Pip from 19.x.x to 20.1.x, numpy and pandas used by yleaf (versions?), and removed items not needed that were left over in release (python-dateutil, pytz, setuptools, six).
* Added a generalized Please Wait to all calls of subprocesses. Gives tool running and estimated time. (Need to add a cancel button. Need to modify time based on # procs, speed of CPU and size of BAM)
* inlined "extract23" script variant used and greatly simplified.
* improved generated file names to remove extraneous text.  Some had over 25 characters added to a file name.
* Code refactored in major ways throughout. More robust in handling of file names to clearly demarcate native OS versus generic path.  Also quoting all paths.  Use "with open ... in" block instead of f.open, f.close, conditional expressions, f-strings instead of formats, lines limited in character length, used multiline string auto concatenation instead of multiple assignments with +=. Code modularized and many modules placed into classes that get initialized. Setup single global variable (settings.py) file that all can share in a common way (wgse.xxxxx)
* greatly simplified and pulled into python code the processing of a bam header, bam body and idxstats run.
