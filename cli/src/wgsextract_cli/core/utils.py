import hashlib
import logging
import os
import shutil
import subprocess
import tempfile

from wgsextract_cli.core.constants import REF_GENOME_FILENAMES
from wgsextract_cli.core.messages import LOG_MESSAGES

try:
    import psutil
except ImportError:
    psutil = None

import atexit
import signal
import threading
import time


class ProcessRegistry:
    """
    Central registry for tracking sub-processes and cancel events.
    Enables reliable cleanup on application exit.
    """

    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def register_process(self, key: str, process: subprocess.Popen):
        with self._lock:
            self.processes[key] = process

    def unregister_process(self, key: str):
        with self._lock:
            if key in self.processes:
                del self.processes[key]

    def register_event(self, key: str, event: threading.Event):
        with self._lock:
            self.events[key] = event

    def unregister_event(self, key: str):
        with self._lock:
            if key in self.events:
                del self.events[key]

    def cleanup(self):
        """Terminate all registered processes and set all events."""
        with self._lock:
            # 1. Signal all events
            for event in self.events.values():
                event.set()

            # 2. Terminate all processes
            if not self.processes:
                return

            # Safety check: if streams are already closed (atexit), skip logging
            try:
                import sys

                if not sys.stderr or sys.stderr.closed:
                    pass
                else:
                    logging.info(
                        f"Cleanup: Terminating {len(self.processes)} active processes..."
                    )
            except (AttributeError, ValueError):
                pass

            # Send termination signals
            for key, proc in self.processes.items():
                if proc.poll() is None:
                    try:
                        if os.name == "nt":
                            # Windows: send CTRL_BREAK_EVENT to process group
                            # Use getattr to avoid MyPy error on non-Windows
                            proc.send_signal(
                                getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM)
                            )
                        else:
                            # Unix: kill the process group
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception as e:
                        logging.debug(f"Failed to term process {key}: {e}")

            # Brief wait for graceful exit
            time.sleep(0.5)

            # Force kill any still alive
            for _key, proc in self.processes.items():
                if proc.poll() is None:
                    try:
                        if os.name == "nt":
                            proc.kill()
                        else:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception:
                        pass

            self.processes.clear()


# Global registry instance
proc_registry = ProcessRegistry()


def cleanup_processes():
    """Entry point for atexit and signal handlers."""
    proc_registry.cleanup()


# Register for atexit
atexit.register(cleanup_processes)


