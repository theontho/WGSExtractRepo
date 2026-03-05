import csv
import gzip
import logging
import os
from typing import Any

from wgsextract_cli.core.utils import run_command

# Official UCSC RefGene database URLs
# These files are approx 4-5MB compressed and contain all RefSeq gene models.
GENE_MAP_URLS = {
    "hg38": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/refGene.txt.gz",
    "hg19": "https://hgdownload.soe.ucsc.edu/goldenPath/hg19/database/refGene.txt.gz",
}


class GeneMap:
    def __init__(self, reflib_dir):
        self.reflib_dir = reflib_dir
        self.maps = {}  # build -> { symbol -> coords }

    def load(self, build="hg38"):
        build_key = "hg38" if "38" in build else "hg19"
        if build_key in self.maps:
            return True

        # Look for local file in reflib (ref/genes_hg38.tsv)
        map_file = os.path.join(self.reflib_dir, "ref", f"genes_{build_key}.tsv")
        if not os.path.exists(map_file):
            # Try root/microarray as fallback
            map_file = os.path.join(
                self.reflib_dir, "microarray", f"genes_{build_key}.tsv"
            )

        if not os.path.exists(map_file):
            return False

        try:
            gene_dict: dict[str, str] = {}
            with open(map_file) as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    symbol = row.get("symbol", "").upper()
                    chrom = row.get("chrom", "")
                    start = row.get("start", "")
                    end = row.get("end", "")
                    if symbol and chrom and start and end:
                        # Store the largest range if multiple transcripts exist
                        if symbol in gene_dict:
                            old_coords = gene_dict[symbol].split(":")[-1].split("-")
                            new_start = min(int(start), int(old_coords[0]))
                            new_end = max(int(end), int(old_coords[1]))
                            gene_dict[symbol] = f"{chrom}:{new_start}-{new_end}"
                        else:
                            gene_dict[symbol] = f"{chrom}:{start}-{end}"
            self.maps[build_key] = gene_dict
            return True
        except Exception as e:
            logging.error(f"Failed to load gene map {map_file}: {e}")
            return False

    def get_coords(self, gene_symbol, build="hg38"):
        build_key = "hg38" if "38" in build else "hg19"
        if build_key not in self.maps:
            if not self.load(build):
                return None
        return self.maps[build_key].get(gene_symbol.upper())


def download_gene_maps(reflib_dir):
    """Downloads and processes official UCSC RefGene maps."""
    target_dir = os.path.join(reflib_dir, "ref")
    os.makedirs(target_dir, exist_ok=True)

    success = True
    for build, url in GENE_MAP_URLS.items():
        gz_path = os.path.join(target_dir, f"refGene_{build}.txt.gz")
        tsv_path = os.path.join(target_dir, f"genes_{build}.tsv")

        logging.info(f"Downloading {build} gene database from UCSC...")
        try:
            # 1. Download
            run_command(["curl", "-L", "-o", gz_path, url])

            # 2. Parse UCSC format to simple TSV
            # UCSC refGene columns: 2=chrom, 4=txStart, 5=txEnd, 12=name2(Symbol)
            gene_data: dict[str, list[Any]] = {}  # Symbol -> (chrom, start, end)

            with gzip.open(gz_path, "rt") as f_in:
                for line in f_in:
                    cols = line.split("\t")
                    if len(cols) < 13:
                        continue

                    chrom = cols[2]
                    start = int(cols[4])
                    end = int(cols[5])
                    symbol = cols[12].upper()

                    if symbol not in gene_data:
                        gene_data[symbol] = [chrom, start, end]
                    else:
                        # Expand range to cover all transcripts/isoforms
                        gene_data[symbol][1] = min(int(gene_data[symbol][1]), start)
                        gene_data[symbol][2] = max(int(gene_data[symbol][2]), end)

            # 3. Write processed TSV
            with open(tsv_path, "w") as f_out:
                f_out.write("symbol\tchrom\tstart\tend\n")
                for symbol in sorted(gene_data.keys()):
                    c, s, e = gene_data[symbol]
                    f_out.write(f"{symbol}\t{c}\t{s}\t{e}\n")

            logging.info(f"Successfully processed {len(gene_data)} genes for {build}")
            os.remove(gz_path)  # Cleanup

        except Exception as e:
            logging.error(f"Failed to setup {build} gene map: {e}")
            success = False

    return success
