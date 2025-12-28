# coding: utf8
# Copyright (C) 2022 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""
Standalone script to process a reference model FASTA to determine the inclusion of N's in the base pair sequence.
Reads the compressed FASTA. Takes as a parameter the FASTA file. Also expects and reads in the DICT file determined
from the FASTA file name -- easier to do one pass if we have the sequence lengths.  Processes all sequences.
Detailed N segment stats writtem to RefModel.nbin.csv. Key stats per sequence and totals written to RefModel.ncnt.csv .
Also creates nat log bucket counts of number of N's; 1000 buckets per sequence. Per David Vance's display criteria.

Sequences in a reference model are arbitrarily broken up into short lines of 50-80 characters (base-pairs) each. All
white space is in-material and to be ignored.  We want to not just count how many N values in a sequence but also
(1) how many regions of contigious N's (with their mean and std dev of size) and
(2) a thousand buckets for each sequence representing the round(natlog(# of N's)) in that bucket.
Runs of contigous N values can overlap the short line and bucket boundaries and must be handled appropriately.
Due to rounding errors, the last bucket may not be the same size of base-pairs as the rest of the buckets.

Detects if a FASTQ instead of FASTA and reports error. Skips any sequence where the name is not found in the
DICT file read in to start.  Key is not just the SN but also LN fields in the DICT file.
"""

import sys
import os
import re
import math
import gzip

empty_dict = [ 0, '00000000000000000000000000000000' ]
NUM_BUCKETS = 1000      # Number of buckets per sequence (seqLN / NUM_BUCKETS == bucksize)
NRUN_SIZE = 300         # Threshold to record Run of N's data (large vs small); Roughly the insert size

# Ref Model passed in as first parameter. From file.fa.gz, find file.dict and create file.ncnt.csv and file.nbin.csv
fagz_FN = None
ncnt_FN = None
nreg_FN = None
nf = None       # short name for open ncnt_file output for writing (per sequence summaries and buckets)
rf = None       # short name for open nreg_file output for writing (each N region)

# Per Sequence (while processing) values
seqSN = None    # Extract sequence name; set if in sequence. Otherwise None.
seqLN = 0       # Length of Sequence from DICT entry (to determine bucket size)
seqBPcnt = 0    # Current base-pair count into sequence (for determining bucket boundary)

seqNregs = 0    # Count of N regions in sequence (may be zero)
seqNcnt  = 0     # Count of N values in sequence; will be less than seqBPcnt and possibly zero
seqNmean = 0    # Current running mean length of each N region (Nregs > 0)
seqNM2   = 0      # For Welford Online Algorithm (one pass std dev calc)
smlNregs = 0    # Separately counting and not tallying small N regions (< 10)

# Per Bucket
buckNcnt  = 0    # Count of Ns in open Bucket
buckBPcnt = 0   # Count of bp's in open Bucket
bucksize  = 0    # Size of bucket in base-pairs for current sequence (NUM_BUCKETS buckets per sequence)
buckets   = []    # List of a thousan buckets. Each entry is round of nat log of number of N's in bucket

# Per run of N's
inNrun = False  # In a run of N's; set when N at end of last line read (open Nrun at line boundary)
Nruncnt = 0     # Count of N's in open run of N's region

# Running total for last line
totalSN = 0
totalLN = 0
totalNcnt = 0
totalNregs = 0
totalsmlNregs = 0

skipping = False # if skipping sequence due to unmatching sequence name to SN in DICT file


def closeFile():
    global seqSN, totalSN, totalLN, totalNcnt, totalNregs, totalsmlNregs, nf

    if seqSN:
        closeSeq()

    print(f'#TOTALS:', file=nf)
    print(f'{totalSN}\t{totalLN:,}\t{totalNcnt:,}\t{totalNregs}\t\t\t{totalsmlNregs}', file=nf)


def closeSeq():
    """
    Close out open Sequence; possibly open N run as well.  Calculate final values and print line to stdout
    """
    global seqSN, seqLN, seqBPcnt, seqNM2, seqNcnt, seqNregs, seqNmean, smlNregs, buckBPcnt, bucksize
    global totalSN, totalLN, totalNcnt, totalNregs, totalsmlNregs

    if seqLN != seqBPcnt:
        print(f'***WARNING: {seqSN} FASTA ({seqBPcnt}) and DICT ({seqLN}) lengths differ: {seqBPcnt-seqLN}',
              file=sys.stderr, flush=True)

    if inNrun:  # Finish open N region at tail of sequence
        closeNrun(0)

    if buckBPcnt:
        closeBucket()       # Always a bucket open; so close the last one still open

    # Only final calc to close a sequence is determining the Std Dev from the running intermediate values
    seqNSD = math.sqrt(seqNM2 / (seqNcnt - 1)) if seqNcnt > 2 else 0

    # print entry for this sequence; including all 1000 buckets
    print(f'{seqSN}\t{seqLN:,}\t{seqNcnt:,}\t{seqNregs}\t{seqNmean:,.0f}\t{seqNSD:,.0f}\t{smlNregs}\t{bucksize}',
          end='', file=nf)  # partial line
    for index, bucket in enumerate(buckets):
        val = round(math.log(bucket) if bucket > 1 else 0)
        # changed to print as sparse list as most of the 1000 entries are zero; so now bucket start (in bp) then ln Ncnt
        if val > 0:
            start = index * bucksize
            print(f'\t{start}\t{val}', end='', file=nf)
    print('', file=nf)

    totalSN += 1
    totalLN += seqLN
    totalNcnt += seqNcnt
    totalNregs += seqNregs
    totalsmlNregs += smlNregs

    seqSN = None


def openSeq(newseq):
    """
    The main startup. Each sequence causes all new stats to be collected. So reset everything.
    """
    global seqSN, seqLN, seqBPcnt, seqNcnt, seqNregs, smlNregs, seqNmean, seqNM2
    global buckBPcnt, buckNcnt, bucksize, buckets, inNrun, Nruncnt, skipping, fagz_FN

    seqSN = newseq
    seqLN = seqdict.get(seqSN, empty_dict)[0]  # Using seq name, get # base pairs from seqdict entry
    if seqLN > 0:
        print(f'***INFO: Processing {seqSN} in FASTA file {os.path.basename(fagz_FN)}',
              file=sys.stdout, flush=True)
        seqBPcnt = 0
        seqNcnt = seqNregs = smlNregs = 0
        seqNmean = seqNM2 = 0

        buckBPcnt = buckNcnt = 0
        bucksize = round(seqLN / NUM_BUCKETS)
        buckets = []

        inNrun = False
        Nruncnt = 0

        skipping = False
    else:
        print(f'***ERROR: Skipping unrecognized SN ({seqSN}) in FASTA file (not found in DICT).',
              file=sys.stderr, flush=True)
        skipping = True
        seqSN = None


def closeBucket():
    """
    Close open bucket by appending current stat to list.  If partial bucket, scale value to full bucket size.
    """
    global buckets, buckNcnt, buckBPcnt

    if buckBPcnt:
        buckets.append(buckNcnt)
    buckNcnt = 0
    buckBPcnt = 0


def closeNrun(trailing):
    """
    Close out (possibly) open Nrun (either end of Nrun or end of Sequence with open Nrun)
    """
    global seqNcnt, buckNcnt, smlNregs, seqNregs, seqNmean, seqNM2, inNrun, Nruncnt, NRUN_SIZE

    seqNcnt += Nruncnt  # Running total of N's for sequence
    buckNcnt += Nruncnt  # Running total of N's for bucket

    # We have found as many as 25% of regions are 1-3 base pairs long.  Most of rest are a multiple of 10K up to
    # millions long. With a few 50-1,00 scattered in there. Mean and Std Dev get thrown off with the short runs.
    # So now report and count short and long runs separately. Only calculate Mean and Std Dev on >NRUN_SIZE regions.
    # NRUN_SIZE should be set insert size of most sequencing tools today.  Longer runs of N cannot be aligned across it.
    if Nruncnt > NRUN_SIZE:
        seqNregs += 1
        delta = Nruncnt - seqNmean
        seqNmean += delta / seqNregs
        delta2 = Nruncnt - seqNmean
        seqNM2 += delta * delta2

        start = seqBPcnt - Nruncnt - trailing
        print(f'{seqSN}\t{seqNregs}\t{start:,}\t{Nruncnt:,}', file=rf)
    else:
        smlNregs += 1

    inNrun = False
    Nruncnt = 0


def processNrun(Nrunlen, keep_open, trailing):
    """
    Process a run of N's from a sequence line; 1 to line length in size. If keep_open True, then this is not the end
    of a run; just an intermediate.
    """
    global seqNcnt, inNrun, buckNcnt, Nruncnt

    Nruncnt += Nrunlen     # Running total of N's for contiguous N run

    inNrun = keep_open

    if not inNrun:
        closeNrun(trailing)


def processSeq(linebp):
    """
    Process a line of base pair values from a FASTA sequence line.
    Lines are often broken up into 50 to 80 character long text lines terminated by a newline.
    Whitespace and newlines are ignored. Big issue if newlines not breaking a multi-million character sequence.

    Use regex matching to spead up processing. Must handle run of N's spanning a full line (from start to end)
    as well as a overlapping a line (start or end) or changing at the line boundary.

    Do not have to worry about bucket boundaries.  Those were handled by splitting line at bucket boundary before
    making this call.
    """
    global inNrun, seqNcnt, seqBPcnt, buckBPcnt

    # If in Nrun but first base-pair is not an N, then close out the previous open Nrun
    if inNrun and linebp and linebp[0] != 'N':
        closeNrun(0)

    seqBPcnt += len(linebp)
    buckBPcnt += len(linebp)

    # Simply quickly finds all runs of N in line.  Does not say where they occur. May butt against the end(s).
    Nruns = re.findall(r'N+', linebp)

    while len(Nruns) > 0:
        keep_open = len(Nruns) == 1 and linebp[-1] == 'N'     # If last Nrun and line ends in N then keep open
        processNrun(len(Nruns[0]), keep_open, len(linebp)-len(Nruns[0]))
        del Nruns[0]


if __name__ == '__main__':
    module = os.path.basename(sys.argv[0])
    if len(sys.argv) != 2:  # Remember first arg is always argv[0] - the module name
        print(f'Usage: python3 {module} RefModel.fa.gz', file=sys.stderr, flush=True)
        print(f'   RefModel.fasta.gz and RefModel.fna.gz also acceptable', file=sys.stderr, flush=True)
        print(f'   RefModel.dict file must exist. See "samtools dict" for how to create.', file=sys.stderr, flush=True)
        print(f'   Output written to RefModel.ncnt.csv and RefModel.nbin.csv', file=sys.stderr, flush=True)
        exit(1)
    fagz_FN = sys.argv[1]                     # Full path, if specified (FN)
    fagz_FBS = os.path.basename(fagz_FN)      # Just FASTQ file name
    print(f'***INFO: Processing Ref Model {fagz_FBS} for >{NRUN_SIZE}bp runs of N and '
          f'{NUM_BUCKETS} buckets per sequence',
          file=sys.stdout, flush=True)

    fagz_FPB  = fagz_FN.replace(".fasta.gz", "").replace(".fna.gz", "").replace(".fa.gz", "")
    dict_file = fagz_FPB + ".dict"
    ncnt_file = fagz_FPB + "_ncnt.csv"
    nreg_file = fagz_FPB + "_nbin.csv"

    # First read DICT file to get length of each sequence we expect to encounter
    seqdict = {}
    with open(dict_file, "r") as f:
        for line in f:
            cols = line.split()
            if cols[0] == '@SQ':
                #       SN (key)               LN          M5           Don't need UR field
                seqdict[cols[1][3:]] = [int(cols[2][3:]), cols[3][3:]]

    # Dump header of output (stdout) TSV file result
    nf = open(ncnt_file, "w")
    print(f'#Processing Ref Model: {fagz_FBS} with >{NRUN_SIZE}bp runs of N and {NUM_BUCKETS} '
          f'buckets per sequence', file=nf)
    print(f'#Seq\tNumBP\tNumNs\tNumNreg\tNregSizeMean\tNregSizeStdDev\tSmlNreg\tBuckSize\t'
          f'Bucket Sparse List (bp start, ln value) when nonzero', file=nf)

    rf = open(nreg_file, "w")
    print(f'#Processing Ref Model: {fagz_FBS} with >{NRUN_SIZE}bp of N runs', file=rf)
    print(f'#SN\tBinID\tStart\tSize', file=rf)

    # Now read and process fagz_file (FASTA reference model) for runs of N
    seq = None      # Holds the current SN we are working on
    inNrun = False  # Holds state of whether in a run of N's or not
    skipping = False    # State of whether skipping a sequence not matching any DICT SN entry

    with gzip.open(fagz_FN, 'rt') as f:
        for dirty_line in f:
            line = dirty_line.strip()
            line_len = len(line)

            # Skip blank or haeder lines (header is in new FASTA / FASTQ standard not yet in use)
            if line_len == 0 or line[0] == '#':
                continue

            # Check if processing a FASTQ file (sequencer output) by accident and drop out
            if line[0] == '+':
                print(f'***ERROR: Appears to be FASTQ sequencer data; not a FASTA reference model.',
                      file=sys.stderr, flush=True)
                exit(1)

            # Starting a new sequence ...
            if line[0] == '>':
                if seqSN:     # Close and Dump open sequence
                    closeSeq()
                openSeq(line.split()[0][1:])        # Split line on whitespace, take first field, throw out initial '@'

                # Finished setting up a new sequence; skip to next line to start processing body of sequence
                continue

            # Did not start a new sequence and still skipping so continue on to next line
            if skipping:
                continue

            # Special case if our bucket boundary is in the middle of the current line. We will split the line in two
            # and process each as if a separate line.  Will handle a bucket boundary between processing split lines.
            # Another special case if boundary falls on end of this line before split.
            new_seqBPcnt = seqBPcnt + line_len
            remain = new_seqBPcnt % bucksize        # guaranteed < len(line) and > 0
            if new_seqBPcnt // bucksize != seqBPcnt // bucksize and remain > 0:    # Line spans a bucket boundary
                extra = line[-remain:]      # Save extra in line beyond bucket boundary
                line = line[:-remain]   # Change line to process to be just up to bucket boundary; line[:0] legal?
            else:
                extra = None
                ebucket_boundary = remain == 0  # Force a bucket close if coincident bucket and line boundary

            processSeq(line)
            if extra:
                closeBucket()
                processSeq(extra)
            elif ebucket_boundary:
                closeBucket()

    closeFile()