def get_resource_defaults(threads_arg=None, memory_arg=None):
    """
    Calculate default CPU threads and memory if not provided.
    Logic inspired by Adjust_Mem in program/mainwindow.py.
    """
    # 1. Threads
    if threads_arg is not None:
        threads = str(threads_arg)
    else:
        # Default to 75% of available cores
        cpus = os.cpu_count() or 4
        threads = str(max(1, int(cpus * 0.75)))

    # 2. Memory (in GB per thread for samtools sort)
    if memory_arg is not None:
        memory = str(memory_arg)
    else:
        # Default to 4GB total or 1GB per thread, whichever is smaller
        if psutil:
            total_mem_gb = psutil.virtual_memory().total / (1024**3)
            # Use 25% of system memory
            safe_mem = max(2, int(total_mem_gb * 0.25))
            # samtools sort -m is PER THREAD
            mem_per_thread = max(1, safe_mem // int(threads))
            memory = f"{mem_per_thread}G"
        else:
            memory = "1G"

    return threads, memory


def get_sam_sort_cmd(
    out_file,
    threads,
    memory,
    fmt="BAM",
    reference=None,
    name_sort=False,
    temp_dir=None,
):
    """
    Returns a command list for sorting BAM/CRAM.
    Uses sambamba if available (except on macOS) and format is BAM, else samtools.
    """
    threads_val = int(threads)
    # Convert memory (e.g. "1G") to just "1" for calculation
    mem_val = int(memory.rstrip("GgMm"))
    is_gb = memory.lower().endswith("g")

    import platform

    is_macos = platform.system() == "Darwin"

    if shutil.which("sambamba") and fmt == "BAM" and not is_macos:
        # sambamba -m is TOTAL memory
        total_mem = mem_val * threads_val
        total_mem_str = f"{total_mem}G" if is_gb else f"{total_mem}M"
        cmd = [
            "sambamba",
            "sort",
            "-t",
            threads,
            "-m",
            total_mem_str,
            "-o",
            out_file,
            "/dev/stdin",
        ]
        if name_sort:
            cmd.insert(2, "-n")
        if temp_dir:
            cmd.insert(2, "--tmpdir")
            cmd.insert(3, temp_dir)
        return cmd
    else:
        # samtools sort -m is PER THREAD
        cmd = ["samtools", "sort", "-@", threads, "-m", memory, "-o", out_file]
        if name_sort:
            cmd.append("-n")
        if temp_dir:
            cmd += ["-T", temp_dir]
        if fmt == "CRAM":
            cmd += ["-O", "CRAM"]
            if reference:
                cmd += ["--reference", reference]
        elif fmt == "SAM":
            cmd += ["-O", "SAM"]
        else:
            cmd += ["-O", "BAM"]
        return cmd


def get_sam_index_cmd(file_path, threads="1"):
    """
    Returns a command list for indexing BAM/CRAM.
    Uses sambamba if available (except on macOS) and file is BAM, else samtools.
    """
    import platform

    is_macos = platform.system() == "Darwin"

    if shutil.which("sambamba") and file_path.lower().endswith(".bam") and not is_macos:
        return ["sambamba", "index", "-t", threads, file_path]
    else:
        return ["samtools", "index", file_path]


def get_sam_view_cmd(threads="1", fmt="BAM", reference=None, is_input_sam=False):
    """
    Returns a command list for viewing/converting BAM/CRAM.
    Uses sambamba if available (except on macOS) and fmt is BAM, else samtools.
    """
    import platform

    is_macos = platform.system() == "Darwin"

    if shutil.which("sambamba") and fmt == "BAM" and not reference and not is_macos:
        cmd = ["sambamba", "view", "-t", threads, "-f", "bam"]
        if is_input_sam:
            cmd += ["-S"]
        return cmd
    else:
        cmd = ["samtools", "view", "-@", threads]
        if fmt == "CRAM":
            cmd += ["-O", "CRAM"]
            if reference:
                cmd += ["-T", reference]
        elif fmt == "BAM":
            cmd += ["-b"]

        return cmd


class ReferenceLibrary:
    """Helper to manage and resolve reference genome paths."""

    def __init__(
        self, root_path, md5_sig=None, skip_full_search=False, input_path=None
    ):
        self.root = root_path
        self.md5 = md5_sig
        self.input_path = input_path
        self.fasta = None
        self.dict_file = None
        self.fai = None
        self.liftover_chain = None
        self.ref_vcf_tab = None
        self.clinvar_vcf = None
        self.revel_file = None
        self.phylop_file = None
        self.gnomad_vcf = None
        self.spliceai_vcf = None
        self.alphamissense_vcf = None
        self.pharmgkb_vcf = None
        self.ploidy_file = None
        self.vep_cache = None
        self.build = None

        if not root_path:
            return

        if os.path.isfile(root_path):
            self.fasta = root_path
            d = os.path.dirname(root_path)
            self.root = d
        else:
            d = root_path

        # Look for Fasta
        if not self.fasta:
            # Check direct directory and 'genomes' subdirectory
            for search_dir in [d, os.path.join(d, "genomes")]:
                if not os.path.isdir(search_dir):
                    continue
                for f in REF_GENOME_FILENAMES.values():
                    potential = os.path.join(search_dir, f)
                    if os.path.exists(potential):
                        self.fasta = potential
                        break
                if self.fasta:
                    break

        # Resolve associated files
        self.fai = self.fasta + ".fai" if self.fasta else None
        if self.fai and not os.path.exists(self.fai):
            self.fai = None

        # Build identification from MD5 (if provided)
        if self.md5:
            from wgsextract_cli.core.constants import REFERENCE_MODELS

            if self.md5 in REFERENCE_MODELS:
                self.build = REFERENCE_MODELS[self.md5][0]
                logging.debug(
                    f"ReferenceLibrary: Identified build as {self.build} from MD5"
                )
                # Normalize hs37d5 etc to hg19 for file lookups
                if self.build == "hs37d5":
                    self.build = "hg19"
                # Normalize hs38DH etc to hg38
                if self.build == "hs38DH":
                    self.build = "hg38"

        # Build identification from SN count (contig count) as fallback
        # Use input_path if provided, else root_path if it's a file
        target_for_header = (
            input_path
            if input_path
            else (root_path if os.path.isfile(root_path) else None)
        )
        if not self.build and target_for_header:
            if target_for_header.lower().endswith((".vcf", ".vcf.gz", ".bcf")):
                self.build = get_vcf_build(target_for_header)
                if self.build:
                    logging.debug(
                        f"ReferenceLibrary: Identified build as {self.build} from VCF header"
                    )

        if not self.build and target_for_header:
            try:
                header = get_bam_header(target_for_header)
                if header:
                    from wgsextract_cli.core.constants import REFGEN_BY_SNCOUNT

                    sq_lines = [
                        line for line in header.splitlines() if line.startswith("@SQ")
                    ]
                    sn_count = len(sq_lines)
                    logging.debug(f"ReferenceLibrary: Detected {sn_count} SQ lines")
                    if not sn_count:
                        # Try VCF contig count
                        sn_count = len(
                            [
                                line
                                for line in header.splitlines()
                                if line.startswith("##contig=")
                            ]
                        )
                        logging.debug(
                            f"ReferenceLibrary: Detected {sn_count} VCF contigs"
                        )

                    if sn_count in REFGEN_BY_SNCOUNT:
                        resolved_file = str(REFGEN_BY_SNCOUNT[sn_count][1]).lower()
                        if (
                            "37" in resolved_file
                            or "hg19" in resolved_file
                            or "hs37" in resolved_file
                        ):
                            self.build = "hg19"
                        elif (
                            "38" in resolved_file
                            or "hg38" in resolved_file
                            or "hs38" in resolved_file
                            or "grch38" in resolved_file
                        ):
                            self.build = "hg38"
                        else:
                            # Fallback to heuristics if filename is ambiguous
                            if sn_count > 190:
                                self.build = "hg38"
                            else:
                                self.build = "hg19"
                    elif sn_count > 190:  # Heuristic for hg38
                        self.build = "hg38"
                    elif sn_count > 80:  # Heuristic for hg19
                        self.build = "hg19"

                    logging.debug(
                        f"ReferenceLibrary: Identified build as {self.build} from SN count {sn_count}"
                    )
                else:
                    logging.debug(
                        f"ReferenceLibrary: No header retrieved from {target_for_header}"
                    )
            except Exception as e:
                logging.debug(f"ReferenceLibrary: Error reading header: {e}")

        # Build identification from path (fallback)
        if not self.build and self.fasta:
            f_lower = self.fasta.lower()
            if "hg38" in f_lower or "grch38" in f_lower:
                self.build = "hg38"
            elif "hg19" in f_lower or "grch37" in f_lower or "hs37d5" in f_lower:
                self.build = "hg19"

        if not self.build:
            if "hg38" in d.lower() or "grch38" in d.lower():
                self.build = "hg38"
            elif "hg19" in d.lower() or "grch37" in d.lower():
                self.build = "hg19"

        # Re-resolve FASTA if build was found from MD5/Header but path-based resolution found something else
        if self.build and self.fasta:
            f_lower = self.fasta.lower()
            is_hg38_path = "hg38" in f_lower or "grch38" in f_lower
            is_hg19_path = (
                "hg19" in f_lower or "grch37" in f_lower or "hs37d5" in f_lower
            )

            mismatch = (self.build == "hg38" and is_hg19_path) or (
                self.build == "hg19" and is_hg38_path
            )

            if mismatch:
                logging.debug(
                    f"Build mismatch detected (Build={self.build}, Path={f_lower}). Re-resolving FASTA..."
                )
                original_fasta = self.fasta
                self.fasta = None
                # Check direct directory and 'genomes' subdirectory for the CORRECT build
                for search_dir in [d, os.path.join(d, "genomes")]:
                    if not os.path.isdir(search_dir):
                        continue
                    # Prioritize genomes that match our build
                    for build_key, f_name in REF_GENOME_FILENAMES.items():
                        # We only want to match the target build (hg38 or hg19)
                        match_hg19 = self.build == "hg19" and (
                            "37" in build_key or "19" in build_key
                        )
                        match_hg38 = self.build == "hg38" and (
                            "38" in build_key or "hs38" in build_key
                        )

                        if match_hg19 or match_hg38:
                            potential = os.path.join(search_dir, f_name)
                            if os.path.exists(potential):
                                self.fasta = potential
                                break
                    if self.fasta:
                        break

                if not self.fasta:
                    logging.warning(
                        f"Could not find {self.build} genome, reverting to {original_fasta}"
                    )
                    self.fasta = original_fasta

        if not self.fasta:
            return

        # Look for .dict
        self.dict_file = (
            self.fasta.replace(".fa.gz", ".dict")
            .replace(".fasta.gz", ".dict")
            .replace(".fa", ".dict")
            .replace(".fasta", ".dict")
        )
        if not os.path.exists(self.dict_file):
            self.dict_file = None

        # Look for ploidy
        if self.build:
            for search_dir in [
                self.root,
                os.path.join(self.root, "ref"),
                os.path.join(self.root, "microarray"),
            ]:
                if not os.path.isdir(search_dir):
                    continue
                potential = os.path.join(search_dir, f"ploidy_{self.build}.txt")
                if os.path.exists(potential):
                    self.ploidy_file = potential
                    break
                # Generic name
                potential = os.path.join(search_dir, "ploidy.txt")
                if os.path.exists(potential):
                    self.ploidy_file = potential
                    break

        # Look for vep cache
        env_vep_cache = os.environ.get("WGSE_VEP_CACHE")
        if env_vep_cache and os.path.isdir(env_vep_cache):
            self.vep_cache = env_vep_cache
        else:
            for search_dir in [self.root, os.path.join(self.root, "vep")]:
                if os.path.isdir(search_dir) and any(
                    f.endswith("_GRCh38") or f.endswith("_GRCh37")
                    for f in os.listdir(search_dir)
                ):
                    self.vep_cache = search_dir
                    break
                vep_sub = os.path.join(search_dir, "vep")
                if os.path.isdir(vep_sub):
                    self.vep_cache = vep_sub
                    break

        if skip_full_search:
            return

        # Annotation VCFs / Microarray Tab files
        potential_vcf_names = ["All_SNPs.vcf.gz", "common_all.vcf.gz"]
        if self.build:
            # e.g. All_SNPs_hg38_ref.tab.gz
            build_suffix = self.build.lower()  # hg38 or hg19
            # GRCh38 mapping
            alt_build = (
                "grch38"
                if build_suffix == "hg38"
                else "grch37"
                if build_suffix == "hg19"
                else None
            )

            potential_vcf_names.extend(
                [
                    f"All_SNPs_{build_suffix}_ref.tab.gz",
                    f"All_SNPs_{build_suffix.upper()}_ref.tab.gz",
                    f"All_SNPs_GRCh{build_suffix[-2:]}_ref.tab.gz",
                    f"All_SNPs_grch{build_suffix[-2:]}_ref.tab.gz",
                ]
            )
            if alt_build:
                potential_vcf_names.extend(
                    [
                        f"All_SNPs_{alt_build.lower()}_ref.tab.gz",
                        f"All_SNPs_{alt_build.upper()}_ref.tab.gz",
                        f"All_SNPs_{alt_build.capitalize()}_ref.tab.gz",
                    ]
                )

        # Check in root, ref/, and microarray/ subdirectories, plus build-specific ones
        search_dirs = [
            self.root,
            os.path.join(self.root, "ref"),
            os.path.join(self.root, "microarray"),
        ]
        if self.build:
            search_dirs.extend(
                [
                    os.path.join(self.root, self.build),
                    os.path.join(self.root, "ref", self.build),
                    os.path.join(self.root, "microarray", self.build),
                ]
            )
            # Add alt build too
            if alt_build:
                search_dirs.extend(
                    [
                        os.path.join(self.root, alt_build),
                        os.path.join(self.root, "ref", alt_build),
                    ]
                )

        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for v in potential_vcf_names:
                potential = os.path.join(search_dir, v)
                if os.path.exists(potential):
                    self.ref_vcf_tab = potential
                    break
            if self.ref_vcf_tab:
                break

        # Look for ClinVar VCF
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                potential = os.path.join(search_dir, f"clinvar_{self.build}.vcf.gz")
                if os.path.exists(potential):
                    self.clinvar_vcf = potential
                    break
                # Fallback check for alternate build names (e.g. hg38 vs grch38)
                alt_names = ["hg38", "hg19", "grch38", "grch37"]
                for alt in alt_names:
                    # Only check if it's potentially compatible
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if is_hg38_alt or is_hg19_alt:
                        potential = os.path.join(search_dir, f"clinvar_{alt}.vcf.gz")
                        if os.path.exists(potential):
                            self.clinvar_vcf = potential
                            break
                if self.clinvar_vcf:
                    break

        # Look for REVEL data
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                # Support .tsv.gz or .vcf.gz
                found = False
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37"]:
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if not (is_hg38_alt or is_hg19_alt):
                        continue
                    for ext in [".tsv.gz", ".vcf.gz"]:
                        potential = os.path.join(search_dir, f"revel_{alt}{ext}")
                        if os.path.exists(potential):
                            self.revel_file = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for PhyloP data
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                found = False
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37"]:
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if not (is_hg38_alt or is_hg19_alt):
                        continue
                    for ext in [".tsv.gz", ".vcf.gz"]:
                        potential = os.path.join(search_dir, f"phylop_{alt}{ext}")
                        if os.path.exists(potential):
                            self.phylop_file = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for gnomAD VCF
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                found = False
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37"]:
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if not (is_hg38_alt or is_hg19_alt):
                        continue
                    # Support .vcf.bgz or .vcf.gz
                    for ext in [".vcf.bgz", ".vcf.gz"]:
                        potential = os.path.join(search_dir, f"gnomad_{alt}{ext}")
                        if os.path.exists(potential):
                            self.gnomad_vcf = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for SpliceAI VCF
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                found = False
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37"]:
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if not (is_hg38_alt or is_hg19_alt):
                        continue
                    for ext in [".vcf.gz", ".vcf.bgz"]:
                        potential = os.path.join(search_dir, f"spliceai_{alt}{ext}")
                        if os.path.exists(potential):
                            self.spliceai_vcf = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for AlphaMissense VCF
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                found = False
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37"]:
                    is_hg38_alt = self.build == "hg38" and (
                        alt == "hg38" or alt == "grch38"
                    )
                    is_hg19_alt = self.build == "hg19" and (
                        alt == "hg19" or alt == "grch37"
                    )
                    if not (is_hg38_alt or is_hg19_alt):
                        continue
                    for ext in [".vcf.gz", ".vcf.bgz"]:
                        potential = os.path.join(
                            search_dir, f"alphamissense_{alt}{ext}"
                        )
                        if os.path.exists(potential):
                            self.alphamissense_vcf = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for PharmGKB VCF
        if self.build:
            for search_dir in [self.root, os.path.join(self.root, "ref")]:
                if not os.path.isdir(search_dir):
                    continue
                found = False
                # PharmGKB is often build-independent or named simply pharmgkb.vcf.gz
                for alt in [self.build, "hg38", "hg19", "grch38", "grch37", ""]:
                    name = f"pharmgkb_{alt}" if alt else "pharmgkb"
                    for ext in [".vcf.gz", ".vcf.bgz", ".tsv.gz"]:
                        potential = os.path.join(search_dir, f"{name}{ext}")
                        if os.path.exists(potential):
                            self.pharmgkb_vcf = potential
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        # Look for Liftover Chain (hg38 -> hg19)
        if self.build == "hg38":
            for search_dir in [
                self.root,
                os.path.join(self.root, "ref"),
                os.path.join(self.root, "microarray"),
            ]:
                if not os.path.isdir(search_dir):
                    continue
                potential = os.path.join(search_dir, "hg38ToHg19.over.chain.gz")
                if os.path.exists(potential):
                    self.liftover_chain = potential
                    break


def resolve_reference(ref_path, md5_sig, input_path=None):
    """Find specific .fa.gz from directory or direct path."""
    lib = ReferenceLibrary(
        ref_path, md5_sig, skip_full_search=True, input_path=input_path
    )
    return lib.fasta if lib.fasta else ref_path


def calculate_bsd_sum(file_path):
    """
    Calculates BSD-style checksum and 1K block count.
    Used for local file comparison.
    """
    checksum = 0
    blocks = 0
    with open(file_path, "rb") as f:
        while chunk := f.read(1024):
            blocks += 1
            for byte in chunk:
                checksum = (checksum >> 1) + ((checksum & 1) << 15)
                checksum += byte
                checksum &= 0xFFFF
    return checksum, blocks


def popen(cmd, stdout=None, stderr=None, stdin=None, text=False, env=None):
    """
    Helper to run subprocess.Popen with shlex splitting and registry.
    Default text=False to allow binary pipes (BAM/BCF).
    """
    import shlex

    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = []
        for item in cmd:
            if isinstance(item, str) and ("pixi run" in item or " " in item):
                if item == cmd[0]:
                    cmd_list.extend(shlex.split(item))
                else:
                    cmd_list.append(item)
            else:
                cmd_list.append(item)

    cmd_str = " ".join(cmd_list)
    logging.debug(f"Popen: {cmd_str}")

    process = subprocess.Popen(
        cmd_list, stdout=stdout, stderr=stderr, stdin=stdin, text=text, env=env
    )
    proc_registry.register_process(cmd_str, process)
    return process


def run_command(cmd, capture_output=False, check=True, env=None):
    """Helper to run subprocess with logging and registry."""
    import shlex

    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = []
        for item in cmd:
            if isinstance(item, str) and ("pixi run" in item or " " in item):
                if item == cmd[0]:
                    cmd_list.extend(shlex.split(item))
                else:
                    cmd_list.append(item)
            else:
                cmd_list.append(item)

    cmd_str = " ".join(cmd_list)
    logging.debug(f"Running: {cmd_str}")

    process = subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        text=True,
        env=env,
    )

    proc_registry.register_process(cmd_str, process)
    try:
        stdout, stderr = process.communicate()
        if check and process.returncode != 0:
            logging.error(f"Command failed: {cmd_str}")
            if stderr:
                logging.error(stderr)
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
        return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    finally:
        proc_registry.unregister_process(cmd_str)


