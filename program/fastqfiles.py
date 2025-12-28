# coding: utf8
# Copyright (C) 2022 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""###################################################################################################################
    FASTQFile (class; fastqfiles module) is the central handler for all things FASTQ.  Processing, determining stats,
    manipulating, etc.  The idea is a class instance for each FASTQ file (pair) specified.  Eventually allowing
    for multiple to be known at the same time.  Once a FSATQ file is selected in the OS interface, the FASTQ
    object is instantiated and processing begins. Mainly used by the Align command.
"""

import os       # for path, stat
import re
import gzip
from math import sqrt

from utilities import DEBUG, is_legal_path, nativeOS, universalOS, unquote, Error, Warning, wgse_message
from commandprocessor import run_bash_script
import settings as wgse


def process_FASTQ(fastq_FN, paired=True):
    """
    Pseudo FASTQ stats processing like for BAM module process_BAM_header and process_BAM_body.
    No FASTQ module yet so used with the alignment command for now.
    Takes in the name of the primary FASTQ file and if paired (simply doubles result if paired)
    Returns the number of segments and avg read length of the FASTQ (so RAW gbases can be calculated as well)
    As well as tries to identify the sequencer.
    """

    fastq_oFN = nativeOS(fastq_FN)
    line_cnt = char_cnt = 0
    seqid = ""
    rcnt = rlen = rmean = rM2 = 0
    with gzip.open(fastq_oFN, 'rt') as f:
        for line in f:
            if line_cnt % 4 == 2:       # more common case; checking length of sequencer read
                rlen += len(line)
                if rlen > 1:
                    rcnt += 1
                    rdelta = rlen - rmean
                    rmean += rdelta / rcnt
                    rdelta2 = rlen - rmean
                    rM2 += rdelta * rdelta2
            elif line_cnt == 0:         # Only at start; while skipping header or to read first sequncer ID
                if line[0] == '#':      # Skip header; do not count (new spec coming out with header)
                    continue
                else:   # line[0] == '@':   # First line and sequencer label
                    seqid = determine_sequencer(line.strip().split("\t")[0][1:])
                    line_cnt = 1
            elif line_cnt > 20000:      # Only at end; Average first 5K segments (4 lines per segment)
                line_cnt -= 1
                break
            char_cnt += len(line)
            line_cnt += 1

    avg_read_length = avg_read_stddev = 0
    if rcnt > 2:
        rstd = sqrt(rM2 / (rcnt - 1))
        avg_read_length = rmean
        avg_read_stddev = rstd

    # Counting all the lines; even as a wc -l subprocess, is just too long. So do a quick estimate based on the
    #  character count in the first 10,000 lines above (2500 read segments) divided into the file size
    numsegs = 0
    fastq_stats = os.stat(fastq_oFN)
    if fastq_stats.st_size > 0:
        numsegs = int(fastq_stats.st_size / (char_cnt / (line_cnt / 4)))
        numsegs *= 2 if paired else 1

    DEBUG(
        f'FASTQ Stats: ID - "{seqid}, # segs - {numsegs},' 
        f' avg read length - {avg_read_length}, read len stddev - {avg_read_stddev}')
    return seqid, numsegs, avg_read_length          # e.g. return "Illumima", 660000000, 150


def determine_sequencer(seqid):
    """
    Determines sequencer type from SN in BAM first field or SeqID first field in FASTQ.  Relies on sequencer_templates
    defined in settings.py.  Used in places like the align command to alter behavior based on sequencer info.
    Called both when processing a BAM and FASTQ file. Todo Should determine_sequencer be in utilities? mainwindow?
    """

    if seqid is None:
        return "Error"
    # Should be guaranteed match as last one is wildcard and returns unknown
    for key, val in wgse.sequencers.items():
        # Should be stored compiled but the dictionary is defined in settings without acess to re module
        # DEBUG(f'Sequencer Key to try: {key}')
        if re.compile(val[0]).match(seqid):
            if key != "Unknown":
                return key
    return seqid[0:23]+"..." if len(seqid) > 25 else seqid[0:25]  # Return what we see. Let user decide what it might be
