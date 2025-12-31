# coding: utf8
# Copyright (C) 2018-2020 City Farmer
# Copyright (C) 2020-2023 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

# __version__ = "Dev ver4n (15 Jul 2022)"  Now captured dynamically from program/program.json
# manual_url = "https://bit.ly/3JCyZNa"       # Version 4 manual (not publicly released yet)

__version__ = None      # Now read in and constructed from the program.json and release.json files
manual_url = "https://get.wgse.io//WGSExtract_v4_User_Manual"  # Default if not set in the program.json file

"""###################################################################################################################
 General Settings module support for the WGS Extract system

  This module is imported as wgse everywhere.  For convenience, we additionally use a local name to reduce name length
  in one instance (font).  Therefore, the code to use this module in other modules is:
    import settings as wgse
    font = wgse.font

  Because Global variables and constants are defined here, this file is included by all others.
  We must simply import; variable names cannot be selectively included with a "from" in Python.
  Imports of any needed System library functions here are buried in function definitions. (None
  are called often so there is not much penalty for doing so.)

  As Python has no structures, and global variable values are read when the file is imported, and redirected naming
   can get unwieldly, we do not use a Class that we later instantiate. It adds yet another layer of naming.
   So we insdtead define a single function init() here that is similar to a Class __init__ and that is expected
   to "instantiate" this "Class" and its global variables.  Then all the variables are simply available. This is all
   simply to reduce an extra level of naming.  All variables can simple be gotten by wgse.name where name is the
   variable name.

  See description at end of this file for naming conventions on variables of files / paths.

 Class(es): none
 Globals: see long list of primary level names below
 Function(s): init(), load(), save()
"""

# -----------------------------------------------------------------------------------------------------------------
# Program global constants
#
# There are no real constants in Python. But we treat these as such.  Read-only, set here once.
ftdna_pubytree_url  = "https://www.familytreedna.com/public/y-dna-haplotree/"
yfull_searchsnp_url = "https://yfull.com/search-snp-in-tree/"
isogg_tree_url      = "https://isogg.org/tree/"

# Key window sizes (fixed size to force word wrap; target min is macbook pro 1366x768 or PC 1280x792)
mainwindow_size   = '700x750'
microarr_winsize  = '615x750'
bamstats_winsize  = '1030x768'  # Need every vertical pixel allowed ...
simResult_winsize = '700x700'
simResult_maxw    = 700
simResult_maxh    = 700
yHgResult_winsize = '850x750'
yHgResult_maxw    = 850
yHgResult_maxh    = 750

# Fonts moved to utilities class definition called from mainwindow_init

# Expected run times of various commands in seconds; for Please Wait window (used in module commandprocessor)
# Number below based on Randy's 40x, 57GB BAM file on his 2 core, AMD A10-5700 processor using CygWin htslib 1.10
# Note: dictionary key name longest length is used in commandprocessor.py to set a field size.
expected_time = {    # hours[1] * Minutes[1] * Seconds
    'GetBAMHeader':               2,  # ## samtools view -H (less than a second usually)
    'ButtonAlignBAM':   9 * 60 * 60,  # ## bwa align of FASTQ to BAM
    'ButtonBAMStats':            15,  # ## samtools idxstats (2 secs if index file there; sometimes a little longer)
    'ButtonBAMNoIndex':     35 * 60,  # ## samtools idxstats (35 min if file not indexed on 30x WGS)
    'ButtonBAMNoSort':      70 * 60,  # ## samtools idxstats (70+ min if file not sorted nor indexed on 30x WGS)
    'ButtonBAMStats2':       3 * 60,  # ## Read first 100,000 lines to get read length, etc
    'ButtonBAMStatsLong':   10 * 60,  # ## Read next 1,900,000 lines to get better read length (ONT is highly variable)
    'GenSortedBAM':         30 * 60,  # ## samtools sort
    'GenBAMIndex':          30 * 60,  # ## samtools index
    'ButtonFastp':          45 * 60,  # ## fastp on fastq
    'ButtonFastqc':         60 * 60,  # ## fastqc on fastq
    'ButtonMicroarrayDNA':   5 * 60,  # ## 1 to 12 aconv() calls; quick
    'ButtonCombinedKit':    50 * 60,  # ## Samtools mpileup, bcftools call on WGS; an hour or more for single processor
    'ButtonYHaplo':         10 * 60,  # ## yleaf haplo
    'ButtonYHaplo2':         5 * 60,  # ## yleaf lookup
    'ButtonMTHaplo':        20 * 60,  # ## haplogrep (java)
    'ButtonUnalignBAM':     75 * 60,  # ## samtools fastq on name sorted bam
    'ButtonUnmappedReads':  45 * 60,  # ## samtools view
    'ButtonMitoFASTA':       3 * 60,  # ## ButtonMitoVCF; samtools fasta
    'ButtonMitoBAM':         3 * 60,  # ## samtools view
    'ButtonMitoVCF':         3 * 60,  # ## bcftools mpileup, call
    'ButtonSNPVCF':        150 * 60,  # ## bcftools mpileup, call for SNP VCF over whole genome
    'ButtonInDelVCF':      150 * 60,  # ## bcftools mpileup, call for InDels VCF over whole genome
    'ButtonYandMT':          3 * 60,  # ## samtools view
    'ButtonYonly':           3 * 60,  # ## samtools view
    'CRAMtoBAM':            90 * 60,  # ## samtools cram to bam (1hr); samtools index (30min)
    'BAMtoCRAM':            30 * 60,  # ## samtools bam to cram (1hr); samtools index (30min)
    'CoverageStats':        45 * 60,  # ## samtools coverage to get per chromosome coverage
    'CoverageStatsWES':     60 * 60,  # ## samtools depth w/ WES BED file to get Coverage and Avg Read Depth
    'CoverageStatsPoz':     10 * 60,  # ## samtools depth w/ Poznik BED file on Y only BAM (so very quick)
    'CoverageStatsBIN':    120 * 60,  # ## samtools depth and custom awk script (ditto CoverageStatsWES)
    'CreateAlignIndices':  180 * 60,  # ## bwa index on fasta file (changed to bwtsw algorithm which is fixed at 3hrs)
    'AlignCleanup':        120 * 60,  # ## Fixmate, Sort
    'AlignCleanup2':        60 * 60,  # ## Markdup, Index
    'LiftoverCleanup':            5,  # ## Sort and Compress of CombinedKit file
    'AnnotatedVCF-yOnly':   10 * 60,  # ## Extract Y-only VCF from BAM and annotate
    'UnsortBAM':            10 * 60,  # ## samtools reheader (to change coord sorted to unknown) (DEBUG_MODE only)
    'ExtractWES':           30 * 60,  # ## samtools view with WES BED
    'GenBAMSubset':         60 * 60,  # ## samtools view -s (generate percentage subset)
    'GenLoadGenome':        20 * 60   # ## curl to NIH, EBI servers; then process for correct compression, DICT, etc
}
# Names used in calls to commandprocessor "run_bash_script"; called from modules mainwindow, bamfiles, microarray,
#     and hg38tohg19; keys also defined as keys in the langstrs i8n dictionary (languages.xlsx)
# Todo Times are adjusted relative to a BAM File Size of 60 GB.  So partial BAMs should get pared down time.

# Used in module bamfiles (specifically, calc_stats()
valid_autos = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
               "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"]
valid_somal = ["X", "Y"]
# REH 20Mar2020 split to two so can sort autosomes; valid_other added
# REH 25Feb2021 removed '*'; REH 26Feb2022 removed "M" and renamed to _somal

# Used exclusively in hg38tohg19 Liftover module (microarray); just brought here for clarity
valid_chromosomes = ["chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10",
                     "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19",
                     "chr20", "chr21", "chr22", "chrM", "chrX", "chrY"]