def verify_paths_exist(paths_dict):
    """Validate that required files exist before starting a command."""
    all_exist = True
    for label, path in paths_dict.items():
        if not path:
            logging.error(LOG_MESSAGES["file_not_found"].format(label=label, path=path))
            all_exist = False
            continue

        # Skip check for commands (like pixi run)
        if "pixi run" in str(path):
            continue

        if not os.path.exists(str(path)) and not shutil.which(str(path)):
            logging.error(LOG_MESSAGES["file_not_found"].format(label=label, path=path))
            all_exist = False
        elif os.path.isdir(str(path)) and not shutil.which(str(path)):
            logging.error(
                f"{label} path is a directory, but a file is expected: {path}"
            )
            all_exist = False
    return all_exist


def ensure_vcf_indexed(vcf_path):
    """Ensure VCF has a .tbi index, creating it if needed."""
    if not (vcf_path.endswith(".gz") or vcf_path.endswith(".bgz")):
        # We can't index plain VCF easily with tabix
        return

    index_path = vcf_path + ".tbi"
    if not os.path.exists(index_path):
        from wgsextract_cli.core.dependencies import get_tool_path

        tabix = get_tool_path("tabix")
        logging.info(LOG_MESSAGES["vcf_indexing"].format(path=vcf_path))
        run_command([tabix, "-p", "vcf", vcf_path])


