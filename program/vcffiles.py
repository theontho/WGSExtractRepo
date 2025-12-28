# coding: utf8
# Copyright (C) 2018-2020 City Farmer
# Copyright (C) 2020-2023 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""###################################################################################################################
    VCFFile (class; vcffiles module) is the central handler for all things VCF.  Processing, determining stats,
    manipulating, etc.  The idea is a class instance for each VCF file specified.  Initially supporting multiple
    identified in the program (mostly as automatically found from the BAM specification).  But eventually
    raising VCFs to the same level and class as BAM (and eventually FASTQ also).  Once a VCF file(s) is selected
    in the interface or by the program automatically, stats on it will be collected and saved here for each file.

    VCF files are tougher in that there is even less information in the header about what they may contain. In lieu
    of scanning the whole file, we develop some quicker heuristics here as well (like done for BAM files).

    Although only created in Oct 2022, it contains replicated / modified code from the BAMfiles which has still some
    remnants from the original, single wgsextract.py file from v2.  So retained full copyright.
"""

import os       # for path, stat
from math import sqrt       # for process_bam_body
from vcf_parser import VCFParser

from utilities import DEBUG, is_legal_path, nativeOS, universalOS, unquote, Error, Warning, wgse_message
from commandprocessor import run_bash_script
from fastqfiles import determine_sequencer
import settings as wgse


######################################################################################################################
# BAM File Processing Error Classes
class VCFContentError(Error):
    def __init__(self, reason):
        self.reason = wgse.lang.i18n[reason]


class VCFContentErrorFile(Error):
    def __init__(self, reason, file):
        self.reason = wgse.lang.i18n[reason].replace('{{FILE}}', file)


class VCFContentWarning(Warning):
    def __init__(self, reason):
        self.reason = wgse.lang.i18n[reason]


######################################################################################################################
# VCF File Processing class

class VCFFile:
    """
        VCF File class object; including all stats and processing thereof
        In init, simply assert if error and let outer caller worry about deleting the object
        (i.e. we assume within invoked from within a try...except). Errors will be of class VCFContentError
        with an additional message parameter. The message parameter must be a LanguageStrings dictionary key.
    """

    def __init__(self, VCF_FN, nameContent):
        """
        True Class init that simply sets up the Class variables by initializing them (even if None).
        BAM file initialization is then called via _setup_BAM file at the end. Which can be called directly (internally)
        as well to setup a new BAM. But generally best to drop the Class instance and start over.

        nameContent is or subset of ({'SNP', 'InDel', 'CNV', 'SV'}, {'A', 'X', 'Y', 'M'})   # include "O"ther contigs?
        """
        self.file_oFN  = None   # Various renditions of the VCF file name, path, etc
        self.file_oFPB = None
        self.file_FN   = None
        self.file_qFN  = None
        self.file_FBS  = None
        self.file_FPB  = None
        self.file_FP   = None
        self.file_FB   = None
        self.file_FS   = None

        self.file_type = None    # for "VCF" or "BCF" (will we ever see BCF?)
        self.var_type  = set()   # e.g. {'SNP'. 'InDel', 'CNV', 'SV'}

        self.Header    = ""      # Will save complete VCF Header in text form (bcftools view -h)
        self.file_stats = None   # File Stat result (for file size and other items)

        self.Refgenome = None    # {hg,GRCh}{19/37,38}, hs37d5, hs38DH (not all combinations valid)
        self.RefgenomeNew = None  # Following Reference Model study: hg, 1kg, ebi, ncbi
        self.Refgenome_qFN = None  # quoted File name of reference genome used for VCF

        self.RefMito   = None    # rCRS, Yoruba, RSRS
        self.SNTypeC   = None    # "Chr", "Num" or "Acc" (NCBI Accession #)
        self.SNTypeM   = None    # M or MT
        self.SNCount   = 0       # Count of '##CONTIG=<ID=' entries in Header
        self.Build     = None    # Major Build (19?, 36, 37, 38, 99 for T2T)

        self.Yonly     = False   # Y only is Y only or Y and MT only (BED files include MT for that reason)
        self.Monly     = False   # M is mito only (not expected but just in case)
        self.Primary   = False   # Set true if A, X, Y and/or MT are set

        self.Indexed   = False

        # todo The following values are immutable once set; could be a tuple or fixed-key dictionary instead
        self.raw_IDs      = 0
        self.filtered_IDs = 0

        self.Stats        = False   # Will delay calculating basic stats if file not indexed

        self.stats_chroms = []  # Summary table by primary (nuclear chromosome and mito entries)
        self.chrom_types = set()  # Stores type of variants by name; e.g. {'A', 'X', 'Y', 'M'}

        self._setup_VCF(VCF_FN, nameContent)

    def _setup_VCF(self, VCF_FN, nameContent):
        """ Check VCF File name / path is legal; fill in basic stats from VCF file if so. Assert on error. """
        VCF_oFN = nativeOS(VCF_FN)
        if not is_legal_path(VCF_oFN):
            raise VCFContentError('errVCFFileSpecialChars')
        if not os.path.isfile(VCF_oFN) or os.path.getsize(VCF_oFN) < 10000:    # file is bad
            raise VCFContentError('errVCFContent')

        # set_VCF_file_settings ... just doing file names. Most content set later while processing file.
        self.file_oFN  = VCF_oFN
        self.file_FN   = VCF_FN
        self.file_qFN  = f'"{self.file_FN}"'

        self.file_FP   = os.path.dirname(VCF_FN)
        self.file_FP  += '/' if self.file_FP[-1] != '/' else ''  # Assure trailing slash; universalOS so forward slash

        self.file_oFPB = os.path.splitext(VCF_oFN)[0]
        self.file_FPB  = universalOS(self.file_oFPB)

        self.file_FBS  = os.path.basename(VCF_FN)
        self.file_FB, self.file_FS = os.path.splitext(self.file_FBS)
        self.disp_FBS  = self.file_FBS if len(self.file_FBS) < 31 else f'{self.file_FBS[:12]} ... {self.file_FBS[-13:]}'

        self.file_type = self.file_FS[1:].upper()    # strip leading dot and upcase
        if self.file_type not in ["VCF", "BCF"]:    # Internal call may pass an incorrect file
            raise VCFContentError('errVCFFileExtension')

        self.file_stats = os.stat(self.file_oFN)
        if self.file_stats.st_size < 10000:
            raise VCFContentError('errVCFFileEmpty')
        self.relfsize = max(0.01, self.file_stats.st_size / (45 * 10.0 ** 9))    # Relative size to 45GB (time adjust)

        # Do a bunch of quick things, custom here, that lets us characterize the BAM a bit. May pop-out witha Raise ...
        wgse.VCFs += self               # May need within the below calls, so setup global setting now
        self.process_vcf_header()       # Quick but may have error exceptions
        self.process_vcf_body()         # Little longer (10 seconds max) but key ones like read length, etc.

        # We have three samtools stats commands we can run. But IDXStats takes only a second if this is a BAM file
        # with an index.  So try stats call to enable the rest of the GUI buttons (change_status_of_actiona_buttons).
        # May "raise" a warning.  Handles if any or all stats files already exist.
        try:
            self.get_samtools_idxstats(button_directly=False)
        except Exception as err:
            # raise VCFContentErrorFile('errBAMNoIDXStatsFile', f'{self.file_FB}_idxstats.csv')
            wgse_message("error", 'errNoFileExists', True, err.reason)
            return

        #  There are three get**stats calls. Each will call process**stats if the previous run exists or newly creates
        #  the file when button_directly=True.  Will call all three get**stats calls when clicking
        #  on the Stats button (with button_directly=True on samtools_stats only). Idea is if any stats
        #  files exist from a previous run, will immediately read and process them.

    def process_vcf_header(self):
        """ Reads and stores BAM header. Sets BAM.CoordSorted also. Does not need BAM Index file (.bai). """

        # Rewritten to process more of header; and process header in Python and not BASH AWK/GREP scripts
        samtools = wgse.samtoolsx_qFN
        bamhead_qFN = f'"{wgse.tempf.FP}bamheader.tmp"'
        bamfile  = self.file_qFN

        commands = f'{samtools} view -H --no-PG {bamfile} > {bamhead_qFN} \n'

        run_bash_script("GetBAMHeader", commands)

        bamhead_oFN = unquote(nativeOS(bamhead_qFN))
        if not os.path.exists(bamhead_oFN) or os.path.getsize(bamhead_oFN) < 1000:  # Command success check
            raise VCFContentError('errBAMHeader')
        try:
            with open(bamhead_oFN, "r") as f:
                self.Header = f.read()
        except Exception:
            raise VCFContentError('errBAMHeader')

        if "SO:coordinate" in self.Header:
            self.Sorted = True
        elif "SO:unsorted" in self.Header:
            self.Sorted = False
        else:
            DEBUG(f"ERROR: BAM coord sorted state in Header?: {self.Header[0]}")
        DEBUG(f"Bam Coord Sorted? {self.Sorted}")
        
        self.Indexed = self.check_for_vcf_index()

        self.determine_reference_genome()       # Only need header available to determine reference_genome

    def process_vcf_body(self, reentrant=None):
        """
        Processes the BAM body.  Operate on first 100K sequence entries (2 million if Nanopore).
        Called internally from the "Show Stats" button as well.
        Will not have run idxstats yet if detected unsorted, unindexed or a CRAM.

        Used mainly to look at body of BAM/CRAM and determine read type (Paired, single-end),
        avg read length and now avg insert size. Other flags may be scanned later.  As BAM is coordinate sorted and
        we are taking the first 100,000 samples, basically reading chromosome 1 for most WGS files presented here.

        Found 100,000 is good enough for most standard 30x WGS paired-end files of around 150 bp read length.
        Found need at least 2,000,000 lines for Nanopore long reads due to large variance.
        ySeq WGS400 single-end files at 400 bp have no variance from that exact length. 

        Originally was our own awk scripts, head, cut, etc. Simply read in value result file.
        Updated 15Sep2021 to use David Wei script (https://gist.github.com/davidliwei/2323462)
        But found it too buggy for the variety of BAMs we see (Nebula, FTDNA BigY, Nanopore from minimap2, etc).
        So went back to all hand-grown code but in python here. As do not have idxstats and a total read count.
        cannot subsample with something like samtools view -s because we do not know what fraction to ask for.
        """
        # This routine is re-entrant. We need to save intermediate calculations to continue to build upon.
        # Instead of class global, we overload the parameter to either be None by default or a list of
        # saved, intermediate values that are passed in. Ugly?
        if reentrant is None:
            first_time = True
            # Initialize stats globals if first time through
            readtyp = 0  # We do not know which yet; negative is paired end and positive is single end
            lencnt = lenmean = lenM2 = 0    # Initializing Welford Algorithm for read length
            sizcnt = sizmean = sizM2 = 0    # Initializing Welford Algorithm for insert size
        else:
            first_time = False
            # Restore stats globals to current values after re-entering
            (readtyp, lencnt, lenmean, lenM2, sizcnt, sizmean, sizM2) = reentrant

        samtools = wgse.samtoolsx_qFN
        head = wgse.headx_qFN
        tail = wgse.tailx_qFN
        bamfile = self.file_qFN
        flagfile_qFN = f'"{wgse.tempf.FP}flags.tmp"'        # To hold BAM samples from body

        if self.file_type == "CRAM" and wgse.reflib.missing_refgenome(self.Refgenome_qFN):
            raise VCFContentErrorFile('errRefGenFileMissing',
                                  os.path.basename(unquote(self.Refgenome_qFN)), self.Refgenome)
        cram_opt = f'-T {self.Refgenome_qFN}' if self.file_type == "CRAM" else ""

        # Re-entrant code allows two runs of sampling from the BAM; numsamp then lonsamp additional
        numsamp = 20000             # Typically can get away with first numsamp as sample size
        lonsamp = numsamp * 29      # Nanopore long read BAMs need more samples; have more variance
        nstep = numsamp / 10
        lstep = lonsamp / 10
        if first_time:
            commands = f'{samtools} view {cram_opt} {bamfile} | {head} -{numsamp} > {flagfile_qFN} \n'
            run_bash_script('ButtonBAMStats2', commands)  # not running stats again; so simply do it
        else:
            commands = f'{samtools} view {cram_opt} {bamfile} | {tail} +{numsamp} | {head} -{lonsamp} > {flagfile_qFN} \n'
            run_bash_script('ButtonBAMStatsLong', commands)

        flagfile_oFN = nativeOS(unquote(flagfile_qFN))
        if not os.path.exists(flagfile_oFN):
            raise VCFContentErrorFile('errBAMNoFlagsFile', flagfile_oFN)

        # Ugly; this was not faster than an awk script; added (one pass) std dev to the calculation
        with open(flagfile_oFN, "r") as flags_file:
            for flag_line in flags_file:
                field = flag_line.split("\t")

                # field[1] = f'{int(field[1]):#014b}'
                # DEBUG(f'FLAG: {field[1]}, Flen: {len(field[9])}, RNEXT: {field[6]}, TLEN: {field[8]}')

                # Skip if higher order flag bits set (supplementary, 2nd alignment, not passing filters)
                if int(field[1]) & 0xB00:
                    continue

                # Check mean and stddev stability
                if wgse.DEBUG_MODE and lencnt % nstep == 0 and (first_time or lencnt % lstep == 0) and lencnt > 0:
                    lenstd = sqrt(lenM2 / (lencnt - 1)) if lencnt > 2 else 0
                    sizstd = sqrt(sizM2 / (sizcnt - 1)) if sizcnt > 2 else 0
                    # DEBUG(f'@Count: {lencnt} - Read Avg: {lenmean:,.0f}, {lenstd:,.0f};  Insert Avg: {sizmean:,.0f}, {sizstd:,.0f}')

                # Process FLAG field (2nd col) with 0x1 mask; 1 to indicate paired-end or 0 for single-end reads
                # Will keep running sum using +1 for each paired read and -1 for each single-end read
                if first_time:      # First time run is enough samples to accurately determine
                    readtyp += 1 if int(field[1]) & 0x1 else -1  # Try to make sure is clearly one or the other

                    if lencnt == 0:
                        # Only need single read to determine seqID; simply take last one still in memory
                        self.Sequencer = determine_sequencer(field[0]) if field and field[0] else "Unknown"
                        DEBUG(f'Sequencer: {self.Sequencer} (ID: {field[0]})')

                # Process SEQ field (10th col) for mean length and std dev (one pass); ignore if only '*'.
                # Not using CIGAR field as discriminator; not reliable in the variety of BAMs
                flen = len(field[9])
                if flen > 1:
                    lencnt += 1
                    lendelta = flen - lenmean
                    lenmean += lendelta / lencnt
                    lendelta2 = flen - lenmean
                    lenM2 += lendelta * lendelta2

                # Process RNEXT and TLEN fields (7th and 9th col) for insert size and std dev. RNEXT is '=' if
                # paired read and then TLEN is the calculated template length. Positive for forward read; negative
                # for reverse.  Only process forward reads and if tlen != 0 (tlen always 0 if RNEXT is not '=')
                # Note: tlen always below 1200 on Novaseq 6000 but sometimes > 50k; throw those out but keep the
                # window of allowable large for Nanopore and PacBio HiFi CCS reads
                tlen = int(field[8]) if field[6] == '=' else 0
                if 0 < tlen < 50000:
                    sizcnt += 1
                    sizdelta = tlen - sizmean
                    sizmean += sizdelta / sizcnt
                    sizdelta2 = tlen - sizmean
                    sizM2 += sizdelta * sizdelta2

        DEBUG(f'Read Length Count: {lencnt}, Insert Size Count: {sizcnt}')
        DEBUG(f'Read Length: {lenmean:,.0f}, Insert Size: {sizmean:,.0f}')

        # Some things are always determinate in the first, shorter pass
        if first_time:
            # Determine read type based on clear majority
            self.ReadType = "Paired" if readtyp > nstep else \
                            "Single" if readtyp < -nstep else \
                            "Unknown"  # Schroedingers paradox
            DEBUG(f'Read Segment Type: {self.ReadType}-end (scale:{readtyp})')

            if self.ReadType == "Unknown":
                # FLAG indicates a near equal mix of paired and single end reads (within 10%)
                raise VCFContentWarning('warnBAMBadReadType')

            if self.ReadType == "Paired" and sizcnt == 0:
                # No insert length because RNEXT never '='; but FLAGS indicate Paired -- inconsistent
                raise VCFContentErrorFile('errBAMInconsistentReadType', flagfile_oFN)

        # Nanopore long-read is highly variable; so need to read many more to get a better mean
        if first_time and lenmean > 410 and "Nanopore" in self.Sequencer:    # Increased len check for ySeq 400 bp single-end read
            #  Although often less total reads when longer read length, need at least 2 million it seems
            DEBUG("Long Read BAM ... reprocessing to get the read length using more read samples")
            self.process_vcf_body(reentrant=[readtyp, lencnt, lenmean, lenM2, sizcnt, sizmean, sizM2])
            return      # Rest of settings will be done in second run only

        # Calculate final standard deviation (sqrt of final variance) for read length and insert size
        if lencnt > 2:
            lenstd = sqrt(lenM2 / (lencnt - 1))
            DEBUG(f'Read Length: {lenmean:,.0f}, stddev={lenstd:,.0f}')
            self.avg_read_length = lenmean
            self.avg_read_stddev = lenstd
        else:
            raise VCFContentError('errBAMBadReadLength')

        if self.ReadType == "Paired" and sizcnt > 2:
            sizstd = sqrt(sizM2 / (sizcnt - 1))
            DEBUG(f'Insert Size: {sizmean:,.0f}, stddev={sizstd:,.0f}')
            self.insert_size = sizmean
            self.insert_stddev = sizstd

    def get_samtools_idxstats(self, button_directly=False):
        """
            Called immediately after (re)setting a BAM file to update the main window summary results display;
            samtools idxstats results are saved for the detailed per-chromosome table from the stats button
            While it is much faster with an index file available, it is not required.  The file must be sorted though.
        """

        if self.Stats:      # Set by a successful process_samtools_idxstats run so nothing to do
            return          # Already ran idxstats; no need to run again. Just display from stored values.

        # May be called before output directory is set; so use temporary files area if so (that must be set)
        path = wgse.tempf.FP if not wgse.outdir and wgse.outdir.FP is None else wgse.outdir.FP
        idxfile_qFN = f'"{path}{self.file_FB}_idxstats.csv"'
        idxfile_oFN = nativeOS(unquote(idxfile_qFN))

        idxstats_file_exists = os.path.isfile(idxfile_oFN) and os.path.getsize(idxfile_oFN) > 480
        #   and os.path.getmtime(idxfile_oFN) > os.path.getmtime(self.file_oFN)
        #   Cannot use file mod times as stats run could be from earlier CRAM / BAM before conversion

        if not idxstats_file_exists:    # If idxstats file does not exist, then create it
            # Unless user hit button directly or is a BAM with Index, then stop as it may take 30+ minutes
            bam_with_index_exists = self.file_type == "BAM" and self.check_for_vcf_index()
            if not (button_directly or bam_with_index_exists):
                return      # Simply return without processing any stats command

            # So either Stats button was hit directly (and not run yet) or in a new, indexed BAM so will run it as if
            #  button hit directly (quick run) to enable full table stats so can enable rest of GUI buttons

            # Create and run Samtools idxstats command on the BAM file
            samtools = wgse.samtoolsx_qFN
            bamfile = self.file_qFN

            commands = f'{samtools} idxstats {bamfile} > {idxfile_qFN} \n'

            # Seconds to minutes to hours ....
            title = "ButtonBAMStats" if self.Sorted and self.Indexed and self.file_type == "BAM" else \
                    "ButtonBAMNoIndex" if self.Sorted else \
                    "ButtonBAMNoSort"
            run_bash_script(title, commands)

            # If still not there then report an error as could not create it when wanted to
            if not (os.path.isfile(idxfile_oFN) and os.path.getsize(idxfile_oFN) > 480):
                raise VCFContentErrorFile('errBAMNoIDXStatsFile', idxfile_oFN)

        self.process_samtools_idxstats(idxfile_oFN)

    def process_samtools_idxstats(self, idxfile_oFN):
        """
        Only called from one place and only if the file exists and likely good. Passed the samtools idxstats result
        file to process and store in various settings.  One of three (possibly long) stats run commands and files.
        """

        # Only capture primary chromosomes and mito separately; lump Alt Contigs in Other and Unmapped in variable

        # These are the arrays to save the IDXstats data and additional processed values to display
        # Eight columns: keySN, storedSN, Modelen, Model N Count, Loc & Unlocalized Seg Counts,  (five initially)
        #                Mapped Gigabases (calc), Mapped Average Read Depth (calc),
        #                Breadth of Coverage (added later; just add 0 now)
        # SNCount rows: SNs but not including the special IDXstats row of unmapped ('*')
        stats_autos = []
        stats_somal = []    # REH 20Mar2020 pulled out X, Y and M to easily numeric sort autosomes
        stats_mito  = []    # REH 26Feb2022 pulled out M so can more easily order after X, Y
        stats_total   = ["T", wgse.lang.i18n['Total'], 0, 0, 0]  # Total row at bottom; before appending new columns
        stats_altcont = ["O", wgse.lang.i18n['OtherChr'], 0, 0, 0]  # Alt Contigs row collecting all others
        stats_grantot = ["G", "", 0, 0, 0]  # A Grand total row including alt contigs for summary stats

        # To store chromosome total mapped segments by type: Autosome, X, Y, Mito, Other (alt contigs) and Unmapped (*)
        chrom_types = {'A': 0, 'X': 0, 'Y': 0, 'M': 0, 'O': 0, '*': 0}

        # Read the idxstats CSV table generated earlier; keep autosomes and others separate
        with open(idxfile_oFN, "r") as stats_file:
            # Todo Need pythonic indices; not numeric position. For both read idxstats file and values table built
            for stats_line in stats_file:
                line_columns = stats_line.split("\t")
                chromosome = line_columns[0].strip()  # Save as found in file for printout, etc
                chromnum = chromosome.upper().replace("CHR", "").replace("MT", "M")  # normalize to numeric only, M only
                len_in_model_bp = int(line_columns[1])
                map_seg_read = int(line_columns[2]) + int(line_columns[3].strip())  # Sum localized and unlocalized

                # Only process and store those Sequences with mapped segment values; due to non-WGS BAMs (e.g. y-only)
                # Stats_ arrays are [nominal Chr SN, actual Chr SN in file, len in model, # map seg]
                # The nominal is consistent for processing (uppercase, no "chr" prefix, MT -> M, etc)
                if map_seg_read == 0:
                    continue
                if chromnum in wgse.valid_autos:
                    ncount = wgse.nadjust[self.Build][chromnum]
                    stats_autos.append([chromnum, chromosome, len_in_model_bp, ncount, map_seg_read])
                    chrom_types['A'] += map_seg_read
                elif chromnum in wgse.valid_somal:
                    ncount = wgse.nadjust[self.Build][chromnum]
                    stats_somal.append([chromnum, chromosome, len_in_model_bp, ncount, map_seg_read])
                    chrom_types[chromnum] += map_seg_read
                elif chromnum == "M":
                    ncount = wgse.nadjust[self.Build][chromnum]
                    stats_mito.append([chromnum, chromosome, len_in_model_bp, ncount, map_seg_read])
                    chrom_types['M'] += map_seg_read
                elif chromnum == '*':
                    chrom_types['*'] += map_seg_read    # unlocalized column 3 has unmapped value total
                else:   # Alt_contigs (or also unknown naming of sequences)
                    # if chromosome in ["EBV", "NC_007605"]:  # Ignore EBV in 1KG as throws off stats
                    #    continue
                    stats_altcont[2] += len_in_model_bp
                    stats_altcont[3] = 0                # We have not loaded N count for contigs; only prinary
                    stats_altcont[4] += map_seg_read
                    chrom_types['O'] += map_seg_read

        DEBUG(f"Chrom_types: {str(chrom_types)}")
        DEBUG(f"Alt Contig values: {str(stats_altcont)}")

        # Determine gender of sample from counts of chromosome type counts; always initialized to 0 if none encountered
        if chrom_types["Y"] == 0 and chrom_types["X"] == 0:  # No X nor Y reads; both 0 so no gender determination
            self.gender = 'Unknown'
        elif chrom_types["Y"] == 0 or (chrom_types["X"] / chrom_types["Y"]) > 20:   # Either Y=0 or X/Y >20
            self.gender = 'Female'
        else:   # Males: Y > x4 X reads ; Females: X > x20 Y reads generally but accept default as Male here
            self.gender = 'Male'
        self.chrom_types = chrom_types

        # If BAM is empty of mapped human genome SN's or unmapped-only (i.e. only alt_contigs),
        #   then raise / report error of BAM content as we do not know what we have.
        #   Could be we just did not recognize the chromosome naming and hence all alt_contigs
        if not (stats_autos or stats_somal or stats_mito or chrom_types['*'] > 0):
            DEBUG("ERROR: BAM has no human genome model elements, what to do?")
            raise VCFContentError('errBAMNonHumanGenome')

        # Numerically sort the chromosomes by chromosome number before building full table    # REH 20Mar2020
        # Most files are sorted alphabetically and not numerically. So chr10 follows chr1.
        stats_autos.sort(key=lambda chra: int(chra[0]))  # Sort entries based on chromosome #
        stats_somal.sort(key=lambda chro: chro[0])  # Sort entries based on somal letter (X, Y)

        # Build table of stats with primaries to get totals; note: some or all may be empty and that is OK
        stats_chroms = stats_autos  # start with autosomes
        stats_chroms.extend(stats_somal)  # Add somal
        stats_chroms.extend(stats_mito)

        # Calc totals of each column before adding Other (alt contigs) (ignore Y if female in total)
        for row in range(len(stats_chroms)):
            if stats_chroms[row][0] == 'Y' and self.gender == 'Female':         # Ignore Y values in Female total
                continue
            for col in range(2, 5):  # Skip first 2 columns of chromosome labels
                stats_total[col] += int(stats_chroms[row][col])  # stats_total initialized to zero at start
        stats_chroms.append(stats_total)       # Add Total row to end of table (always, even if empty table otherwise)

        # Add alt_contig row after primary and total; with a grand total row then also
        if stats_altcont[4] > 0:   # REH 09Mar2020 so only MAPped alt contigs included if they exist
            for col in range(2, 5):
                stats_grantot[col] = stats_total[col] + stats_altcont[col]
            stats_chroms.append(stats_altcont)
            stats_chroms.append(stats_grantot)

        # Calculate and append new columns (Mapped gbases, mapped avg read depth, coverage) to each row
        for i in range(len(stats_chroms)):  # Fall back to C / Assembly, use i for row index :)
            len_in_model_bp = stats_chroms[i][2] + 0.0001   # make non-zero to help with divide by zero; especially '*'
            nlen_bp = stats_chroms[i][3]
            map_seg_read = stats_chroms[i][4]
            temp_mapped_gbases = float(map_seg_read * self.avg_read_length)
            stats_chroms[i].append(round(temp_mapped_gbases / (10**9), 2))      # gbases column -- col 5
            stats_chroms[i].append(round(temp_mapped_gbases / (len_in_model_bp - nlen_bp)))  # ARD (no N) -- col 6
            stats_chroms[i].append(0)       # Save a zero'ed out coverage row to be filled in later -- col 7

        # Finished with constructing table; save for detailed stats button display in mainWindow routines
        # Note that an unmapped BAM will have a single row (Total) that will be all zero's. An unidentified sequence
        #  named BAM will have a zero'ed Total row, everything in Other, then a grand total row mimicing Other.
        # There is no intent to ever display the Grand total row; only use it to calculate the summary values
        self.stats_chroms = stats_chroms

        # Calculate summary values from new stats table; using grand total row (if it exists), otherwise total row
        # Always guaranteed at least one row exists; even if all zero entries

        # Give nice names to use in formulas below
        total_len_in_model = stats_chroms[-1][2] + 0.0001  # for divide by zero in unmapped BAM
        total_nlen_in_model = stats_chroms[-1][3]
        total_map_seg_read = stats_chroms[-1][4]    # Note: will not include '*'
        total_unmap_seg_read = chrom_types['*']     # We no longer have an unmapped row entry; just the total
        total_map_gbases = stats_chroms[-1][5] if total_map_seg_read > 0 else 0.0
        total_segs_read = total_map_seg_read + total_unmap_seg_read + 0.0001  # for divide by zero when unmapped BAM
        total_bases = total_segs_read * self.avg_read_length

        # Set global stats that will be retained, displayed and used for decision making
        self.raw_gigabases = total_bases / (10**9)
        self.raw_avg_read_depth_NoN = 0 if total_len_in_model < 0.001 else \
            round(total_bases / (total_len_in_model - total_nlen_in_model), 1)
        if self.raw_avg_read_depth_NoN >= 10.0:
            self.raw_avg_read_depth_NoN = round(self.raw_avg_read_depth_NoN)
        self.raw_avg_read_depth_full = 0 if total_len_in_model < 0.001 else \
            round(total_bases / total_len_in_model, 1)     # Old style; deprecated
        if self.raw_avg_read_depth_full >= 10.0:
            self.raw_avg_read_depth_full = round(self.raw_avg_read_depth_full)
        self.raw_segs_read = total_segs_read
        # self.total_reads_percent = total_segs_read / total_segs_read  #  Will always be 1 or 100%
        # self.avg_read_length = avg_read_length    # Calculated before this call and stored then
        self.mapped_gbases = total_map_gbases
        self.mapped_avg_read_depth_NoN = \
            round(total_map_seg_read * self.avg_read_length / (total_len_in_model - total_nlen_in_model), 1)
        if self.mapped_avg_read_depth_NoN >= 10.0:
            self.mapped_avg_read_depth_NoN = round(self.mapped_avg_read_depth_NoN)
        self.mapped_avg_read_depth_full = \
            round(total_map_seg_read * self.avg_read_length / total_len_in_model, 1)   # Old style; deprecated
        if self.mapped_avg_read_depth_full >= 10.0:
            self.mapped_avg_read_depth_full = round(self.mapped_avg_read_depth_full)
        self.mapped_segs_read = total_map_seg_read
        self.mapped_reads_percent = total_map_seg_read / total_segs_read

        # Set some convenient values revolving around the data content types
        self.Content = (0x01 if chrom_types["A"] > 0 else 0) + \
                       (0x02 if chrom_types["X"] > 0 else 0) + \
                       (0x04 if chrom_types["Y"] > 0 else 0) + \
                       (0x08 if chrom_types["M"] > 0 else 0) + \
                       (0x10 if chrom_types['O'] > 0 else 0) + \
                       (0x20 if chrom_types['*'] > 0 else 0)
        # Set Y only if Y content and no Autosomal, X and Unmapped (*) set. Allow MT and Other as part of Y only.
        self.Monly = (self.Content & 0x08 > 0) and (self.Content & 0x08 == self.Content)
        self.Yonly = (self.Content & 0x04 > 0) and (self.Content & 0x1C == self.Content)
        self.Primary = self.Content & 0x0F > 0

        # Process and post a few warnings if appropriate
        if self.mapped_avg_read_depth_NoN < 10 and self.Primary:
            # If unmapped ('*'), then mapped avg read depth is 0 so no warning there
            wgse_message("warning", 'LowCoverageWindowTitle', False, 'LowCoverageWarning')
            self.low_coverage = True

        if self.avg_read_length > 410:      # We have not fully accounted for long read processing throughout
            wgse_message("warning", 'LongReadSequenceTitle', False, 'LongReadSequenceWarning')
            self.long_read = True

        self.Stats = True

    def determine_reference_genome(self):
        """
        Try to determine the reference genome from just the header information.

        The VCF Header is set from the caller creating the VCF.  It is generally carried through in full when subsets
        of the VCF are made (e.g. Y-only VCF).  Header "contig"" records should be based only on the reference model
        and not actual variants called content.

        Original, generic, major model naming comes from:
         hg if old style "chr22/chrM" sequence names, GRCh if numeric-only
         19 if old style hg with Yoruba, 37 if build 37 model lengths, 38 if Build 38 model lengths, ditto T2T 99
         Number of "contig" entries in the header is a good indicator of class and other model characteristics

        NOTE: Much of this code is duplicated in the BAMFiles class call of the same name.  Should likely pull out
        just the differences and make a single, generic call that adopts to the differences.  Maybe simply extract
        the SN/ID and LN/length fields into separate entry and process that?
        """

        # Determine SN names as given as opposed to relying on reference model to determine
        accession = ["##contig=<ID=CM0", "##contig=<ID=CP", "##contig=<ID=J0", "##contig=<ID=NC_"]
        self.SNTypeC = "Chr" if "##contig=<ID=chr" in self.Header else \
                       "Num" if "##contig=<ID=1\t" in self.Header else \
                       "Acc" if any(x in self.Header for x in accession) else \
                       "Unk"
        self.SNTypeM = "MT" if "##contig=<ID=MT" in self.Header or "##contig=<ID=chrMT" in self.Header else "M"
        self.SNCount = self.Header.count('##contig=<ID=')   # Almost sufficient for an analysis model determination
        DEBUG(f"ID: {self.SNTypeC}, {self.SNTypeM}; ID#:{self.SNCount}")

        # Possible that header has been shortened if a subset BAM file? So only use chr1, Y and X to check length
        # If only MT or Unmapped (*) in header, then cannot tell RefGenome
        self.Build, self.RefMito = \
            (99, "Custom") if any(x in self.Header for x in ["length=248387561", "length=248387328", "length=248387497",
                    "length=248415701", "length=62456832", "length=62460029", "length=62480187", "length=154343774",
                    "length=25843790",  "length=154259566", "length=154259625", "length=154269076", "length=154349815",
                    "length=154434329"]) else \
            (38, "rCRS")   if any(x in self.Header for x in ["length=248956422", "length=57227415", "length=156040895"]) else \
            (37, "rCRS")   if any(x in self.Header for x in ["length=249250621", "length=59373566", "length=155270560"]) else \
            (18, "Yoruba") if any(x in self.Header for x in ["length=247249719", "length=57772954", "length=154913754"]) else \
            (17, "Yoruba") if any(x in self.Header for x in ["length=245522847", "length=57701691", "length=154824264"]) else \
            (16, "Yoruba") if any(x in self.Header for x in ["length=246127941", "length=50286555", "length=153692391"]) else \
            (15, "Yoruba") if any(x in self.Header for x in ["length=245203898", "length=50961097", "length=152634166"]) else \
            ( 0, "Unknown")

        # Modify Mitochondria model based on its length if Build 37 (only one with both types in releases)
        if self.Build == 37 and any(x in self.Header for x in ["M,length=16571", "MT,length=16571"]):
            self.Build, self.RefMito = (19, "Yoruba")
        # Todo handling RSRS model -- look for spacers?

        DEBUG(f"Build: {self.Build:3d}")
        DEBUG(f"Ref Genome Mito: {self.RefMito}")

        # New form is based on Major / Class mechanism in Reference Genome study: https://bit.ly/34CO0vj
        #  Used to rely on SNCount.  But oddball, unrecognized ref genomes in BAMs may have something close set by user.
        #  So, rely more on key items found in special ref genomes. Keep patching this.  Need to use the MD5sum method.
        if self.Build == 99:        # Used chr1, chrX or chrY lengths to determine Build99 earlier
            # Use X and Y length to determine T2T / HPP model
            if "length=62456832" in self.Header and "length=154343774" in self.Header:  # CHM13 v1.1 & HG002 v2 XY
                self.Refgenome = self.RefgenomeNew = "THGv20"
            elif "length=62460029" in self.Header and "length=154349815" in self.Header:  # CHM13 v1.1 & HG002 v2.7 XY
                self.Refgenome = self.RefgenomeNew = "THGv27"
            elif "length=62480187" in self.Header and "length=154434329" in self.Header:  # HG01243 v3 PR1 Puerto Rican
                self.Refgenome = self.RefgenomeNew = "THG1243v3"
            elif "length=57277415" in self.Header and "length=154259566" in self.Header:  # CHM13 v1.1 & GRCh38 Y
                self.Refgenome = self.RefgenomeNew = "HPPv11"
            elif "length=57277415" in self.Header and "length=154259625" in self.Header:  # CHM13 v1 X & GRCh38 Y
                self.Refgenome = self.RefgenomeNew = "HPPv1"
            elif "length=62456832" in self.Header and "length=156040895" in self.Header:  # GRCh38 w/ HG002 v2 Y  (ySeq)
                self.Refgenome = self.RefgenomeNew = "THGySeqp"
            elif "length=62460029" in self.Header and "length=154259566" in self.Header:  # CHM13 v1.1 & HG002 v2.7 Y
                self.Refgenome = self.RefgenomeNew = "T2Tv20"
            elif "length=154259566" in self.Header:  # Must be plain CHM13 v1.1 as special Y not found
                self.Refgenome = self.RefgenomeNew = "T2Tv11"
            elif "length=154259625" in self.Header:  # Must be plain CHM13 v1 as special Y not found
                self.Refgenome = self.RefgenomeNew = "T2Tv10"
            elif "length=154259664" in self.Header:  # Must be plain CHM13 v0.9
                self.Refgenome = self.RefgenomeNew = "T2Tv09"
            else:  # Think it is T2T / HPP build but cannot recognize Y or X length
                DEBUG(f'Unrecognized T2T model; no matching X or Y length in BAM to known models.')
        elif "##contig=<ID=NC_007605" in self.Header and self.SNCount in [85, 86]:
            # hs37 class have SN:NC007605 (EBV in Numeric naming) sans human_g1k / GRCh37.primary_assembly models
            # human_1kg model is 84 and one less SN than hs37.fa.gz; hs37d5 is 86 and one more than hs37 (hs37d5 decoy)
            self.Refgenome = "hs37d5" if "##contig=<ID=hs37d5" in self.Header else "hs37"
            self.RefgenomeNew = "1k37g"
        elif "##contig=<ID=chrEBV" in self.Header and self.SNCount in [85, 298]:
            self.Refgenome = None     # 1KGenome analysis models in NCBI Genbank Archive or UCSC; but not handled yet
            self.RefgenomeNew = "1k37h"
        elif self.SNCount == 84:      # human_g1k (if Num), GRCh37.primary_assembly.genome (if Chr)
            self.Refgenome = "hs37-" if self.SNTypeC == "Num" else \
                             "GRCh37-" if self.SNTypeC == "Chr" else None
            self.RefgenomeNew = "1K37g" if self.SNTypeC == "Num" else \
                                "EBI37h" if self.SNTypeC == "Chr" else None
        elif ("##contig=<ID=chrEBV" in self.Header or "##contig=<ID=EBV" in self.Header) and \
              self.SNCount in [195, 456, 2581, 3366]:
            # hs38DH is 3366 SN count and has SN:HLA- unique; hs38 is 195 and hs38a is 456; all uniquely have chrEBV
            # hs38s is sequencing.com model of GCA_000001405.15_GRCh38_no_alt_plus_hs38d1.fna.gz with 22_KI270879v1_alt
            self.Refgenome = "hs38DH"  if "##contig=<ID=chr22_KI270879v1_alt" in self.Header and self.SNCount == 3366 else \
                             "hs38s"   if "##contig=<ID=22_KI270879v1_alt" in self.Header and self.SNCount == 2581 else \
                             "hs38a"   if self.SNCount == 456 else \
                             "hs38"  # if self.SNCount == 195
            self.RefgenomeNew = "1k38" + ("pg" if self.Refgenome == "hs38s" else "h")
        elif self.SNCount in [25, 93, 297, 455, 639]:    # SNCounts of 6 hg/ebi models; 2 duplicated
            # Handle the hg (UCSC) and GRCh (EBI) models here
            self.Refgenome  = "hg" if self.SNTypeC == "Chr" else "GRCh"
            self.Refgenome += str(self.Build)   # Build already takes into account mito for 19/37 differentiation
            self.RefgenomeNew = self.Refgenome.replace("GRCh", "EBI") + ("g" if self.SNTypeC == "Chr" else "h")
        DEBUG(f'Ref Genome: {self.Refgenome}, by New nomenclature: {self.RefgenomeNew}')

        # Todo Mimic BAM / DICT file header duplication with md5sum to get a more reliable determination

        # We give up if still not set; simply ask the user
        if not self.Refgenome:  # not set yet: and (self.chrom_types["A"] > 1 or self.chrom_types["Y"] > 1):
            wgse.reflib.ask_reference_genome(self, type="VCF", inBAM=True)  # Return value in self class pointer
            DEBUG(f'Ref Genome (User): {self.Refgenome}')
            # todo ask user to send VCF header so we can get its signature for future runs

        self.Refgenome_qFN = wgse.reflib.get_refgenome_qFN(self.Refgenome)
        tempFN = unquote(self.Refgenome_qFN)
        DEBUG(f'Ref Genome File: {tempFN}')

    def chrom_types_str(self):
        """
        Create a string of comma-separated BAM SN components: Auto(somes), X, Y, Mito, etc of BAM / CRAM for stats
        Typical 30x WGS male BAM file would return: "Auto, X, Y, Mito, Unmap, Other" (in English lang setting)
        """
        count = 0
        chrom_types_str = ""
        for key, value in self.chrom_types.items():
            if value > 1 and not (key == 'Y' and self.gender == 'Female'):  # Do not show Y on Female
                count += 1
                chrom_types_str += (", " if chrom_types_str != "" else "") + wgse.lang.i18n[key]
                ''' Key values are one of: ("A", "X", "Y", "M", "O"). Single character lookup in language file. '''
        if count == 1:
            chrom_types_str += f' {wgse.lang.i18n["Only"]}'
        return chrom_types_str

    def refgenome_str(self):
        """ Create string of ref genome, mito genome, and SN Count of VCF for stats """

        if self.Refgenome:
            result = self.Refgenome
        else:
            bldstr = f' {str(self.Build)}' if self.Build else ""
            result = wgse.lang.i18n["Unknown"] + bldstr
        if self.SNTypeC:
            result += f' ({self.SNTypeC})'
        if self.RefMito:
            result += ", " if result else ""
            result += self.RefMito
        if self.SNCount:
            result += ", " if result else ""
            result += f'{self.SNCount} {wgse.lang.i18n["SNs"]}'
        return result

    def filestatus_str(self):
        """ Create string of sorted, indexed and file size status of BAM / CRAM for stats """
        result = ""
        #if self.Indexed:
        #  result += ", " if result else ""
        result += wgse.lang.i18n["Indexed"] if self.Indexed else wgse.lang.i18n["Unindexed"]
        # File size
        result += ", " if result else ""
        result += f'{round(self.file_stats.st_size / (10.0 ** 9), 1)} {wgse.lang.i18n["GBs"]}' if self.file_stats.st_size >= 10 ** 9 else \
                  f'{round(self.file_stats.st_size / (10.0 ** 6), 1)} {wgse.lang.i18n["MBs"]}' if self.file_stats.st_size >= 10 ** 6 else \
                  f'{round(self.file_stats.st_size / (10.0 ** 3), 1)} {wgse.lang.i18n["KBs"]}' if self.file_stats.st_size >= 10 ** 3 else \
                  f'{round(self.file_stats.st_size, 1)} {wgse.lang.i18n["Bs"]}'
        return result

    def get_chr_name(self,chrtype):
        """ Return chromosome name of "type" (MT or Y) specific to the BAM reference model. """
        if self.SNTypeC == "Chr":
            chrM = "chrM" if self.SNTypeM == "M" else "chrMT"
            chrY = "chrY"
        elif self.SNTypeC == "Num":
            chrM = "MT" if self.SNTypeM == "MT" else "M"
            chrY = "Y"
        elif self.SNTypeC == "Acc":
            chrM = "M"
            chrY = "Y"
        else:
            chrM = chrY = ""
        return chrM if chrtype == "M" else chrY

    def check_for_vcf_index(self):
        """ VCF Index file exists check.  """
        # todo need to add check in OUT directory, if set. And add option to use in samtools calls if located there
        self.Indexed = os.path.isfile(self.file_oFN + ".tbi") or os.path.isfile(self.file_oFN + ".TBI")
        # todo case sensitive check needed? how does bcftools handle?
        return self.Indexed

'''  Part of BAMfiles (copied here when file duplicated)
    def find_VCFs(self):
        """
        A special to search for commonly-named VCFs from a vendor for the loaded BAM file.  As a precursor to creating
        them from the BAM.  In here as if they are found, will set class variable so they can be used and associated.
        Eventually, add "get_" routine like for reference_genome to ask the user if not found. Saves time and disk
        space to reuse instead of recreating. Helpful especially when we start saving and restore BAM/FASTQ/VCF
        library stats for a complete test kit.
        """
        # todo checking dates (compared to BAM) and sizes (minimum)

        # First check if names have already been set in this BAM class
        if not (self.VCFs and len(self.VCFs) > 0):
            self.VCFs = VCFs = {}

            # First look in output directory for VCFs we create (our naming convention)
            if wgse.outdir and wgse.outdir.FPB:
                VCFs += {
                    f'{wgse.outdir.FPB}_SNP.vcf.gz'  : ({'SNP'}, {'A', 'X', 'Y', 'M'}),
                    f'{wgse.outdir.FPB}_InDel.vcf.gz': ({'InDel'}, {'A', 'X', 'Y', 'M'}),
                    f'{wgse.outdir.FPB}_CNV.vcf.gz'  : ({'CNV'}, {'A', 'X', 'Y', 'M'}),
                    f'{wgse.outdir.FPB}_SV.vcf.gz'   : ({'SV'}, {'A', 'X', 'Y', 'M'}),
                    f'{wgse.outdir.FPB}.vcf.gz'      : ({'unk'}, {'A', 'X', 'Y', 'M'})
                }

            # Now look in BAM directory for common test company names that come with their BAMs
            VCFs += {
                f'{self.file_FPB}.filtered.snp.vcf.gz'    : ({'SNP'}, {'A', 'X', 'Y', 'M'}),    # Dante Labs
                f'{self.file_FPB}.filtered.indel.vcf.gz'  : ({'InDel'}, {'A', 'X', 'Y', 'M'}),  # Dante Labs
                f'{self.file_FPB}.cnv.vcf.gz'             : ({'CNV'}, {'A', 'X', 'Y', 'M'}),  # Dante Labs & Sequencing
                f'{self.file_FPB}.sv.vcf.gz'              : ({'SV'}, {'A', 'X', 'Y', 'M'}),   # Dante Labs & Sequencing
                f'{self.file_FPB}.vcf.gz'                 : ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'}),  # Nebula & ySeq
                f'chrY_called_{self.file_FPB}.vcf.gz'     : ({'SNP'}, {'Y',}),                    # ySeq
                f'chrY_cleaned_{self.file_FPB}.vcf.gz'    : ({'SNP'}, {'Y',}),                    # ySeq
                f'chrY_derived_{self.file_FPB}.vcf.gz'    : ({'SNP'}, {'Y',}),                    # ySeq
                f'chrY_INDELS_{self.file_FPB}.vcf.gz'     : ({'InDel'}, {'Y',}),                  # ySeq
                f'chrY_novel_SNPs_{self.file_FPB}.vcf.gz' : ({'SNP'}, {'Y',}),                    # ySeq
                f'{self.file_FPB}.snp-indel.genome.vcf.gz': ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'}),  # Sequencing.com
                f'{self.file_FPB}.mito.vcf.gz'            : ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'})   # Sequencing.com
                # Full Genomes Corp?
            }
            for key, val in VCFs.items():
                if os.path.exists(nativeOS(key)):
                    self.VCFs += { key, val }

        if not (self.VCFs and len(self.VCFs) > 0):
            # todo ask the user if they know where they are and let them set.  Implement once VCF stats save happens.
            pass

        process_vcf_headers(self)

        return self.VCFs
'''
