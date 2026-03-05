from __future__ import annotations

import csv
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command

# Global cache for genome data
_GENOME_DATA_CACHE: list[dict[str, Any]] = []


def download_file(
    url: str,
    dest: str,
    progress_callback: Callable[[int, int, float], None] | None = None,
    cancel_event: Any | None = None,
) -> bool:
    """Downloads a file with progress reporting, optional cancellation, and resume support."""
    partial_dest = dest + ".partial"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    initial_size = 0
    mode = "wb"

    # If the final file exists but we are here, it might be incomplete (e.g. missing index)
    # Move it to .partial to attempt a resume/verify
    if not os.path.exists(partial_dest) and os.path.exists(dest):
        os.rename(dest, partial_dest)

    if os.path.exists(partial_dest):
        initial_size = os.path.getsize(partial_dest)
        if initial_size > 0:
            headers["Range"] = f"bytes={initial_size}-"
            mode = "ab"
        else:
            mode = "wb"

    try:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            code = response.getcode()
            # If we requested a range but got 200, the server doesn't support range or sent full file
            if initial_size > 0 and code == 200:
                logging.info(
                    "Server does not support Range requests, starting from scratch."
                )
                initial_size = 0
                mode = "wb"

            content_length = int(response.info().get("Content-Length", 0))
            total_size = initial_size + content_length
            bytes_downloaded = initial_size
            start_time = time.time()
            last_report_time = 0.0

            with open(partial_dest, mode) as f:
                while True:
                    if cancel_event and cancel_event.is_set():
                        logging.info("Download cancelled by user.")
                        return False

                    chunk = response.read(1024 * 256)  # 256KB chunks
                    if not chunk:
                        break

                    f.write(chunk)
                    bytes_downloaded += len(chunk)

                    curr_time = time.time()
                    if progress_callback and (
                        curr_time - last_report_time > 0.1
                        or bytes_downloaded == total_size
                    ):
                        elapsed = curr_time - start_time
                        speed = (
                            (bytes_downloaded - initial_size) / elapsed
                            if elapsed > 0
                            else 0
                        )
                        progress_callback(bytes_downloaded, total_size, speed)
                        last_report_time = curr_time

        # Rename to final destination on success
        if os.path.exists(dest):
            os.remove(dest)
        os.rename(partial_dest, dest)
        return True
    except Exception as e:
        logging.error(f"Download error: {e}")
        return False


def load_genomes_from_csv(csv_path):
    if not os.path.exists(csv_path):
        return []
    genomes = []
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                genomes.append(
                    {
                        "code": row.get("Pyth Code"),
                        "source": row.get("Source"),
                        "final": row.get("Final File Name"),
                        "url": row.get("URL"),
                        "label": row.get("Library Menu Label"),
                        "description": row.get("Description", ""),
                        "md5": "",
                    }
                )
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
            {
                "code": "T2Tv20",
                "source": "AWS",
                "final": "chm13v2.0.fa.gz",
                "url": "https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz",
                "label": "T2T_v2.0 (PGP/HPP chrN) (Rec)",
                "description": "T2T v2.0 (chm13 v1.1; HG002 Y v2.7; UCSC SN; @AWS)",
                "md5": "7cee777f1939f4028926017158ed5512",
            },
            {
                "code": "hs37d5",
                "source": "NIH",
                "final": "hs37d5.fa.gz",
                "url": "https://ftp.ncbi.nlm.nih.gov/1000genomes/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz",
                "label": "hs37d5 (Dante) (NIH) (Rec)",
                "description": "hs37d5 (1K Genome; @US NIH)",
                "md5": "5a23f5a85bd78221010561466907bf7d",
            },
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
                "description": item.get("description", ""),
                "code": item.get("code", ""),
                "sources": [],
            }
        grouped[fname]["sources"].append(item)
    return list(grouped.values())


def get_genome_status(final_name: str, reflib_dir: str) -> str:
    """Returns 'installed', 'incomplete', or 'missing'."""
    if not reflib_dir:
        return "missing"
    target_dir = os.path.join(reflib_dir, "genomes")
    final_path = os.path.join(target_dir, final_name)
    partial_path = final_path + ".partial"
    fai_path = final_path + ".fai"

    if os.path.exists(final_path):
        if os.path.exists(fai_path):
            return "installed"
        else:
            # File exists but index is missing; treat as incomplete to allow resume/verify
            return "incomplete"
    if os.path.exists(partial_path):
        return "incomplete"
    return "missing"


