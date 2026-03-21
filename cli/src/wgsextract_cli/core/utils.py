import hashlib
import logging
import os
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

            logging.info(
                f"Cleanup: Terminating {len(self.processes)} active processes..."
            )

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


class ReferenceLibrary:
    """Helper to manage and resolve reference genome paths."""

    def __init__(self, root_path, md5_sig=None, skip_full_search=False):
        self.root = root_path
        self.md5 = md5_sig
        self.fasta = None
        self.dict_file = None
        self.fai = None
        self.liftover_chain = None
        self.ref_vcf_tab = None
        self.ploidy_file = None
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
            for f in REF_GENOME_FILENAMES:
                potential = os.path.join(d, f)
                if os.path.exists(potential):
                    self.fasta = potential
                    break

        if not self.fasta:
            return

        # Resolve associated files
        self.fai = self.fasta + ".fai"
        if not os.path.exists(self.fai):
            self.fai = None

        # Build identification from path
        if "hg38" in d.lower() or "grch38" in d.lower():
            self.build = "hg38"
        elif "hg19" in d.lower() or "grch37" in d.lower():
            self.build = "hg19"

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
            ploidy_name = f"ploidy_{self.build}.txt"
            potential = os.path.join(d, ploidy_name)
            if os.path.exists(potential):
                self.ploidy_file = potential

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

        for v in potential_vcf_names:
            # Check same dir as fasta
            potential = os.path.join(d, v)
            if os.path.exists(potential):
                self.ref_vcf_tab = potential
                break
            # Check microarray subfolder
            potential = os.path.join(self.root, "microarray", v)
            if os.path.exists(potential):
                self.ref_vcf_tab = potential
                break


def resolve_reference(ref_path, md5_sig):
    """Find specific .fa.gz from directory or direct path."""
    lib = ReferenceLibrary(ref_path, md5_sig, skip_full_search=True)
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


def run_command(cmd, capture_output=False, check=True, env=None):
    """Helper to run subprocess with logging and registry."""
    cmd_str = " ".join(cmd)
    logging.debug(f"Running: {cmd_str}")

    process = subprocess.Popen(
        cmd,
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
        if not path or not os.path.exists(path):
            logging.error(LOG_MESSAGES["file_not_found"].format(label=label, path=path))
            all_exist = False
    return all_exist


def ensure_vcf_indexed(vcf_path):
    """Ensure VCF has a .tbi index, creating it if needed."""
    if not vcf_path.endswith(".gz"):
        # We can't index plain VCF easily with tabix
        return

    index_path = vcf_path + ".tbi"
    if not os.path.exists(index_path):
        logging.info(LOG_MESSAGES["vcf_indexing"].format(path=vcf_path))
        subprocess.run(["tabix", "-p", "vcf", vcf_path], check=True)


def ensure_vcf_prepared(vcf_path):
    """Ensure VCF is bgzipped and indexed, returns path to .gz file."""
    if vcf_path.endswith(".gz"):
        ensure_vcf_indexed(vcf_path)
        return vcf_path

    # Need to bgzip
    gz_path = vcf_path + ".gz"
    if os.path.exists(gz_path):
        # Check if gz is newer than raw
        if os.path.getmtime(gz_path) > os.path.getmtime(vcf_path):
            ensure_vcf_indexed(gz_path)
            return gz_path

    logging.info(f"Compressing VCF: {vcf_path}")
    subprocess.run(["bgzip", "-c", vcf_path], stdout=open(gz_path, "wb"), check=True)
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

    norm_vcf = vcf_path.replace(".vcf.gz", ".norm.vcf.gz")
    if norm_vcf == vcf_path:
        norm_vcf += ".norm.gz"

    logging.info(f"Normalizing chromosomes in {vcf_path}...")
    try:
        subprocess.run(
            [
                "bcftools",
                "annotate",
                "--rename-chrs",
                map_file,
                "-Oz",
                "-o",
                norm_vcf,
                vcf_path,
            ],
            check=True,
        )
        ensure_vcf_indexed(norm_vcf)
        os.remove(map_file)
        return norm_vcf
    except Exception as e:
        logging.error(f"Normalization failed: {e}")
        if os.path.exists(map_file):
            os.remove(map_file)
        return vcf_path


def get_bam_header(bam_path, cram_opt=None):
    """Retrieve header using samtools view -H."""
    cmd = ["samtools", "view", "-H"]
    is_cram = bam_path.lower().endswith(".cram")

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
            bcftools_cmd = ["bcftools", "view", "-h", bam_path]
            result = run_command(bcftools_cmd, capture_output=True)
            return result.stdout
        except Exception:
            pass

        # Attempt 3: If it's a CRAM and we had a reference, try WITHOUT it.
        if is_cram:
            try:
                logging.debug(LOG_MESSAGES["util_header_retry"])
                result = run_command(
                    ["samtools", "view", "-H", bam_path], capture_output=True
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
        res = subprocess.run(
            ["bcftools", "view", "-h", vcf_path], capture_output=True, text=True
        )
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
        res = subprocess.run(
            ["bcftools", "index", "-s", vcf_path], capture_output=True, text=True
        )
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