def ensure_vcf_prepared(vcf_path):
    """Ensure VCF is bgzipped and indexed, returns path to compressed file."""
    if not vcf_path:
        return vcf_path

    # If it's a BAM or CRAM, don't try to prepare it as a VCF
    if vcf_path.lower().endswith((".bam", ".cram")):
        return vcf_path

    if vcf_path.endswith(".gz") or vcf_path.endswith(".bgz"):
        ensure_vcf_indexed(vcf_path)
        return vcf_path

    # Need to bgzip
    gz_path = vcf_path + ".gz"
    if os.path.exists(gz_path):
        # Check if gz is newer than raw
        if os.path.getmtime(gz_path) > os.path.getmtime(vcf_path):
            ensure_vcf_indexed(gz_path)
            return gz_path

    from wgsextract_cli.core.dependencies import get_tool_path

    bgzip = get_tool_path("bgzip")
    logging.info(f"Compressing VCF: {vcf_path}")
    with open(gz_path, "wb") as f_out:
        import shlex

        subprocess.run(shlex.split(bgzip) + ["-c", vcf_path], stdout=f_out, check=True)
    ensure_vcf_indexed(gz_path)
    return gz_path


def get_vcf_samples(vcf_path):
    """Retrieve sample names from VCF header."""
    try:
        res = subprocess.run(
            ["bcftools", "query", "-l", vcf_path], capture_output=True, text=True
        )
        return res.stdout.strip().split("\n")
    except Exception:
        return []


