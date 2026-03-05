import logging
import os
import shutil

# Internal machine benchmarks for high-performance reference
# Obtained from 30x WGS (7.3GB CRAM) on M1 Pro class hardware
M1_PRO_ESTIMATES = {
    "GetBAMHeader": 0.03,
    "LiftoverCleanup": 0.01,
    "ButtonBAMStats": 0.04,
    "ButtonBAMStats2": 50.53,
    "CoverageStatsPoz": 49.09,
    "GenBAMIndex": 1.98,
    "BAMtoCRAM": 11.69,
    "ButtonMitoBAM": 2.77,
    "ButtonYonly": 3.03,
    "ButtonUnmappedReads": 0.08,
    "ButtonSNPVCF": 6085.92,
    "ButtonInDelVCF": 6942.84,
    "ButtonCombinedKit": 470.79,
    "ButtonFastp": 1.69,
    "ButtonFastqc": 5.65,
    "CoverageStatsBIN": 3547.49,
    "CoverageStatsWES": 177.89,
    "CreateAlignIndices": 0.03,
    "ButtonAlignBAM": 20.30,
    "GenSortedBAM": 858.75,
    "CRAMtoBAM": 234.73,
    "ButtonUnalignBAM": 1907.09,
    "GenBAMSubset": 391.29,
}

# Expected run times of various commands in seconds
# Extracted from program/settings.py
EXPECTED_TIME = {
    "GetBAMHeader": 2,
    "LiftoverCleanup": 5,
    "ButtonBAMStats": 15,
    "ButtonBAMStats2": 3 * 60,
    "ButtonMitoFASTA": 3 * 60,
    "ButtonMitoBAM": 3 * 60,
    "ButtonMitoVCF": 3 * 60,
    "ButtonYandMT": 3 * 60,
    "ButtonYonly": 3 * 60,
    "ButtonMicroarrayDNA": 5 * 60,
    "ButtonYHaplo2": 5 * 60,
    "ButtonBAMStatsLong": 10 * 60,
    "ButtonYHaplo": 10 * 60,
    "CoverageStatsPoz": 10 * 60,
    "AnnotatedVCF-yOnly": 10 * 60,
    "UnsortBAM": 10 * 60,
    "ButtonMTHaplo": 20 * 60,
    "GenLoadGenome": 20 * 60,
    "GenSortedBAM": 30 * 60,
    "GenBAMIndex": 30 * 60,
    "BAMtoCRAM": 30 * 60,
    "ExtractWES": 30 * 60,
    "ButtonBAMNoIndex": 35 * 60,
    "ButtonFastp": 45 * 60,
    "ButtonUnmappedReads": 45 * 60,
    "CoverageStats": 45 * 60,
    "ButtonCombinedKit": 50 * 60,
    "ButtonFastqc": 60 * 60,
    "CoverageStatsWES": 60 * 60,
    "AlignCleanup2": 60 * 60,
    "GenBAMSubset": 60 * 60,
    "ButtonBAMNoSort": 70 * 60,
    "ButtonUnalignBAM": 75 * 60,
    "CRAMtoBAM": 90 * 60,
    "CoverageStatsBIN": 120 * 60,
    "AlignCleanup": 120 * 60,
    "ButtonSNPVCF": 150 * 60,
    "ButtonInDelVCF": 150 * 60,
    "CreateAlignIndices": 180 * 60,
    "ButtonAlignBAM": 9 * 60 * 60,
}

