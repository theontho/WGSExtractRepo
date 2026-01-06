import sys
import os
import subprocess
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.logging import logger, echo_tee
from core.common import WGSE_FP, BASHX

URL38 = "ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_full_analysis_set.fna.gz"
URL37D5 = "ftp://ftp.ncbi.nlm.nih.gov/1000genomes/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz"

def gen_ref(genome: str):
    """Generates reference genome (transliterated from bwa-kit-gen-ref.sh)."""
    root = Path(__file__).parent
    output_fa = Path(f"{genome}.fa")
    
    echo_tee = print # Simple redirect for now

    if genome == "hs38DH":
        echo_tee("Downloading hs38 and appending DH extras...")
        # (wget -O- $url38 | gzip -dc; cat "$root"/resource-GRCh38/hs38DH-extra.fa) > "$1".fa
        with open(output_fa, 'wb') as out_f:
            p1 = subprocess.Popen(['curl', '-Lk', URL38], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=subprocess.PIPE)
            out_f.write(p2.communicate()[0])
            extra = root / "resource-GRCh38" / "hs38DH-extra.fa"
            if extra.exists():
                with open(extra, 'rb') as ex_f:
                    out_f.write(ex_f.read())
        
        alt_src = root / "resource-GRCh38" / "hs38DH.fa.alt"
        alt_dst = Path(f"{genome}.fa.alt")
        if alt_src.exists() and not alt_dst.exists():
            import shutil
            shutil.copy2(alt_src, alt_dst)

    elif genome == "hs38a":
        with open(output_fa, 'wb') as out_f:
            p1 = subprocess.Popen(['curl', '-Lk', URL38], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=out_f)
            p2.wait()
        
        # [ ! -f "$1".fa.alt ] && grep _alt "$root"/resource-GRCh38/hs38DH.fa.alt > "$1".fa.alt
        alt_src = root / "resource-GRCh38" / "hs38DH.fa.alt"
        alt_dst = Path(f"{genome}.fa.alt")
        if alt_src.exists() and not alt_dst.exists():
            with open(alt_dst, 'wb') as out_alt:
                subprocess.run(['grep', '_alt', str(alt_src)], stdout=out_alt)

    elif genome == "hs38":
        # wget -O- $url38 | gzip -dc | awk '/^>/{f=/_alt/?0:1}f' > "$1".fa
        with open(output_fa, 'w') as out_f:
            p1 = subprocess.Popen(['curl', '-Lk', URL38], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
            f = True
            for line in p2.stdout:
                if line.startswith(">"):
                    f = "_alt" not in line
                if f:
                    out_f.write(line)

    elif genome == "hs37d5":
        with open(output_fa, 'wb') as out_f:
            subprocess.run(['curl', '-Lk', URL37D5], stdout=subprocess.PIPE)
            # Simplified: just gunzip to output
            p1 = subprocess.Popen(['curl', '-Lk', URL37D5], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=out_f)
            p2.wait()

    elif genome == "hs37":
        # wget -O- $url37d5 | gzip -dc 2>/dev/null | awk '/^>/{f=/>hs37d5/?0:1}f' > "$1".fa
        with open(output_fa, 'w') as out_f:
            p1 = subprocess.Popen(['curl', '-Lk', URL37D5], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
            f = True
            for line in p2.stdout:
                if line.startswith(">"):
                    f = ">hs37d5" not in line
                if f:
                    out_f.write(line)
    else:
        print(f"ERROR: unknown genome build {genome}")
        sys.exit(1)

    if not Path(f"{genome}.fa.bwt").exists():
        print(f"\nPlease run 'bwa index {genome}.fa'...\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <hs38|hs38a|hs38DH|hs37|hs37d5>")
    else:
        gen_ref(sys.argv[1])