def normalize_vcf_chromosomes(vcf_path, target_chroms):
    """
    Ensure VCF chromosome naming (chr1 vs 1) matches the targets.
    Returns path to a temporary normalized VCF if changes were needed.
    """
    v_chroms = []
    try:
        res = subprocess.run(
            ["bcftools", "index", "-s", vcf_path], capture_output=True, text=True
        )
        v_chroms = [l.split("\t")[0] for l in res.stdout.strip().split("\n")]
    except Exception:
        return vcf_path

    needs_rename = False
    mapping = []

    # Check for mismatches
    for tc in target_chroms:
        # Simple match
        if tc in v_chroms:
            continue

        # Try prefix mismatch
        if tc.startswith("chr"):
            alt = tc[3:]
        else:
            alt = "chr" + tc

        if alt in v_chroms:
            needs_rename = True
            mapping.append(f"{alt} {tc}")

    if not needs_rename:
        return vcf_path

    # Create mapping file
    fd, map_file = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(mapping))

    # Use a unique temporary file for the normalized VCF to avoid collisions
    fd_out, norm_vcf = tempfile.mkstemp(suffix=".vcf.gz", dir=os.path.dirname(vcf_path))
    os.close(fd_out)

    logging.info(f"Normalizing chromosomes in {vcf_path}...")
    try:
        from wgsextract_cli.core.dependencies import get_tool_path

        bcftools = get_tool_path("bcftools")
        run_command(
            [
                bcftools,
                "annotate",
                "--rename-chrs",
                map_file,
                "-Oz",
                "-o",
                norm_vcf,
                vcf_path,
            ]
        )
        ensure_vcf_indexed(norm_vcf)
        os.remove(map_file)
        return norm_vcf
    except Exception as e:
        logging.error(f"Normalization failed: {e}")
        if os.path.exists(map_file):
            os.remove(map_file)
        if os.path.exists(norm_vcf):
            os.remove(norm_vcf)
        return vcf_path


