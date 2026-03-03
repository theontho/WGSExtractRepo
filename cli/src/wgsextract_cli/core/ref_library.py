import os
import csv
import logging
import subprocess
import hashlib
import re
import math
import gzip
from typing import List, Dict, Optional, Tuple
from wgsextract_cli.core.utils import run_command
from wgsextract_cli.core.dependencies import verify_dependencies

# Reference genome data from base_reference/seed_genomes.csv
GENOME_DATA = [
    {"code": "T2Tv20", "source": "AWS", "final": "chm13v2.0.fa.gz", "url": "https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz", "label": "T2T_v2.0 (PGP/HPP chrN) (Rec)", "md5": "7cee777f1939f4028926017158ed5512"},
    {"code": "hs37d5", "source": "NIH-Alt", "final": "hs37d5.fa.gz", "url": "https://ftp.ncbi.nlm.nih.gov/1000genomes/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz", "label": "hs37d5 (Dante) (NIH) (Rec)", "md5": "5a23f5a85bd78221010561466907bf7d"},
    {"code": "hs38", "source": "NIH-Alt", "final": "hs38.fa.gz", "url": "https://ftp.ncbi.nlm.nih.gov/genomes/archive/old_genbank/Eukaryotes/vertebrates_mammals/Homo_sapiens/GRCh38/seqs_for_alignment_pipelines/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz", "label": "hs38 (Nebula) (NIH) (Rec)", "md5": "eec5eb2eeae44c48a31eb32647cd04f6"},
    {"code": "hs37d5", "source": "EBI-Alt", "final": "hs37d5.fa.gz", "url": "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz", "label": "hs37d5 (Dante) (EBI) (Rec)", "md5": "5a23f5a85bd78221010561466907bf7d"},
    {"code": "hs38", "source": "EBI-Alt", "final": "hs38.fa.gz", "url": "https://get.wgse.io/hs38.fa.gz", "label": "hs38 (Nebula) (EBI) (Rec)", "md5": "eec5eb2eeae44c48a31eb32647cd04f6"},
    {"code": "hg38", "source": "UCSC", "final": "hg38.fa.gz", "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz", "label": "hg38 (YSEQ)", "md5": "4bdbf8a3761d0cd03b53a398b6da026d"},
    {"code": "hs37", "source": "WGSE", "final": "hs37.fa.gz", "url": "https://get.wgse.io/hs37.fa.gz", "label": "hs37 (1K Gen)", "md5": "f7c76dbcf8cf8b41d2c1d05c1ed58a75"},
]

