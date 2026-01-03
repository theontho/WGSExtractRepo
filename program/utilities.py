# coding: utf8
# Copyright (C) 2018-2020 City Farmer
# Copyright (C) 2020-2023 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""###################################################################################################################
  General Utilities module support for the WGS Extract system

   This file is included by all others; import
  So imports of library functions are buried in function definitions where needed.
   (None are called often so there is little penalty for doing so.)

  Classes: TemporaryFiles, LanguageStrings
"""
import settings as wgse


def time_label(etime):
    time_exp = (etime / 3600., 'hours')      if etime > 3600 else \
                (int(etime / 60), 'minutes') if etime > 60 else \
                (etime, 'seconds')
    return f"{time_exp[0]:3.1f} {time_exp[1]}" if time_exp[1] == 'hours' else f"{time_exp[0]:3d} {time_exp[1]}"


def DEBUG(msg):
    """ Old C Macro hack for programmer debug system; but remains as executed code in Python """
    if wgse and wgse.DEBUG_MODE:         # Could use __debug__ but does not save much as calls have if statement then
        print(f"DEBUG: {msg}")


def wgse_message(etype, title, bodyx, body):
    """ Global message utility.  But only show in interactive / GUI mode or if DEBUG is on"""
    from mainwindow import gui_popup

    if wgse.lang and wgse.lang.i18n:
        ttitle = wgse.lang.i18n[title]
        tbody = body if bodyx else wgse.lang.i18n[body]    # Is body translated yet? If not, then translate
        ptbody = tbody.replace("\n\n", "\n")
    else:
        ttitle = title
        tbody = body + ' (no language set yet)'
        ptbody = body

    if wgse.gui or wgse.DEBUG_MODE:
        if etype == "error":
            print(f'***ERROR: {ptbody}')
        elif etype == "warning":
            print(f'---WARN: {ptbody}')
        elif etype == "info":
            print(f'+++INFO: {ptbody}')
        # Other etypes (yesno, okcancel, yesnocancel) are all questions and only handled by the gui popup in the mainwindow

    if wgse.gui and wgse.window:
        return gui_popup(etype, ttitle, tbody)      # Some are questions with return of None, True and/or False


# Technically, Cygwin BASH will accept both forms.  And in fact, WinPython returns Win10 disk drive letters to
# start a path. Which most programs (CygWin bash included) seem to still accept even if they require a forward slash.
def nativeOS(path_FP):
    """
    From Universal to native OS specific.  Replace os_slash forward slash to back slash if Win10.
    Also handles drive designations buried in pseudo-Unix paths to proper Win10 system paths.
    Nothing to do on non-Win10 systems.
    """
    if wgse.os_plat == "Windows" and path_FP:
        if path_FP[0:9] == "/cygdrive/":            # Just in case; should never occur
            path_FP = f'{path_FP[10].upper()}:{path_FP[11:]}'    # Convert to Win10 Drive letter format
        elif path_FP[0:4] == "/mnt/":               # In case used WSL mechanism
            path_FP = f'{path_FP[5].upper()}:{path_FP[6:]}'      # Convert to Win10 Drive letter format
        elif path_FP[1] == ":":                    # Often drive letters still come through on Win10 systems
            pass
        elif path_FP[0:1] == "//":                 # Network drive
            pass
        path_oFP = path_FP.replace("/", "\\")       # Change to backward slash
    else:
        path_oFP = path_FP      # Nothing to do for Linux, Unix, MacOS
    # DEBUG(f'nativeOS: before {path_FP}, after {path_oFP}')
    return path_oFP


def universalOS(path_oFP, wsl_fix=False):
    """
    From Native to Universal OS Specific (back slash to forward slash on Win10)
    Is a no-op except in Win10.  Win10 has for forward / back slash change.
    wsl bwa is the only command line that will NOT accept win10 drive letters; so remove drive letters here
    """
    if wgse.os_plat == "Windows":
        path_FP = path_oFP.replace("\\", "/")      # Change to forward slash
        if path_FP[1] == ":":                      # Win10 Drive letter
            if wsl_fix:
                path_FP = f'/mnt/{path_FP[0].lower()}{path_FP[2:]}'  # Change driver letter to path
            else:
                # path_FP = f'/cygdrive/{path_FP[0].lower()}{path_FP[2:]}'   # Change driver letter to path
                # Leave as is; most programs do not follow or understand Cygwin introduced mount points
                # and Cygwin Bash understands windows disk letter specifiers
                pass
        elif path_FP[0:1] == "//":                  # Network drive; leave alone
            pass
    else:
        path_FP = path_oFP                          # Nothing to do for Linux, Unix, MacOS
    # DEBUG(f'universalOS: before {path_oFP}, after {path_FP}')
    return path_FP


def unquote(path):
    """ Simple routine to remove quotes surrounding a path; instead of simply calling .replace('"', '') """
    return path.replace('"', '')


# Todo Still needed?  Historical, before quoted path names everywhere.  Added space as legal character now.
def is_legal_path(path_to_check):
    """
    Check file path string for illegal characters. Space no longer illegal as have quoted paths everywhere.
    (but with quoted paths is this check even still needed?)
    """
#    import re
#    return re.match(r'^[\w%/\-:~.\s\\]+$', path_to_check)
#    from pathvalidate import is_valid_filepath
#    result = is_valid_filepath(nativeOS(path_to_check)) # Not dealing with Cygwin / Windows properly
    return True


def check_exists(file_oFN, error_mesg):
    import os       # Utilities gets imported all over so hide this import inside routine

    exists = os.path.exists(file_oFN)
    if not exists:
        wgse_message('error', 'errNoFileExists',
                     True, wgse.lang.i18n[error_mesg].replace("{{FILE}}", file_oFN))
    return exists


class Error(Exception):
    pass


class Warning(Exception):
    pass


######################################################################################################################
# Todo Temp Location should become part of a settings class; that also saves / restores settings
class TemporaryFiles:
    """
    A class to manage temporary files.
    Includes self.list for list of files and folders to clean; likely in the user specified output directory
    Optionally clears out user specified temp directory of all files.

    As of 1 Apr 2021, we have modified to use the os.getpid() of the process instance to create a subdirectory
    within the specified Temporary Files directory.  That way, multiple instances of the program can be safely
    started and run.
    """

    def __init__(self, default_FP, top_level=False):

        self.set  = None
        self.FP   = None
        self.oFP  = None
        self.FB   = None            # Now will always be the PID

        self.default_FP = None      # For the root "default"
        self.save_FP = None

        self.change(default_FP)     # Initial call uses this value to define default_FP

        self.list = []  # files to be cleaned that are not inside TempFiles area (helps limit os.remove calls)
        if self.FP:
            self.clean(True) if top_level else ""  # Start with a clean temporary files directory
        else:
            # Setting temporary files directory failed; really fatal and should probably exit (raise exception)
            DEBUG(f'***ERROR: Cannot set default Temporary Files directory: {default_FP}')
            del self

    def change(self, dir_FP):       # For when changing temporary files directory; including initialization
        """
        The real guts of the Temporary Files Directory setup.

        Note: no longer require the directory be empty.  We will setup a subdirectory based on the PID which will,
        by definition, be empty when we start.  OK if other files in the directory to start. This way we now support
        multiple instances of the program at the same time.
        """
        import os

        if not dir_FP:
            # Parameter with new Temporary Dirctory must exist
            return      # Simply return and ignore as null may be due to bad restore settings or user cancel

        dir_FP += '/' if dir_FP[-1] != '/' else ''  # Assure trailing slash; universalOS so always forward slash
        dir_oFP = nativeOS(dir_FP)

        if not (is_legal_path(dir_FP) and os.path.isdir(dir_oFP)) or \
           dir_FP in [wgse.install_FP, wgse.prog_FP, "/"] or \
           (wgse.reflib and (dir_FP == wgse.reflib.default_FP or dir_FP == wgse.reflib.FP)) or \
           (wgse.BAM and dir_FP == wgse.BAM.file_FP) or \
           (wgse.outdir and dir_FP == wgse.outdir.FP):
            # We want to make sure they do not specify an important area for the installation.  So we do not wipe
            # out important files when we initialize the temporary directory area. So do not allow the installation
            # directory, reference library, BAM source directory, or output directory areas (if set).
            # Or maybe simply a bad path (not a directory, does not exist, etc)
            # Trying to be extra careful as we delete any files or directories in the Temporary Files directory
            if wgse.lang and wgse.lang.i18n:
                wgse_message("error", 'InvalidTempDirTitle', True,
                             wgse.lang.i18n['errTempDirPath'].replace('{{tempf}}', dir_FP))
            else:
                DEBUG(f'***ERROR: Bad Temporary File Path: {dir_FP}')
            return

        # OK, finally, everything is good and we can set the values
        self.save_FP = dir_FP
        self.set = self.save_FP != self.default_FP
        self.FB  = os.path.basename(dir_FP[:-1]) # Trick; remove trailing slash so basename returns directory name
        # self.list[] is independent of the temporary files directory setting

        if not self.default_FP:     # If just initializsing, default is not set yet. Set to dir without PID yet
            self.default_FP = dir_FP

        # Adjust for process ID (runtime) based temporary directory
        pid = str(wgse.os_pid) + "/"
        if dir_FP + pid == self.FP:     # No change; nothing to do and not initializing. Silently return.
            return
        self.FP  = dir_FP + pid
        self.oFP = nativeOS(self.FP)

        if not os.path.isdir(self.oFP):  # Maybe resetting to old temp area where pid directory already exists
            try:
                os.mkdir(self.oFP)  # Create PID-based temporary directory if not there already
            except OSError:
                if wgse.lang and wgse.lang.i18n:
                    wgse_message("error", 'InvalidTempDirTitle', True,
                             wgse.lang.i18n['errTempDirPath'].replace('{{tempf}}', self.oFP))
                else:
                    DEBUG(f'***ERROR: Cannot create Temporary File directory: {self.oFP}')

        # Want to start with an empty temporary files directory to make sure not the wrong area we wipe out
        # So warn user if not empty.
        dir_contents = [x for x in os.listdir(self.oFP) if not x.startswith('.')]
        if len(dir_contents) > 0:
            if wgse.lang and wgse.lang.i18n:
                wgse_message("warning", 'InvalidTempDirTitle', False, 'errTempDirNotEmpty')
            else:
                DEBUG(f'+++WARNING: New Temporary File area already has content (# files: {len(dir_contents)})\n{dir_contents}')

    def clean(self, incl_temp_dir=True):        # To clean the list[] and temp dir
        import os       # for os.path.*, os.remove, os.listdir
        import shutil   # shutil.rmtree()

        # First, cleanup files on the clean-up list (ever specify a directory? maybe remove)
        for oFN in self.list:
            DEBUG(f"Clean Temp List has {len(self.list)} files or directories to clean:\n{self.list}")
            try:
                if os.path.isdir(oFN):
                    oFN += wgse.os_slash
                    shutil.rmtree(oFN) if not wgse.DEBUG_MODE else ''  # Careful: remove hieararchical tree
                elif os.path.isfile(oFN):
                    os.remove(oFN) if not wgse.DEBUG_MODE else ''
                else:
                    DEBUG(f"Cleanup object is not a file or directory? {oFN} (ignoring)")
            except OSError:
                pass
        self.list.clear()

        if not incl_temp_dir:
            return

        if not (self.oFP and os.path.isdir(self.oFP)):  # Just being extra careful; directory path not set or invalid
            DEBUG(f"***FATAL ERROR: No valid Temporary Directory set; inside wgse.tempf.clean(): {self.oFP}")
            wgse_message("error", 'InvalidTempDirTitle', True,
                         wgse.lang.i18n['errTempDirPath'].replace('{{tempf}}', self.oFP))
            exit()

        # Now clean-up the temp directory no matter what was listed in the cleanup global
        #  but do not clean temp directory if DEBUG mode is on -- want to save files for analysis
        for oFBS in os.listdir(self.oFP):
            oFN = self.oFP + oFBS  # make absolute
            try:
                if os.path.isdir(oFN):  # yleaf tempYleaf dirctory is only commonly occuring directory
                    oFN += wgse.os_slash
                    DEBUG(f"Clean_Temp dir: {oFN} (DEBUG_MODE = {wgse.DEBUG_MODE})")
                    shutil.rmtree(oFN) if not wgse.DEBUG_MODE else ''  # Must be careful; hierarchical tree removal
                elif os.path.isfile(oFN):
                    DEBUG(f"Clean_Temp file: {oFN} (DEBUG_MODE = {wgse.DEBUG_MODE})")
                    os.remove(oFN) if not wgse.DEBUG_MODE else ''
                else:
                    DEBUG(f"Cleanup type? {oFN} (ignoring)")
            except OSError:
                pass


######################################################################################################################
class LanguageStrings:
    """
      Internationalization subsystem providing language specific labels, buttons and messages via table lookup.

      Entry Points:
        __init__ (Class creation entry; takes in language.csv file spec. Read at class init)
        change_language  (waterfall call from read_language_setting; also from mainWindow language button)
        switch_language  (to set or switch a language mid-stream; creates new mainWindow if language change)

        In DEBUG_MODE, for language translators, there is a reload languages.csv button to recreate this class instance
         and start with change_language_setting again (like at program start). Purposely do not save set language
         so query pop-up happens again to help verify new languages.csv file loaded correctly.

      Note:
        Moved get_lanugage GUI to to mainwindow.py button_set_language (keep all GUI stuff there)
        Moved store / read language setting to generalized functions in settings module (added more settings)
        Greatly simplified this class then.
    """

    def __init__(self, language_oFN):
        """ Read in file language_oFN as init action. Is a CSV dictionary file of language translations
            wait till actually read_language_setting to then set language and active wgse.lang.i18n dictionary. """
        import openpyxl

        # Start by reading in the language.csv file to determine languages supported and their translations
        self._lang = {};   self.request = {}
        try:
            wb = openpyxl.load_workbook(language_oFN)
            ws = wb.active
            dim = ws.calculate_dimension()
            DEBUG(f'Language.xlsx Dimension: {dim}')

            first = True  ;  avail_langs = []
            for row in ws.iter_rows(values_only=True):
                if first:       # To get header row; does not seem to be a next in this package
                    num_of_lang = int(row[0])
                    avail_langs = [row[i+1] for i in range(num_of_lang)]    # iterate over # langs to read language names / key
                    self._lang = {key: {} for key in avail_langs}   # iterate langs to create empty translation dictionaries
                    first = False
                else:
                    # Rest of file is language translations with the Key in column 1 and each native string following
                    # A special entry is RequestLang that has language specific string to ask for a language setting
                    # _lang is a dictionary of dictionaries. Language is first key. First column in each row is next key
                    # Final dictionary has string representation (i18n) of the second key identifier.

                    k = row[0]  # initial element (col 0) is key index into language dictionary
                    for i in range(0, len(avail_langs)):
                        self._lang[avail_langs[i]][k] = row[i + 1].replace("^", "\n") if row[i + 1] else ""

            # Directory with language request strings for get_language pop-up; no reliance on internal _lang{}{}
            for i in range(0, len(avail_langs)):
                self.request[avail_langs[i]] = self._lang[avail_langs[i]]["RequestLanguage"]
        except Exception:
            print(f"***Error reading from system Language Strings file: {language_oFN}")
            raise ValueError
        self.language_oFN = language_oFN
        self.avail_langs = avail_langs
        # self.request = request
        # self._lang = _lang
        self.language = None    # Keep null; language not set yet; just the language translations
        self.i18n = {}          # only set to particular translation dictionary once language is selected
        self.selectLanguageWindow = None        # Used to save language window popup to cancel from here

    def change_language(self, language=None):
        """
        Called after loading settings from user file. If not set or not valid, query user.
        Local import to avoid loop. All GUI pushed to mainwindow module.
        """
        from mainwindow import button_set_language

        if not wgse.gui and (language is None or language not in self.avail_langs):
            # In auto / non-interactive mode, default to English if available, or first available
            # This avoids the popup dialog that would stall the process
            new_lang = 'English' if 'English' in self.avail_langs else self.avail_langs[0]
            DEBUG(f"Auto-selecting language: {new_lang}")
            self.switch_language(new_lang)
            return

        if language not in self.avail_langs:      # If requested language not set or not understand
            button_set_language()           # Ask user for language; calls switch_language() directly
        else:
            self.switch_language(language)  # Switch language

    def switch_language(self, language):
        """
        Language Subsytem function to set/switch language; externally called to change language.
        May be called before initial window is setup; called as result of set_language pop-up dialog and buttons
        """
        from mainwindow import mainwindow_reset, mainwindow_resume

        # If got here from the Language Selection button; destroy its pop-up window (ignore errors)
        # We saved the window ID in the class' local variables
        if self.selectLanguageWindow:
            try:
                self.selectLanguageWindow.destroy()
            except Exception:
                pass
            self.selectLanguageWindow = None

        if language == self.language:           # If no change, then simply return
            pass
        elif language not in self.avail_langs:  # If not valid language to switch too ...
            DEBUG(f'*** INTERNAL ERROR: Unknown language: "{language}"; ignoring')
        else:                                   # Everything OK; setup new language translation for selected lang
            self.i18n = self._lang[language]    # Set wgse.lang.i18n to selected language dictionary
            self.language = language            # Save current language in class
            DEBUG(f"New Language: {language}")

            if wgse.window and wgse.dnaImage:   # Only reset mainwindow if exists and setup (wgse.dnaImage is set)
                mainwindow_reset()              # Destroys current window and runs mainwindow_setup() again

        if wgse.window and wgse.dnaImage:
            mainwindow_resume()


######################################################################################################################
class OutputDirectory:
    """
    A class to handle the Output Directory setup.  Mostly for changing it in a consistent way from the users button
    as well as the stored setting.  And to move the functionality out of mainwindow so it can focus on UI.
    """

    def __init__(self):
        self.oFP   = None  # Output directory path (user specified)
        self.FP    = None  # Output directory path (user specified) (Unix/Universal format)
        self.oFPB  = None  # Output directory path with BAM basename (both user specified)
        self.FPB   = None  # Output directory path with BAM Basename (both user specified) (Unix/Universal format)
        self.FB    = None  # Output directory path (user specified) basename (not BAM but last directory name in path)

    def change(self, new_FP):
        """
          Called to change (or initially set) the Output Directory.
        """
        import os

        if new_FP == self.FP:
            return      # No change; simply return. Especially if stll None

        new_oFP = nativeOS(new_FP)

        # If a valid and legal output path; then set the global variables for this new setting
        if is_legal_path(new_FP) and os.path.exists(new_oFP) and os.path.isdir(new_oFP):
            self.FP = new_FP
            self.oFP = new_oFP
            DEBUG(f"Output Path (final): {self.FP}")
            if wgse.BAM:
                self.FPB  = new_FP  + wgse.BAM.file_FB
                self.oFPB = new_oFP + wgse.BAM.file_FB
            # Like the Unix basename() for directories; save last name in path
            self.FB = new_FP.split('/')[-2] if len(new_FP.split('/')) > 1 else new_FP


######################################################################################################################
class FontTypes:
    """
    Setup in mainwindow_init() after the first call to Tk(), this stores the fonts that will be used for the UI.
    OS platform dependent. Must be dynamically called by each routine using fonts to get the latest setting.
    """

    """ def __new__(self):
        try:        # Should never be called if tkinter is not available, but just in case...
            from tkinter.font import families       # Historical reason for isolated import
        except (ImportError, TypeError):
            print(f'FontTypes class create when tkinter does not exist; in GUI mode?\n')
            return None
        return super(FontTypes, self).__new__(self) """

    def __init__(self):
        from tkinter.font import families       # Historical reason for isolated import

        if wgse.os_plat == "Darwin":
            self.face   = "STIX Two Text" if "STIX Two Text" in families() else "Times New Roman"
            self.facelg = "Arial Black"
            self.basept = 13
        elif wgse.os_plat == "Linux":
            # WSLG with Ubuntu has very limited fonts so use DejaVu Serif and Ubuntu if so; also needs smaller pt sizes
            self.face   = "Times New Roman" if 'Times New Roman' in families() else "DejaVu Serif"
            self.facelg = "Arial Black" if "Arial Black" in families() else "Ubuntu"
            self.basept = 9
        else:   # Windows; nominal
            self.face   = "Times New Roman"
            self.facelg = "Arial Black"
            self.basept = 12
        DEBUG(f'Fonts (init): face {self.face}, size {self.basept}, available {self.face in families()}')

        self.default_face = self.face
        self.default_facelg = self.facelg           # Cannot be changed in UI or stored settings currently
        self.default_basept = self.basept

        self.table = self._newtable()

    def change(self, newface=None, newfacelg=None, newbasept=None):
        from tkinter.font import families       # Historical reason for isolated import

        change = False
        if newface is not None and newface != self.face:
            change = True
            self.face = newface if newface in families() else self.default_face
        if newfacelg is not None and newfacelg != self.facelg:
            change = True
            self.facelg = newfacelg if newfacelg in families() else self.default_facelg
        if newbasept is not None and newbasept != self.basept:
            change = True
            self.basept = newbasept if 6 <= newbasept <= 20 else self.default_basept

        if change:
            DEBUG(f'Fonts (change): face {self.face}, size {self.basept}')
            self.table = self._newtable()

    def _newtable(self):
        return {  # Ugly hand-coded window GUI.  This at least gets us a little more generality ...
            '12': (self.face, self.basept),  # For version/date/time in Title and various result pages (below min size)
            '13': (self.face, self.basept + 1),  # Stats by-chr table; Title manual / exit buttons (below min size)
            '14': (self.face, self.basept + 2),  # Minimum size per Marko (for laptops / Macbook with 1366x768 screen)
            '14b': (self.face, self.basept + 2, "bold"),
            '14o': (self.face, self.basept + 2, "overstrike"),
            '14u': (self.face, self.basept + 2, "underline"),
            '16': (self.face, self.basept + 4),
            '16b': (self.face, self.basept + 4, "bold"),
            '18': (self.face, self.basept + 6),
            '18b': (self.face, self.basept + 6, "bold"),
            '20b': (self.face, self.basept + 8, "bold"),
            '28b': (self.face, self.basept + 16, "bold"),
            '32': (self.facelg, self.basept + 20)  # Main Window Program Title; font face is fixed per platform / init
        }