def get_bam_header(bam_path, cram_opt=None):
    """Retrieve header using samtools view -H."""
    from wgsextract_cli.core.dependencies import get_tool_path

    is_cram = bam_path.lower().endswith(".cram")
    is_vcf = bam_path.lower().endswith((".vcf", ".vcf.gz", ".bgz", ".bcf"))

    if is_vcf:
        try:
            bcftools = get_tool_path("bcftools")
            cmd = [bcftools, "view", "-h", bam_path]
            # Execute without check=True to avoid printing red error logs if it fails
            result = run_command(cmd, capture_output=True, check=False)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return ""

    samtools = get_tool_path("samtools")
    cmd = [samtools, "view", "-H"]

    if is_cram and cram_opt:
        if isinstance(cram_opt, list):
            cmd.extend(cram_opt)
        elif os.path.isfile(cram_opt):
            cmd.extend(["-T", cram_opt])
        else:
            # Maybe it's a directory, samtools -T needs a file.
            cmd.extend(["-T", cram_opt])

    cmd.append(bam_path)

    try:
        result = run_command(cmd, capture_output=True)
        return result.stdout
    except Exception as e:
        # Attempt 2: Try bcftools view -h (often more robust for CRAM)
        try:
            logging.debug("Header fetch with samtools failed, trying bcftools...")
            bcftools = get_tool_path("bcftools")
            bcftools_cmd = [bcftools, "view", "-h", bam_path]
            result = run_command(bcftools_cmd, capture_output=True)
            return result.stdout
        except Exception:
            pass

        # Attempt 3: If it's a CRAM and we had a reference, try WITHOUT it.
        if is_cram:
            try:
                logging.debug(LOG_MESSAGES["util_header_retry"])
                result = run_command(
                    [samtools, "view", "-H", bam_path], capture_output=True
                )
                return result.stdout
            except Exception:
                pass

        logging.error(LOG_MESSAGES["util_header_failed"].format(path=bam_path, error=e))
        return ""


