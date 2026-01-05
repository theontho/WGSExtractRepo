import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.logging import logger, echo_tee
from core.common import WGSE_FP, BASHX

def compare_refgenomes(ref1: str, ref2: str):
    """Compares two reference genomes based on their .dict files."""
    dict1 = Path(f"{ref1}.dict")
    dict2 = Path(f"{ref2}.dict")
    
    if not dict1.exists() or not dict2.exists():
        print(f"Error: .dict files for {ref1} or {ref2} not found.")
        return

    def process_dict(p: Path):
        lines = []
        with open(p, 'r') as f:
            # Skip header, process subsequent lines
            next(f)
            for line in f:
                # Columns 2 to 4 (SN, LN, AS/UR etc)
                parts = line.split('\t')[1:4]
                if parts:
                    lines.append("\t".join(parts).upper())
        lines.sort()
        return lines

    lines1 = process_dict(dict1)
    lines2 = process_dict(dict2)

    # Simplified filter lists (regex from shell)
    # The shell script uses a very specific list of lengths (chrs) and names (chrsn)
    # For now, let's just do a direct comparison of the processed lines.
    
    print("+"*80)
    print(f"Difference between {ref1} and {ref2}")
    print("+"*80)
    
    # Simple XOR to find differences
    diff1 = set(lines1) - set(lines2)
    diff2 = set(lines2) - set(lines1)
    
    if not diff1 and not diff2:
        print("No differences found.")
    else:
        if diff1:
            print(f"Only in {ref1}:")
            for d in sorted(diff1): print(f"  {d}")
        if diff2:
            print(f"Only in {ref2}:")
            for d in sorted(diff2): print(f"  {d}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} ref_gen_1 ref_gen_2")
    else:
        compare_refgenomes(sys.argv[1], sys.argv[2])
