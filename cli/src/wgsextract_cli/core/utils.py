import subprocess
import os
import logging
import hashlib
from wgsextract_cli.core.constants import REFERENCE_MODELS, REF_GENOME_FILENAMES

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
                pass # Use "2G" fallback

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
        self.build = None
        
        if not ref_path:
            return

        if os.path.isfile(ref_path):
            if ref_path.lower().endswith(('.fa', '.fasta', '.fa.gz', '.fasta.gz')):
                self.fasta = ref_path
            self._search_dir(os.path.dirname(ref_path))
        
        if os.path.isdir(ref_path):
            self._search_dir(ref_path)
            # Search subdirectories
            for sub in ['genome', 'genomes', 'microarray', 'ref']:
                self._search_dir(os.path.join(ref_path, sub))
            
            # If we are inside 'genomes' or 'genome', also search the parent and its siblings
            # to handle cases where --ref points directly to the genomes folder.
            base_dir = ref_path.rstrip(os.sep)
            if os.path.basename(base_dir) in ['genomes', 'genome']:
                parent = os.path.dirname(base_dir)
                self._search_dir(parent)
                for sub in ['genome', 'genomes', 'microarray', 'ref']:
                    self._search_dir(os.path.join(parent, sub))

        # If we found a fasta, try to deduce the build if not already known
        if self.fasta and not self.build and self.md5 in REFERENCE_MODELS:
            self.build = REFERENCE_MODELS[self.md5][0]
        
        if self.fasta:
            logging.info(f"Auto-resolved FASTA: {self.fasta}")
        if self.ploidy_file:
            logging.info(f"Auto-resolved ploidy: {self.ploidy_file}")
        if self.ref_vcf_tab:
            logging.info(f"Auto-resolved ref-vcf-tab: {self.ref_vcf_tab}")

    def _search_dir(self, d):
        if not os.path.isdir(d):
            return
        
        # 1. Look for FASTA
        if not self.fasta:
            if self.md5 and self.md5 in REFERENCE_MODELS:
                self.build = REFERENCE_MODELS[self.md5][0]
                # Try specific filename from constants
                potential = os.path.join(d, REF_GENOME_FILENAMES.get(self.build, REFERENCE_MODELS[self.md5][2]))
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
                        if f.lower().endswith(('.fa.gz', '.fasta.gz', '.fa', '.fasta')):
                            self.fasta = os.path.join(d, f)
                            break
                except Exception: pass

        # 2. Look for ploidy.txt
        if not self.ploidy_file:
            for p in ['ploidy.txt', 'ploidy_file.txt']:
                potential = os.path.join(d, p)
                if os.path.exists(potential):
                    self.ploidy_file = potential

        # 3. Look for microarray VCF
        if not self.ref_vcf_tab:
            search_builds = []
            if self.build:
                search_builds.append(self.build)
                # Map common equivalents
                if self.build in ['hs38DH', 'hg38', 'GRCh38']:
                    search_builds.extend(['hg38', 'GRCh38', 'hs38DH'])
                elif self.build in ['hg19', 'GRCh37', 'hs37d5']:
                    search_builds.extend(['hg19', 'GRCh37', 'hs37d5'])
            else:
                search_builds = ["hg38", "GRCh38", "hs38DH", "hg19", "GRCh37", "hs37d5"]

            for b in search_builds:
                if not b: continue
                for pattern in [f"All_SNPs_{b}_ref.tab.gz", f"snps_{b}.vcf.gz", f"All_SNPs_{b.lower()}_ref.tab.gz", f"snps_{b.lower()}.vcf.gz"]:
                    potential = os.path.join(d, pattern)
                    if os.path.exists(potential):
                        self.ref_vcf_tab = potential
                        break
                if self.ref_vcf_tab: break
            
            # General fallbacks
            if not self.ref_vcf_tab:
                for v in ['microarray.vcf.gz', 'ref_vcf_tab.vcf.gz', 'CombinedKit_Ref.vcf.gz']:
                    potential = os.path.join(d, v)
                    if os.path.exists(potential):
                        self.ref_vcf_tab = potential
                        break

def resolve_reference(ref_path, md5_sig):
    """Find specific .fa.gz from directory or direct path."""
    lib = ReferenceLibrary(ref_path, md5_sig)
    return lib.fasta if lib.fasta else ref_path

def verify_paths_exist(paths_dict):
    """
    Verify that multiple paths exist.
    paths_dict: { '--arg-name': 'path/to/file' }
    """
    for arg, path in paths_dict.items():
        if path and not os.path.exists(path):
            logging.error(f"Required file for {arg} not found: {path}")
            return False
    return True

def run_command(cmd_list, capture_output=False, check=True, **kwargs):
    """Run a command securely via subprocess."""
    try:
        return subprocess.run(cmd_list, capture_output=capture_output, text=True, check=check, **kwargs)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd_list)}")
        if e.stderr:
            logging.error(e.stderr)
        raise

def get_bam_header(bam_path, cram_opt=None):
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
                logging.debug("Header fetch failed with reference, retrying without reference...")
                result = run_command(["samtools", "view", "-H", bam_path], capture_output=True)
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
        parts = line.split('\t')
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
    
    return target_chr # fallback

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
        for part in line.split('\t'):
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
    is_build37 = any(x in header for x in ["LN:249250621", "LN:59373566", "LN:155270560"])
    if is_build37 and any(x in header for x in ["M\tLN:16571", "MT\tLN:16571"]):
        return "Yoruba"
        
    # Check for other Yoruba builds (15, 16, 17, 18)
    if any(x in header for x in ["LN:247249719", "LN:57772954", "LN:154913754"]): return "Yoruba" # Build 18
    if any(x in header for x in ["LN:245522847", "LN:57701691", "LN:154824264"]): return "Yoruba" # Build 17
    if any(x in header for x in ["LN:246127941", "LN:50286555", "LN:153692391"]): return "Yoruba" # Build 16
    if any(x in header for x in ["LN:245203898", "LN:50961097", "LN:152634166"]): return "Yoruba" # Build 15
    
    return "rCRS" # Default

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