def get_chr_name(bam_path, target_chr, cram_opt=None):
    """
    Dynamically map a target chromosome (like MT or Y) to the specific
    naming convention used in the BAM header (e.g., chrM, MT, M, chrY).
    """
    header = get_bam_header(bam_path, cram_opt)
    sq_lines = [line for line in header.splitlines() if line.startswith("@SQ")]

    # Extract SN fields
    sn_names = []
    for line in sq_lines:
        parts = line.split("\t")
        for part in parts:
            if part.startswith("SN:"):
                sn_names.append(part[3:])
                break

    if target_chr.upper() in ["M", "MT", "CHRM", "CHRMT"]:
        for c in ["chrM", "chrMT", "MT", "M"]:
            if c in sn_names:
                return c
    elif target_chr.upper() in ["Y", "CHRY"]:
        for c in ["chrY", "Y"]:
            if c in sn_names:
                return c

    return target_chr  # fallback


def calculate_bam_md5(bam_path, cram_opt=None, header=None):
    """
    Calculates MD5 signature from BAM header @SQ lines.
    It takes SN and LN, upcases SN, sorts ASCII-wise, and hashes.
    If a @CO line with MD5: exists, it returns that instead.
    """
    if header is None:
        header = get_bam_header(bam_path, cram_opt)
    if not header:
        return "00000000000000000000000000000000"

    # Check for embedded MD5 signature in comments or read groups first
    for line in header.splitlines():
        if (line.startswith("@CO") or line.startswith("@RG")) and "MD5:" in line:
            parts = line.split("MD5:")
            if len(parts) > 1:
                sig = parts[1].strip().split()[0]
                if len(sig) == 32:
                    return sig

    sq_lines = [line for line in header.splitlines() if line.startswith("@SQ")]

    bamsq_header = {}
    for line in sq_lines:
        sn = None
        ln = None
        for part in line.split("\t"):
            if part.startswith("SN:"):
                sn = part[3:].upper()
            elif part.startswith("LN:"):
                ln = part[3:]
        if sn and ln:
            bamsq_header[sn] = ln

    pseudo_header = ""
    for key in sorted(bamsq_header.keys()):
        pseudo_header += f"SN:{key}\tLN:{bamsq_header[key]}\n"

    md5hash = hashlib.md5(pseudo_header.encode())
    return md5hash.hexdigest()