# Messages extracted from program/language.xlsx (English)
MESSAGES = {
    "infoFreeSpace": "Operation {app} needs {size} GB of Free Space in the Temporary Directory to proceed. You likely also need {final} GB of free space in the Output Directory for the final file to be created. This is in addition to any space already used. Make sure the needed space is available before continuing.",
    "RealignBAMTimeWarnMesg": """There are several long tasks to (re)align a BAM file. Each major step and the rough time to complete it are:
(1) Unalign the BAM to create the FASTQ files (1-3 hours)
(2) Create new Reference Genome Index (2-3 hours)
(3) Align FASTQ to Reference Genome (8-160 hours)
(4) Remove Duplicates, Sort and Index to Create the Final BAM (1-2 hours)
(5) Create the CRAM (1-2 hours)

We estimate, on this machine, this will take {time} hours.""",
    "ExpectedWait": "Expected Wait is {time}",
    "YorubaWarning": "Your BAM file uses the Yoruba reference genome for mitochondrial DNA. This is incompatible with the rCRS genome that tools use. We cannot convert this for you at this time.",
    "LowCoverageWarning": "This BAM file has a low mapped average read depth. This can lead to incorrect and fewer variant calls.",
    "LongReadSequenceWarning": "The BAM file appears to be from a long-read sequencer (e.g. Nanopore). Tools have not been tuned to handle this special case.",
    "warnBAMNoStatsNoIndex": "The specified BAM File is not sorted and / or indexed. Some commands cannot run or will take longer to run without these features. We encourage you to sort and / or index your BAM File first; which takes ~30 min each.",
    "warnCRAMNoStats": "The stats for a CRAM file take over 30 minutes to complete with 30x WGS and so are not automatically run. You may need to run 'info --detailed' once to calculate and cache these stats.",
}


def format_time(seconds):
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"


def get_free_space_needed(file_size_bytes, sort_type="Coord", is_cram=False):
    """
    Calculates the free space needed based on the logic in program/mainwindow.py:Adjust_Mem
    """
    cram_mult = 1.95 if is_cram else 1.0
    name_mult = 1.45 if sort_type == "Name" else 1.0

    isize_gb = file_size_bytes * cram_mult / 10**9
    temp_needed_gb = int(isize_gb * name_mult + isize_gb)
    final_needed_gb = int(isize_gb)

    return temp_needed_gb, final_needed_gb


def print_warning(
    action_key,
    app_name=None,
    size_gb=None,
    final_gb=None,
    threads=None,
    file_size=None,
    is_cram=False,
):
    """Prints a warning message and expected time for a given action."""

    # 1. Expected Time
    if action_key in EXPECTED_TIME:
        wait_time = EXPECTED_TIME[action_key]
        # Adjust for threads if it's a parallelizable action
        # This is a rough estimation as per the original app's logic
        if threads and action_key in [
            "ButtonAlignBAM",
            "ButtonUnalignBAM",
            "GenSortedBAM",
            "ButtonSNPVCF",
            "ButtonInDelVCF",
        ]:
            try:
                t = int(threads)
                if t > 1:
                    # Very rough heuristic: speed up but not linearly
                    wait_time = wait_time / (t**0.7)
            except:
                pass

        time_str = format_time(int(wait_time))
        logging.warning(
            f"!!! WARNING: {MESSAGES['ExpectedWait'].format(time=time_str)} !!!"
        )

    # 2. Specific Messages
    if action_key == "infoFreeSpace":
        if file_size is not None:
            # Dynamic calculation
            sort_type = "Name" if app_name and "Name" in app_name else "Coord"
            calc_temp, calc_final = get_free_space_needed(file_size, sort_type, is_cram)
            size_gb = size_gb if size_gb is not None else calc_temp
            final_gb = final_gb if final_gb is not None else calc_final

        if app_name and size_gb is not None and final_gb is not None:
            msg = MESSAGES["infoFreeSpace"].format(
                app=app_name, size=size_gb, final=final_gb
            )
            logging.warning(f"!!! {msg} !!!")

    elif action_key == "RealignBAMTimeWarnMesg" and threads:
        try:
            cpus = int(threads)
            estimated_hours = 5 + 160 / cpus
            msg = MESSAGES["RealignBAMTimeWarnMesg"].format(
                time=f"{estimated_hours:.1f}"
            )
            logging.warning(f"!!! {msg} !!!")
        except:
            pass

    elif action_key in MESSAGES:
        logging.warning(f"!!! {MESSAGES[action_key]} !!!")


def check_free_space(path, required_gb):
    """Helper to check if a path has enough free space."""
    if not os.path.exists(path):
        return True  # Can't check if path doesn't exist yet

    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024**3)
    if free_gb < required_gb:
        logging.warning(
            "!!! EXTRA LARGE WARNING: Insufficient Disk Space Detected! !!!"
        )
        logging.warning(f"!!! Detected: {free_gb:.1f} GB available on {path} !!!")
        logging.warning(f"!!! Estimated: {required_gb} GB needed !!!")
        logging.warning(
            "!!! This operation will likely consume more space than you have available. !!!"
        )
        return False
    return True
