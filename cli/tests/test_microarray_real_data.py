import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

# Path to the directory where this test is located (cli/tests/)
this_dir = Path(__file__).resolve().parent
# cli/ root (parent of tests/)
cli_root = this_dir.parent
# repo root (parent of cli/)
repo_root = cli_root.parent

# Ensure cli/src is in sys.path
cli_src = cli_root / "src"
if str(cli_src) not in sys.path:
    sys.path.insert(0, str(cli_src))

from wgsextract_cli.core.utils import ReferenceLibrary, calculate_bam_md5  # noqa: E402
from wgsextract_cli.main import main  # noqa: E402

# Load environment variables
env_local = cli_root / ".env.local"
env_std = cli_root / ".env"

if env_local.exists():
    load_dotenv(dotenv_path=env_local)
elif env_std.exists():
    load_dotenv(dotenv_path=env_std)

# Get paths from environment
REF_PATH = os.environ.get("WGSE_REF")
INPUT_PATH = os.environ.get("WGSE_INPUT")

# Check for --full-data flag in sys.argv
FULL_DATA = "--full-data" in sys.argv
if FULL_DATA:
    sys.argv.remove("--full-data")


class TestMicroarrayRealData(unittest.TestCase):
    """
    End-to-end test for microarray command using real genomic data.
    Verifies genotype accuracy against source BAM/CRAM for multiple vendors.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wgse_microarray_real_")
        if (
            not REF_PATH
            or not INPUT_PATH
            or not os.path.exists(REF_PATH)
            or not os.path.exists(INPUT_PATH)
        ):
            self.skipTest(
                f"Real data paths not configured or missing: REF={REF_PATH}, INPUT={INPUT_PATH}"
            )

        # --- ISOLATION: Symlink the input into the test directory ---
        ext = os.path.splitext(INPUT_PATH)[1]
        self.isolated_input = os.path.join(self.test_dir, f"input_isolated{ext}")
        os.symlink(INPUT_PATH, self.isolated_input)
        # -------------------------------------------------------------

        # Resolve reference FASTA for verification
        md5_sig = calculate_bam_md5(self.isolated_input)
        self.lib = ReferenceLibrary(REF_PATH, md5_sig)
        self.ref_fasta = self.lib.fasta

        if not self.ref_fasta or not os.path.exists(self.ref_fasta):
            self.skipTest(f"Reference FASTA not found: {self.ref_fasta}")

        # --- REGION DEPENDENCY: Index the isolated input ---
        subprocess.run(["samtools", "index", self.isolated_input], check=False)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def run_samtools_mpileup(self, chrom, pos):
        """Helper to get base at position from source BAM/CRAM."""
        if not chrom.startswith("chr"):
            chrom = f"chr{chrom}"
        region = f"{chrom}:{pos}-{pos}"
        cmd = [
            "samtools",
            "mpileup",
            "-r",
            region,
            "-f",
            self.ref_fasta,
            self.isolated_input,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            return None

        parts = res.stdout.strip().splitlines()[0].split("\t")
        if len(parts) < 5:
            return None
        ref_base, bases_str = parts[2].upper(), parts[4]
        called_bases = []
        i = 0
        while i < len(bases_str):
            b = bases_str[i]
            if b in ".,":
                called_bases.append(ref_base)
            elif b in "ACGTNacgt":
                called_bases.append(b.upper())
            elif b == "^":
                i += 1
            elif b in "+-":
                num_str = ""
                i += 1
                while i < len(bases_str) and bases_str[i].isdigit():
                    num_str += bases_str[i]
                    i += 1
                i += int(num_str) - 1
            i += 1
        return "".join(sorted(set(called_bases))) if called_bases else None

    def test_microarray_multi_vendor(self):
        """
        Runs microarray command for multiple vendors and verifies results.
        """
        # 1. Run CLI for 23andMe, Ancestry, and MyHeritage
        formats_to_test = ["23andme_v3", "ancestry_v2", "myheritage_v2"]
        args = [
            "wgsextract-cli",
            "--outdir",
            self.test_dir,
            "--ref",
            REF_PATH,
            "--input",
            self.isolated_input,
            "microarray",
            "--formats",
            ",".join(formats_to_test),
        ]

        if not FULL_DATA:
            args.extend(["--region", "chr1"])

        print("\n>>> Running multi-vendor microarray on real data...")
        with patch.object(sys, "argv", args):
            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)

        # 2. Verify Base CombinedKit.txt (GEDMATCH/All)
        base_txt = os.path.join(self.test_dir, "CombinedKit.txt")
        self.assertTrue(os.path.exists(base_txt), "Base CombinedKit.txt missing")
        with open(base_txt) as f:
            base_lines = [line for line in f if not line.startswith("#")]

        print(f"Base CombinedKit.txt generated with {len(base_lines)} SNPs")
        self.assertGreater(len(base_lines), 1000)

        # 3. Verify each vendor format
        verified_snps = {
            "rs3094315": {"hg19": "752566", "hg38": "817186"},
            "rs3131972": {"hg19": "752721", "hg38": "817341"},
        }

        vendor_files = {
            "23andme_v3": "CombinedKit_23andMe_V3.txt",
            "ancestry_v2": "CombinedKit_Ancestry_V2.txt",
            "myheritage_v2": "CombinedKit_MyHeritage_V2.csv",
        }

        for fmt_key, filename in vendor_files.items():
            zip_path = os.path.join(
                self.test_dir, filename.replace(".txt", ".zip").replace(".csv", ".zip")
            )
            self.assertTrue(
                os.path.exists(zip_path), f"Output ZIP missing for {fmt_key}"
            )

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.test_dir)

            out_path = os.path.join(self.test_dir, filename)
            self.assertTrue(
                os.path.exists(out_path), f"Extracted file missing for {fmt_key}"
            )

            with open(out_path) as f:
                lines = f.readlines()

            data_lines = [
                line.strip()
                for line in lines
                if not line.startswith("#") and line.strip()
            ]
            print(f"Format {fmt_key}: {len(data_lines)} SNPs")
            self.assertGreater(len(data_lines), 10000)

            # Check specific SNPs in this vendor file
            delimiter = "," if filename.endswith(".csv") else "\t"
            for line in data_lines:
                # Remove quotes for CSV formats like MyHeritage
                parts = line.replace('"', "").split(delimiter)
                if len(parts) < 4:
                    continue

                snp_id = parts[0]
                if snp_id in verified_snps:
                    v = verified_snps[snp_id]
                    # Genotype is the last field (or last two for Ancestry)
                    genotype = "".join(parts[3:]).replace("\t", "").replace(" ", "")

                    source_geno = self.run_samtools_mpileup("chr1", v["hg38"])
                    if source_geno:
                        print(
                            f"[{fmt_key}] SNP {snp_id}: Output={genotype}, Source={source_geno}"
                        )
                        for b in genotype:
                            if b not in "-0":  # Skip uncalled
                                self.assertIn(b, source_geno)

        print("<<< Multi-vendor verification complete.")


if __name__ == "__main__":
    unittest.main()