def is_sorted(bam_path, cram_opt=None, header=None):
    """Verifies if BAM is coordinate sorted."""
    if header is None:
        header = get_bam_header(bam_path, cram_opt)
    if not header:
        return False
    for line in header.splitlines():
        if line.startswith("@HD"):
            if "SO:coordinate" in line:
                return True
    return False


def get_ref_mito(bam_path, cram_opt=None, header=None):
    """
    Identifies if mitochondrial reference is Yoruba based on chromosome lengths.
    Logic from program/bamfiles.py.
    """
    if header is None:
        header = get_bam_header(bam_path, cram_opt)
    if not header:
        return "rCRS"

    # Check for Build 37 with Yoruba length (16571)
    is_build37 = any(
        x in header for x in ["LN:249250621", "LN:59373566", "LN:155270560"]
    )
    if is_build37 and any(x in header for x in ["M\tLN:16571", "MT\tLN:16571"]):
        return "Yoruba"

    # Check for other Yoruba builds (15, 16, 17, 18)
    if any(x in header for x in ["LN:247249719", "LN:57772954", "LN:154913754"]):
        return "Yoruba"  # Build 18
    if any(x in header for x in ["LN:245522847", "LN:57701691", "LN:154824264"]):
        return "Yoruba"  # Build 17
    if any(x in header for x in ["LN:246127941", "LN:50286555", "LN:153692391"]):
        return "Yoruba"  # Build 16
    if any(x in header for x in ["LN:245203898", "LN:50961097", "LN:152634166"]):
        return "Yoruba"  # Build 15

    return "rCRS"  # Default


def get_file_version(filepath: str) -> str:
    """Retrieve the format and version of a genomic file using htsfile."""
    try:
        res = subprocess.run(["htsfile", filepath], capture_output=True, text=True)
        if res.returncode == 0:
            # Output format: "path: Format version X sequence data"
            # e.g., "file.cram: CRAM version 3.1 sequence data"
            out = res.stdout.strip()
            if ":" in out:
                version_info = out.split(":", 1)[1].strip()
                # Clean up "sequence data" suffix if present
                version_info = version_info.replace(" sequence data", "")
                return version_info
    except Exception:
        pass
    return "Unknown"


def is_long_read(bam_path, cram_opt=None, header=None):
    """
    Rough heuristic to detect long-read data (e.g. Nanopore) from BAM header.
    In the original app, it checks if read length > 500.
    """
    if header is None:
        header = get_bam_header(bam_path, cram_opt)
    if not header:
        return False
    if "PL:ONT" in header or "PL:PACBIO" in header:
        return True
    return False


def get_vcf_build(vcf_path):
    """Scan VCF header for build identifiers."""
    try:
        from wgsextract_cli.core.dependencies import get_tool_path

        bcftools = get_tool_path("bcftools")
        import shlex

        cmd = shlex.split(bcftools) + ["view", "-h", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        header = res.stdout.lower()
        if "hg38" in header or "grch38" in header:
            return "hg38"
        if "hg19" in header or "grch37" in header:
            return "hg19"
    except Exception:
        pass
    return None


def get_vcf_chr_name(vcf_path, target_chr):
    """Map standard chromosome to VCF-specific naming."""
    try:
        from wgsextract_cli.core.dependencies import get_tool_path

        bcftools = get_tool_path("bcftools")
        import shlex

        cmd = shlex.split(bcftools) + ["index", "-s", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        v_chroms = [l.split("\t")[0] for l in res.stdout.strip().split("\n")]

        if target_chr.upper() in ["M", "MT", "CHRM", "CHRMT"]:
            for c in ["chrM", "chrMT", "MT", "M"]:
                if c in v_chroms:
                    return c
        elif target_chr.upper() in ["Y", "CHRY"]:
            for c in ["chrY", "Y"]:
                if c in v_chroms:
                    return c
    except Exception:
        pass
    return target_chr


def get_region_bed(region_str):
    """
    Converts a region string (chr:start-end) to a temporary BED file.
    Returns the path to the temporary file.
    """
    if not region_str:
        return None

    chrom = region_str
    start = 0
    end = 500000000  # Large default

    if ":" in region_str:
        chrom, coords = region_str.split(":")
        if "-" in coords:
            start_s, end_s = coords.split("-")
            start = int(start_s)
            end = int(end_s)
        else:
            try:
                start = int(coords)
                end = start + 1
            except ValueError:
                # Could be just a chrom name that happens to have a colon?
                # Unlikely in bio, but let's be safe.
                pass

    fd, path = tempfile.mkstemp(suffix=".bed")
    with os.fdopen(fd, "w") as f:
        f.write(f"{chrom}\t{max(0, start - 1)}\t{end}\n")
    return path
