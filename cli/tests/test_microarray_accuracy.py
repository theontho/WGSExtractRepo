import os
import random
import subprocess
import unittest
from pathlib import Path

from dotenv import load_dotenv

# Path setup
this_dir = Path(__file__).resolve().parent
cli_root = this_dir.parent
load_dotenv(dotenv_path=cli_root / ".env.local")

# Get paths from environment
REF_PATH = os.environ.get("WGSE_REF")
INPUT_PATH = os.environ.get("WGSE_INPUT")
OUT_DIR = os.environ.get("WGSE_OUTDIR", "/tmp/wgse_tests")


class TestMicroarrayAccuracy(unittest.TestCase):
    """
    Verifies that the genotypes called by the microarray command
    match the raw data in the source BAM/CRAM.
    """

    def setUp(self):
        if not REF_PATH or not INPUT_PATH or not os.path.exists(INPUT_PATH):
            self.skipTest("Real data paths not configured or missing.")

        # Find the most recent run in OUT_DIR or a specific test run
        # For this test, we expect a run to have already happened or we run a small one
        self.vcf_file = None
        base_name = os.path.basename(INPUT_PATH).split(".")[0]
        potential_vcf = os.path.join(
            OUT_DIR, "full_vendor_test", f"{base_name}_combined.vcf.gz"
        )

        if os.path.exists(potential_vcf):
            self.vcf_file = potential_vcf
        else:
            # Try micro_test dir
            potential_vcf = os.path.join(
                OUT_DIR, "micro_test", f"{base_name}_combined.vcf.gz"
            )
            if os.path.exists(potential_vcf):
                self.vcf_file = potential_vcf

        if not self.vcf_file:
            self.skipTest(f"No generated VCF found for verification in {OUT_DIR}")

        # Resolve reference FASTA
        from wgsextract_cli.core.utils import ReferenceLibrary, calculate_bam_md5

        md5_sig = calculate_bam_md5(INPUT_PATH)
        self.lib = ReferenceLibrary(REF_PATH, md5_sig)
        self.ref_fasta = self.lib.fasta

    def run_samtools_mpileup(self, chrom, pos):
        """Helper to get base at position from source BAM/CRAM."""
        if not chrom.startswith("chr") and "hs38" in self.ref_fasta:
            chrom = f"chr{chrom}"
        region = f"{chrom}:{pos}-{pos}"
        cmd = ["samtools", "mpileup", "-r", region, "-f", self.ref_fasta, INPUT_PATH]
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

    def test_genotype_concordance(self):
        """Pick 20 random SNPs from the VCF and verify against raw CRAM."""
        # 1. Get all SNPs from VCF
        cmd = ["bcftools", "query", "-f", "%CHROM\t%POS\t%ID\t[%TGT]\n", self.vcf_file]
        res = subprocess.run(cmd, capture_output=True, text=True)
        all_lines = res.stdout.strip().splitlines()

        if not all_lines:
            self.fail("VCF is empty")

        # 2. Pick 20 random ones
        sample_size = min(20, len(all_lines))
        test_snps = random.sample(all_lines, sample_size)

        print(f"\n>>> Verifying {sample_size} random SNPs from {self.vcf_file}...")
        failures = 0
        for line in test_snps:
            parts = line.split("\t")
            chrom, pos, rsid, tgt = parts[0], parts[1], parts[2], parts[3]
            vcf_geno = tgt.replace("/", "").replace("|", "").replace(".", "")

            if not vcf_geno:
                continue  # Skip no-calls

            raw_bases = self.run_samtools_mpileup(chrom, pos)

            # Check if all bases in VCF call are present in raw reads
            match = True
            if not raw_bases:
                print(f"[WARN] No coverage at {chrom}:{pos} ({rsid})")
                continue

            for b in vcf_geno:
                if b not in raw_bases:
                    match = False

            status = "✅" if match else "❌"
            print(
                f"  {rsid:<15} | {chrom + ':' + pos:<15} | VCF:{vcf_geno:<4} | RAW:{raw_bases:<10} | {status}"
            )

            if not match:
                failures += 1

        self.assertEqual(failures, 0, f"{failures} SNP calls did not match raw data.")


if __name__ == "__main__":
    unittest.main()
