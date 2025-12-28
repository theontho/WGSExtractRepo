# coding: utf8
# Copyright (C) 2021-2022 Randy Harr
#
# License: GNU General Public License v3 or later
# A copy of GNU GPL v3 should have been included in this software package in LICENSE.txt.

"""
Standalone script to process BWA Alignment stderr output and provide a progress line instead of tens of thousands of
individual progress report lines.  Keeps the final output command window cleaner while providing updated progress.
Takes the total read segments expected as the second parameter after the log file.  Normally you can pipe stderr from
BWA to this module via "2> >(python progress.py - numsegs)". Reads from first file parameter (stdin if -) and writes
to stdout (stderr if '-'). Provides Percent done and Estimated Time to Completion along with frequencing of updates.
Had to make file parameter as pycharm does not allow stdin when standalone debugging. Process BWA Indexing stderr output
as well.  Passes on lines that are not progress lines (so errors, etc).
"""

import sys
import os


def time_string(time_left):
    """
    Routine to compose custom days and time (left) string from parameter of total seconds.
    Key is the integer division (//) that truncates the value at each stage.
    """
    fover = "time OVER is" if time_left < 0 else "time left is"
    time_left = abs(time_left)
    days  = time_left // (3600 * 24) ; time_left -= days  * 3600 * 24
    hours = time_left //  3600       ; time_left -= hours * 3600
    mins  = time_left //  60         ; time_left -= mins  * 60
    secs  = time_left
    days_left = f'{days:>2n} day ,' if days == 1 else \
                f'{days:>2n} days,'     # f'        ' if days == 0 else \
    return f'{fover} {days_left} {hours:02n}:{mins:02n}:{secs:02n}'


def print_time(piped, total_seqs, total_iter, time_so_far, total_seqs_read):
    """
    Print the current BWA Align progress line based on time and read sequences so far.
    If log_file is dash ('-', stdin), then print update progress line to stderr.  Else dump each line to stdout.
    """
    fraction_done = total_seqs_read / total_seqs if total_seqs > 0 else 0
    total_time = int(time_so_far * total_seqs / (total_seqs_read + 0.0001))
    ftime = time_string(total_time - time_so_far)       # includes text of status (left, run-over)
    update = time_so_far / total_iter if total_iter > 0 else 600
    iter_str = f'{total_iter:>3}' if total_iter < 1000 else f'{total_iter}'
    msg = f' {fraction_done:>7.2%} aligned; {ftime} ({iter_str} iters, 1 every {int(update):>3} secs)'
    print(msg, end='\r', file=sys.stderr, flush=True) if piped else print(msg)
    # Purposely use \r and not (default) newline \n so we overwrite the same progress line
    # But during debug using file input instead of stdin; use newline and so simple print


if __name__ == '__main__':
    module = os.path.basename(sys.argv[0])
    if len(sys.argv) < 3 or len(sys.argv) > 4:  # Remember first arg is always argv[0] - the module name
        print(f'***ERROR: Exactly two parameters needed for {module} call.', file=sys.stderr, flush=True)
        print(f'   python3 progress.py log_file total_read_segments_to_process', file=sys.stderr, flush=True)
        print(f'     log_file can be "-" to read stdin stream', file=sys.stderr, flush=True)
        print(f'    Optional fourth DEBUG parameter allowed also.', file=sys.stderr, flush=True)
        exit(1)
    log_file = sys.argv[1]
    total_seqs = int(sys.argv[2])
    DEBUG = len(sys.argv) == 4

    piped = log_file == "-"         # Also, if piped from stdin, then print to stderr instead of stdout

    total_iter = 0
    dangling_line = False
    total_lines = 0
    time_so_far = 0
    total_seqs_read = 0

    print_time(piped, total_seqs, total_iter, time_so_far, total_seqs_read)    # Print initial status line at start
    dangling_line = piped

    f = sys.stdin if piped else open(log_file, "r")
    for line in f:
        if DEBUG:       # If DEBUG set, print lines as received
            if piped and dangling_line:
                print(f'\n{line}', end='', file=sys.stderr, flush=True)
                dangling_line = False
            elif piped:
                print(line, end='', file=sys.stderr, flush=True)
            else:
                print(line, end='')

        # Process lines
        if "mem_process_seqs" in line:              # BWA Align progress line to process; every
            fields = line.split(" ")
            total_iter += 1
            time_so_far += int(round(float(fields[8]), 0))
            total_seqs_read += int(fields[2])
            print_time(piped, total_seqs, total_iter, time_so_far, total_seqs_read)
            dangling_line = piped
        # elif "BWTIncCreate" in line:                # BWA Index initial size report (how many iterations)
            # Reports the text length in billions of bytes. Every stat line of 10 iterations is 100 million chars
            # total_lines = int(line.spit(" ")[1].split("=")[1]) / 100000000
        elif "BWTIncConstructFromPacked" in line:   # BWA Index progress line to process; every 10 iterations
            total_iter += 1
            fraction_indexed = total_iter / 69
            msg = f'[BWTIncConstructFromPacked]{fraction_indexed:>7.2%} indexed'
            if piped:
                print(msg, end='\r', file=sys.stderr, flush=True)
                dangling_line = True
            else:
                print(msg+'\n')
                dangling_line = False

    if not piped:
        f.close()

    if piped and dangling_line:
        print("", end="\n", file=sys.stderr, flush=True)    # Force final newline on console progress
