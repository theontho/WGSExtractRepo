# coding: utf8
# Copyright (C) 2018-2020 City Farmer
# Copyright (C) 2020-2023 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""###################################################################################################################
    The first major module / subsystem that is a proper object Class.  BAMFile (class; bamfiles module) is the central
    handler for all things BAM.  Processing, determining stats, manipulating (sorting, indexing; eventually CRAM/SAM
    processing)  The idea is a class instance for each BAM file specified.  Eventually allowing for multiple to be
    known at the same time.  Once a BAM file is selected in the OS interface in the main Window module, the BAM
    object is instantiated and processing begins. Is the main driver of the referencegenome module.
"""

import os       # for path, stat
from math import sqrt       # for process_bam_body

from utilities import DEBUG, is_legal_path, nativeOS, universalOS, unquote, Error, Warning, wgse_message, check_exists
from commandprocessor import run_bash_script
from fastqfiles import determine_sequencer
import settings as wgse


######################################################################################################################
# BAM File Processing Error Classes
class BAMContentError(Error):
    def __init__(self, reason):
        self.reason = wgse.lang.i18n[reason]


class BAMContentErrorFile(Error):
    def __init__(self, reason, file, refgen=None):
        self.reason = wgse.lang.i18n[reason].replace('{{FILE}}', file)
        if refgen:
            self.reason = self.reason.replace('{{REFGEN}}', refgen)
            self.reason = "RefGen"  # Override reporting error by setting reason to RefGen


class BAMContentWarning(Warning):
    def __init__(self, reason):
        self.reason = wgse.lang.i18n[reason]


######################################################################################################################
# BAM File Processing class

class BAMFile:
    """
        BAM File class object; including all stats and processing thereof
        In init, simply assert if error and let outer caller worry about deleting the object
        (i.e. we assume within invoked from within a try...except). Errors will be of class BAMContentError
        with an additional message parameter. The message parameter must be a LanguageStrings dictionary key.
    """

    def __init__(self, BAM_FN):        # Formerly known as process_BAM() before becoming Class.__init__
        """
        True Class init that simply sets up the Class variables by initializing them (even if None).
        BAM file initialization is then called via _setup_BAM file at the end. Which can be called directly (internally)
        as well to setup a new BAM. But generally best to drop the Class instance and start over.
        """
        self.file_oFN  = None   # Various renditions of the BAM/CRAM file name, path, etc
        self.file_oFPB = None
        self.file_FN   = None
        self.file_qFN  = None
        self.file_FBS  = None
        self.file_FPB  = None
        self.file_FP   = None
        self.file_FB   = None
        self.file_FS   = None

        self.file_type = None    # for "SAM", "BAM", or "CRAM" (file_FS without the leading dot)

        self.R1fastq_FN = None   # Now storing FASTQ file names associated with BAM / CRAM file (if known)
        self.R2fastq_FN = None
        self.VCFs = None         # e.g. [ (f'{wgse.outdir.FPB}.vcf.gz', {'SNP'. 'InDel'}, {'A', 'X', 'Y', 'M'}) ]

        self.Header    = ""      # Will save complete BAM Header in text form (samtools view -H)
        self.file_stats = None   # File Stat result (for file size and other items)
        self.relfsize  = None    # Relative file size (to 45 GB) (to scale time values)

        self.Refgenome = None    # {hg,GRCh}{19/37,38}, hs37d5, hs38DH (not all combinations valid)
        self.RefgenomeNew = None  # Following Reference Model study: hg, 1kg, ebi, ncbi
        self.Refgenome_qFN = None  # quoted File name of reference genome used for BAM
        self.RefMito   = None    # rCRS, Yoruba, RSRS
        self.SNTypeC   = None    # "Chr", "Num" or "Acc" (NCBI Accession #)
        self.SNTypeM   = None    # M or MT
        self.SNCount   = 0       # Count of '@SQ:\tSN' entries in Header
        self.Build     = None    # Major Build (19?, 36, 37, 38, 99 for T2T)
        self.ReadType  = None    # Read type: Paired or Single (-end)
        self.Content   = 0       # Bitfield: * && O && M && Y && X && A
        self.Yonly     = False   # Y only is Y only or Y and MT only (BED files include MT for that reason)
        self.Monly     = False   # M is mito only
        self.Primary   = False   # Set true if A, X, Y and/or MT are set
        self.Sequencer = None

        self.gender    = None

        self.Aligned   = False
        self.Sorted    = False
        self.Indexed   = False
        self.low_coverage = False
        self.long_read    = False

        # todo The following values are immutable once set; could be a tuple or fixed-key dictionary instead
        self.raw_gigabases              = 0
        self.raw_avg_read_depth_WES     = 0  # WES (Exome) region ARD (full WES region)
        self.raw_avg_read_depth_full    = 0  # Traditional, Full (old style) includes N's in model
        self.raw_avg_read_depth_NoN     = 0  # No N's included (new)
        self.raw_segs_read              = 0  # Total number of segments read (in BAM, or FASTQs)
        self.mapped_gbases              = 0
        self.mapped_avg_read_depth_WES  = 0  # WES (Exome) region ARD (only tested portion)
        self.mapped_avg_read_depth_full = 0  # Traditional, Full (old style) includes N's in model
        self.mapped_avg_read_depth_NoN  = 0  # No N's included (new)
        self.mapped_segs_read           = 0  # Total # segments mapped (localized and unlocalized)

        self.mapped_reads_percent       = 0  # RAW reads percent is always 100% so no need to save

        self.avg_read_length            = 0  # Read Length Mean
        self.avg_read_stddev            = 0  # Read Length standard deviation
        self.insert_size                = 0  # Read Insert Size mean (aka Read Span or Read Fragment Length)
        self.insert_stddev              = 0  # Read Insert Size standard deviation

        self.Stats        = False   # Will delay calculating basic stats if file not indexed
        self.coverage     = None    # Breadth of Coverage for whole BAM (valid value may be zero)
        self.coverage_WES = None    # Breadth of Coverage for WES (valid value may be zero)

        self.stats_chroms = []  # Will save IDXStats based summary table for display with "Show Stats" button
        self.stats_bin    = []  # For WGS Bin Coverage table
        self.stats_binwes = []  # For WES Bin Coverage table
        self.chrom_types = {"A": 0, "X": 0, "Y": 0, "M": 0, "*": 0, "O": 0}  # Stores num of read segments for each

        self._setup_BAM(BAM_FN)

    def _setup_BAM(self, BAM_FN):
        """ Check BAM File name / path is legal; fill in basic stats from BAM file if so. Assert on error. """
        BAM_oFN = nativeOS(BAM_FN)
        if not is_legal_path(BAM_oFN):
            raise BAMContentError('errBAMFileSpecialChars')
        if not os.path.isfile(BAM_oFN) or os.path.getsize(BAM_oFN) < 10000:    # file is bad
            raise BAMContentError('errBAMContent')

        # set_BAM_file_settings ... just doing file names. Most content set later while processing file.
        self.file_oFN  = BAM_oFN
        self.file_FN   = BAM_FN
        self.file_qFN  = f'"{self.file_FN}"'

        self.file_FP   = os.path.dirname(BAM_FN)
        self.file_FP  += '/' if self.file_FP[-1] != '/' else ''  # Assure trailing slash; universalOS so forward slash

        self.file_oFPB = os.path.splitext(BAM_oFN)[0]
        self.file_FPB  = universalOS(self.file_oFPB)

        self.file_FBS  = os.path.basename(BAM_FN)
        self.file_FB, self.file_FS = os.path.splitext(self.file_FBS)
        self.disp_FBS  = self.file_FBS if len(self.file_FBS) < 31 else f'{self.file_FBS[:12]} ... {self.file_FBS[-13:]}'

        self.file_type = self.file_FS[1:].upper()    # strip leading dot and upcase
        if self.file_type not in ["BAM", "CRAM", "SAM"]:    # Internal call may pass an incorrect file
            raise BAMContentError('errBAMFileExtension')

        self.file_stats = os.stat(self.file_oFN)
        if self.file_stats.st_size == 0:
            raise BAMContentError('errBAMFileEmpty')
        self.relfsize = max(0.01, self.file_stats.st_size / (45 * 10.0 ** 9))    # Relative size to 45GB (time adjust)

        # Do a bunch of quick things, custom here, that lets us characterize the BAM a bit. May pop-out witha Raise ...
        wgse.BAM = self                 # May need within the below calls, so setup global setting now
        self.process_bam_header()       # Quick but may have error exceptions
        self.process_bam_body()         # Little longer (10 seconds max) but key ones like read length, etc.

        # We have three stats commands we can run. We try the get_samtools_idxstats call as it enables the rest of
        # the GUI buttons (change_status_of_actiona_buttons). But it will only actually run the stats command if
        # button_directly=true OR it is a BAM file with an index (both are under one second). Get_samtools_idxstats
        # calls the other two but with button_directly=False. That way, if a previous call results exist (on any of
        # the three), we process the stats file now. May "raise" a warning.
        try:
            self.get_samtools_idxstats(button_directly=False)
        except Exception as err:
            # raise BAMContentErrorFile('errBAMNoIDXStatsFile', f'{self.file_FB}_idxstats.csv')
            wgse_message("error", 'errNoFileExists', True, err.reason)
            return

    def process_bam_header(self):
        """ Reads and stores BAM header. Sets BAM.CoordSorted also. Does not need BAM Index file (.bai). """

        # Rewritten to process more of header; and process header in Python and not BASH AWK/GREP scripts
        samtools = wgse.samtoolsx_qFN
        bamhead_qFN = f'"{wgse.tempf.FP}bamheader.tmp"'
        bamfile  = self.file_qFN

        commands = f'{samtools} view -H --no-PG {bamfile} > {bamhead_qFN} \n'

        run_bash_script("GetBAMHeader", commands)

        bamhead_oFN = unquote(nativeOS(bamhead_qFN))
        if not os.path.exists(bamhead_oFN) or os.path.getsize(bamhead_oFN) < 25:  # Command success check
            raise BAMContentError('errBAMHeader')
        try:
            with open(bamhead_oFN, "r") as f:
                self.Header = f.read()
        except Exception:
            raise BAMContentError('errBAMHeader')

        if "SO:coordinate" in self.Header:
            self.Sorted = True
        elif "SO:unsorted" in self.Header or "SO:unknown" in self.Header or "SO:queryname" in self.Header:
            self.Sorted = False
        else:
            firstline = self.Header.partition('\n')[0]
            DEBUG(f"ERROR: Unknown BAM sorted state in Header?: {firstline}")
        DEBUG(f"Bam Coord Sorted? {self.Sorted}")
        
        self.Indexed = self.check_for_bam_index()

        self.determine_reference_genome()       # Only need header to determine reference_genome or if unaligned BAM

    def process_bam_body(self, reentrant=None):
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

        if self.file_type == "CRAM":
            if self.Refgenome and wgse.reflib.missing_refgenome(self.Refgenome_qFN):
                raise BAMContentErrorFile('errRefGenFileMissing', os.path.basename(unquote(self.Refgenome_qFN)),
                                          self.Refgenome)  # Will override and not print error when Refgenome set
            elif not self.Refgenome:
                raise BAMContentError('errCRAMCannotDetermineReference')
            cram_opt = f'-T {self.Refgenome_qFN}'
        else:
            cram_opt = ""

        # Re-entrant code allows two runs of sampling from the BAM; numsamp then lonsamp additional
        numsamp = 20000             # Typically can get away with first numsamp as sample size
        lonsamp = numsamp * 29      # Nanopore long read BAMs need more samples; have more variance
        nstep = numsamp // 10
        lstep = lonsamp // 10
        if first_time:
            commands = f'{samtools} view {cram_opt} {bamfile} | {head} -{numsamp} > {flagfile_qFN} \n'
            run_bash_script('ButtonBAMStats2', commands)  # not running stats again; so simply do it
        else:
            commands = f'{samtools} view {cram_opt} {bamfile} | {tail} +{numsamp} | {head} -{lonsamp} > {flagfile_qFN} \n'
            run_bash_script('ButtonBAMStatsLong', commands)

        flagfile_oFN = nativeOS(unquote(flagfile_qFN))
        if not os.path.exists(flagfile_oFN):
            raise BAMContentErrorFile('errBAMNoFlagsFile', flagfile_oFN)

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
                    DEBUG(f'@Count: {lencnt} - Read Avg: {lenmean:,.0f}, {lenstd:,.0f};'  
                          f'Insert Avg: {sizmean:,.0f}, {sizstd:,.0f}')

                # Process FLAG field (2nd col) with 0x1 mask; 1 to indicate paired-end or 0 for single-end reads
                # Will keep running sum using +1 for each paired read and -1 for each single-end read
                if first_time:      # First time run is enough samples to accurately determine
                    readtyp += 1 if int(field[1]) & 0x1 else -1  # Try to make sure is clearly one or the other

                    if lencnt == 0:
                        # Only need single read to determine seqID; simply take last one still in memory
                        # Special replace() to insert the Dante MGI bad flow plate ID
                        self.Sequencer = determine_sequencer(field[0]).replace("6xxx", field[0][6:10] + " bad") \
                            if field and field[0] else "Unknown"
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
        if first_time:  #  and self.SNCount > 0:
            # Determine read type based on clear majority
            self.ReadType = "Paired" if readtyp > nstep else "Single" if readtyp < -nstep else "Unknown"  # Schroedingers paradox
            DEBUG(f'Read Segment Type: {self.ReadType}-end (scale:{readtyp})')

            if self.ReadType == "Unknown":
                # FLAG indicates a near equal mix of paired and single end reads (within 10%)
                raise BAMContentWarning('warnBAMBadReadType')

            if self.ReadType == "Paired" and sizcnt == 0 and self.Aligned:
                # No insert length because RNEXT never '='; but FLAGS indicate Paired -- inconsistent
                raise BAMContentErrorFile('errBAMInconsistentReadType', flagfile_oFN)

        # Nanopore long-read is highly variable; so need to read many more to get a better mean
        if first_time and lenmean > 410 and "Nanopore" in self.Sequencer:    # Increased len check for ySeq 400 bp single-end read
            #  Although often less total reads when longer read length, need at least 2 million it seems
            DEBUG("Long Read BAM ... reprocessing to get the read length using more read samples")
            self.process_bam_body(reentrant=[readtyp, lencnt, lenmean, lenM2, sizcnt, sizmean, sizM2])
            return      # Rest of settings will be done in second run only

        # Calculate final standard deviation (sqrt of final variance) for read length and insert size
        if lencnt > 2:
            lenstd = sqrt(lenM2 / (lencnt - 1))
            DEBUG(f'Read Length: {lenmean:,.0f}, stddev={lenstd:,.0f}')
            self.avg_read_length = lenmean
            self.avg_read_stddev = lenstd
        else:
            raise BAMContentError('errBAMBadReadLength')

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

        if not self.Aligned:    # Cannot calculate stats for an unaligned BAM (except FASTQ style ones, maybe)
            return

        # May be called before output directory is set; so use temporary files area if so (that must be set)
        path = wgse.tempf.FP if not wgse.outdir and wgse.outdir.FP is None else wgse.outdir.FP
        idxfile_qFN = f'"{path}{self.file_FB}_idxstats.csv"'
        idxfile_oFN = nativeOS(unquote(idxfile_qFN))

        idxstats_file_exists = os.path.isfile(idxfile_oFN) and os.path.getsize(idxfile_oFN) > 480
        #   and os.path.getmtime(idxfile_oFN) > os.path.getmtime(self.file_oFN)
        #   Cannot use file mod times as stats run could be from earlier CRAM / BAM before conversion

        if not idxstats_file_exists:    # If idxstats file does not exist, then create it
            # Unless user hit button directly or is a BAM with Index, then stop as it may take 30+ minutes
            bam_with_index_exists = self.file_type == "BAM" and self.check_for_bam_index()
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
                raise BAMContentErrorFile('errBAMNoIDXStatsFile', idxfile_oFN)

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
            raise BAMContentError('errBAMNonHumanGenome')

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

    def get_coverage_stats(self, window, button_directly=False):    # DEPRECATED; use get_bincvg_stats with bam_type="WGS"
        """
            Called from the BAM Stats display page to fill in the Breadth of Coverage column by running
            samtools coverage command.  Takes another 30 minutes so only give it as a second step option. Is only
            internally called so simply need to add to the self.stats_chroms array and return.  mainWindow will
            redisplay appropriately once returned.

            Coverage command file header:
            #rname startpos endpos numreads covbases coverage meandepth meanbaseq meanmapq
            Stats are based on full length; not less N coverage. So do not use coverage, meandepth
            Instead use covbases divided by (Model Len - N Bases; in stats_chroms)
            Using meanbaseq and meanmapq is OK
        """

        covfile_qFN = f'"{wgse.outdir.FPB}_coverage.csv"'
        covfile_oFN = nativeOS(unquote(covfile_qFN))

        # Long enough operation; if have file from before then reuse
        if button_directly and \
           not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 100 and
                os.path.getmtime(covfile_oFN) > os.path.getmtime(self.file_oFN)):

            # Run samtools coverage
            samtools = wgse.samtoolsx_qFN
            bamfile = self.file_qFN
            cramopts = f'--reference {self.Refgenome_qFN}' if self.file_type == "CRAM" else ""
            if self.file_type == "CRAM" and wgse.reflib.missing_refgenome(self.Refgenome_qFN):
                return

            commands = f'{samtools} coverage {cramopts} -o {covfile_qFN} {bamfile} \n'
            run_bash_script("CoverageStats", commands, parent=window)

        # Check if coverage file generated; even if generated, skip if unmapped-only BAM
        if not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 100):
            # if os.path.isfile(covfile_oFN):
            #    os.remove(covfile_oFN)  # Error in generating Coverage Stats file
            if button_directly:
                wgse_message("error", 'errBAMNoFileExists', True,
                             wgse.lang.i18n['errBAMNoCovStatsFile'].replace('{{FILE}}', covfile_oFN))
        elif len(self.stats_chroms) == 1:     # Is unmapped only BAM so coverage is 0 and pre-filled
            # Pretend we processed it because is empty (all zero's) which has been defaulted already
            self.coverage = self.stats_chroms[-1][7]    # Setting coverage summary value to 0 so says we processed
        else:
            self.process_coverage_stats(covfile_oFN)

    def process_coverage_stats(self, covfile_oFN):  # DEPRECATED: use process_bincvg_stats() with bam_type="WGS"
        """
        Process the samtools coverage stats file (we either found or created)
        """
        # Note: Total row at stats_chroms[-1] must always exist; Other row at stats_chroms[-2] may exist
        # Modified in v3 Aug 2021 to remove Y if Female and not include Other entries in Total stats
        with open(covfile_oFN, "r") as stats_file:
            stats_file.readline()       # Skip header line that we purposely left in for users perusing file
            modlen_deduction = 0        # Will hold Other row model length and Y if Female sample
            for stats_line in stats_file:
                line_columns = stats_line.split("\t")
                found = False
                for i in range(len(self.stats_chroms)):
                    if str(line_columns[0]) == self.stats_chroms[i][1]:
                        model_length = self.stats_chroms[i][2] - self.stats_chroms[i][3]
                        self.stats_chroms[i][7] = int(line_columns[4]) / model_length
                        if self.stats_chroms[i][0] == 'Y' and self.gender == 'Female':
                            modlen_deduction += model_length       # Save length of Y model to subtract out from Total
                        else:
                            self.stats_chroms[-1][7] += int(line_columns[4])    # Sum into Total row if not Y in Female
                        found = True
                        break
                if not found and str(line_columns[0]) not in ["*", "EBV", "NC_007605"] and \
                        self.stats_chroms[-2][0] == 'O':    # Must be Alt Contig to lump in with Other
                    # Note: will not call if only single row (Total); but could be only 2 (Y or mtDNA only)
                    self.stats_chroms[-2][7] += int(line_columns[4])        # Sum into Other row
                    # self.stats_chroms[-1][7] += int(line_columns[4])      # Sum into Total row (changed; no more)

            if self.stats_chroms[-2][0] == 'O':     # If Other row exists
                model_length = self.stats_chroms[-2][2] - self.stats_chroms[-2][3]
                self.stats_chroms[-2][7] /= model_length    # Have all Other's now to do division
                modlen_deduction += model_length            # Save length of Other model to subtract out from Total

            # Final finish up on Total row
            model_length = self.stats_chroms[-1][2] - self.stats_chroms[-1][3] - modlen_deduction
            self.stats_chroms[-1][7] /= model_length

            # Set summary value from total row at bottom; indicates coverage has been finished successfully
            self.coverage = self.stats_chroms[-1][7]

    def get_WEScvg_stats(self, window, button_directly=False): # DEPRECATED; use get_bincvg_stats() with scantype="WES"
        """
        Routine to get WES bincov stats using BED file.  Same as get_bincvg_stats except using BED file (and -a).
        Same samtools depth and awk script.  If you change it here, change it there. But this command only generates
        summary stats values for update of the main stats page.
        """
        covfile_qFN = f'"{wgse.outdir.FPB}_wescvg.csv"'
        covfile_oFN = nativeOS(unquote(covfile_qFN))

        # Long enough operation; if we have file from before then simply reuse
        if button_directly and \
           not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 120 and
                os.path.getmtime(covfile_oFN) > os.path.getmtime(self.file_oFN)):

            # Run samtools depth with WES Bed file to get avg read depth and coverage
            # The normal samtools coverage does not accept a bed file; samtools bedcov does not work well
            samtools = wgse.samtoolsx_qFN
            awk = wgse.awkx_qFN
            bamfile = self.file_qFN
            bedfile = wgse.reflib.get_wes_bed_file_qFN(self.Build, self.SNTypeC)
            cramopts = f'--reference {self.Refgenome_qFN}' if self.file_type == "CRAM" else ""
            if not check_exists(nativeOS(unquote(bedfile)), 'errNoBEDFile') or \
               (self.file_type == "CRAM" and wgse.reflib.missing_refgenome(self.Refgenome_qFN)):
                return

            # Because the depth file is so large; we process it via a pipe and awk; save per chromosome for user perusal
            # Expanded to include buckets 0-1, 1-4, 4-8, 8+ (inclusive on lower number only)
            script = """'{ names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; 
              if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else 
              {n3[$1]++ ; sumn3[$1]+=$3} } } } END {
              printf("%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n",
                "chr","zero","nonzero","sum nz","fract nz","avg nz","avg all",
                "TotalBC","Bet1-3","sum Bet1-3","Bet4-7","sum Bet4-7","Gtr7","sum Gtr7");
              for (x in names) { totalbc = zero[x]+nz[x]+1 ; 
                printf("%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",
                x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,
                totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }'"""

            commands = f'{samtools} depth -a -b {bedfile} {cramopts} {bamfile} | {awk} {script} > {covfile_qFN}'

            run_bash_script("CoverageStatsWES", commands, parent=window)

        # Check if coverage file generated; even if generated, skip if unmapped-only BAM (only headers)
        if not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 120):    # header-only is 107 bytes
            #if os.path.isfile(covfile_oFN):
            #    os.remove(covfile_oFN)  # Error in generating WES Coverage Stats file
            if button_directly:
                wgse_message("error", 'errBAMNoFileExists', True,
                             wgse.lang.i18n['errBAMNoCovStatsFile'].replace('{{FILE}}', covfile_oFN))
        elif len(self.stats_chroms) == 1:         # Is unmapped only BAM (total only row) so coverage is 0
            self.raw_avg_read_depth_WES = 0     # these were not defaulted to zero
            self.mapped_avg_read_depth_WES = 0  #
            self.coverage_WES = 0               # Setting coverage summary value, even if 0, says we processed the data
        else:
            self.process_WEScvg_stats(covfile_oFN)

    def process_WEScvg_stats(self, covfile_oFN):    # DEPRECATED; use process_bin_stats() with scantype="WES"
        """
        Process our custom WES stats file created from a run of samtools depth and a custom awk script post-processor.
        Even though the file has per sequence values, we only want the summary values saved and displayed.
        Have gotten here from single internal call that has already assured the file exists.  Just filling in the data
        table from the file content.
        """
        # For WES Stats, only save total average read depth (zero count and non-zero); as well as Coverage. Not per chr
        zero_bases_cnt = nonzero_bases_cnt = sumnz_bases = 0
        with open(covfile_oFN, "r") as stats_file:
            next(stats_file)        # Skip header line that we added in for user persuing file
            # We simply sum all rows as WES Coverage file as only primary sequences
            for stats_line in stats_file:
                columns = stats_line.split("\t")
                zero_bases_cnt    += int(columns[1])    # WES zero count does not include N's
                nonzero_bases_cnt += int(columns[2])
                sumnz_bases       += int(columns[3])

            total_bases = zero_bases_cnt + nonzero_bases_cnt + 1    # To avoid divide zero
            self.raw_avg_read_depth_WES    = round(sumnz_bases / total_bases, 1)
            if self.raw_avg_read_depth_WES >= 10.0:
                self.raw_avg_read_depth_WES = round(self.raw_avg_read_depth_WES)
            self.mapped_avg_read_depth_WES = round(sumnz_bases / nonzero_bases_cnt, 1)
            if self.mapped_avg_read_depth_WES >= 10.0:
                self.mapped_avg_read_depth_WES = round(self.mapped_avg_read_depth_WES)
            self.coverage_WES              = nonzero_bases_cnt / total_bases

    def get_bincvg_stats(self, window, scantype="WGS", button_directly=True):
        """
        Very similar to get_WEScvg_stats except doing a full WGS (-aa) instead of using a BED file.  Same
        samtools depth command with same awk script post-processing.  If you change it here, change it there.
        Note: Can only be called after regular idxstats run so certain parameters available
        """
        covfile_qFN = f'"{wgse.outdir.FPB}_bincvg.csv"' if scantype == 'WGS' else \
                      f'"{wgse.outdir.FPB}_wescvg.csv"'
        covfile_oFN = nativeOS(unquote(covfile_qFN))

        # Only unmapped BAM will have stats_chroms array (idxstats) of length 1 (total row only)
        if len(self.stats_chroms) == 1:  # Do not try and process (run samtools depth) if unmapped only BAN
            if scantype == "WGS":
                self.coverage = 0   # Is unmapped only BAM (total only row) so coverage is 0
            else:
                self.raw_avg_read_depth_WES = 0  # these were not defaulted to zero
                self.mapped_avg_read_depth_WES = 0  #
                self.coverage_WES = 0  # Setting coverage summary value, even if 0, says we processed the data
            return

        # Long enough operation (2hrs); if we have valid file from before then simply reuse
        if button_directly and \
           not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 120 and
                os.path.getmtime(covfile_oFN) > os.path.getmtime(self.file_oFN)):

            # Run samtools depth to get Bin Coverage values
            # The normal samtools coverage does not accept range of bins
            samtools = wgse.samtoolsx_qFN
            awk = wgse.awkx_qFN
            bamfile = self.file_qFN

            # Use BED file if WES scan type.  If Y (or Y and MT) only BAM; use special "Poz" non-exome BED file
            bedfile = wgse.reflib.get_wes_bed_file_qFN(self.Build, self.SNTypeC, self.Yonly) if scantype == "WES" else ""
            #cramopts = f'--reference {self.Refgenome_qFN}' if self.file_type == "CRAM" else ""

            if bedfile and not check_exists(nativeOS(unquote(bedfile)), 'errNoBEDFile'):
                # or (cramopts and wgse.reflib.missing_refgenome(self.Refgenome_qFN)):
                return

            # Because the depth file is so large; we process it via a pipe and awk; save per chromosome for user perusal
            # Expanded to include buckets 0, 1-3, 4-7, 8+ (inclusive)
            script = """'{ names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; 
              if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else 
              {n3[$1]++ ; sumn3[$1]+=$3} } } } END {
              printf("%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n",
                "chr","zero","nonzero","sum nz","fract nz","avg nz","avg all",
                "TotalBC","Bet1-3","sum Bet1-3","Bet4-7","sum Bet4-7","Gtr7","sum Gtr7");
              for (x in names) { totalbc = zero[x]+nz[x]+1 ; 
                printf("%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",
                x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,
                totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }'"""

            subopts = "-aa" if scantype == "WGS" else f'-a -b {bedfile}'
            # Per John Bonfield (https://github.com/samtools/samtools/issues/1643#issuecomment-1111133582)
            # no need for a reference spec when a CRAM file supplied to the samtools depth command.
            commands = f'{samtools} depth {subopts} {bamfile} | {awk} {script} > {covfile_qFN}'

            run_bash_script("CoverageStatsBIN", commands, parent=window)

        # Check if coverage file generated properly
        if not (os.path.isfile(covfile_oFN) and os.path.getsize(covfile_oFN) > 120):     # header-only is 107 bytes
            # if os.path.isfile(covfile_oFN):
            #   os.remove(covfile_oFN)  # Error in generating Coverage Stats file
            if button_directly:
                wgse_message("error", 'errNoFileExists', True,
                             wgse.lang.i18n['errBAMNoCovStatsFile'].replace('{{FILE}}', covfile_oFN))
        else:
            self.process_bincvg_stats(covfile_oFN, scantype)

    def process_bincvg_stats(self, bincov_oFN, scantype="WGS"):
        """
        Processes both WGS bincvg and WEScvg file (both same format from samtools depth piped to awk script)
        Like for idxstats, WGS form has all sequences so have to clump non-primary into "Other". May be subset BAM.
        See process_samtools_idxstats for template from which this routine was developed. We rely on idxstats having
        been run so we can make use of basic values like gender, etc.
        """

        # The WESCoverage and (WGS)binCoverage stats files are identical and created from an AWK script run on the
        # output of "samtools depth".  For WES, with a bed file, only the primaries are included.  For WGS, with the
        # "-aa" option, then like for idxstats, includes the model N values so have to reduce the overall model length.
        # The column header of the result table stored and read in (.csv file in TSV format) is:
        #  chr (seq name), zero (base count), nonzero (base count), sum nz (sum of non-zero base depths),
        #  [fract nz, avg nz, avg all, TotalBC,] bet1-3, sum bet1-3, bet4-7, sum bet4-7, gtr7, sum gtr7
        # Items 4-7 (in []'s) are derived from other values and not really needed. The N's count is not in the file.
        # The resultant stored Stats arrays have the following columns:
        #  keySN, storedSN, Modelen, N Count, then bins 0, 1-3, 4-7, 8up, nzcnt
        stats_autos = []
        stats_somal = []    # REH 20Mar2020 pulled out to easily numeric sort autosomes
        stats_mito  = []    # REH 25Feb2022 pulled out so can sort somal
        stats_total = ["T", wgse.lang.i18n['Total'], 0, 0, 0, 0, 0, 0, 0]  # Total row of primaries at bottom
        stats_altcont = ["O", wgse.lang.i18n['OtherChr'], 0, 0, 0, 0, 0, 0, 0]  # Alt Contigs row collecting all others
        stats_grantot = ["G", "", 0, 0, 0, 0, 0, 0, 0]      # Grand total row including Alt_contigs

        sumnz_bases = 0
        with open(bincov_oFN, "r") as stats_file:
            next(stats_file)        # Skip header line that we added in for user persuing file
            for stats_line in stats_file:
                columns = stats_line.split("\t")

                chromosome = columns[0].strip()
                chromnum = chromosome.upper().replace("CHR", "").replace("MT", "M")  # normalize to numeric only, M only

                ncount = wgse.nadjust[self.Build][chromnum] if \
                    (chromnum in wgse.valid_autos or chromnum in wgse.valid_somal) and scantype == "WGS" else 0

                zero_bases_cnt  = int(columns[1]) - ncount  # N's only counted in Primary sequences of WGS files
                nz_bases_cnt    = int(columns[2])           # Same as bin*cnt summed
                sumnz_bases    += int(columns[3])           # From WESCvg original before buckets; only primary counted
                total_bases_cnt = int(columns[7])           # Same as zero_bases_cnt + nz_bases_cnt
                bin1_3_cnt      = int(columns[8])
                bin4_7_cnt      = int(columns[10])
                bin8_up_cnt     = int(columns[12])
                # Not using sum values as not trying to calculate any kind of mean or std dev; only count of entries

                if nz_bases_cnt == 0:    # Only save rows with values
                    continue

                # Constructed row in the wgse.BAM.stats_bin[wes] table
                row = [chromnum, chromosome, total_bases_cnt, ncount, zero_bases_cnt,
                       bin1_3_cnt, bin4_7_cnt, bin8_up_cnt, nz_bases_cnt]

                # Build up table elements (separately so can sort before adding)
                if chromnum in wgse.valid_autos:        # Handle Autosomes separately so can sort before storing
                    stats_autos.append(row)
                elif chromnum in wgse.valid_somal:      # Somal in Primary
                    stats_somal.append(row)
                elif chromnum == "M":
                    # total_bases_cnt -= 1              # There is one N in there; just to be accurate
                    stats_mito.append(row)
                else:                                   # All others (alt contigs); if they exist
                    #if chromosome not in ["EBV", "NC_007605", '*']:   # non-zero Alt Contigs except EBV (not in WES)
                    #    continue
                    stats_altcont[2] += total_bases_cnt
                    stats_altcont[3] += 0  # We have not loaded N count for contigs; only prinary
                    stats_altcont[4] += zero_bases_cnt
                    stats_altcont[5] += bin1_3_cnt
                    stats_altcont[6] += bin4_7_cnt
                    stats_altcont[7] += bin8_up_cnt
                    stats_altcont[8] += nz_bases_cnt

        # Numerically sort the Autosomes by chromosome number before building full table.
        # Some files are sorted alphabetically and not numerically. chr10 follows chr1 in alphabetic sort.
        stats_autos.sort(key=lambda chrn: int(chrn[0]))  # Sort entries based on chromosome # (side effect)
        stats_somal.sort(key=lambda chrn: chrn[0])

        # Build table
        stats_bin = stats_autos  # start with autosomes
        stats_bin.extend(stats_somal)
        stats_bin.extend(stats_mito)

        # Sum up entries for Total row (not including Other / Alt Contigs or Y if female)
        for entry in stats_bin:
            for col in range(2, 8+1):
                if entry[0] == 'Y' and self.gender == 'Female':
                    continue
                stats_total[col] += entry[col]

        # Add Total Row
        stats_bin.append(stats_total)

        # Add in Alt Contig (Other) row; create and add Grand Total row
        if stats_altcont[8] > 0:   # WES will not have any alts; this is the true "Other" row
            stats_bin.append(stats_altcont)
            for col in range(2, 8+1):
                stats_grantot[col] = stats_total[col] + stats_altcont[col]
            stats_bin.append(stats_grantot)

        # Save before normalizing (for WES case use)
        total_bases = stats_bin[-1][2]
        nonzero_bases_cnt = stats_bin[-1][8]

        # Normalize all entries (for percentage) including total row(s)
        for entry in stats_bin:
            real_base_cnt = entry[2] - entry[3]
            entry[4] = (entry[4] - entry[3]) / real_base_cnt    # Special handling for zero_base_cnt that includes Ns
            for i in range (5, 8+1):
                entry[i] /= real_base_cnt

        if scantype == "WGS":
            self.stats_bin = stats_bin          # Save table for display in coverage stats pop-up
            # Fill in main stats table last column for display in main stats page; simpler way with map and iterables?
            for rowc in range(len(self.stats_chroms)):
                for rowb in range(len(self.stats_bin)):
                    if self.stats_chroms[rowc][0] == stats_bin[rowb][0]:
                        self.stats_chroms[rowc][7] = stats_bin[rowb][8]
            self.coverage = stats_total[8]
        elif scantype == "WES":
            self.stats_binwes = stats_bin       # Save table for display in coverage (WES) stats pop-up

            # Calculate and save the three summary values used in main stats page summary area now
            self.raw_avg_read_depth_WES    = round(sumnz_bases / total_bases, 1)
            if self.raw_avg_read_depth_WES >= 10.0:
                self.raw_avg_read_depth_WES = round(self.raw_avg_read_depth_WES)
            self.mapped_avg_read_depth_WES = self.raw_avg_read_depth_WES    # By definition, there are no unmapped bases
            self.coverage_WES              = nonzero_bases_cnt / total_bases

    def determine_reference_genome(self):
        """
        Try to determine the reference genome from just the header information.
        Has gotten more complicated since we accept any BAM; including subsets we produce (Y, MT, unmapped only).

        The BAM Header is set from the reference genome by the alignment tool creating the BAM.  It is generally
        carried through in full when subsets of the BAM are made (e.g. unmapped BAM).  So you may get an answer here
        even if only an unmapped BAM body.  Header SQ records should be based only on the reference model and
        not alignment content.

        Original, generic, major model naming comes from:
         hg if old style "chr22/chrM" sequence names, GRCh if numeric-only
         19 if old style hg with Yoruba, 37 if build 37 model lengths, 38 if Build 38 model lengths, ditto T2T 99
         Number of Sequence Names in the header is a good indicator of class and other model characteristics

        NOTE: Much of this code is duplicated in the VCFFiles class call of the same name.  Should likely pull out
        just the differences and make a single, generic call that adopts to the differences.  Maybe simply extract
        the SN/ID and LN/length fields into separate entry and process that generically?
        """

        # Determine SN names as given as opposed to relying on reference model to determine
        accession = ["@SQ\tSN:CM0", "@SQ\tSN:CP", "@SQ\tSN:J0", "@SQ\tSN:NC_"]
        self.SNTypeC = "Chr" if "@SQ\tSN:chr" in self.Header else \
                       "Num" if "@SQ\tSN:1\t" in self.Header else \
                       "Acc" if any(x in self.Header for x in accession) else \
                       "Unk"

        self.SNTypeM = "MT" if "@SQ\tSN:MT" in self.Header or "@SQ\tSN:chrMT" in self.Header else \
                       "M"  if "@SQ\tSN:M" in self.Header or "@SQ\tSN:chrM" in self.Header else \
                       "Unk"

        self.SNCount = self.Header.count('@SQ\tSN:')   # Almost sufficient for an analysis model determination

        DEBUG(f"SN: {self.SNTypeC}, {self.SNTypeM}; SN Count:{self.SNCount}")

        # If unaligned BAM, simply return and set unknowns. Checks only apply to SAM/BAM; not CRAM. uBAMs used with
        #  Broad Institute Best Practice in place of FASTQs. Should scan all reads in body to assure they are all
        #  unmapped; in case these header variations are not indicative. uBAM is not defined anywhere.
        #  java -Xmx1G -jar picard.jar ReverSam I=input.aligned.bam O=output.unaligned.bam SANITIZE=true
        if self.SNCount == 0 and not self.Sorted:
            DEBUG(f"Unaligned BAM: no reference model, etc.")
            self.Aligned = False
            self.SNTypeM = "Unk"
            self.SNTypeM, self.Build, self.RefMito = ("Unk", 0, "Unknown")
            self.Refgenome = self.RefgenomeNew = "Unaligned"
            return

        self.Aligned = True

        # Possible that header has been shortened if a subset BAM file? So only use chr1, Y and X to check length
        # If only MT or Unmapped (*) in header, then cannot tell RefGenome
        self.Build, self.RefMito = \
            (99, "Custom") if any(x in self.Header for x in ["LN:248387561", "LN:248387328", "LN:248387497",
                        "LN:248415701", "LN:62456832", "LN:62460029", "LN:62480187", "LN:154343774", "LN:25843790",
                        "LN:154259566", "LN:154259625", "LN:154269076", "LN:154349815", "LN:154434329"]) else \
            (38, "rCRS")   if any(x in self.Header for x in ["LN:248956422", "LN:57227415", "LN:156040895"]) else \
            (37, "rCRS")   if any(x in self.Header for x in ["LN:249250621", "LN:59373566", "LN:155270560"]) else \
            (18, "Yoruba") if any(x in self.Header for x in ["LN:247249719", "LN:57772954", "LN:154913754"]) else \
            (17, "Yoruba") if any(x in self.Header for x in ["LN:245522847", "LN:57701691", "LN:154824264"]) else \
            (16, "Yoruba") if any(x in self.Header for x in ["LN:246127941", "LN:50286555", "LN:153692391"]) else \
            (15, "Yoruba") if any(x in self.Header for x in ["LN:245203898", "LN:50961097", "LN:152634166"]) else \
            ( 0, "Unknown")

        # Modify Mitochondria model based on its length if Build 37 (only one with both types in releases)
        if self.Build == 37 and any(x in self.Header for x in ["M\tLN:16571", "MT\tLN:16571"]):
            self.Build, self.RefMito = (19, "Yoruba")
        # Todo handling RSRS model -- look for spacers?

        DEBUG(f"Build: {self.Build:3d}")
        DEBUG(f"Ref Genome Mito: {self.RefMito}")

        # New form is based on Major / Class mechanism in Reference Genome study: https://bit.ly/34CO0vj
        #  Used to rely on SNCount.  But oddball, unrecognized ref genomes in BAMs may have something close set by user.
        #  So, rely more on key items found in special ref genomes. Keep patching this.  Need to use the MD5sum method.
        if self.Build == 99:        # Used chr1, chrX or chrY lengths to determine Build99 earlier
            # Use X and Y length to determine T2T / HPP model
            if "LN:62456832" in self.Header and "LN:154343774" in self.Header:  # CHM13 v1.1 & HG002 v2 XY
                self.Refgenome = self.RefgenomeNew = "THGv20"
            elif "LN:62460029" in self.Header and "LN:154349815" in self.Header:  # CHM13 v1.1 & HG002 v2.7 XY
                self.Refgenome = self.RefgenomeNew = "THGv27"
            elif "LN:62480187" in self.Header and "LN:154434329" in self.Header:  # HG01243 v3 PR1 "Puerto Rican"
                self.Refgenome = self.RefgenomeNew = "THG1243v3"
            elif "LN:57277415" in self.Header and "LN:154259566" in self.Header:  # CHM13 v1.1 & GRCh38 Y
                self.Refgenome = self.RefgenomeNew = "HPPv11"
            elif "LN:57277415" in self.Header and "LN:154259625" in self.Header:  # CHM13 v1 X & GRCh38 Y
                self.Refgenome = self.RefgenomeNew = "HPPv1"
            elif "LN:62456832" in self.Header and "LN:156040895" in self.Header:  # GRCh38 w/ HG002 v2 Y  (ySeq)
                self.Refgenome = self.RefgenomeNew = "THGySeqp"
            elif "LN:62460029" in self.Header and "LN:154259566" in self.Header:  # CHM13 v1.1 & HG002 v2.7 Y
                self.Refgenome = self.RefgenomeNew = "T2Tv20"
            elif "LN:154259566" in self.Header:  # Must be plain CHM13 v1.1 as special Y not found
                self.Refgenome = self.RefgenomeNew = "T2Tv11"
            elif "LN:154259625" in self.Header:  # Must be plain CHM13 v1 as special Y not found
                self.Refgenome = self.RefgenomeNew = "T2Tv10"
            elif "LN:154259664" in self.Header:  # Must be plain CHM13 v0.9
                self.Refgenome = self.RefgenomeNew = "T2Tv09"
            else:  # Think it is T2T / HPP build but cannot recognize Y or X length
                DEBUG(f'Unrecognized T2T model; no matching X or Y length in BAM to known models.')
        elif self.SNCount in [85, 86] and "SN:NC_007605" in self.Header:
            # hs37 class have SN:NC007605 (EBV in Numeric naming) sans human_g1k / GRCh37.primary_assembly models
            # human_1kg model is 84 and one less SN than hs37.fa.gz; hs37d5 is 86 and one more than hs37 (hs37d5 decoy)
            self.Refgenome = "hs37d5" if "@SQ\tSN:hs37d5" in self.Header else "hs37"
            self.RefgenomeNew = "1k37g"
        elif self.SNCount in [85, 298] and "SN:chrEBV" in self.Header:
            self.Refgenome = None     # 1KGenome analysis models in NCBI Genbank Archive or UCSC; but not handled yet
            self.RefgenomeNew = "1k37h"
        elif self.SNCount == 84:      # human_g1k (if Num), GRCh37.primary_assembly.genome (if Chr)
            self.Refgenome = "hs37-" if self.SNTypeC == "Num" else \
                             "GRCh37-" if self.SNTypeC == "Chr" else None
            self.RefgenomeNew = "1K37g" if self.SNTypeC == "Num" else \
                                "EBI37h" if self.SNTypeC == "Chr" else None
        elif self.SNCount in [195, 456, 2580, 2581, 2841, 3366] and \
             ("SN:chrEBV" in self.Header or "SN:EBV" in self.Header):
            # hs38DH is 3366 SN count and has SN:HLA- unique; hs38 is 195 and hs38a is 456; all uniquely have chrEBV
            # hs38d1s is sequencing.com model made by hs38d1 with 22_KI270879v1_alt added
            self.Refgenome = "hs38DH"  if "SN:chr22_KI270879v1_alt" in self.Header and self.SNCount == 3366 else \
                             "hs38d1a" if self.SNCount == 2841 else \
                             "hs38d1s" if self.SNCount == 2581 and "SN:22_KI270879v1_alt" in self.Header else \
                             "hs38d1"  if self.SNCount == 2580 else \
                             "hs38a"   if self.SNCount == 456 else \
                             "hs38"  # if self.SNCount == 195
            self.RefgenomeNew = "1k38" + ("pg" if self.Refgenome == "hs38d1s" else "h")
            if self.SNCount == 2580 and \
               ("M5:a491618313b78cdca84ae9513e4f4844" in self.Header or "Verily" in self.Header):
                self.Refgenome = "hs38d1v"      # Special Google Verily model; cannot be distinguished without M5 field;
                self.RefgenomeNew = "1k38ph"    # but has very different m5 signature on each SN than hs38d1
        elif self.SNCount in [93, 297, 455, 639]:    # SNCounts of 6 hg/ebi models; 2 duplicated
            # Handle the hg (UCSC) and GRCh (EBI) models here
            self.Refgenome = "hg" if self.SNTypeC == "Chr" else "GRCh"     # 297 & 639 are Patch 13 GRCh models
            self.Refgenome += str(self.Build)   # Build already takes into account mito for 19/37 differentiation
            self.RefgenomeNew = self.Refgenome.replace("GRCh", "EBI") + ("g" if self.SNTypeC == "Chr" else "h")
        elif self.SNCount == 25:        # T2T models of this size already captured with LN fields above
            self.Refgenome = "hg37w"   # Odd WGSE v1/2 25 SN hg19 model with EBI primaries
            self.RefgenomeNew = "EBI37ph"
        DEBUG(f'Ref Genome: {self.Refgenome}, by New nomenclature: {self.RefgenomeNew}')

        # Using the MD5 on the BAM header, see if we know the refgenome more refined (actual model file); for CRAM
        # Note: MD5 method requires full WGS header with all FASTA model SNs defined there; not subsetted in header
        pass  # Todo implement code to lookup MD5Sum on BAM Header of SN & LN fields

        # We give up if still not set, simply ask the user
        if not self.Refgenome:  # not set yet: and (self.chrom_types["A"] > 1 or self.chrom_types["Y"] > 1):
            wgse.reflib.ask_reference_genome(inBAM=True)      # Ignore return value as setup self.Refgenome in call
            DEBUG(f'Ref Genome (User): {self.Refgenome}')
            # todo ask user to send BAM header so we can get its md5 signature for future runs

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
                ''' Key values are one of: ("A", "X", "Y", "M", "O", "*"). Single character lookup in language file. '''
        if count == 1:
            chrom_types_str += f' {wgse.lang.i18n["Only"]}'
        return chrom_types_str

    def refgenome_str(self):
        """ Create string of ref genome, mito genome, and SN Count of BAM / CRAM for stats """

        if not self.Aligned:
            result = wgse.lang.i18n["Unaligned"]
            return result

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
        if not self.Aligned:
            result += wgse.lang.i18n["Unaligned"]
        else:
            # if self.Sorted:
            result += wgse.lang.i18n["Sorted"] if self.Sorted else wgse.lang.i18n["Unsorted"]
            # if self.Indexed:
            result += ", " if result else ""
            result += wgse.lang.i18n["Indexed"] if self.Indexed else wgse.lang.i18n["Unindexed"]

        # File size
        result += ", " if result else ""
        result += f'{round(self.file_stats.st_size / (10.0 ** 9), 1)} {wgse.lang.i18n["GBs"]}'
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

    def check_for_bam_index(self):
        """ Marko's original BAM Index file exists check.  """
        # todo need to add check in OUT directory, if set. And add option to use in samtools calls if located there
        self.Indexed = \
            (os.path.isfile(self.file_oFN + ".bai") or os.path.isfile(self.file_oFN + ".BAI")) if self.file_type == "BAM" else \
            (os.path.isfile(self.file_oFN + ".crai") or os.path.isfile(self.file_oFN + ".CRAI")) if self.file_type == "CRAM" else None
        # todo case sensitive check needed? how does samtools handle?
        return self.Indexed

    def realign_BAM_filename(self, new_refgenome):
        """
        For use when realigning BAM to different build (37 to 38; or 38 to 37)
        To avoid lengthening the BAM name, see if we can simply replace the build ID already embedded in the file name
        """
        # Will never go back to hg19 in current form as do not generate Yoruba target models
        if "GRCh38" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("GRCh38", "GRCh37")
        elif "GRCh37" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("GRCh37", "GRCh38")
        elif "_hg38" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_hg38", "_hg37")
        elif "_hg37" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_hg37", "_hg38")
        elif "_hg19" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_hg19", "_hg38")
        elif "_hs37d5" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_hs37d5", "_hs38")
        elif "_hs38" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_hs38", "_hs37d5")
        elif "_T2Tv2" in self.file_FB:
            newBAM_FBS = self.file_FBS.replace("_T2Tv2", "_hs38")
        else:  # Could not find acceptable name to patch so append the new Refgenome to the current file name.
            newBAM_FBS = f'{self.file_FB}_{new_refgenome}{self.file_FS}'
        # Need to place the new file in the Output Directory
        return f'{wgse.outdir.oFP}{newBAM_FBS}'

    def find_FASTQs(self):
        """
        A special to search for commonly-named FASTQs from vendor.  As a precursor to creating them from the BAM.
        In here as if they are found, will set class variable so they can be used and associated.  Likely will do
        similar for VCF.  Eventually, add "get_" routine like for reference_genome to ask the user. Saves time and
        disk space to reuse. Helpful especially when we start saving and restore BAM library stats.
        """
        paired = self.ReadType == "Paired"
        # todo checking dates and sizes

        # First check if names have been set in this BAM class already
        if self.R1fastq_FN and (not paired or self.R2fastq_FN):
            if os.path.exists(nativeOS(self.R1fastq_FN)) and (not paired or os.path.exists(nativeOS(self.R2fastq_FN))):
                return True

        # First look in output directory and BAM directory for ones we create (our naming convention)
        if wgse.outdir.FPB and paired:      # Look in Output Directory
            r1fastq_FN = f'{wgse.outdir.FPB}_R1.fastq.gz'
            r2fastq_FN = f'{wgse.outdir.FPB}_R2.fastq.gz'
            if os.path.exists(nativeOS(r1fastq_FN)) and os.path.exists(nativeOS(r2fastq_FN)):
                self.R1fastq_FN = r1fastq_FN
                self.R2fastq_FN = r2fastq_FN
                return True
            r1fastq_FN = f'{self.file_FPB}_R1.fastq.gz'
            r2fastq_FN = f'{self.file_FPB}_R2.fastq.gz'
            if os.path.exists(nativeOS(r1fastq_FN)) and os.path.exists(nativeOS(r2fastq_FN)):
                self.R1fastq_FN = r1fastq_FN
                self.R2fastq_FN = r2fastq_FN
                return True

        if wgse.outdir.FPB and not paired:
            fastq_FN = f'{wgse.outdir.FPB}.fastq.gz'
            if os.path.exists(nativeOS(fastq_FN)):
                self.R1fastq_FN = fastq_FN
                return True
            fastq_FN = f'{self.file_FPB}.fastq.gz'
            if os.path.exists(nativeOS(fastq_FN)):
                self.R1fastq_FN = fastq_FN
                return True

        # Now look in BAM directory for common test company names: Nebula Genomics
        if paired:
            r1fastq_FN = f'{self.file_FPB}_1.fq.gz'
            r2fastq_FN = f'{self.file_FPB}_2.fq.gz'
            if os.path.exists(nativeOS(r1fastq_FN)) and os.path.exists(nativeOS(r2fastq_FN)):
                self.R1fastq_FN = r1fastq_FN
                self.R2fastq_FN = r2fastq_FN
                return True  # todo checking dates and sizes

        # Now look in BAM directory for common test company names: Dante Labs
        if paired:
            r1fastq_FN = f'{self.file_FPB}_SA_L001_R1_001.fastq.gz'
            r2fastq_FN = f'{self.file_FPB}_SA_L001_R2_001.fastq.gz'
            if os.path.exists(nativeOS(r1fastq_FN)) and os.path.exists(nativeOS(r2fastq_FN)):
                self.R1fastq_FN = r1fastq_FN
                self.R2fastq_FN = r2fastq_FN
                return True  # todo checking dates and sizes

        # Now look in BAM directory for common test company names: ySeq (does not provide FASTQ's ?)

        # Now look in BAM directory for common test company names: Sequencing.com
        if paired:
            r1fastq_FN = f'{self.file_FPB}.1.fq.gz'
            r2fastq_FN = f'{self.file_FPB}.2.fq.gz'
            if os.path.exists(nativeOS(r1fastq_FN)) and os.path.exists(nativeOS(r2fastq_FN)):
                self.R1fastq_FN = r1fastq_FN
                self.R2fastq_FN = r2fastq_FN
                return True  # todo checking dates and sizes

        # Now look in BAM directory for common test company names: Full Genomes Corp

        # todo ask the user if they know where they are and let them set.  Implement once fastq_FN stats save happens.

        self.R1fastq_FN = self.R2fastq_FN = None
        return False

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
                VCFs[f'{wgse.outdir.FPB}_SNP.vcf.gz']   = ({'SNP'}, {'A', 'X', 'Y', 'M'})
                VCFs[f'{wgse.outdir.FPB}_InDel.vcf.gz'] = ({'InDel'}, {'A', 'X', 'Y', 'M'})
                VCFs[f'{wgse.outdir.FPB}_CNV.vcf.gz']   = ({'CNV'}, {'A', 'X', 'Y', 'M'})
                VCFs[f'{wgse.outdir.FPB}_SV.vcf.gz']    = ({'SV'}, {'A', 'X', 'Y', 'M'})
                VCFs[f'{wgse.outdir.FPB}.vcf.gz']       = ({'unk'}, {'A', 'X', 'Y', 'M'})

            # Now look in BAM directory for common test company names that come with their BAMs
            VCFs[f'{self.file_FPB}.filtered.snp.vcf.gz']    = ({'SNP'}, {'A', 'X', 'Y', 'M'})    # Dante Labs
            VCFs[f'{self.file_FPB}.filtered.indel.vcf.gz']  = ({'InDel'}, {'A', 'X', 'Y', 'M'})  # Dante Labs
            VCFs[f'{self.file_FPB}.cnv.vcf.gz']             = ({'CNV'}, {'A', 'X', 'Y', 'M'})  # Dante Labs & Sequencing
            VCFs[f'{self.file_FPB}.sv.vcf.gz']              = ({'SV'}, {'A', 'X', 'Y', 'M'})   # Dante Labs & Sequencing
            VCFs[f'{self.file_FPB}.vcf.gz']                 = ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'})  # Nebula & ySeq
            VCFs[f'chrY_called_{self.file_FPB}.vcf.gz']     = ({'SNP'}, {'Y',})                  # ySeq
            VCFs[f'chrY_cleaned_{self.file_FPB}.vcf.gz']    = ({'SNP'}, {'Y',})                  # ySeq
            VCFs[f'chrY_derived_{self.file_FPB}.vcf.gz']    = ({'SNP'}, {'Y',})                  # ySeq
            VCFs[f'chrY_INDELS_{self.file_FPB}.vcf.gz']     = ({'InDel'}, {'Y',})                # ySeq
            VCFs[f'chrY_novel_SNPs_{self.file_FPB}.vcf.gz'] = ({'SNP'}, {'Y',})                  # ySeq
            VCFs[f'{self.file_FPB}.snp-indel.genome.vcf.gz'] = ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'}) # Sequencing.com
            VCFs[f'{self.file_FPB}.mito.vcf.gz']            = ({'SNP', 'InDel'}, {'A', 'X', 'Y', 'M'})  # Sequencing.com
            # Full Genomes Corp?

            for key, val in VCFs.items():
                if os.path.exists(nativeOS(key)):
                    self.VCFs[key] = val

        if not (self.VCFs and len(self.VCFs) > 0):
            # todo ask the user if they know where they are and let them set.  Implement once VCF stats save happens.
            pass

        # process_vcf_headers(self)

        return self.VCFs
