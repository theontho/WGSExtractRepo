import csv
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from new_scripts.core.common import WGSE_FP, OSTYPE, get_reflib_dir, rmx, cpx, BASHX
from new_scripts.core.logging import logger, echo_tee

def read_genomes_file() -> List[Dict[str, str]]:
    """Reads genomes.csv and returns a list of dictionaries."""
    reflibdir = get_reflib_dir()
    genomes_csv = reflibdir / "genomes" / "genomes.csv"
    seed_csv = reflibdir / "seed_genomes.csv"
    
    if not genomes_csv.exists() and seed_csv.exists():
        genomes_csv.parent.mkdir(parents=True, exist_ok=True)
        cpx(seed_csv, genomes_csv)
    
    if not genomes_csv.exists():
        return []
    
    genomes = []
    with open(genomes_csv, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            genomes.append(row)
    return genomes

def _filesizebad(path: Path, min_size: int) -> bool:
    """Returns True if file is smaller than min_size or doesn't exist."""
    if not path.exists():
        return True
    return path.stat().st_size < min_size

def get_and_process_refgenome(genome_data: Dict[str, str]):
    """Downloads and processes a reference genome."""
    reflibdir = get_reflib_dir()
    genomes_dir = reflibdir / "genomes"
    
    descr = genome_data.get("Description", "Unknown")
    finalf = genome_data.get("Final File Name")
    initf = genome_data.get("Downloaded File Name")
    gurl = genome_data.get("URL")
    pytcode = genome_data.get("Python Genome Code")
    
    if not finalf or not initf or not gurl:
        logger.error(f"Missing data for genome: {descr}")
        return

    echo_tee(f"\nDownloading and Processing {descr}")
    
    final_path = genomes_dir / finalf
    init_path = genomes_dir / initf
    
    rmx(final_path)
    rmx(init_path)
    
    echo_tee(f"DEBUG: Downloading from URL: {gurl}")
    echo_tee(f"DEBUG: Destination path: {init_path}")
    
    try:
        # Using curl for download as in shell
        subprocess.run(['curl', '-Lk#LC', '-', '--retry', '5', '-o', str(init_path), gurl], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading {initf}: {e}")
        rmx(init_path)
        return

    if _filesizebad(init_path, 500000000):
        logger.error(f"Error downloading {initf}: File too small or missing.")
        rmx(init_path)
        return

    init_path.chmod(0o774)
    
    # Process ref genomes script
    process_refgenomes_sh = WGSE_FP / "scripts" / "process_refgenomes.sh"
    try:
        # We still call the bash script for processing for now, until it's also transliterated
        subprocess.run([str(BASHX), str(process_refgenomes_sh), str(init_path)], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing {finalf}: {e}")
        rmx(final_path)
        rmx(init_path)
        return

    if _filesizebad(final_path, 500000000):
        logger.error(f"Error processing {finalf}: Final file too small or missing.")
        rmx(final_path)
        rmx(init_path)
        return

    echo_tee(f"{finalf}: Finished installing {pytcode}")
