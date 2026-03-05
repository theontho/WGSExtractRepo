import hashlib
import logging
import os
import subprocess

from wgsextract_cli.core.constants import REF_GENOME_FILENAMES, REFERENCE_MODELS

try:
    import psutil
except ImportError:
    psutil = None


def get_resource_defaults(threads_arg=None, memory_arg=None, mode="per_thread"):
    """
    Calculates default threads and memory based on system resources.

    Args:
        threads_arg: User-provided thread count
        memory_arg: User-provided memory string (e.g., '2G')
        mode: 'per_thread' (default for samtools sort -m) or 'total'

    Returns: (threads: str, memory: str)
    """
    # Calculate threads
    if threads_arg:
        threads_val = int(threads_arg)
    else:
        # Default to 75% of available CPU cores, minimum 1
        cpu_count = os.cpu_count() or 1
        threads_val = max(1, int(cpu_count * 0.75))

    threads = str(threads_val)

    # Calculate memory
    if memory_arg:
        memory = memory_arg
    else:
        # Default fallback
        memory = "2G"
        if psutil:
            try:
                # Default to safe fraction of available RAM, formatted as "XG" or "XM"
                total_ram_gb = psutil.virtual_memory().total / (1024**3)
                available_ram_gb = psutil.virtual_memory().available / (1024**3)

                # Total safe memory for the app (e.g., 50% of total or 80% of available)
                total_safe_gb = min(available_ram_gb * 0.8, total_ram_gb * 0.5)

                if mode == "per_thread":
                    # Divide total safe memory by threads for tools like samtools sort -m
                    per_thread_gb = total_safe_gb / threads_val
                    if per_thread_gb >= 1:
                        memory = f"{int(per_thread_gb)}G"
                    else:
                        per_thread_mb = max(256, int(per_thread_gb * 1024))
                        memory = f"{per_thread_mb}M"
                else:
                    # Return total safe memory
                    memory = f"{max(2, int(total_safe_gb))}G"
            except Exception:
                pass  # Use "2G" fallback

    return threads, memory


