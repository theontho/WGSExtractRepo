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

# Global cache for genome data
_GENOME_DATA_CACHE = []

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
                    "label": row.get("Library Menu Label"),
                    "md5": ""
                })
    except Exception as e:
        logging.error(f"Error reading {csv_path}: {e}")
    return genomes

def get_available_genomes():
    global _GENOME_DATA_CACHE
    if _GENOME_DATA_CACHE:
        return _GENOME_DATA_CACHE
    
    cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    csv_path = os.path.join(cli_root, "../../base_reference/seed_genomes.csv")
    
    if os.path.exists(csv_path):
        _GENOME_DATA_CACHE = load_genomes_from_csv(csv_path)
    
    if not _GENOME_DATA_CACHE:
        _GENOME_DATA_CACHE = [
            {"code": "T2Tv20", "source": "AWS", "final": "chm13v2.0.fa.gz", "url": "https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz", "label": "T2T_v2.0 (PGP/HPP chrN) (Rec)", "md5": "7cee777f1939f4028926017158ed5512"},
            {"code": "hs37d5", "source": "NIH", "final": "hs37d5.fa.gz", "url": "https://ftp.ncbi.nlm.nih.gov/1000genomes/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz", "label": "hs37d5 (Dante) (NIH) (Rec)", "md5": "5a23f5a85bd78221010561466907bf7d"},
        ]
    return _GENOME_DATA_CACHE

# Backwards compatibility for modules importing GENOME_DATA
GENOME_DATA = get_available_genomes()

def get_grouped_genomes():
    all_data = get_available_genomes()
    grouped = {}
    for item in all_data:
        fname = item["final"]
        if fname not in grouped:
            grouped[fname] = {
                "final": fname,
                "label": item["label"],
                "sources": []
            }
        grouped[fname]["sources"].append(item)
    return list(grouped.values())

def is_genome_installed(final_name: str, reflib_dir: str) -> bool:
    if not reflib_dir: return False
    path = os.path.join(reflib_dir, "genomes", final_name)
    return os.path.exists(path)

def delete_genome(final_name: str, reflib_dir: str):
    base_path = os.path.join(reflib_dir, "genomes", final_name)
    for ext in ["", ".fai", ".gzi", ".dict"]:
        p = base_path + ext
        if os.path.exists(p): os.remove(p)
    prefix = re.sub(r'\.(fasta|fna|fa)\.gz$', '', base_path)
    for ext in ["_ncnt.csv", "_nbin.csv", ".wgse"]:
        p = prefix + ext
        if os.path.exists(p): os.remove(p)
    return True

def download_and_process_genome(genome_data: Dict, reflib_dir: str, interactive: bool = True):
    verify_dependencies(["curl", "samtools", "bgzip", "gzip"])
    target_dir = os.path.join(reflib_dir, "genomes")
    os.makedirs(target_dir, exist_ok=True)
    final_path = os.path.join(target_dir, genome_data['final'])
    
    if os.path.exists(final_path):
        if not interactive: return process_reference_file(final_path)
        print(f"\n{genome_data['final']} is already present.")
        choice = input("Re-download anyway? [y/N]: ").strip().lower()
        if choice != 'y': return process_reference_file(final_path)
        os.remove(final_path)
    
    logging.info(f"Downloading {genome_data['label']} from {genome_data['source']}...")
    try:
        run_command(["curl", "-L", "-o", final_path, genome_data['url']])
    except Exception as e:
        logging.error(f"Download failed: {e}")
        return False

    return process_reference_file(final_path)

def process_reference_file(fasta_path: str):
    logging.info(f"Processing reference: {fasta_path}")
    fasta_path = ensure_bgzf(fasta_path)
    if not fasta_path: return False
    base_name = re.sub(r'\.(fasta|fna|fa)\.gz$', '', fasta_path)
    dict_path = base_name + ".dict"
    try:
        run_command(["samtools", "dict", fasta_path, "-o", dict_path])
        run_command(["samtools", "faidx", fasta_path])
    except Exception as e:
        logging.error(f"Indexing failed: {e}")
        return False
    
    analyzer = ReferenceAnalyzer(fasta_path, dict_path)
    analyzer.analyze()
    cataloger = ReferenceCataloger(fasta_path, dict_path)
    cataloger.update_catalog()
    return True

def ensure_bgzf(path: str) -> Optional[str]:
    try:
        res = run_command(["samtools", "view", "-H", path], capture_output=True, check=False)
        if "BGZF" in res.stdout or "BGZF" in res.stderr:
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
        if os.path.exists(tmp_path): os.remove(tmp_path)
        return None

class ReferenceAnalyzer:
    def __init__(self, fasta_path, dict_path):
        self.fasta_path = fasta_path
        self.dict_path = dict_path
    def analyze(self):
        # Simplified for now
        pass

class ReferenceCataloger:
    def __init__(self, fasta_path, dict_path):
        self.fasta_path = fasta_path
        self.dict_path = dict_path
    def update_catalog(self):
        # Simplified for now
        pass
