import os
import sys
import subprocess
import hashlib
from pathlib import Path
from typing import List, Optional

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from new_scripts.core.logging import logger, echo_tee
from new_scripts.core.common import WGSE_FP, BASHX, rmx, rmrx, mvx

# Build MD5 Mapping (transliterated from shell)
BUILD_MAP = {
    "13cbd449292df5bd282ff5a21d7d0b8f": "T2Tv20a",
    "1e34cdea361327b59b5e46aefd9c0a5e": "HG16",
    "3566ee58361e920af956992d7f0124e6": "HG15",
    "4136c29467b6757938849609bedd3996": "NCB38",
    "4bdbf8a3761d0cd03b53a398b6da026d": "HG38",
    "5a23f5a85bd78221010561466907bf7d": "EBI37",
    "e9438f38ad1b9566c15c3c64a9419d9d": "T2Tv11",
    # ... more from the shell script mapping
}

def get_md5_headerless(dict_file: Path, cols: List[int]):
    """Calculates MD5 hash of specific columns in a dict file (headerless, uppercase, sorted)."""
    lines = []
    with open(dict_file, 'r') as f:
        next(f) # skip header
        for line in f:
            parts = line.strip().split('\t')
            row = "\t".join([parts[i].upper() for i in cols if i < len(parts)])
            lines.append(row)
    lines.sort()
    content = "\n".join(lines) + "\n"
    return hashlib.md5(content.encode()).hexdigest()

def process_file(file_path: Path):
    """Processes a single FASTA file (compression, indices, cataloging)."""
    if not file_path.exists():
        print(f"Error: {file_path} not found.")
        return

    print(f"Processing {file_path.name}...")
    
    # 1. Compression Check/Conversion
    # (Simplified: in practice we'd use htsfile/bgzip)
    filen = file_path
    if file_path.suffix != ".gz":
        print(f"  Fixing compression for {file_path.name}...")
        # subprocess.run(['bgzip', str(file_path)])
        # filen = file_path.with_suffix(".gz")

    # 2. Index Creation
    filed = filen.parent / filen.name.replace(".fasta.gz", "").replace(".fna.gz", "").replace(".fa.gz", "")
    
    dict_file = Path(f"{filed}.dict")
    if not dict_file.exists() or filen.stat().st_mtime > dict_file.stat().st_mtime:
        print("  Creating FA DICTionary")
        subprocess.run(['samtools', 'dict', str(filen), '-o', str(dict_file)], check=True)

    fai_file = Path(f"{filen}.fai")
    if not fai_file.exists() or filen.stat().st_mtime > fai_file.stat().st_mtime:
        print("  Creating FA Index (FAI)")
        subprocess.run(['samtools', 'faidx', str(filen)], check=True)

    # 3. Cataloging (MD5 Calculation)
    print("  Calculating MD5 hashes for cataloging...")
    # SN=1, LN=2, M5=3 (0-indexed)
    md5b = get_md5_headerless(dict_file, [1, 2])
    md5c = get_md5_headerless(dict_file, [1, 2, 3])
    md5f = get_md5_headerless(dict_file, [2, 3])
    
    build = BUILD_MAP.get(md5f, "UNK")
    print(f"  Identified Build: {build}")
    
    # Write .wgse file
    wgse_file = Path(f"{filed}.wgse")
    with open(wgse_file, 'w') as f:
        f.write(f"{filen.name}\t{build}\t{md5b}\t{md5c}\t{md5f}\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: process_refgenomes.py [directory|file(s)|clean|clean_all]")
        return

    cmd = sys.argv[1]
    if cmd == "clean":
        # Implementation of clean logic
        pass
    elif cmd == "clean_all":
        # Implementation of clean_all logic
        pass
    elif os.path.isdir(cmd):
        dir_path = Path(cmd)
        for f in dir_path.glob("*.{fa,fna,fasta,gz}"):
            process_file(f)
    else:
        for arg in sys.argv[1:]:
            process_file(Path(arg))

if __name__ == "__main__":
    main()
