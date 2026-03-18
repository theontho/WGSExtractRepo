import hashlib
import logging
import os
import subprocess

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
        self.ploidy_file = None
        self.ref_vcf_tab = None
        self.build = None
        self.vep_cache = None

        if root_path and os.path.isdir(root_path):
            self.vep_cache = os.path.join(root_path, "vep")
            self._resolve(skip_full_search)
        elif root_path and os.path.isfile(root_path):
            self.fasta = root_path
            self._resolve_sidecars(root_path)

    def _resolve(self, skip_full_search):
        # 1. Try known filenames for this MD5
        if self.md5 and self.md5 in REF_GENOME_FILENAMES:
            for fname in REF_GENOME_FILENAMES[self.md5]:
                path = os.path.join(self.root, "genomes", fname)
                if os.path.exists(path):
                    self.fasta = path
                    self._resolve_sidecars(path)
                    return

        # 2. If skip_full_search is True, don't walk the directory
        if skip_full_search:
            return

        # 3. Fallback: Search for any .fa/.fasta/.fna file
        for d, _, files in os.walk(self.root):
            for f in files:
                if f.endswith(
                    (".fa", ".fasta", ".fna", ".fa.gz", ".fasta.gz", ".fna.gz")
                ):
                    path = os.path.join(d, f)
                    self.fasta = path
                    self._resolve_sidecars(path)
                    return

    def _resolve_sidecars(self, fasta_path):
        base = os.path.splitext(fasta_path)[0]
        if base.endswith(".fa") or base.endswith(".fasta") or base.endswith(".fna"):
            base = os.path.splitext(base)[0]

        for ext in [".dict", ".fna.dict", ".fa.dict", ".fasta.dict"]:
            if os.path.exists(base + ext):
                self.dict_file = base + ext
                break

        if os.path.exists(fasta_path + ".fai"):
            self.fai = fasta_path + ".fai"

        # Look for chain files in root or same dir
        d = os.path.dirname(fasta_path)
        for c in ["hg38ToHg19.over.chain.gz", "GRCh38ToGRCh37.over.chain.gz"]:
            potential = os.path.join(d, c)
            if os.path.exists(potential):
                self.liftover_chain = potential
                break

        # Ploidy files
        for p in ["ploidy.txt", "ploidy"]:
            potential = os.path.join(d, p)
            if os.path.exists(potential):
                self.ploidy_file = potential
                break

        # Annotation VCFs
        for v in ["All_SNPs.vcf.gz", "common_all.vcf.gz"]:
            potential = os.path.join(d, v)
            if os.path.exists(potential):
                self.ref_vcf_tab = potential
                break

        # Deduce build
        bn = os.path.basename(fasta_path).upper()
        if "38" in bn or "HG38" in bn or "GRCH38" in bn:
            self.build = "hg38"
        elif "37" in bn or "HG19" in bn or "GRCH37" in bn:
            self.build = "hg19"
        elif "DOG" in bn:
            self.build = "dog"
        elif "CAT" in bn:
            self.build = "cat"


def resolve_reference(ref_path, md5_sig):
    """Find specific .fa.gz from directory or direct path."""
    lib = ReferenceLibrary(ref_path, md5_sig, skip_full_search=True)
    return lib.fasta if lib.fasta else ref_path


def calculate_bsd_sum(file_path):
    """
    Calculates BSD-style checksum and 1K block count.
    Matches the 'sum' command (without -s) on many systems and Ensembl CHECKSUMS.
    """
    checksum = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            for byte in chunk:
                checksum = (checksum >> 1) + ((checksum & 1) << 15)
                checksum += byte
                checksum &= 0xFFFF

    size = os.path.getsize(file_path)
    blocks = (size + 1023) // 1024
    return checksum, blocks


def verify_paths_exist(paths_dict):
    """
    Verify that multiple paths exist and are files.
    paths_dict: { '--arg-name': 'path/to/file' }
    """
    for arg, path in paths_dict.items():
        if path:
            if not os.path.exists(path):
                logging.error(
                    LOG_MESSAGES["util_required_file_not_found"].format(
                        arg=arg, path=path
                    )
                )
                return False
            if os.path.isdir(path):
                logging.error(
                    LOG_MESSAGES["util_required_file_is_dir"].format(arg=arg, path=path)
                )
                return False
    return True