# Chromosome length sets for build identification
CHR_LENS = [
    [245203898, 246127941, 245522847, 247249719, 249250621, 248956422, 248415701, 248387561, 248387328, 248387497], # chr1
    [243315028, 243615958, 243018229, 242951149, 243199373, 242193529, 242509959, 242696759, 242696752, 242696747], # chr2
    [199411731, 199344050, 199505740, 199501827, 198022430, 198295559, 200717518, 201106621, 201105948, 201106605], # chr3
    [191610523, 191731959, 191411218, 191273063, 191154276, 190214555, 193408891, 193575384, 193574945, 193575430], # chr4
    [180967295, 181034922, 180857866, 180857866, 180915260, 181538259, 182049998, 182045443, 182045439, 182045437], # chr5
    [170740541, 170914576, 170975699, 170899992, 171115067, 170805979, 171893897, 172126875, 172126628, 172126870], # chr6
    [158431299, 158545518, 158628139, 158821424, 159138663, 159345973, 160394084, 160567465, 160567428, 160567423], # chr7
    [145908738, 146308819, 146274826, 146274826, 146364022, 145138636, 146097661, 146259347, 146259331, 146259322], # chr8
    [134505819, 136372045, 138429268, 140273252, 141213431, 138394717, 149697505, 150617238, 150617247, 150617274], # chr9
    [135480874, 135037215, 135413628, 135374737, 135534747, 133797422, 134341430, 134758139, 134758134, 134758122], # chr10
    [134978784, 134482954, 134452384, 134452384, 135006516, 135086622, 134654341, 135129789, 135127769, 135127772], # chr11
    [133464434, 132078379, 132449811, 132349534, 133851895, 133275309, 133439878, 133324792, 133324548, 133324781], # chr12
    [114151656, 113042980, 114142980, 114142980, 115169878, 114364328, 113815969, 114240132, 113566686, 114240146], # chr13
    [105311216, 105311216, 106368585, 106368585, 107349540, 107043718, 100860689, 101219190, 101161492, 101219177], # chr14
    [100114055, 100256656, 100338915, 100338915, 102531392, 101991189, 99808683, 100338336, 99753195, 100338308],   # chr15
    [89995999, 90041932, 88827254, 88827254, 90354753, 90338345, 96296229, 96330509, 96330374, 96330493],           # chr16
    [81691216, 81860266, 78774742, 78774742, 81195210, 83257441, 83946371, 84277212, 84276897, 84277185],           # chr17
    [77753510, 76115139, 76117153, 76117153, 78077248, 80373285, 80696073, 80537682, 80542538, 80542536],           # chr18
    [63790860, 63811651, 63811651, 63811651, 59128983, 58617616, 61612450, 61707413, 61707364, 61707359],           # chr19
    [63644868, 63741868, 62435964, 62435964, 63025520, 64444167, 67262993, 66210261, 66210255, 66210247],           # chr20
    [46976537, 46976097, 46944323, 46944323, 48129895, 46709983, 44996062, 45827694, 45090682, 45827691],           # chr21
    [49476972, 49396972, 49554710, 49691432, 51304566, 50818468, 51228122, 51353916, 51324926, 51353906],           # chr22
    [152634166, 153692391, 154824264, 154913754, 155270560, 156040895, 154343774, 154259664, 154259566, 154259625, 154269076, 154349815, 154434329],  # chrX
    [50961097, 50286555, 57701691, 57772954, 59373566, 57227415, 62480187, 62456832, 62460029],                        # chrY
]

MD5_TO_BUILD = {
    "13cbd449292df5bd282ff5a21d7d0b8f": "T2Tv20a",
    "1e34cdea361327b59b5e46aefd9c0a5e": "HG16",
    "3566ee58361e920af956992d7f0124e6": "HG15",
    "4136c29467b6757938849609bedd3996": "NCB38",
    "46cf0768c13ec7862c065e45f58155bf": "EBI18",
    "4bdbf8a3761d0cd03b53a398b6da026d": "HG38",
    "4bf6c704e4f8dd0d31a9bf305df63ed3": "THGv27",
    "4d0aa9b8472b69f175d279a9ba8778a1": "HPPv11",
    "591bb02c89ed438566ca68b077fee367": "1K37p",
    "5a23f5a85bd78221010561466907bf7d": "EBI37",
    "5e16e3cbdcc7b69d21420c332deecd3b": "T2Tv10",
    "5f451c1014248af62b41c18fec1c3660": "T2Tv07",
    "65a05319ad475cf51c929d3b55341bc2": "THGv20",
    "7083d4ee8aa126726961ab1ae41c66c1": "THG1243v3",
    "7cee777f1939f4028926017158ed5512": "T2Tv20",
    "84e78573982f3ea293bfeb54cd529309": "1K38p",
    "85c436650ffe85696c0fb51de4a3a74f": "THG1243v3",
    "90814fe70fd8bbc59cacf2a3fd08e24c": "T2Tv09",
    "a2fe6ab831d884104783f9be437ddbc0": "EBI38p",
    "a9634b94a29618dc3faf15a3060006ec": "HG18",
    "b05113b52031beadfb6737bc1185960b": "HG19",
    "b7884451f3069579e5f2e885582b9434": "1K38",
    "bbd2cf1448ccc0eaa2472408fa9d514a": "THGySeqp",
    "bc811d53b8a6fc404d279ab951f2be4d": "HG17",
    "bee8aebc6243ff5963c30abbd738d1f6": "NCB38",
    "c182b40ef3513ef9a1196881a4315392": "HPPv1",
    "ca2e97bc5ecff43a27420eee237dbcc3": "EBI37p",
    "e9438f38ad1b9566c15c3c64a9419d9d": "T2Tv11",
    "eec5eb2eeae44c48a31eb32647cd04f6": "EBI38",
    "f7c76dbcf8cf8b41d2c1d05c1ed58a75": "NCB37",
}