def is_genome_installed(final_name: str, reflib_dir: str) -> bool:
    return get_genome_status(final_name, reflib_dir) == "installed"


def get_genome_size(final_name: str, reflib_dir: str) -> str:
    """Returns human-readable local size of the genome and its index files."""
    if not reflib_dir:
        return ""
    base_path = os.path.join(reflib_dir, "genomes", final_name)
    total_bytes = 0
    # Include .partial, .fai, .gzi, .dict etc
    for ext in ["", ".partial", ".fai", ".gzi", ".dict"]:
        p = base_path + ext
        if os.path.exists(p):
            total_bytes += os.path.getsize(p)

    if total_bytes == 0:
        return ""
    if total_bytes > 1024 * 1024 * 1024:
        return f"{total_bytes / (1024 * 1024 * 1024):.1f} GB"
    return f"{total_bytes / (1024 * 1024):.1f} MB"


def delete_genome(final_name: str, reflib_dir: str):
    base_path = os.path.join(reflib_dir, "genomes", final_name)
    for ext in ["", ".partial", ".fai", ".gzi", ".dict"]:
        p = base_path + ext
        if os.path.exists(p):
            os.remove(p)
    prefix = re.sub(r"\.(fasta|fna|fa)\.gz$", "", base_path)
    for ext in ["_ncnt.csv", "_nbin.csv", ".wgse"]:
        p = prefix + ext
        if os.path.exists(p):
            os.remove(p)
    return True


def download_and_process_genome(
    genome_data: dict,
    reflib_dir: str,
    interactive: bool = True,
    progress_callback: Callable | None = None,
    cancel_event: Any | None = None,
    restart: bool = False,
):
    verify_dependencies(["samtools", "bgzip", "gzip"])
    target_dir = os.path.join(reflib_dir, "genomes")
    os.makedirs(target_dir, exist_ok=True)
    final_path = os.path.join(target_dir, genome_data["final"])
    partial_path = final_path + ".partial"

    if restart:
        if os.path.exists(final_path):
            os.remove(final_path)
        if os.path.exists(partial_path):
            os.remove(partial_path)

    status = get_genome_status(genome_data["final"], reflib_dir)
    if status == "installed":
        if not interactive:
            return process_reference_file(final_path)
        print(f"\n{genome_data['final']} is already installed.")
        choice = input("Re-download anyway? [y/N]: ").strip().lower()
        if choice != "y":
            return True
        os.remove(final_path)
    elif status == "incomplete" and interactive:
        print(f"\n{genome_data['final']} is incomplete.")
        choice = input("[R]esume, [D]elete, or [C]ancel? ").strip().lower()
        if choice == "c":
            return False
        if choice == "d":
            delete_genome(genome_data["final"], reflib_dir)
            return False
        # 'r' continues to download_file below

    logging.info(f"Downloading {genome_data['label']} from {genome_data['source']}...")

    success = download_file(
        genome_data["url"], final_path, progress_callback, cancel_event
    )
    if not success:
        return False

    return process_reference_file(final_path)


def process_reference_file(fasta_path: str):
    logging.info(f"Processing reference: {fasta_path}")
    bgzf_path = ensure_bgzf(fasta_path)
    if not bgzf_path:
        return False
    base_name = re.sub(r"\.(fasta|fna|fa)\.gz$", "", bgzf_path)
    dict_path = base_name + ".dict"
    try:
        run_command(["samtools", "dict", bgzf_path, "-o", dict_path])
        run_command(["samtools", "faidx", bgzf_path])
    except Exception as e:
        logging.error(f"Indexing failed: {e}")
        return False

    analyzer = ReferenceAnalyzer(bgzf_path, dict_path)
    analyzer.analyze()
    cataloger = ReferenceCataloger(bgzf_path, dict_path)
    cataloger.update_catalog()
    return True


def ensure_bgzf(path: str) -> str | None:
    try:
        res = run_command(
            ["samtools", "view", "-H", path], capture_output=True, check=False
        )
        if "BGZF" in res.stdout or "BGZF" in res.stderr:
            return path
    except Exception:
        pass
    logging.info(f"Recompressing {path} to BGZF format...")
    tmp_path = path + ".tmp.gz"
    try:
        if path.endswith(".gz"):
            with open(tmp_path, "wb") as f_out:
                p1 = subprocess.Popen(["gunzip", "-c", path], stdout=subprocess.PIPE)
                p2 = subprocess.Popen(["bgzip", "-c"], stdin=p1.stdout, stdout=f_out)
                if p1.stdout:
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
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
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
