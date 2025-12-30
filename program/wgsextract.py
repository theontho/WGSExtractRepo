#!/usr/bin/env python3
# coding: utf8
# Copyright (C) 2018-2020 City Farmer
# Copyright (C) 2020-2023 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""###################################################################################################################
  Main WGS Extract program module. As can see, is pretty devoid of effort.  Simply gets global system setup via
  settings module. Then calls the mainWindow processing subsystem setup and loop to wait on a user button input.
  Included by all other modules that need settings. Hence kept simple as well with local imports inside wgse_main()
"""
import os
import sys
from argparse import ArgumentParser

import settings as wgse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # Needed for Windows Embedded Python


def get_arguments():
    """
    For stand-alone, command line invocation (or even double click in GUI after associating BAM/CRAM file
    types with program)
    Todo implement this feature; template / fragment now
    Todo processing if standalone file name without other args
    Todo help args need internationalization
    """

    parser = ArgumentParser(prog='WGSExtract',
            epilog=("If no options are specified, an interactive GUI mode is assumed. \n"
                    "BATCH MODE FROM THE COMMAND LINE IS NOT YET IMPLEMENTED."))

    # -h, --help is automatic with ArgumentParser
    parser.add_argument("-v", "--version", action='version', version=f'WGSExtract {wgse.__version__}')

    # Really a required button for batch mode; but optional because without any args starts interactive mode
    parser.add_argument("-p", "--process_button",
            dest="button", required=False,
            help="Button you wish to process (required for batch mode)", metavar="BUTTON_TO_CLICK")

    # Mutually exclusive arguments (only one of the three can be used; target file to work on)
    # Not required because can be in stored settings from previous run
    mutex = parser.add_mutually_exclusive_group()

    mutex.add_argument("-b", "--bam",
            dest="Bamfile", required=False,
            help="BAM file to process")

    mutex.add_argument("-c", "--cram",
            dest="Cramfile", required=False,
            help="CRAM file to process")

    mutex.add_argument("-f", "--fastq", action='append',
            dest="fastq", required=False, nargs='+',
            help="FASTQ file(s) to process (two if paired-end)", metavar="FASTQ_FILE")

    align = parser.add_argument_group('required_alignment_button_args')

    align.add_argument("-n", "--new_outfile",
            dest="newfile", required=False,
            help="New BAM/CRAM file to create (with a .bam or .cram extension)",
            metavar="NEW_BAM_CRAM_FILE")

    align.add_argument("-r", "--reference_genome",
            dest="refgenome", required=False,
            help="Reference genome file to align to", metavar="REFERENCE_GENOME_FILE")

    # Rest of arguments
    parser.add_argument("-o", "--output_directory",
            dest="outdir", required=False,
            help="Folder for all Output files", metavar="OUTPUT_DIRECTORY")

    parser.add_argument("-l", "--library",
            dest="reflib", required=False,
            help="Reference library directory", metavar="REFERENCE_LIBRARY_DIRECTORY")

    parser.add_argument("-t", "--threads",
            dest="threads", required=False, type=int,
            help="Processor threads to use (override)")

    parser.add_argument("-d", "--debug", action='store_true',
            dest="DebugMode", required=False,
            help="Turn on Debug Mode")

    return parser.parse_args()


def wgse_main(module, interactive):
    """ WGS Extract main program start as independent task. Gives a direct call. """
    from mainwindow import mainwindow_setup

    # Start WGSE subsystem with all the main program settings (settings.py)
    #   Used to be a class; now just module to remove an additional layer of naming
    # print("Starting WGS Extract ...")  # Put in each startup shell script so appears before any errors
    # wgse.init(interactive)     # Includes all subsystem init calls including mainwindow_init

    if module == '__main__' and wgse.gui:
        # Print explanation to command script window, setup main window, let's go
        print(wgse.lang.i18n["ExplainWhyTerminalWinIsOpen"])
        wgse.window = mainwindow_setup()
        wgse.window.mainloop()  # Go wait for a button click on the main window ...


# ***************MAIN PROGRAM*******************
if __name__ == '__main__':
    from mainwindow import set_output_path, set_BAM_file

    if not (1 <= len(sys.argv) <= 2):
        print(f'Usage: {sys.argv[0]} [ <bam_file_name> ]')
        print(f'       If output directory is not specified in the settings, it is set to the location of the BAM.')
        exit()

    # If --version or -h/--help are present, handle them before full init
    if "--version" in sys.argv or "-v" in sys.argv or "-h" in sys.argv or "--help" in sys.argv:
        parser = get_arguments()
        parser.parse_args() # This will handle --version or --help and exit
    
    wgse.init(interactive=True)     # Reads and restores settings BEFORE processing args

    # args = get_arguments()      # Todo Place holder. Intent is to allow complete batch mode processing (no gui)

    # Restore BAM if specified on the Command Line -- to setup OS File association of WGSExtract to BAM and CRAM files
    if len(sys.argv) == 2:
        set_output_path(os.path.dirname(sys.argv[1]))
        if not set_BAM_file(sys.argv[1]):
            exit()      # Already reported issue

    # Todo If (command) args, use batch mode; otherwise startup interactive

    wgse_main(__name__, interactive=True)


"""
  To use the global settings in other modules, we need the following code:
    import settings as wgse
  
  Instead of a class Settings in settings.py, we instead use a simple module settings.py with all the global 
   variables defined and initialized at the top level there. Then simply define an init() function that is called
   from the wgsextract main area. If using a class, it requires an extra level of naming as there are no globals.

  Both techniques still require the additional line:
    font = wgse.font
  which exists to get a global variable without any context / module path.  Simply shortens the common name in the GUI.
  Works only if it is a static value. As it is not now, we use local font = wgse.fonts.table instead.
"""