def get_available_genomes():
    return GENOME_DATA

def load_genomes_from_csv(csv_path):
    if not os.path.exists(csv_path):
        return []
    genomes = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                genomes.append({
                    "code": row.get("Pyth Code"),
                    "source": row.get("Source"),
                    "final": row.get("Final File Name"),
                    "url": row.get("URL"),
                    "label": row.get("Library Menu Label")
                })
    except Exception as e:
        logging.error(f"Error reading {csv_path}: {e}")
    return genomes

def verify_genome_checksum(final_path: str, genome: Dict) -> bool:
    """Helper to verify checksum of a local file against static or remote metadata."""
    expected_sum = genome.get('md5')
    
    if genome.get('checksum_url'):
        logging.info(f"Fetching remote checksums from {genome['checksum_url']}...")
        try:
            res = subprocess.run(["curl", "-s", "-L", genome['checksum_url']], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and (parts[-1].endswith(genome['final']) or parts[-1] == genome['final']):
                        expected_sum = parts[0]
                        logging.info(f"Found remote checksum for {genome['final']}: {expected_sum}")
                        break
        except Exception as e:
            logging.debug(f"Failed to fetch remote checksum: {e}")

    if not expected_sum:
        return True # Can't verify, assume OK or handled by gzip -t elsewhere

    logging.info(f"Verifying integrity of {os.path.basename(final_path)}...")
    if len(expected_sum) == 32:
        hash_md5 = hashlib.md5()
        with open(final_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        calculated = hash_md5.hexdigest()
    else:
        from wgsextract_cli.core.utils import calculate_bsd_sum
        calculated_sum, _ = calculate_bsd_sum(final_path)
        calculated = str(calculated_sum)

    if calculated == expected_sum:
        logging.info("Checksum verification successful.")
        return True
    else:
        logging.error(f"Checksum verification FAILED for {os.path.basename(final_path)}!")
        logging.error(f"Expected: {expected_sum}")
        logging.error(f"Calculated: {calculated}")
        return False

def download_and_process_genome(genome_index: int, reflib_dir: str, genomes_list: List[Dict] = None):
    verify_dependencies(["curl", "samtools", "bgzip", "gzip"])
    data = genomes_list if genomes_list else GENOME_DATA
    if genome_index < 0 or genome_index >= len(data):
        logging.error(f"Invalid genome index: {genome_index}")
        return False
    
    genome = data[genome_index]
    target_sub = "genomes"
    if not os.path.exists(os.path.join(reflib_dir, "genomes")) and os.path.exists(os.path.join(reflib_dir, "genome")):
        target_sub = "genome"
    
    target_dir = os.path.join(reflib_dir, target_sub)
    os.makedirs(target_dir, exist_ok=True)
    final_path = os.path.join(target_dir, genome['final'])
    
    if os.path.exists(final_path):
        # Check integrity of EXISTING file
        if verify_genome_checksum(final_path, genome):
            print(f"\n{genome['final']} is already present and VERIFIED.")
            choice = input("Re-download anyway? [y/N]: ").strip().lower()
            if choice != 'y':
                return process_reference_file(final_path)
            os.remove(final_path)
        else:
            print(f"\nExisting file {genome['final']} is CORRUPTED.")
            choice = input("Download a fresh copy to fix it? [Y/n]: ").strip().lower()
            if choice == 'n':
                logging.warning("Proceeding with corrupted file (not recommended).")
                return process_reference_file(final_path)
            os.remove(final_path)
    
    if not os.path.exists(final_path):
        logging.info(f"Downloading {genome['label']} from {genome['url']}...")
        try:
            run_command(["curl", "-L", "-o", final_path, genome['url']])
        except Exception as e:
            logging.error(f"Download failed: {e}")
            return False

    if not os.path.exists(final_path) or os.path.getsize(final_path) < 1000000:
        logging.error(f"Download failed or file too small: {final_path}")
        return False

    # Verify NEW download
    if not verify_genome_checksum(final_path, genome):
        choice = input("The new download also appears corrupted. Continue processing anyway? [y/N]: ").strip().lower()
        if choice != 'y':
            return False

    return process_reference_file(final_path)

def process_reference_file(fasta_path: str):
    logging.info(f"Processing reference: {fasta_path}")
    fasta_path = ensure_bgzf(fasta_path)
    if not fasta_path:
        return False

    base_name = re.sub(r'\.(fasta|fna|fa)\.gz$', '', fasta_path)
    dict_path = base_name + ".dict"
    
    try:
        logging.info("Creating samtools dict and faidx...")
        run_command(["samtools", "dict", fasta_path, "-o", dict_path])
        run_command(["samtools", "faidx", fasta_path])
        if not os.path.exists(fasta_path + ".gzi"):
            run_command(["bgzip", "-r", fasta_path])
    except Exception as e:
        logging.error(f"Indexing failed: {e}")
        return False

    logging.info("Analyzing N segments...")
    analyzer = ReferenceAnalyzer(fasta_path, dict_path)
    analyzer.analyze()

    logging.info("Updating catalog...")
    cataloger = ReferenceCataloger(fasta_path, dict_path)
    cataloger.update_catalog()

    logging.info(f"Successfully processed {os.path.basename(fasta_path)}")
    return True

def ensure_bgzf(path: str) -> Optional[str]:
    try:
        res = run_command(["samtools", "view", "-H", path], capture_output=True, check=False)
        if "BGZF" in res.stdout or "BGZF" in res.stderr: # Crude check
             return path
    except Exception: pass

    logging.info(f"Recompressing {path} to BGZF format...")
    tmp_path = path + ".tmp.gz"
    try:
        if path.endswith(".gz"):
            with open(tmp_path, "wb") as f_out:
                p1 = subprocess.Popen(["gunzip", "-c", path], stdout=subprocess.PIPE)
                p2 = subprocess.Popen(["bgzip", "-c"], stdin=p1.stdout, stdout=f_out)
                p1.stdout.close()
                p2.communicate()
            os.remove(path)
            os.rename(tmp_path, path)
            return path
        else:
            with open(tmp_path, "wb") as f_out:
                subprocess.run(["bgzip", "-c", path], stdout=f_out, check=True)
            os.remove(path)
            new_path = path + ".gz" if not path.endswith(".gz") else path
            os.rename(tmp_path, new_path)
            return new_path
    except Exception as e:
        logging.error(f"Recompression failed: {e}")
        if os.path.exists(tmp_path): os.remove(tmp_path)
        return None

class ReferenceAnalyzer:
    """Ported from program/countingNs.py."""
    def __init__(self, fasta_path, dict_path):
        self.fasta_path = fasta_path
        self.dict_path = dict_path
        self.num_buckets = 1000
        self.nrun_threshold = 300
        self.seq_dict = self._load_dict()

    def _load_dict(self):
        d = {}
        with open(self.dict_path, "r") as f:
            for line in f:
                cols = line.split()
                if cols[0] == '@SQ':
                    sn = cols[1][3:]
                    ln = int(cols[2][3:])
                    d[sn] = ln
        return d

    def analyze(self):
        base_name = re.sub(r'\.(fasta|fna|fa)\.gz$', '', self.fasta_path)
        ncnt_file = base_name + "_ncnt.csv"
        nbin_file = base_name + "_nbin.csv"

        total_sn = total_ln = total_ncnt = total_nregs = total_sml_nregs = 0

        with gzip.open(self.fasta_path, 'rt') as f_in, \
             open(ncnt_file, 'w') as f_ncnt, \
             open(nbin_file, 'w') as f_nbin:
            
            f_ncnt.write(f"#Processing Ref Model: {os.path.basename(self.fasta_path)}\n")
            f_ncnt.write("#Seq\tNumBP\tNumNs\tNumNreg\tNregSizeMean\tNregSizeStdDev\tSmlNreg\tBuckSize\tBuckets...\n")
            f_nbin.write(f"#Processing Ref Model: {os.path.basename(self.fasta_path)}\n")
            f_nbin.write("#SN\tBinID\tStart\tSize\n")

            current_sn = None
            seq_bp_cnt = 0
            seq_ncnt = 0
            seq_nregs = 0
            seq_sml_nregs = 0
            seq_nmean = 0
            seq_nm2 = 0
            
            buck_size = 0
            buckets = []
            buck_ncnt = 0
            buck_bp_cnt = 0
            
            in_n_run = False
            n_run_cnt = 0

            def close_n_run():
                nonlocal seq_ncnt, buck_ncnt, seq_nregs, seq_nmean, seq_nm2, in_n_run, n_run_cnt, seq_sml_nregs
                seq_ncnt += n_run_cnt
                buck_ncnt += n_run_cnt
                if n_run_cnt > self.nrun_threshold:
                    seq_nregs += 1
                    delta = n_run_cnt - seq_nmean
                    seq_nmean += delta / seq_nregs
                    delta2 = n_run_cnt - seq_nmean
                    seq_nm2 += delta * delta2
                    start = seq_bp_cnt - n_run_cnt
                    f_nbin.write(f"{current_sn}\t{seq_nregs}\t{start:,}\t{n_run_cnt:,}\n")
                else:
                    seq_sml_nregs += 1
                in_n_run = False
                n_run_cnt = 0

            def close_bucket():
                nonlocal buckets, buck_ncnt, buck_bp_cnt
                if buck_bp_cnt > 0:
                    buckets.append(buck_ncnt)
                buck_ncnt = 0
                buck_bp_cnt = 0

            def process_seq_segment(segment):
                nonlocal in_n_run, seq_bp_cnt, buck_bp_cnt, n_run_cnt
                for char in segment:
                    seq_bp_cnt += 1
                    buck_bp_cnt += 1
                    if char == 'N':
                        if not in_n_run:
                            in_n_run = True
                        n_run_cnt += 1
                    else:
                        if in_n_run:
                            close_n_run()

            def close_seq():
                nonlocal total_sn, total_ln, total_ncnt, total_nregs, total_sml_nregs, current_sn
                if in_n_run: close_n_run()
                while len(buckets) < self.num_buckets: close_bucket()
                
                std_dev = math.sqrt(seq_nm2 / (seq_nregs - 1)) if seq_nregs > 1 else 0
                f_ncnt.write(f"{current_sn}\t{seq_ln:,}\t{seq_ncnt:,}\t{seq_nregs}\t{seq_nmean:,.0f}\t{std_dev:,.0f}\t{seq_sml_nregs}\t{buck_size}")
                for i, val in enumerate(buckets):
                    if val > 0:
                        ln_val = round(math.log(val)) if val > 1 else 0
                        if ln_val > 0:
                            f_ncnt.write(f"\t{i*buck_size}\t{ln_val}")
                f_ncnt.write("\n")
                
                total_sn += 1
                total_ln += seq_ln
                total_ncnt += seq_ncnt
                total_nregs += seq_nregs
                total_sml_nregs += seq_sml_nregs
                current_sn = None

            for line in f_in:
                line = line.strip()
                if not line or line.startswith(('#', '+')): continue
                if line.startswith('>'):
                    if current_sn: close_seq()
                    current_sn = line.split()[0][1:]
                    seq_ln = self.seq_dict.get(current_sn, 0)
                    if seq_ln == 0:
                        current_sn = None # Skip unknown
                        continue
                    seq_bp_cnt = seq_ncnt = seq_nregs = seq_sml_nregs = seq_nmean = seq_nm2 = 0
                    buck_size = round(seq_ln / self.num_buckets)
                    buckets = []
                    buck_ncnt = buck_bp_cnt = 0
                    in_n_run = False
                    n_run_cnt = 0
                elif current_sn:
                    # Handle bucket boundaries within line
                    pos = 0
                    while pos < len(line):
                        space_in_buck = buck_size - buck_bp_cnt
                        if space_in_buck <= 0:
                            close_bucket()
                            space_in_buck = buck_size
                        
                        chunk = line[pos : pos + space_in_buck]
                        process_seq_segment(chunk)
                        pos += len(chunk)
                        if buck_bp_cnt >= buck_size:
                            close_bucket()

            if current_sn: close_seq()
            f_ncnt.write(f"#TOTALS:\n{total_sn}\t{total_ln:,}\t{total_ncnt:,}\t{total_nregs}\t\t\t{total_sml_nregs}\n")

class ReferenceCataloger:
    """Cataloging logic from process_refgenomes.sh."""
    def __init__(self, fasta_path, dict_path):
        self.fasta_path = fasta_path
        self.dict_path = dict_path

    def update_catalog(self):
        target_dir = os.path.dirname(self.fasta_path)
        base_name = re.sub(r'\.(fasta|fna|fa)\.gz$', '', os.path.basename(self.fasta_path))
        wgse_path = os.path.join(target_dir, base_name + ".wgse")
        
        # 1. Parse .dict
        dict_entries = []
        with open(self.dict_path, "r") as f:
            for line in f:
                if line.startswith("@SQ"):
                    parts = {p[:2]: p[3:] for p in line.strip().split("\t")[1:]}
                    dict_entries.append(parts)
        
        # 2. Identify Build (MD5 of primary chromosomes)
        # Sort dict entries by SN for consistent hashing
        sorted_entries = sorted(dict_entries, key=lambda x: x['SN'].upper())
        
        # Full MD5s
        md5_bam = hashlib.md5("".join([f"SN:{e['SN'].upper()}\tLN:{e['LN']}\n" for e in sorted_entries]).encode()).hexdigest()
        md5_cram = hashlib.md5("".join([f"SN:{e['SN'].upper()}\tLN:{e['LN']}\tM5:{e.get('M5','')}\n" for e in sorted_entries]).encode()).hexdigest()
        md5_fasta = hashlib.md5("".join([f"LN:{e['LN']}\tM5:{e.get('M5','')}\n" for e in sorted_entries]).encode()).hexdigest()

        # Primary chromosomes
        primary = []
        mito = None
        for e in sorted_entries:
            ln = int(e['LN'])
            sn = e['SN'].upper()
            is_primary = False
            for lens in CHR_LENS:
                if ln in lens:
                    # Double check naming convention (chr1, 1, etc)
                    if any(re.match(p, "SN:"+sn) for p in [r"SN:CHR[1-9XY]\b", r"SN:CHR1[0-9]\b", r"SN:CHR2[0-2]\b", r"SN:[1-9XY]\b", r"SN:1[0-9]\b", r"SN:2[012]\b"]):
                         is_primary = True
                         break
            if is_primary: primary.append(e)
            if ln in [16569, 16571, 16568]: mito = e

        md5_p = hashlib.md5("".join([f"LN:{e['LN']}\tM5:{e.get('M5','')}\n" for e in primary]).encode()).hexdigest()
        md5_s = hashlib.md5("".join([f"SN:{e['SN'].upper()}\n" for e in primary]).encode()).hexdigest()
        
        build = MD5_TO_BUILD.get(md5_p, "UNK")
        
        # 3. Create .wgse
        sn_names = "\t".join([f'"{e["SN"]}"' for e in primary])
        if mito: sn_names += f'\t"{mito["SN"]}"'
        
        with open(wgse_path, "w") as f:
            f.write(f'"{os.path.basename(self.fasta_path)}"\t{build}\t{len(dict_entries)}\t{md5_bam}\t{md5_cram}\t{md5_fasta}\t{md5_p}\t{md5_s}\t')
            if mito:
                f.write(f'{mito["SN"]}\t{mito["LN"]}\t{mito.get("M5","")}')
            else:
                f.write("\t\t")
            f.write(f'\t""\t{sn_names}\n')

        # 4. Update WGSE.csv
        csv_path = os.path.join(target_dir, "WGSE.csv")
        header = "File\tBuild\tSN_CNT\tBAM_(SN,_LN)\tCRAM_(SN,_LN,_M5)\tFASTA_(LN,_M5)\tChromo_(LN,_M5)\tChromo_(SN)\tMito:_SN\tLN\tM5\tMessage\tSNs\n"
        
        lines = []
        if os.path.exists(csv_path):
            with open(csv_path, "r") as f:
                lines = f.readlines()
        
        if not lines or lines[0].strip() != header.strip():
            lines = [header]
            
        # Update or append
        with open(wgse_path, "r") as f:
            new_line = f.read()
            
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f'"{os.path.basename(self.fasta_path)}"'):
                lines[i] = new_line
                found = True
                break
        if not found:
            lines.append(new_line)
            
        with open(csv_path, "w") as f:
            f.writelines(lines)