def run_command(cmd_list, capture_output=False, check=True, **kwargs):
    """Run a command securely via subprocess."""
    try:
        return subprocess.run(
            cmd_list, capture_output=capture_output, text=True, check=check, **kwargs
        )
    except subprocess.CalledProcessError as e:
        logging.error(
            LOG_MESSAGES["util_command_failed"].format(command=" ".join(cmd_list))
        )
        if e.stderr:
            logging.error(e.stderr)
        raise


def ensure_vcf_indexed(vcf_path):
    """
    Checks if a VCF/BCF file is indexed (.tbi or .csi).
    If not, and the file is bgzipped, it creates the index automatically.
    """
    if not vcf_path or not os.path.exists(vcf_path):
        return False

    # Standard index extensions
    indices = [vcf_path + ".tbi", vcf_path + ".csi"]
    if vcf_path.endswith(".gz"):
        indices.append(vcf_path[:-3] + ".tbi")
        indices.append(vcf_path[:-3] + ".csi")

    if any(os.path.exists(i) for i in indices):
        return True

    # Check if bgzipped (magic bytes 1f 8b 08)
    is_bgzipped = False
    try:
        with open(vcf_path, "rb") as f:
            header = f.read(3)
            if header == b"\x1f\x8b\x08":
                is_bgzipped = True
    except Exception:
        pass

    if is_bgzipped:
        logging.info(LOG_MESSAGES["util_auto_indexing_vcf"].format(path=vcf_path))
        try:
            # Try tbi first, fall back to csi if needed (csi supports larger chromosomes)
            subprocess.run(["tabix", "-p", "vcf", vcf_path], check=True)
            return True
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["bcftools", "index", vcf_path], check=True)
                return True
            except Exception as e:
                logging.warning(
                    LOG_MESSAGES["util_auto_indexing_failed"].format(
                        path=vcf_path, error=e
                    )
                )
    else:
        logging.debug(LOG_MESSAGES["util_skipping_auto_index"].format(path=vcf_path))

    return False


def ensure_vcf_prepared(vcf_path: str) -> str:
    """
    Ensures a VCF is bgzipped and indexed.
    Returns the path to the usable (bgzipped) VCF file.
    """
    if not vcf_path or not os.path.exists(vcf_path):
        return vcf_path

    # Check if already bgzipped
    is_bgzipped = False
    try:
        with open(vcf_path, "rb") as f:
            header = f.read(3)
            if header == b"\x1f\x8b\x08":
                is_bgzipped = True
    except Exception:
        pass

    usable_path = vcf_path
    if not is_bgzipped:
        # If it's a plain VCF, we need to bgzip it
        if vcf_path.lower().endswith(".vcf"):
            bgzipped_path = vcf_path + ".gz"
            if not os.path.exists(bgzipped_path):
                logging.info(f"ℹ️: Bgzipping {vcf_path}...")
                try:
                    subprocess.run(
                        ["bgzip", "-c", vcf_path],
                        stdout=open(bgzipped_path, "wb"),
                        check=True,
                    )
                except Exception as e:
                    logging.error(f"❌: Failed to bgzip VCF: {e}")
                    return vcf_path
            usable_path = bgzipped_path
        else:
            # Not a .vcf extension and not bgzipped? Might be a problem, but let's try to index anyway
            pass

    # Ensure it's indexed
    ensure_vcf_indexed(usable_path)
    return usable_path