class ReferenceLibrary:
    """
    Handles automatic resolution of various reference files based on
    the provided reference directory or file path.
    """

    def __init__(self, ref_path, md5_sig=None):
        self.root = ref_path
        self.md5 = md5_sig
        self.fasta = None
        self.ploidy_file = None
        self.ref_vcf_tab = None
        self.wes_bed = None
        self.ymt_bed = None
        self.cma_dir = None
        self.vep_cache = None
        self.liftover_chain = None
        self.dict_file = None
        self.build = None

        if not ref_path:
            return

        if os.path.isfile(ref_path):
            if ref_path.lower().endswith((".fa", ".fasta", ".fa.gz", ".fasta.gz")):
                self.fasta = ref_path
                potential_dict = (
                    ref_path.replace(".fa.gz", ".dict")
                    .replace(".fasta.gz", ".dict")
                    .replace(".fa", ".dict")
                    .replace(".fasta", ".dict")
                )
                if os.path.exists(potential_dict):
                    self.dict_file = potential_dict
            self._search_dir(os.path.dirname(ref_path))

        if os.path.isdir(ref_path):
            # Search specialized subdirectories FIRST
            for sub in ["microarray", "genomes", "genome", "ref", "vep"]:
                self._search_dir(os.path.join(ref_path, sub))

            # Then search the root directory
            self._search_dir(ref_path)

            # If we are inside 'genomes' or 'genome', also search the parent and its siblings
            # to handle cases where --ref points directly to the genomes folder.
            base_dir = ref_path.rstrip(os.sep)
            if os.path.basename(base_dir) in ["genomes", "genome"]:
                parent = os.path.dirname(base_dir)
                self._search_dir(parent)
                for sub in ["genome", "genomes", "microarray", "ref", "vep"]:
                    self._search_dir(os.path.join(parent, sub))

        # If we found a fasta, try to deduce the build if not already known
        if self.fasta and not self.build and self.md5 in REFERENCE_MODELS:
            self.build = REFERENCE_MODELS[self.md5][0]

        if self.fasta:
            logging.info(f"Auto-resolved FASTA: {self.fasta}")
        if self.vep_cache:
            logging.info(f"Auto-resolved VEP cache: {self.vep_cache}")
        if self.ploidy_file:
            logging.info(f"Auto-resolved ploidy: {self.ploidy_file}")
        if self.ref_vcf_tab:
            logging.info(f"Auto-resolved ref-vcf-tab: {self.ref_vcf_tab}")
        if self.dict_file:
            logging.info(f"Auto-resolved dict: {self.dict_file}")

    def _search_dir(self, d):
        if not os.path.isdir(d):
            return

        # 1. Look for FASTA
        if not self.fasta:
            if self.md5 and self.md5 in REFERENCE_MODELS:
                self.build = REFERENCE_MODELS[self.md5][0]
                # Try specific filename from constants
                potential = os.path.join(
                    d,
                    REF_GENOME_FILENAMES.get(self.build, REFERENCE_MODELS[self.md5][2]),
                )
                if os.path.exists(potential):
                    self.fasta = potential
                else:
                    # Try the exact filename registered in REFERENCE_MODELS for this MD5
                    potential = os.path.join(d, REFERENCE_MODELS[self.md5][2])
                    if os.path.exists(potential):
                        self.fasta = potential

            # General fallback: pick first fasta found in this directory
            if not self.fasta:
                try:
                    for f in os.listdir(d):
                        if f.lower().endswith((".fa.gz", ".fasta.gz", ".fa", ".fasta")):
                            self.fasta = os.path.join(d, f)
                            break
                except Exception:
                    pass

        # Look for dict if we have fasta
        if self.fasta and not self.dict_file:
            potential_dict = (
                self.fasta.replace(".fa.gz", ".dict")
                .replace(".fasta.gz", ".dict")
                .replace(".fa", ".dict")
                .replace(".fasta", ".dict")
            )
            if os.path.exists(potential_dict):
                self.dict_file = potential_dict
            else:
                try:
                    for f in os.listdir(d):
                        if f.lower().endswith(".dict"):
                            self.dict_file = os.path.join(d, f)
                            break
                except Exception:
                    pass

        # 2. Look for ploidy.txt
        if not self.ploidy_file:
            for p in ["ploidy.txt", "ploidy_file.txt"]:
                potential = os.path.join(d, p)
                if os.path.exists(potential):
                    self.ploidy_file = potential

        # 3. Look for microarray VCF
        if not self.ref_vcf_tab:
            search_builds = []
            if self.build:
                search_builds.append(self.build)
                # Map common equivalents
                if self.build in ["hs38DH", "hg38", "GRCh38"]:
                    search_builds.extend(["hg38", "GRCh38", "hs38DH"])
                elif self.build in ["hg19", "GRCh37", "hs37d5"]:
                    search_builds.extend(["hg19", "GRCh37", "hs37d5"])
            else:
                search_builds = ["hg38", "GRCh38", "hs38DH", "hg19", "GRCh37", "hs37d5"]

            for b in search_builds:
                if not b:
                    continue
                # Prioritize All_SNPs patterns over snps patterns
                for pattern in [
                    f"All_SNPs_{b}_ref.tab.gz",
                    f"All_SNPs_{b.lower()}_ref.tab.gz",
                    f"snps_{b}.vcf.gz",
                    f"snps_{b.lower()}.vcf.gz",
                ]:
                    potential = os.path.join(d, pattern)
                    if os.path.exists(potential):
                        self.ref_vcf_tab = potential
                        break
                if self.ref_vcf_tab:
                    break

            # General fallbacks
            if not self.ref_vcf_tab:
                for v in [
                    "microarray.vcf.gz",
                    "ref_vcf_tab.vcf.gz",
                    "CombinedKit_Ref.vcf.gz",
                ]:
                    potential = os.path.join(d, v)
                    if os.path.exists(potential):
                        self.ref_vcf_tab = potential
                        break

        # 4. Look for WES BED
        if not self.wes_bed:
            for b in [
                "TruSeq_Exome_TargetedRegions_v1.2.bed",
                "TruSeq_Exome_TargetedRegions_v1.2num.bed",
                "xgen_plus_spikein.GRCh38.bed",
                "xgen_plus_spikein.GRCh38num.bed",
            ]:
                potential = os.path.join(d, b)
                if os.path.exists(potential):
                    self.wes_bed = potential
                    break

        # 5. Look for Y/MT BED
        if not self.ymt_bed:
            for b in [
                "CombBED_McDonald_Poznik_Merged_hg37.bed",
                "CombBED_McDonald_Poznik_Merged_hg37num.bed",
                "CombBED_McDonald_Poznik_Merged_hg38.bed",
                "CombBED_McDonald_Poznik_Merged_hg38num.bed",
            ]:
                potential = os.path.join(d, b)
                if os.path.exists(potential):
                    self.ymt_bed = potential
                    break

        # 6. Look for cma_dir (directory containing raw_file_templates)
        if not self.cma_dir:
            if os.path.isdir(os.path.join(d, "raw_file_templates")):
                self.cma_dir = d + ("/" if not d.endswith("/") else "")
            elif os.path.isdir(os.path.join(d, "microarray", "raw_file_templates")):
                self.cma_dir = os.path.join(d, "microarray") + "/"

        # 7. Look for vep cache (directory containing homo_sapiens)
        if not self.vep_cache:
            if os.path.isdir(os.path.join(d, "homo_sapiens")):
                self.vep_cache = d
            elif os.path.isdir(os.path.join(d, "vep", "homo_sapiens")):
                self.vep_cache = os.path.join(d, "vep")

        # 5. Look for liftover chain
        if not self.liftover_chain:
            for c in ["hg38ToHg19.over.chain.gz", "GRCh38ToGRCh37.over.chain.gz"]:
                potential = os.path.join(d, c)
                if os.path.exists(potential):
                    self.liftover_chain = potential
                    break


