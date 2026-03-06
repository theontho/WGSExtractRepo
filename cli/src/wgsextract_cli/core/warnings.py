import logging
import os
import shutil

from wgsextract_cli.core.messages import SYSTEM_MESSAGES as MESSAGES

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
        # This is a rough heuristic as per the original app's logic
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
            except Exception:
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
        except Exception:
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
        logging.warning(f"!!! {MESSAGES['insufficient_disk_title']} !!!")
        msg = MESSAGES["insufficient_disk_msg"].format(
            detected=f"{free_gb:.1f}", path=path, needed=required_gb
        )
        for line in msg.split("\n"):
            logging.warning(f"!!! {line} !!!")
        return False
    return True