def get_vcf_samples(vcf_path: str) -> list[str]:
    """Returns a list of sample names in the VCF file."""
    try:
        result = subprocess.run(
            ["bcftools", "query", "-l", vcf_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n")
    except Exception as e:
        logging.debug(f"Failed to get samples from {vcf_path}: {e}")
        return []


def get_vcf_chr_name(vcf_path, target_chr):
    """
    Identifies the chromosome name used in a VCF for a target (MT or Y).
    """
    try:
        result = subprocess.run(
            ["bcftools", "index", "-s", vcf_path],
            capture_output=True,
            text=True,
            check=True,
        )
        vcf_chroms = [line.split("\t")[0] for line in result.stdout.strip().split("\n")]
    except Exception:
        return target_chr

    if target_chr.upper() in ["M", "MT", "CHRM", "CHRMT"]:
        for c in ["chrM", "chrMT", "MT", "M"]:
            if c in vcf_chroms:
                return c
    elif target_chr.upper() in ["Y", "CHRY"]:
        for c in ["chrY", "Y"]:
            if c in vcf_chroms:
                return c

    return target_chr


def get_vcf_build(vcf_path):
    """Detects genome build (hg19/hg38) from VCF header."""
    try:
        res = subprocess.run(
            ["bcftools", "view", "-h", vcf_path], capture_output=True, text=True
        )
        header = res.stdout.upper()
        if "38" in header or "HG38" in header or "GRCH38" in header:
            return "hg38"
        if "37" in header or "HG19" in header or "GRCH37" in header:
            return "hg19"
    except Exception:
        pass
    return None


def normalize_vcf_chromosomes(vcf_path: str, target_chroms: list[str]) -> str:
    """
    Checks if VCF chromosomes match target_chroms style (e.g., '1' vs 'chr1').
    If not, creates a temporary normalized VCF and returns its path.
    Otherwise returns original path.
    """
    try:
        # Get first few chroms to check style
        result = subprocess.run(
            ["bcftools", "index", "-s", vcf_path],
            capture_output=True,
            text=True,
            check=True,
        )
        vcf_chroms = [line.split("\t")[0] for line in result.stdout.strip().split("\n")]
    except Exception:
        return vcf_path

    vcf_has_chr = any(c.startswith("chr") for c in vcf_chroms)
    target_has_chr = any(c.startswith("chr") for c in target_chroms)

    if vcf_has_chr == target_has_chr:
        return vcf_path

    # Need normalization
    import tempfile

    fd, map_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            for i in range(1, 23):
                if target_has_chr:
                    f.write(f"{i} chr{i}\n")
                else:
                    f.write(f"chr{i} {i}\n")
            if target_has_chr:
                f.write("X chrX\nY chrY\nMT chrM\nM chrM\n")
            else:
                f.write("chrX X\nchrY Y\nchrM MT\nchrMT MT\n")

        out_vcf = vcf_path.replace(".vcf.gz", ".norm.vcf.gz")
        if out_vcf == vcf_path:
            out_vcf = vcf_path + ".norm.vcf.gz"

        logging.info(f"ℹ️: Normalizing chromosomes for {os.path.basename(vcf_path)}...")
        subprocess.run(
            [
                "bcftools",
                "annotate",
                "--rename-chrs",
                map_path,
                "-Oz",
                "-o",
                out_vcf,
                vcf_path,
            ],
            check=True,
        )
        subprocess.run(["bcftools", "index", out_vcf], check=True)
        return out_vcf
    finally:
        if os.path.exists(map_path):
            os.remove(map_path)


def get_bam_header(bam_path, cram_opt=None):
    """Fetch BAM/CRAM header using samtools view -H."""
    if not bam_path or not os.path.exists(bam_path):
        return ""

    if not bam_path.lower().endswith((".bam", ".cram")):
        return ""

    # Attempt 1: As provided
    if cram_opt is None:
        cram_opt = []
    cmd = ["samtools", "view", "-H"]
    if cram_opt:
        if isinstance(cram_opt, list):
            cmd.extend(cram_opt)
        else:
            cmd.extend(["-T", cram_opt])
    cmd.append(bam_path)

    try:
        result = run_command(cmd, capture_output=True)
        return result.stdout
    except Exception as e:
        # Attempt 2: If it's a CRAM and we had a reference, try WITHOUT it.
        # Sometimes samtools fails on CRAM header even with -T if the ref is a dir or wrong.
        # But often the header can be read without -T.
        if bam_path.lower().endswith(".cram") and cram_opt:
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
    """
    if header is None:
        header = get_bam_header(bam_path, cram_opt)
    if not header:
        return "00000000000000000000000000000000"

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