def resolve_reference(ref_path, md5_sig):
    """Find specific .fa.gz from directory or direct path."""
    lib = ReferenceLibrary(ref_path, md5_sig)
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
                logging.error(f"Required file for {arg} not found: {path}")
                return False
            if os.path.isdir(path):
                logging.error(f"Required file for {arg} is a directory: {path}")
                return False
    return True


def run_command(cmd_list, capture_output=False, check=True, **kwargs):
    """Run a command securely via subprocess."""
    try:
        return subprocess.run(
            cmd_list, capture_output=capture_output, text=True, check=check, **kwargs
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd_list)}")
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
        logging.info(f"Auto-indexing VCF: {vcf_path}")
        try:
            # Try tbi first, fall back to csi if needed (csi supports larger chromosomes)
            subprocess.run(["tabix", "-p", "vcf", vcf_path], check=True)
            return True
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["bcftools", "index", vcf_path], check=True)
                return True
            except Exception as e:
                logging.warning(f"Failed to auto-index {vcf_path}: {e}")
    else:
        logging.debug(f"Skipping auto-index for non-bgzipped file: {vcf_path}")

    return False


def get_bam_header(bam_path, cram_opt=[]):
    """Fetch BAM/CRAM header using samtools view -H."""
    # Attempt 1: As provided
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
                logging.debug(
                    "Header fetch failed with reference, retrying without reference..."
                )
                result = run_command(
                    ["samtools", "view", "-H", bam_path], capture_output=True
                )
                return result.stdout
            except Exception:
                pass

        logging.error(f"Failed to fetch BAM header for {bam_path}: {e}")
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


def calculate_bam_md5(bam_path, cram_opt=None):
    """
    Calculates MD5 signature from BAM header @SQ lines.
    It takes SN and LN, upcases SN, sorts ASCII-wise, and hashes.
    """
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


def is_sorted(bam_path, cram_opt=None):
    """Verifies if BAM is coordinate sorted."""
    header = get_bam_header(bam_path, cram_opt)
    for line in header.splitlines():
        if line.startswith("@HD"):
            if "SO:coordinate" in line:
                return True
    return False


def get_ref_mito(bam_path, cram_opt=None):
    """
    Identifies if mitochondrial reference is Yoruba based on chromosome lengths.
    Logic from program/bamfiles.py.
    """
    header = get_bam_header(bam_path, cram_opt)

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


def is_long_read(bam_path, cram_opt=None):
    """
    Rough heuristic to detect long-read data (e.g. Nanopore) from BAM header.
    In the original app, it checks if read length > 500.
    """
    # This usually requires sampling reads, which we might want to avoid for speed.
    # However, some platforms set specific tags in @RG.
    header = get_bam_header(bam_path, cram_opt)
    if "PL:ONT" in header or "PL:PACBIO" in header:
        return True
    return False