# Currently, we just fork off 25 jobs as if 32 processors.  Can we more smartly manage when less processors?
# This is a load balance grouping based on the max available processors **2 groups. Stopped using because drops
# Alt Contigs which are vital for calling variants.
parallelBAM = {
    32: ["chr1",  "chr2",  "chr3",  "chr4",  "chr5",  "chr6",  "chr7",  "chr8", "chr9",
         "chr10", "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19",
         "chr20", "chr21", "chr22", "chrM", "chrX", "chrY"],
    16: ["chr1", "chr2", "chr3,chr22", "chr4,chr21", "chr5,chr20", "chr6,chr19", "chr7,chr18", "chr8,chr17",
         "chr9,chr16", "chr10,chr15", "chr11,chr14", "chr12,chr13", "chrM,chrX,chrY"],
     8: ["chr1,chrM,chrX,chrY", "chr2,chr8,chr17", "chr3,chr9,chr16,chr22", "chr4,chr6,chr19,chr21",
         "chr5,chr12,chr13,chr20", "chr7,chr10,chr15,chr18", "chr11,chr14"],
     4: ["chr1,chr11,chr14,chrM,chrX,chrY", "chr2,chr7,chr8,chr10,chr15,chr17,chr18",
         "chr3,chr5,chr9,chr12,chr13,chr16,chr20,chr22", "chr4,chr6,chr19,chr21"],
     2: ["chr1,chr2,chr7,chr8,chr10,chr11,chr14,chr15,chr17,chr18,chrM,chrX,chrY",
         "chr3,chr5,chr9,chr12,chr13,chr16,chr20,chr22,chr4,chr6,chr19,chr21"],
     1: ["."]
}

# Same order as Valid Chromosomes; numbers originally from James Kane via GATK CallableLoci.
# https://docs.google.com/spreadsheets/d/1S3a69mxHeiwRb2l3s_uyFK5KGjHhL9Qv1odObJBgOdQ/view#gid=477598766
# Now from our own scan tool that generates from the reference model directly (countingNs.py).
# So refined original numbers that were different from GATK CallableLoci use by James.
# Confirmed no N's in T2T models but minor variances in major builds except 1K hs38 >> 3 mil more.
# Note: override chrM which actually has 1. Causes breadth of coverage to become 100.01%
# Todo nadjust for major AND minor class (hs38 has 12 million more N's than the others)
nadjust = {
    99: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0,
         "8": 0, "9": 0, "10": 0, "11": 0, "12": 0, "13": 0, "14": 0,
         "15": 0, "16": 0, "17": 0, "18": 0, "19": 0, "20": 0, "21": 0,
         "22": 0, "X": 0, "Y": 0, "M": 0},
    38: {"1": 18475410, "2": 1645301, "3": 195424, "4": 461888, "5": 2555066, "6": 727457, "7": 375842, "8": 370500,
         "9": 16604167, "10": 534460, "11": 552880, "12": 137493, "13": 16381203, "14": 18525617, "15": 17349864,
         "16": 8532402, "17": 337237, "18": 283680, "19": 2851219, "20": 499910, "21": 8671412, "22": 13746488,
         "X": 1147866, "Y": 33591060, "M": 0},
    37: {"1": 23970000, "2": 4994855, "3": 3225295, "4": 3492600, "5": 3220000, "6": 3720001, "7": 3785000,
         "8": 3475100, "9": 21070000, "10": 4220009, "11": 3877000, "12": 3370502, "13": 19580000, "14": 19060000,
         "15": 20836626, "16": 11470000, "17": 3400000, "18": 3420019, "19": 3320000, "20": 3520000, "21": 13023253,
         "22": 16410021, "X": 4170000, "Y": 36389037, "M": 0},
    19: {"1": 23970000, "2": 4994855, "3": 3225295, "4": 3492600, "5": 3220000, "6": 3720001, "7": 3785000,
         "8": 3475100, "9": 21070000, "10": 4220009, "11": 3877000, "12": 3370502, "13": 19580000, "14": 19060000,
         "15": 20836626, "16": 11470000, "17": 3400000, "18": 3420019, "19": 3320000, "20": 3520000, "21": 13023253,
         "22": 16410021, "X": 4170000, "Y": 36389037, "M": 0},
    36: {"1": 22250000, "2": 5241355, "3": 4797002, "4": 3976000, "5": 3155100, "6": 3626001, "7": 3869000,
         "8": 3662000, "9": 20130000, "10": 3750009, "11": 3321631, "12": 2046502, "13": 18583000, "14": 18078000,
         "15": 18997000, "16": 9942502, "17": 974522, "18": 1460998, "19": 8026000, "20": 2930711, "21": 12774217,
         "22": 14840121, "X": 3855000, "Y": 34789037, "M": 0},
    "hg38": {"1": 18475229, "2": 1645291, "3": 195420, "4": 461888, "5": 272881, "6": 727255, "7": 375841,
         "8": 370500, "9": 16604127, "10": 534287, "11": 552880, "12": 137270, "13": 16381200, "14": 16475569,
         "15": 17349841, "16": 8532401, "17": 336367, "18": 283627, "19": 176858, "20": 499586, "21": 6621300,
         "22": 11658691, "X": 1147765, "Y": 30812232, "M": 0},
}

# Stored primary sequence lengths for major builds (guaranteed identical)
# Todo change to file read in for seed; updated by ref library installs
seqlen = {
    "ids": [ 36, 37, 38, 99 ],
    "1": [ 247249719, 249250621, 248956422, 248387328 ],
    "2": [ 241251241, 241291271, 241291221, 241291252 ],
    "3": [ 191201221, 191221231, 191291251, 201201248 ],
    "4": [ 191271261, 191251271, 191211251, 191271245 ],
    "5": [ 181251261, 181211261, 181231251, 181241239 ],
    "6": [ 171291291, 171211261, 171201271, 171221228 ],
    "7": [ 151221221, 151231261, 151241271, 161261228 ],
    "8": [ 141271221, 141261221, 141231231, 141251231 ],
    "9": [ 141271251, 141211231, 131291211, 151211247 ],
    "10": [ 131271231, 131231241, 131291221, 131251234 ],
    "11": [ 131251281, 131201211, 131281221, 131221269 ],
    "12": [ 131241231, 131251291, 131271201, 131221248 ],
    "13": [ 111241281, 111261271, 111261221, 111261286 ],
    "14": [ ],
    "15": [ ],
    "16": [ ],
    "17": [ ],
    "18": [ ],
    "19": [ ],
    "20": [ ],
    "21": [ ],
    "22": [ ],
    "X": [ ],
    "Y": [ ],
    "M": [ ]
}

# Stored primary Sequence Names for major reference models (non GRCh numeric and UCSC "chr1" style); no versions
seqnam = {
    "ids": ["GRCh", "UCSC", "RefSeq", "GenBank", "T2T CHM13", "T2T HG01243"],
    "1": ["1", "chr1", "NC_000001", "CM000663", "CP068277", "CM034951"],
    "2": ["NC_000002", "CM000664", "CP068276", "CM034952"],
    "3": ["NC_000003", "CM000665", "CP068275", "CM034953"],
    "4": [],
    "5": [],
    "6": [],
    "7": [],
    "8": [],
    "9": [],
    "10": [],
    "11": [],
    "12": [],
    "13": [],
    "14": [],
    "15": [],
    "16": [],
    "17": [],
    "18": [],
    "19": [],
    "20": [],
    "21": [],
    "22": [],
    "X": [],
    "Y": [],
    "M": ["MT", "chrM", ""]
}


# Templates for sequencer ID's used in SN field of BAMs and @seqID of FASTQs; see http://bit.ly/2TfoAP2
# relying on "ordered Dict" (Python 3.7 and later). HWI- prefix appears to be for Solexa Genome Analyzer series
# Order similar entries from more specific to more general.
valid_markdup = ("Illumina", "Solexa", "MGI DNB")
sequencers = {      # Wanted re.compile for the raw strings but import re not possible as this file is globally imported
    # SeqID key :    [RegEx for seqID in FASTQ or QNAME in BAM , RegEx for fields in markdup, order for markdup]
    'Illumina NS 6000 (Dante)':  [r"^(A00910|A00925|A00966|A01245):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    #    Serial #'s 910, 925 and 966 from Jul 2020- ; added 1245 in Fall 2022
    'Illumina NS 6000 (FTDNA)':  [r"^(A00186):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina NS 6000 (GeneDX)': [r"^(A00571):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina NS 6000 (Illum)':  [r"^(A00582):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina Novaseq 6000':     [r"^(M_)?(A\d{5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina Novaseq X':        [r"^(LH\d{5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina NextSeq 500/550':  [r"^(N[BS]\d{6}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina NextSeq 2000':     [r"^(V\d{5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Solexa GAI (HiSeq 1000)':   [r"^(HWI-C\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina HiSeq 1000':       [r"^(C\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Solexa GAII (HiSeq 2000)':  [r"^(HWI-ST\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Solexa GAII (HiSeq 2500)':  [r"^(HWI-D\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina HiSeq 2500':       [r"^(D\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Solexa GAIIx (HiSeq 3000)': [r"^(HWI-J\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina HiSeq 3000':       [r"^(J\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina HiSeq 4000':       [r"^(K\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Solexa GAxx? (FTDNA)':      [r"^(SN\d{6,8}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]:[0-9]+):([0-9]+):([0-9]+)", "txy"],
    'Illumina HiSeq X':          [r"^(ST[-_])?(E\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina MiniSeq':          [r"^(MN\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Solexa GA (MiSeq)':         [r"^(HWI-M\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'Illumina MiSeq':            [r"^(M\d{3,5}):(\d+):([a-zA-Z0-9]{9}):(\d):(\d+):(\d+):(\d+)$",
                                  r":([0-9]+:[a-zA-Z0-9]{9}:[0-9]):[0-9]+:([0-9]+):([0-9]+)", "txy"],
    'MGI DNB T7 (ProPhase)':     [r"^(PRO\d{7})(_[A-Za-z0-9_]{25,29}_)(E100\d{6})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T7 (ProPhase-bug)': [r"^(<NEBULA_ID>)(_[A-Za-z0-9_]{25,29}_)(E100\d{6})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T7 (ProPhase 2)':   [r"^(N[A-Z0-9]{9}_[0-9_]{17}_ProPhase_BP_)(E\d{9})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T7 (Dante, 6xxx)':  [r"^(E200006\d{3})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T7 v1':             [r"^(E1\d{8})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T7 v2x':            [r"^(E2\d{8})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"E([0-9]{9}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T10 (ProPhase)':    [r"^(PRO\d{7})(_[A-Za-z0-9_]{25,29}_)(FP200\d{6})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"FP2([0-9]{8}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    # PRO0001117_2022_10_07_688579_ProPhase_BP_FP200006640L1C041R06000486480
    'MGI DNB T10 (ProPhase-bug)': [r"^(<NEBULA_ID>)(_[A-Za-z0-9_]{25,29}_)(FP200\d{6})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                   r"FP2([0-9]{8}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    # <NEBULA_ID>_2022_12_10_688579_ProPhase_BP_FP200006640L1C041R06000486480
    'MGI DNB T10 (ProPhase 2)':  [r"^(N[A-Z0-9]{9}_[0-9_]{17}_ProPhase_BP_)(FP2\d{8})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"FP2([0-9]{8}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    # NG1MU9RJA2_2023_04_06_093100_ProPhase_BP_FP200009330L1C086R02600469793   (?:/[12])?
    'MGI DNB T10 v1':            [r"^(FP20\d{7})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"FP2([0-9]{8}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB T10 v2.7':          [r"^(FP27\d{7})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"FP2([0-9]{8}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB G400':              [r"^(V3[05]0\d{6})(L\d)(C\d{3})(R\d{3})(\d{6,8})([/1]?|[/2]?)$",
                                  r"V3[05]0([0-9]{6}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    'MGI DNB G400 FAST':         [r"^([CV]L?100\d{6})(L\d)(C\d{3})(R\d{3})_?(\d{6,8})([/1]?|[/2]?)$",
                                  r"[CV]L?100([0-9]{6}L[0-9])C([0-9]{3})R([0-9]{3})", "txy"],
    "MGI DNB G400 (YSEQ)":       [r"^(YSEQ1):(\d+):([A-Z0-9]{10,12}):(\d):(\d{5,7}):(\d{3}):(\d{3})$",
                                  r"YSEQ1:[0-9]+:([A-Z0-9]{10,12}:[0-9]):[0-9]{6}:([0-9]{3}):([0-9]{3})", "txy"],
    'PacBio HiFi Revio':         [r"^(m\d{5}e?)_(\d{6})_(\d{6})(_s\d+)?/(\d{9})/ccs", r"", ""],  # Early R&D models missing s_n
    'Oxford Nanopore':           [r"^([0-9a-f]{8})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{12})$", r"", ""],
    'Unknown':                   [r"^[\S]+$", r"", ""]
}


''' Variables contain File Name Path, Base, and Suffix (FPBS) naming conventions explained at the end of this file. '''
# --------------------------------------------------------------------------------------------------------------------
# Program global variables
#

# Variables initially set here but used globally in the WGSE system. Accessed via wgse.<varname> after doing
#  import settings as wgse

DEBUG_MODE    = None  # Global DEBUG mode setting (similar to __debug__ removed by python -O)
wsl_bwa_patch = None  # To bypass Win10 BWA which is single processorlanguage
prefserver    = None  # Special as saved in settings with many of the above
gui           = None  # To determine if interactive or not; wgse.window if gui

# Class object instantiation points
outdir = None  # Output Directory subsystem
reflib = None  # Reference Library subsystem
tempf  = None  # TemporaryFile subsystem (user override of default location possible)
lang   = None  # Internationalization Language subsystem (fixed location)
window = None  # main Tk() window (fixed once created unless language change asked)
BAM    = None  # main BAM Class instance with all its stats, attributes, etc
fonts  = None  # Main Class instance for font faces and sizes used in UI

style = None   # Placeholder for ttk frame style set later

# OS / HW Platform specific variables
os_plat     = None   # type: [str]  # OS Platform; to avoid multiple calls to system.platform
os_arch     = None   # type: [str]  # OS CPU architecture (x86_64 / AMD64, arm64 for Apple M1)
os_slash    = None   # type: [str]  # OS Platform file path slash (forward or backward)
os_batch_FS = None   # type: [str]  # OS Platform batch file suffix (.bat or .sh)
os_threads  = 1                     # OS Platform # of virtual processors; will set later but default is 1 until set
os_totmem   = 2*10**9               # OS Platform Total available memory for large job use (less 5%)
os_mem      = "500M" # type: [str]  # OS Platform amount of memory per thread available (overriden later) (string)
os_pid      = 0                     # OS Process ID of this run; just set to 1000 till read to get the type

os_threads_proc = 0                 # To store platform reported settings (with minor corrections)
os_totmem_proc = 0                  # To store platform reported settings (with minor corrections) (in GB)
os_threads_saved = 0                # User desired override of platform threads
os_totmem_saved  = 0                # User desired override of platform total memory (in GB)

# from Typing import Optional
# Users home area (determined from OS) and setting files we will look for and manipulate there
User_oFP     = None  # Users home area directory path (~, users/name)
debugset_oFN = None  # type: [str]  # File name for DEBUG mode toggle
wgseset_oFN  = None  # type: [str]  # File name for global settings
wslbwa_oFN   = None  # type: [str]  # File name for WSL BWA Patch toggle

# Key paths all determined from where this settings file is located.
install_FP   = None  # type: [str]  # Installation path for WGS Extract; program/ below is where this file is
install_oFP  = None  # type: [str]  # Installation path for WGS Extract; program/ below is where this file is
prog_oFP     = None  # type: [str]  # File path of this Python file (location of WGS Extract program)
prog_FP      = None  # type: [str]  # File path of this Python file (location of WGS Extract program)
language_oFN = None  # type: [str]  # File path and name of Internationalization language settings
image_oFP    = None  # type: [str]  # Icon image in program header file pointer
dnaImage     = None  #              # Placeholder for banner image (used in MainWindow; needs global variable)
icon_oFP     = None  # type: [str]  # For Windows Icon image file pointer

# Key external program path, names and suffixes (OS dependent)
python3_FP     = None   # type: [str]  # Installation path to Python3 installation
python3x_qFN   = None   # type: [str]  # Actual file name w/ path of Python3 executable
python_version = [0, 0, 0]  # Python major / minor version

yleaf_FP       = None   # type: [str]  # Installation path for our version of yLeaf

java8x_FN      = None   # type: [str]  # Java 8 runtime path executable file name
java8args      = None   # type: [str]  # "-Xmx2g --module-path=xxxx -jar"
java8x_FNp     = None   # type: [str]  # Java 8 runtime executable with standard parameters (javaargs)
java8_version  = [0, 0, 0]             # Java 8 runtime version major / minor

java17x_FN     = None   # type: [str]  # Java 11+ runtime path executable file name
java17args     = None   # type: [str]  # "-Xmx2g --module-path=xxxx -jar"
java17x_FNp    = None   # type: [str]  # Java 11+ runtime executable with standard parameters (javaargs)
java17_version = [0, 0, 0]             # Java 11+ runtime version major / minor

jartools_FP   = None    # type: [str]  # Installation path for jars
haplogrepx_FN = None    # type: [str]  # Haplogrep command (Java Jar file)
picardx_FN    = None    # type: [str]  # Broad Institute Picard (part of GATK3)
gatk3x_FN     = None    # type: [str]  # Broad Institute GATK3
gatk4x_FN     = None    # type: [str]  # Broad Institute GATK4 (maybe setup subfolder for release)
igvx_FN       = None    # type: [str]  # IGV Genomics Viewer (maybe setup subfolder for release)
varqcx_FN     = None    # type: [str]  # VarientQC command (Java Jar file)

bashx_oFN     = None    # type: [str]  # Bash shell (needed in Windows and MacOS to run a specific shell)
headx_qFN     = None    # type: [str]  # Unix head command
tailx_qFN     = None    # type: [str]  # Unix tail command
awkx_qFN      = None    # type: [str]  # Unix awk command
grepx_qFN     = None    # type: [str]  # Unix grep command
sortx_qFN     = None    # type: [str]  # Unix sort command
catx_qFN      = None    # type: [str]  # Unix cat/type command
zcatx_qFN     = None    # type: [str]  # Unix zcat command (for compressed archives)
wcx_qFN       = None    # type: [str]  # Unix wc (word count) command; used wc -l for quick line count)
sedx_qFN      = None    # type: [str]  # Unix sed command
zipx_qFN      = None    # type: [str]  # Unix zip command
unzipx_qFN    = None    # type: [str]  # Unix unzip command
mv_qFN        = None    # type: [str]  # Unix mv (move) command

samtools_oFP  = None    # type: [str]  # Installation path to HTSLib Bioinformatic tools (samtools, bcftools, etc)
samtools_FP   = None    # type: [str]  # Installation path to HTSLib Bioinformatic tools (samtools, bcftools, etc)
samtoolsx_qFN = None    # type: [str]  # HTSlib samtools bioinformatics command (WGSE v3, samtools 1.10+)
bcftoolsx_qFN = None    # type: [str]  # HTSLib bcftools bioinformatics command
tabixx_qFN    = None    # type: [str]  # HTSLib tabix bioinformatics command
bgzipx_qFN    = None    # type: [str]  # HTSlib bgzip bioinformatics command
bwax_qFN      = None    # type: [str]  # BWA MEM Alignment command
bwamem2x_qFN  = None    # type: [str]  # BWA MEM v2 Alignment command
minimap2x_qFN = None    # type: [str]  # Minimap2 aligner (for Nanopore long read)
fastqcx_qFN   = None    # type: [str]  # Fastqc analysis tool
fastpx_qFN    = None    # type: [str]  # Fastp analysis tool

samtools_version = [0, 0, 0]   # samtools major / minor version
cp_version = [0, 0, 0]         # return value of command_processor.is_command_available() (simpler as global)

defbut_bg     = None    # type: [str]  # Default button background color for this run (can change if OS in darkmode)

# Todo make table of all external execs needed (i.e. a registry) with name, status if available, version, etc.
#   fill table at start; then check JIT when needed for availability (no error till needed).  That way,
#   can simply return with NOOP if necessary programs are not available.  Make sure to account for PIP/PythonLib
#   and Java Jar availability also; not just executables?  Confirm actually used in scripts here (or likely needed)
#   AND in the install environment

# -----------------------------------------------------------------------------------------------------------------
# Program global routine(s)
#


def init(interactive=False):
    """
    Main routine, like a Class init, to initialize all the global variables. We do local imports here as this
    module / file is imported everywhere and there are conflicts otherwise.
    """
    import os  # os.path, etc
    import psutil    # cpu_count, virtual_memory().available
    import locale    # For setting locale for number format (thousands separator, etc)
    import platform  # platform.system
    # import multiprocessing

    # Local imports as this module / file is imported everywhere else; no .h/.c separation like in C
    from utilities import DEBUG, universalOS, unquote  # , wgse_message
    from utilities import TemporaryFiles, LanguageStrings, OutputDirectory, FontTypes       # subsystem classes
    from commandprocessor import is_command_available, simple_command
    from referencelibrary import ReferenceLibrary           # subsystem class
    from mainwindow import mainwindow_init

    # Globals we want to access from in here
    global DEBUG_MODE, wsl_bwa_patch, prefserver, gui           # Some universal settings
    global tempf, lang, outdir, reflib, window, BAM, fonts      # Some universal class imstamces
    global os_plat, os_arch, os_threads, os_totmem, os_mem, os_pid, os_threads_proc, os_totmem_proc
    global os_slash, os_batch_FS
    global User_oFP, debugset_oFN, wgseset_oFN, wslbwa_oFN  # , langset_oFN
    global prog_oFP, prog_FP, language_oFN, image_oFP, dnaImage, icon_oFP
    global install_FP, install_oFP
    global python3_FP, python3x_qFN, yleaf_FP
    global java8x_FN, java8args, java8x_FNp, java17x_FN, java17args, java17x_FNp
    global jartools_FP, haplogrepx_FN, picardx_FN, gatk3x_FN, gatk4x_FN, igvx_FN, varqcx_FN
    global bashx_oFN, headx_qFN, tailx_qFN, awkx_qFN, grepx_qFN, sortx_qFN
    global catx_qFN, zcatx_qFN, wcx_qFN, sedx_qFN, zipx_qFN, unzipx_qFN, mv_qFN
    global samtools_oFP, samtools_FP, samtoolsx_qFN, bcftoolsx_qFN, tabixx_qFN, bgzipx_qFN, bwax_qFN, bwamem2x_qFN
    global minimap2x_qFN, fastqcx_qFN, fastpx_qFN
    global java8_version, java17_version, python_version, samtools_version, cp_version

    gui = interactive

    #
    # OS / current host platform Specific values
    #
    plat = platform.uname()     # Collection of values: system OS type, OS version, machine type, possibly processor
    os_plat = plat.system       # Windows, Darwin, Linux, ...
    os_arch = plat.machine      # arm64, x86_64, AMD64, etc
    os_slash, os_batch_FS = ('\\', '.bat') if os_plat == "Windows" else ('/', '.sh')
    os_pid = os.getpid()        # Will use to create a unique area in the Temp directory for our run

    os_threads = psutil.cpu_count()  # For parallelizing commands that can use multiple processors

    if os_plat == "Darwin" and os_arch == 'arm64':
        # cpu_count always returns total cores. But Apple M* has Performance and Efficiency cores. Do not want to
        #  parallize onto Efficiency cores. (Samtools sends OS into thrashing mode on Efficiency cores)
        perfcpus = simple_command(['sysctl', '-n', 'hw.perflevel0.logicalcpu'])
        if perfcpus and perfcpus.isdigit() and int(perfcpus) < os_threads:
            os_threads = int(perfcpus)

    os_threads_proc = os_threads

    os_totmem = int(0.95 * psutil.virtual_memory().available)

    os_totmem_proc = os_totmem

    set_mem_per_thread_millions(os_totmem, os_threads)      # Sets global os_mem internal to call

    # Todo gather and update free disk space on temp and outputdir; do not start command if not enough left
    #  See https://psutil.readthedocs.io/en/latest/ for additional info (e.g. psutil.disk_usage(path)['free'])

    #
    # Stored settings set per user / run
    #

    # Users home directory for settings (Unix hidden style with dot (.))
    User_oFP = os.path.expanduser("~")
    if User_oFP[-1] != os_slash:                # In case returns as root (/) or (C:\\)
        User_oFP += os_slash                    # Assure trailing os_slash
    debugset_oFN  = f'{User_oFP}.wgsedebug'     # No content; just existence of file turns on debugging
    wslbwaset_oFN = f'{User_oFP}.wgsewslbwa'    # No content; just existence turns on WSL BWA patch on Win10 systems
    wgseset_oFN   = f'{User_oFP}.wgsextract'    # General settings save / restore

    # Start global debug messages if requested (utilities.py); start after TemporaryFiles so it can clean directory
    if os.path.exists(debugset_oFN) and os.path.isfile(debugset_oFN):
        DEBUG_MODE = True
        DEBUG("***** Debug Mode Turned On *****") if gui else ''

    # Special for Win10 patch to use WSL BWA as CygWIn64 is not running multiproc
    if os.path.exists(wslbwaset_oFN) and os.path.isfile(wslbwaset_oFN):
        wsl_bwa_patch = True
        DEBUG("***** WSL BWA Patch Mode Turned On *****") if gui else ''

    # Need to set default locale; for decimal number (:n) formatting;
    #   override to POSIX when needed for consistent sort order (BAM header signature)
    # On Unix-based systems, sets language in OS messagebox dialogs also (Win10 does not allow altering)
    DEBUG(f'Locale: {locale.getlocale()[0]}')
    DEBUG(f'Default Locale: {locale.getdefaultlocale()[0]}')
    locale.setlocale(locale.LC_ALL, '')

    # Did not have DEBUG available before when set
    DEBUG(f'OS: {os_plat}, CPU: {os_arch}, PID: {os_pid}, (Perf) Threads: {os_threads}, '
          f'Total Mem: {(os_totmem/10**9):.1f} GB, Mem per thread: {os_mem}')

    #
    # Global, hardwired locations of key files, areas based on where this file is located
    #

    # Setup all the needed paths and filenames; based mostly on where this program (Python script) resides
    prog_oFP = os.path.dirname(os.path.abspath(__file__))       # Where does this Python program reside?
    # Todo should call is_legal_path() here at first use; but language system not setup yet to report error
    if prog_oFP[-1] != os_slash[0]:  # In case returns as root (/) or (C:\\); never should as buried in installation ...
        prog_oFP += os_slash  # Assure trailing os_slash
    prog_FP = universalOS(prog_oFP)

    # Some key static files we need to read in and use
    image_oFP = f"{prog_oFP}img{os_slash}dna.png"
    icon_oFP  = f"{prog_oFP}img{os_slash}favicon.ico"
    language_oFN = f'{prog_oFP}language.xlsx'  # Moved from subdir of files in v2 to single file here; .txt to .csv

    # aconv_FN = f'{prog_FP}aconv.py'                   # Static inside microarray.py
    # hg39tohg19 = f'{prog_fp}hg38tohg19.py'            # Static inside microarray.py

    # Find program installation by assuming this file is in a program/ folder below the installation root
    install_FP  = prog_FP.split('program')[0]  # Has trailing os_slash
    install_oFP = prog_oFP.split('program')[0]

    tempfiles_FN = f'{install_FP}temp/'        # Default installation location
    reflib_FN = f'{install_FP}reference/'      # Default installation location
    # Microarray templates now in reflib and set after initializing reference library; in case was moved in settings

    load_program_version()  # Create program version string and get user manual URL from json files (needs install_oFP)
    DEBUG(f'WGS Extract: {__version__}')

    prefserver = "NIH"      # Default value; otherwise "EBI"

    #
    # Setup bioinformatic, OS and other tools we need to access too
    #
    yleaf_FP       = f'{install_FP}yleaf/'
    jartools_FP    = f'{install_FP}jartools/'

    # Check for a preinstalled, default Java first; before checking platform specific versions
    java8x_FN = java17x_FN = None
    if is_command_available("java", "--version", True) or is_command_available("java", "-version", True):
        # Java 8 uses single dash version spec; Java 11+ also uses double dash and different format
        # So try --version first and then fall back to -version. Simplifies lookup pattern match
        if cp_version[0] == 1 and cp_version[1] == 8:      # Java version 8
            java8x_FN = "java"       # Most installations, if installed, on the call path and so just mentioned
            java8_version = cp_version
        elif cp_version[0] >= 11:                           # Java version 11+
            java17x_FN = "java"       # Most installations, if installed, on the call path and so just mentioned
            java17_version = cp_version
        # Else we ignore the preinstalled version as not being one of the two we need
        DEBUG(f'Java preinstalled Version: {java17_version}{java8_version}')    # Only one if any will be set

    # Distinguish Windows bioinformatic tool support via existence of our install folders
    os_wintype = "cygwin64" if os.path.exists(f'{install_oFP}cygwin64') else \
                 "msys2"    if os.path.exists(f'{install_oFP}msys2'   ) else \
                 "unknown"

    # Set all the OS platform specific path / program names; see file variable naming spec at end; 'x' is executable
    if os_plat == "Windows" and os_wintype == "cygwin64":
        python3_FP   = f'{install_FP}python/'
        python3x_qFN = f'"{python3_FP}python.exe"'

        cygwin64_oFP = f'{install_oFP}cygwin64\\bin\\'
        cygwin64_FP  = f'{install_FP}cygwin64/bin/'
        samtools_oFP = f'{install_oFP}cygwin64\\usr\\local\\bin\\'
        samtools_FP  = f'{install_FP}cygwin64/usr/local/bin/'

        bashx_oFN  = f'{cygwin64_oFP}sh.exe'         # sh.exe is bash in cygwin and works while bash.exe fails
        # Ensure cygwin64/bin is in PATH for DLL resolution
        if cygwin64_oFP not in os.environ["PATH"]:
            os.environ["PATH"] = f'{cygwin64_oFP};{os.environ["PATH"]}'
        headx_qFN  = f'"{cygwin64_FP}head.exe"'
        tailx_qFN  = f'"{cygwin64_FP}tail.exe"'
        awkx_qFN   = f'"{cygwin64_FP}gawk.exe"'
        grepx_qFN  = f'"{cygwin64_FP}grep.exe"'
        sortx_qFN  = f'"{cygwin64_FP}sort.exe"'      # Only in hg39tohg19 liftover module
        catx_qFN   = f'"{cygwin64_FP}cat.exe"'       # Only in hg39tohg19 liftover module
        zcatx_qFN  = f'"{cygwin64_FP}zcat.exe"'
        wcx_qFN    = f'"{cygwin64_FP}wc.exe"'
        sedx_qFN   = f'"{cygwin64_FP}sed.exe"'       # Only in microarray
        zipx_qFN   = f'"{cygwin64_FP}zip.exe"'       # Only in microarray
        unzipx_qFN = f'"{cygwin64_FP}unzip.exe"'     # Only in microarray
        mv_qFN     = f'"{cygwin64_FP}mv.exe"'

        samtoolsx_qFN = f'"{samtools_FP}samtools.exe"'
        bcftoolsx_qFN = f'"{samtools_FP}bcftools.exe"'
        tabixx_qFN    = f'"{samtools_FP}tabix.exe"'
        bgzipx_qFN    = f'"{samtools_FP}bgzip.exe"'  # Only in export_unmapped_reads
        bwax_qFN      = f'"{samtools_FP}bwa.exe"'
        bwamem2x_qFN  = f'"{samtools_FP}bwamem2.exe"'
        minimap2x_qFN = f'"{samtools_FP}minimap2.exe"'
        fastpx_qFN    = f'"{samtools_FP}fastp.exe"'
        fastqcx_qFN   = f'"{install_FP}FastQC/FastQC.jar"'

        jre8 = f'{install_FP}jre8/bin/java'     # If Win10 installer had to install, then local to WGSE
        if not java8x_FN and is_command_available(jre8, "-version", True):
            java8x_FN = jre8
            java8_version = cp_version

        jre17 = f'{install_FP}jre17/bin/java'   # If Win10 installer had to install, then local to WGSE
        if not java17x_FN and is_command_available(jre17, "--version", True):
            java17x_FN = jre17
            java17_version = cp_version

    elif os_plat == "Windows" and os_wintype == "msys2":
        python3_FP   = f'{install_FP}/msys2/ucrt64/bin/'
        python3x_qFN = f'"{python3_FP}python.exe"'

        msys2_oFP    = f'{install_oFP}msys2\\usr\\bin\\'
        msys2_FP     = f'{install_FP}msys2/usr/bin/'
        samtools_oFP = f'{install_oFP}msys2\\ucrt64\\bin\\'
        samtools_FP  = f'{install_FP}msys2/ucrt64/bin/'

        # Might need the cygwin fix here for dev_launch.py , not tested yet
        bashx_oFN  = f'{msys2_oFP}bash.exe'    # Exception, native-OS and no quote
        headx_qFN  = f'"{msys2_FP}head.exe"'
        tailx_qFN  = f'"{msys2_FP}tail.exe"'
        awkx_qFN   = f'"{msys2_FP}gawk.exe"'
        grepx_qFN  = f'"{msys2_FP}grep.exe"'
        sortx_qFN  = f'"{msys2_FP}sort.exe"'   # Only in hg39tohg19 liftover module
        catx_qFN   = f'"{msys2_FP}cat.exe"'    # Only in hg39tohg19 liftover module
        zcatx_qFN  = f'"{msys2_FP}zcat.exe"'
        wcx_qFN    = f'"{msys2_FP}wc.exe"'
        sedx_qFN   = f'"{msys2_FP}sed.exe"'    # Only in microarray
        zipx_qFN   = f'"{msys2_FP}zip.exe"'    # Only in microarray
        unzipx_qFN = f'"{msys2_FP}unzip.exe"'  # Only in microarray
        mv_qFN     = f'"{msys2_FP}mv.exe"'

        samtoolsx_qFN = f'"{samtools_FP}samtools.exe"'
        bcftoolsx_qFN = f'"{samtools_FP}bcftools.exe"'
        tabixx_qFN    = f'"{samtools_FP}tabix.exe"'
        bgzipx_qFN    = f'"{samtools_FP}bgzip.exe"'  # Only in export_unmapped_reads
        bwax_qFN      = f'"{samtools_FP}bwa.exe"'
        bwamem2x_qFN  = f'"{samtools_FP}bwamem2.exe"'
        minimap2x_qFN = f'"{samtools_FP}minimap2.exe"'
        fastpx_qFN    = f'"{samtools_FP}fastp.exe"'
        fastqcx_qFN   = f'"{install_FP}FastQC/FastQC.jar"'

        jre8 = f'{install_FP}jre8/bin/java'     # If Win10 installer had to install, then local to WGSE
        if not java8x_FN and is_command_available(jre8, "-version", True):
            java8x_FN = jre8
            java8_version = cp_version

        jre17 = f'{install_FP}jre17/bin/java'   # If Win10 installer had to install, then local to WGSE
        if not java17x_FN and is_command_available(jre17, "--version", True):
            java17x_FN = jre17
            java17_version = cp_version

    elif os_plat == "Windows":
        DEBUG(f'*** ERROR: Cannot determine windows install type (cygwin64 nor msys2)')
        exit()

    elif os_plat == "Darwin":  # Apple MacOS
        new_homebrew_root = '/opt/homebrew'
        homebrew_root = new_homebrew_root if os.path.exists(new_homebrew_root) else '/usr/local/Homebrew'
        macports_root = "/opt/local/bin"
        custom_python_root = "/usr/local/bin"
        has_macports = os.path.exists(macports_root)
        has_custom_python = os.path.exists(custom_python_root)

        bash_samtools_root = macports_root if has_macports else homebrew_root
        python_root = custom_python_root if has_custom_python else homebrew_root
        python_executable = "python3" if has_custom_python else "python3.11"

        python3_FP    = f'{python_root}/bin/'
        python3x_qFN  = f'"{python3_FP}{python_executable}"'

        samtools_oFP  = f'{bash_samtools_root}/bin/'
        samtools_FP   = f'{bash_samtools_root}/bin/'

        bashx_oFN  = f'{bash_samtools_root}/bin/bash'       # default MacOS Bash is v3 and too old
        headx_qFN  = '"/usr/bin/head"'
        tailx_qFN  = '"/usr/bin/tail"'
        awkx_qFN   = '"/usr/bin/awk"'
        grepx_qFN  = '"/usr/bin/grep"'
        sortx_qFN  = '"/usr/bin/sort"'
        catx_qFN   = '"/bin/cat"'
        zcatx_qFN  = '"/bin/zcat"'
        wcx_qFN    = '"/bin/wc"'
        sedx_qFN   = '"sed"'
        zipx_qFN   = '"zip"'
        unzipx_qFN = '"unzip"'
        mv_qFN     = '"mv"'

        samtoolsx_qFN = f'"{samtools_FP}samtools"'
        bcftoolsx_qFN = f'"{samtools_FP}bcftools"'
        tabixx_qFN    = f'"{samtools_FP}tabix"'
        bgzipx_qFN    = f'"{samtools_FP}bgzip"'  # Only used in export_unmapped_reads at the current time
        bwax_qFN      = f'"{samtools_FP}bwa"'
        bwamem2x_qFN  = f'"{samtools_FP}bwamem2"'
        # minimap2x_qFN  = f'"{samtools_FP}minimap2"'
        # fastpx_qFN   = f'"{samtools_FP}fastp"'         # Make sure to enable in fastp button as well
        fastqcx_qFN   = f'"{install_FP}FastQC/FastQC.jar"'

        jre8 = f'/Library/Java/JavaVirtualMachines/zulu-8.jre/Contents/Home/bin/java'
        if not java8x_FN and is_command_available(jre8, "-version", True):
            java8x_FN = jre8
            java8_version = cp_version

        if not java17x_FN:
            import glob
            jvms = glob.glob(f'/Library/Java/JavaVirtualMachines/zulu-[12]?.jre/Contents/Home')
            if len(jvms) > 0:
                jre17 = f'{jvms[0]}/bin/java'
                if is_command_available(jre17, "--version", True):
                    java17x_FN = jre17
                    java17_version = cp_version

    else:  # All others (Unix, Linux) are simply found in path; quotes not needed but keep for consistency
        python3_FP    = ''
        python3x_qFN  = '"python3"'

        samtools_oFP  = ''
        samtools_FP   = ''

        bashx_oFN  = '/bin/bash'
        headx_qFN  = '"head"'
        tailx_qFN  = '"tail"'
        awkx_qFN   = '"awk"'
        grepx_qFN  = '"grep"'
        sortx_qFN  = '"sort"'
        catx_qFN   = '"cat"'
        zcatx_qFN  = '"zcat"'
        wcx_qFN    = '"wc"'
        sedx_qFN   = '"sed"'
        zipx_qFN   = '"zip"'
        unzipx_qFN = '"unzip"'
        mv_qFN     = '"mv"'

        samtoolsx_qFN = '"samtools"'
        bcftoolsx_qFN = '"bcftools"'
        tabixx_qFN    = '"tabix"'
        bgzipx_qFN    = '"bgzip"'
        bwax_qFN      = '"bwa"'
        bwamem2x_qFN  = '"bwamem2"'
        minimap2x_qFN = '"minimap2"'
        fastpx_qFN    = '"fastp"'
        fastqcx_qFN   = f'"{install_FP}FastQC/FastQC.jar"'

        jre8 = f'/usr/lib/jvm/java-8-openjdk-amd64/bin/java'
        if not java8x_FN and is_command_available(jre8, "-version", True):
            java8x_FN = jre8
            java8_version = cp_version

        if not java17x_FN:
            import glob
            jvms = glob.glob(f'/usr/lib/jvm/java-[12]?-openjdk-amd64')
            if len(jvms) > 0:
                jre17 = f'{jvms[0]}/bin/java'
                if is_command_available(jre17, "--version", True):
                    java17x_FN = jre17
                    java17_version = cp_version

    if is_command_available(unquote(python3x_qFN), "--version", True):
        python_version = cp_version
        DEBUG(f'Python Version: {python_version}')

    if is_command_available(unquote(samtoolsx_qFN), "--version", True):
        samtools_version = cp_version
        DEBUG(f'Samtools Version: {samtools_version}')

    if java8x_FN:
        # java8args = f'-Xmx2g --module-path={jartools_FP} -jar'
        java8args = f'-Xmx1500m -jar'        # Not sophisticated enough yet to have modules in jartools
        java8x_FNp = f'{java8x_FN} {java8args}'
        DEBUG(f'Java 8 version: {java8_version}')
    else:
        DEBUG(f'*** ERROR: No Java 8 installation found')

    if java17x_FN:
        # java17args = f'-Xmx2g --module-path={jartools_FP} -jar'
        java17args = f'-Xmx1500m -jar'        # Not sophisticated enough yet to have modules in jartools
        java17x_FNp = f'{java17x_FN} {java17args}'
        DEBUG(f'Java 11+ version: {java17_version}')
    else:
        DEBUG(f'*** ERROR: No Java 11+ installation found')

    #
    # Start up key subsystems:  Language Translation, Temporary Files directory, Reference Library directory
    #

    # window not null says mainwindow_init has been run, dnaImage not null says mainwindow_setup has been run
    if gui:   # When not called by independent programs without GUI; setup now in case language not in settings
        window = mainwindow_init()      # pseudo class __init__ call; creates root window and Fonts subsystem
        fonts = FontTypes()    # Only needed with GUI active

    # Start i18n Language subsystem (utilities.py)  (start first so warnings / error messages can be translated)
    lang = LanguageStrings(language_oFN)  # Start language subsystem (utilities.py)
    # lang.read_language_setting(langset_oFN)  # Try stored lang setting; otherwise ask user if missing / error

    # Start Temporary Files subsystem (utilities.py) with default location
    tempf = TemporaryFiles(tempfiles_FN, gui)  # Initiate TemporaryFiles @ default, do clean of directory

    # Start Reference Library subsystem (referencelibrary.py) with default location
    reflib = ReferenceLibrary(reflib_FN)  # Initiate ReferenceLibrary @ default location

    # Start Output Directory subsystem (utilities.py) with none (no default).
    outdir = OutputDirectory()      # No default value

    BAM = None        # No default BAMFile instance; keep unset until a BAM is loaded by user or from settings restore

    load_settings(gui)    # Grab saved setting from users home directory; finish subsystem setup

    # Special check; if default reflib does not exist AND no stored setting of reflib then fail as no reflib available
    # if not (reflib and reflib.valid):
    #    wgse_message("error", 'InvalidRefLibTitle', True,
    #                 lang.i18n['errRefLibPath'].replace("{{DIR}}", reflib.oFP))


def set_mem_per_thread_millions(totmem, threads):
    """ Mainly for samtools sort; per thread. Here as we allow saved setting override of threads and totmem """
    global os_mem       # Global settings value we will set here

    mpt = totmem // threads

    # Get a nice floor (round down) per 100+ million bytes if over 100 million; hopefully over 1GB
    mpt_mills = (mpt // 10 ** 8) * 100 if mpt > 10 ** 8 else (mpt // 10 ** 6)

    os_mem = str(mpt_mills) + 'M'   # Set global value (as string) to use in commands later

    return mpt_mills    # Return numeric value of os_mem in millions


def load_program_version():
    """
    Read the program/version.json file purely to setup the __version__ string for the program
    """
    import os
    import json
    from utilities import DEBUG

    global __version__, manual_url

    # Fallback defaults
    rel_type = "Unk"
    wgse_version = 0
    wgse_date = "1 Jan 1970"
    manual_url = "https://wgsextract.github.io/"

    release_json = {}
    if os.path.exists(f'{install_oFP}/release.json'):
        try:
            with open(f'{install_oFP}/release.json', "r") as f:
                release_json = json.load(f).get('release')
            DEBUG(f'Installer.json: {release_json}')
        except OSError:  # Exception here if file processing error on existing file
            DEBUG(f'*** Error processing Program.json file')
            return
        finally:
            rel_type = release_json.get('track', rel_type)

    program_json = {}
    if os.path.exists(f'{prog_oFP}/program.json'):
        try:
            with open(f'{prog_oFP}/program.json', "r") as f:
                program_json = json.load(f).get('program')
            DEBUG(f'Program version.json: {program_json}')
        except OSError:  # Exception here if file processing error on existing file
            DEBUG(f'*** Error processing Program.json file')
            return
        finally:
            wgse_version = program_json.get('version', wgse_version)
            wgse_date    = program_json.get('date', wgse_date)
            manual_url   = program_json.get('manual', manual_url)

    if rel_type == "Dev":
        __version__ = f'{rel_type} 4.{wgse_version} ({wgse_date})'      # two v's in a row looks weird
    else:
        __version__ = f'{rel_type} v4.{wgse_version} ({wgse_date})'


# noinspection PyUnresolvedReferences
def load_settings(gui=False):
    """
    To read / load saved settings on program startup. For now, just a select few values restored.
    """
    import os
    import json
    from utilities import DEBUG, wgse_message, nativeOS
    from bamfiles import BAMFile, BAMContentError, BAMContentErrorFile, BAMContentWarning
    from mainwindow import update_action_buttons

    global outdir, reflib, tempf, lang, BAM, fonts
    global wgseset_oFN, prefserver, os_threads, os_totmem, os_threads_saved, os_totmem_saved, os_mem

    settings_to_restore = {}
    if os.path.exists(wgseset_oFN):
        try:
            with open(wgseset_oFN, "r") as f:
                settings_to_restore = json.load(f)
        except OSError:  # Exception here if file processing error on existing file; so delete
            DEBUG(f'*** Error processing settings file; deleting')
            os.remove(wgseset_oFN)
            return

    # Restore value IF stored in file and class subsystem setup to receive the value; else retain old value
    # We have avoided setting up each subsystem until this call as a stored setting may override default
    #  (or in the case of language, the stored setting or pop-up to user selects the language)

    DEBUG(f'Settings to restore: {settings_to_restore}')

    if not lang:
        DEBUG("*** FATAL ERROR: Language subsystem not available!")
        raise RuntimeError("Language subsystem not available!")
    lang.change_language(settings_to_restore.get('lang.language', lang.language))

    if not tempf:
        DEBUG("*** FATAL ERROR: Temporary Files subsystem not available!")
        raise RuntimeError("Temporary Files subsystem not available!")
    tempf.change(settings_to_restore.get('tempf.save_FP', tempf.default_FP))

    if not (tempf.oFP and os.path.isdir(tempf.oFP)):
        # Cannot proceed with setting up BAM file from settings if there is no valid temporary files area
        # Either the default directory (temp/) or a restored temp file setting must be valid to proceed
        tpath = tempf.oFP if tempf.oFP else "invalid"
        wgse_message("error", 'InvalidTempDirTitle', True,
                     lang.i18n['errTempDirPath'].replace('{{tempf}}', tpath))
        raise RuntimeError(f"Invalid Temporary Files Directory: {tpath}")

    if not reflib:
        DEBUG("*** FATAL ERROR: Reference Library subsystem not available!")
        raise RuntimeError("Reference Library subsystem not available!")
    reflib.change(settings_to_restore.get('reflib.FP', reflib.FP))

    if not outdir:
        DEBUG("*** FATAL ERROR: Output Directory subsystem not available!")
        raise RuntimeError("Output Directory subsystem not available!")
    outdir.change(settings_to_restore.get('outdir.FP', outdir.FP))

    if not fonts and gui:
        DEBUG("*** FATAL ERROR: Fonts Subsytem not available!")
        raise RuntimeError("Fonts Subsystem not available!")
    if gui:
        fonts.change(newface=settings_to_restore.get('fonts.face', fonts.face),
                     newbasept=settings_to_restore.get('fonts.basept', fonts.basept))

    # Set now because BAM load / restore may caused Ref Library download request
    prefserver = settings_to_restore.get('prefserver', prefserver)

    # Allow user override of threads and total memory (but not greater than platform returned values)
    updated = False
    os_threads_saved = settings_to_restore.get('os_threads_saved', 0)
    if 1 <= os_threads_saved < os_threads_proc:
        os_threads = os_threads_saved       # Make sure always one or greater to avoid div0 later
        updated = True

    os_totmem_saved  = settings_to_restore.get('os_totmem_saved', 0)
    if 2 <= os_totmem_saved < os_totmem_proc//10**9:  # Really should be 12 GB min for BWA but just stick with 2 GB for now
        os_totmem = os_totmem_saved * 10**9
        updated = True

    set_mem_per_thread_millions(os_totmem, os_threads)      # Ignore return; just use setting global os_mem value

    if updated:
        DEBUG(f'Updated: Procs: {os_threads}, total Mem: {(os_totmem/10**9):.1f} GB, mem per thread: {os_mem}')

    # Restore saved BAM / CRAM file IF gui (only); otherwise no need to process
    if gui and outdir.FP:
        saved_BAM_FN = settings_to_restore.get('BAM.file_FN', "")
        if saved_BAM_FN:
            try:
                DEBUG(f'Attempting to restore saved BAM file: {saved_BAM_FN}')
                BAM = BAMFile(saved_BAM_FN)
                DEBUG(f'Success restoring saved BAM file: {saved_BAM_FN}')
            except BAMContentErrorFile as err:
                BAM = None      # Ignore errors from trying restore; simply ignore setting
            except BAMContentError as err:
                BAM = None      # Ignore errors
            except BAMContentWarning as warn:
                pass            # Ignore warnings
            else:
                pass    # Ignore issuing warnings about CRAM, unindexed or unsorted file
            if outdir.FP and BAM:  # Sets part of output File variables that include BAM base name
                outdir.oFPB = outdir.oFP + BAM.file_FB
                outdir.FPB  = outdir.FP  + BAM.file_FB

    DEBUG(f'Finished restoring saved settings.')


def save_settings():
    """
    To store "saved" settings on program exit or whenever changed.  For now, just a select few values:
    DEBUG_MODE, language, output directory, reference library directory, temporary directory, wsl_bwa_patch
    """
    import json
    from utilities import DEBUG

    global outdir, BAM, reflib, tempf, lang, fonts
    global wgseset_oFN, prefserver, os_threads, os_totmem

    # DEBUG(f'WGSE JSON Setting file: {wgseset_oFN}')
    settings_to_save = {}

    # Only save value if set and not default (ones with default have "set" variable)
    # Order of save does not really matter. Read all at once and then process in specific order with load_settings()
    if lang and lang.language:
        settings_to_save['lang.language'] = lang.language
    if tempf and tempf.set:
        settings_to_save['tempf.save_FP'] = tempf.save_FP
    if reflib and reflib.set:
        settings_to_save['reflib.FP'] = reflib.FP
    if outdir and outdir.FP:
        settings_to_save['outdir.FP'] = outdir.FP
    if fonts and fonts.face != fonts.default_face:
        settings_to_save['fonts.face'] = fonts.face
    if fonts and fonts.basept != fonts.default_basept:
        settings_to_save['fonts.basept'] = fonts.basept
    if prefserver != 'NIH':     # Only save if not default
        settings_to_save['prefserver'] = prefserver
    if os_threads_saved and os_threads_saved > 0:
        settings_to_save['os_threads_saved'] = os_threads_saved
    if os_totmem_saved and os_totmem_saved > 0:
        settings_to_save['os_totmem_saved'] = os_totmem_saved
    if BAM and BAM.file_FN:
        settings_to_save['BAM.file_FN'] = BAM.file_FN
    # DEBUG_MODE is not a saved setting; as is in a special file checked and read at program startup earlier
    # DEBUG(f'WGSE JSON Settings to save: {settings_to_save}')

    # Do not save if no values set; language should always be set though (and newer always set values)
    if settings_to_save:
        try:
            with open(wgseset_oFN, 'w') as f:
                json.dump(settings_to_save, f)
        except OSError:
            DEBUG("*** Error writing settings file; skipping.")
            pass    # We try. If cannot write file then just move on silently


"""      ******************  FILE VARIABLE NOMENCLATURE  ***********************
 We do a lot of file name construction and manipulation. So we need clear conventions for naming the variables.
 File Variable Naming Acronyms (_suffix):
  FN    -- fully qualified File Name (path, base, suffix; i.e FPBS) (absolute or relative) (DEFAULT is uFN)
  FP    -- File Path name only (including trailing slash; head in split + /)
  FB    -- File Base name only (NO path, NO suffix) (simple root; splitext[0].split[1])
  FS    -- File Suffix only (including dot prefix; also called extension in splitext)
  FBS   -- File Base and Suffix (traditional file name; tail in split, basename())
  FPB   -- File Path and Base name (no suffix) (called root in splitext)
  qFN   -- Quoted fully qualified File Name (would never quote anything else) (with possible spaces in name)
  oFN   -- Native OS (slash) File Name (what you pass to open(); also oFP if directory)
  wFN   -- Windows (back slash) path File Name (or FP, etc)
  uFN   -- Unix/Universal (forward slash) path File Name (or FP, etc) (DEFAULT, if not specified)
            uFN is DEFAULT for ALL OS's in BASH and Win10 PowerShell; C:/users/name/.wgselang is OK
  x_qFN -- indicates actual executable program file name; usually always quoted but not in Native OS format

  In our terminology here:
   os.path.split elements:    [ oFP , FBS ]
   os.path.splitext elements: [ oFPB , FS ]
   os.path.basename returns FBS (same as split[1])
  But remember os.path is OS specific.  Pathlib is the OS independent representation.

  As most of the manipulation is done for BASH scripts; the default stored is Unix paths (forward slash)
  Only when needed in a native / root OS form for Windows, will it be converted (i.e. to Windows back slash)
  wgse.os_slash will contain the appropriate slash for file paths in the current OS
  outFPB is the historic outfws + '/' (fws was file withOUT suffix)

  Python "open" command needs oFN without quotes (native OS, uses appropriate slash).
  Bash scripts need qFN (in Unix slash format); even on Windows machines when path includes drive letter format.
  Python "process" command is a list of strings so no quoting of individual strings is necessary; not shell parsed.
"""

# Todo
#  Beginning setup here for a Check-Generate/Gather subsystem to allow button commands to simply specify what they need.
#  Allowing the Check-Generate/Gather to try and find AND make available the necessary files. Can maybe automatically
#  invoke major functions like alignment, variant calling, etc. if the button command does not care
#  about the parameters used to get from a to b. Also allows test vendor supplied files (or previously user generated
#  ones) to be looked for and utilized directly.  To be moved up into the main section once settled and implemented.
#  Thinking of using bit masks for efficiency over dictionaries.  But may need more parameters attached so maybe not?
'''
# Mask Categories for Required Files
mask_UserFiles
mask_RefGenome
mask_Liftover
mask_Microarray
mask_CombinedKit

# Masks for Required User Input Files
mask_FASTQ              = 0x0001
mask_FASTQ_PE           = 0x0002
mask_BAM                = 0x0010
mask_BAM_Sorted         = 0x0020
mask_BAM_Index          = 0x0040
mask_BAM_Unaligned      = 0x0080
mask_CRAM               = 0x0100
mask_CRAN_Index         = 0x0200
mask_VCF_RAW
mask_VCF_RAW_Index
mask_VCF_Called
mask_VCF_Called_Index
mask_CombinedKit

# Masks for Required Microarray Template files
mask_23andMe_API
mask_23andMe_v2
mask_23andMe_v3
mask_23andMe_v4
mask_23andMe_v5
mask_Ancestry_v1
mask_Ancestry_v2
mask_FTDNA_v1
mask_FTDNA_v2
mask_FTDNA_v3
mask_LivDNA_v1
mask_LivDNA_v2
mask_MyHeri_v1
mask_MyHeri_v2
mask_NGG_v2
mask_NGG_v2NG
'''
