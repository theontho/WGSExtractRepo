import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


class TestRobustness(unittest.TestCase):
    """
    Validation of CLI stability under common operational edge cases.

    Goal: Check that the CLI handles invalid path types (e.g., directory instead of file)
    and subprocess failures without unexpected crashes, maintaining system integrity.
    Tests run as isolated subprocesses with a strict timeout.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="wgse_robust_")
        cls.dummy_dir = os.path.join(cls.test_dir, "is_a_directory")
        os.makedirs(cls.dummy_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)

    def run_robust(self, name, args):
        """Helper to run a command with an INVALID path (directory where file expected)."""
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../src")
        )
        env["WGSE_SKIP_DOTENV"] = "1"
        for k in list(env.keys()):
            if k.startswith("WGSE_") and k != "WGSE_SKIP_DOTENV":
                del env[k]

        cmd = [sys.executable, "-m", "wgsextract_cli.main"] + args

        try:
            # Passing a directory (self.dummy_dir) where a file is expected should be handled gracefully.
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, env=env, input=""
            )
            output = res.stdout + res.stderr

            self.assertNotIn(
                "Traceback", output, f"Traceback found in robustness test of {name}"
            )
            # It should either print help, a clean error, or just exit.
        except subprocess.TimeoutExpired:
            self.fail(f"Robustness test for {name} timed out after 5s")
        except Exception as e:
            self.fail(f"Robustness test for {name} failed to run: {e}")

    def test_00_help(self):
        self.run_robust("help", ["--help"])

    # Passing self.dummy_dir instead of a file to trigger path validation logic
    def test_01_info(self):
        self.run_robust("info", ["--input", self.dummy_dir, "info"])

    def test_02_info_detailed(self):
        self.run_robust(
            "info --detailed", ["--input", self.dummy_dir, "info", "--detailed"]
        )

    def test_03_info_calc_cov(self):
        self.run_robust(
            "info calculate-coverage",
            ["--input", self.dummy_dir, "info", "calculate-coverage"],
        )

    def test_04_info_cov_samp(self):
        self.run_robust(
            "info coverage-sample",
            ["--input", self.dummy_dir, "info", "coverage-sample"],
        )

    def test_05_bam_sort(self):
        self.run_robust("bam sort", ["--input", self.dummy_dir, "bam", "sort"])

    def test_06_bam_index(self):
        self.run_robust("bam index", ["--input", self.dummy_dir, "bam", "index"])

    def test_07_bam_unindex(self):
        self.run_robust("bam unindex", ["--input", self.dummy_dir, "bam", "unindex"])

    def test_08_bam_unsort(self):
        self.run_robust("bam unsort", ["--input", self.dummy_dir, "bam", "unsort"])

    def test_09_bam_tocram(self):
        self.run_robust("bam to-cram", ["--input", self.dummy_dir, "bam", "to-cram"])

    def test_10_bam_tobam(self):
        self.run_robust("bam to-bam", ["--input", self.dummy_dir, "bam", "to-bam"])

    def test_11_bam_unalign(self):
        self.run_robust(
            "bam unalign",
            ["--input", self.dummy_dir, "bam", "unalign", "--r1", "r1", "--r2", "r2"],
        )

    def test_12_extract_bam_subset(self):
        self.run_robust(
            "extract bam-subset",
            ["--input", self.dummy_dir, "extract", "bam-subset", "-f", "0.1"],
        )

    def test_13_extract_mito(self):
        self.run_robust("extract mito", ["--input", self.dummy_dir, "extract", "mito"])

    def test_14_extract_ydna(self):
        self.run_robust("extract ydna", ["--input", self.dummy_dir, "extract", "ydna"])

    def test_15_extract_unmapped(self):
        self.run_robust(
            "extract unmapped",
            [
                "--input",
                self.dummy_dir,
                "extract",
                "unmapped",
                "--r1",
                "u1",
                "--r2",
                "u2",
            ],
        )

    def test_16_vcf_snp(self):
        self.run_robust("vcf snp", ["--input", self.dummy_dir, "vcf", "snp"])

    def test_17_vcf_indel(self):
        self.run_robust("vcf indel", ["--input", self.dummy_dir, "vcf", "indel"])

    def test_18_vcf_annotate(self):
        self.run_robust(
            "vcf annotate",
            [
                "--input",
                self.dummy_dir,
                "vcf",
                "annotate",
                "--ann-vcf",
                self.dummy_dir,
                "--cols",
                "ID",
            ],
        )

    def test_19_vcf_filter(self):
        self.run_robust(
            "vcf filter",
            ["--input", self.dummy_dir, "vcf", "filter", "--expr", "QUAL>30"],
        )

    def test_20_qc_vcf(self):
        self.run_robust("qc vcf", ["--input", self.dummy_dir, "qc", "vcf"])

    def test_21_microarray(self):
        self.run_robust("microarray", ["--input", self.dummy_dir, "microarray"])

    def test_22_lineage_mtdna(self):
        self.run_robust(
            "lineage mt-haplogroup",
            ["--input", self.dummy_dir, "lineage", "mt-haplogroup"],
        )

    def test_23_lineage_ydna(self):
        self.run_robust(
            "lineage y-haplogroup",
            ["--input", self.dummy_dir, "lineage", "y-haplogroup"],
        )

    def test_24_repair_bam(self):
        self.run_robust(
            "repair ftdna-bam", ["--input", self.dummy_dir, "repair", "ftdna-bam"]
        )

    def test_25_repair_vcf(self):
        self.run_robust(
            "repair ftdna-vcf", ["--input", self.dummy_dir, "repair", "ftdna-vcf"]
        )

    def test_26_qc_fastp(self):
        self.run_robust("qc fastp", ["qc", "fastp", "--r1", self.dummy_dir])

    def test_27_qc_fastqc(self):
        self.run_robust("qc fastqc", ["qc", "fastqc", "--fastq", self.dummy_dir])

    def test_28_qc_cov_wgs(self):
        self.run_robust(
            "qc coverage-wgs", ["--input", self.dummy_dir, "qc", "coverage-wgs"]
        )

    def test_29_qc_cov_wes(self):
        self.run_robust(
            "qc coverage-wes",
            ["--input", self.dummy_dir, "qc", "coverage-wes", "--bed", self.dummy_dir],
        )

    def test_30_pet_align(self):
        self.run_robust(
            "pet-align",
            [
                "--input",
                self.dummy_dir,
                "pet-align",
                "--r1",
                self.dummy_dir,
                "--species",
                "dog",
                "--ref",
                self.dummy_dir,
            ],
        )

    def test_31_bam_identify(self):
        self.run_robust("bam identify", ["--input", self.dummy_dir, "bam", "identify"])

    def test_32_ref_download(self):
        self.run_robust(
            "ref download",
            ["ref", "download", "--url", "http://fake", "--out", self.dummy_dir],
        )

    def test_33_ref_index(self):
        self.run_robust("ref index", ["--ref", self.dummy_dir, "ref", "index"])

    def test_34_align(self):
        self.run_robust("align", ["align", "--r1", self.dummy_dir])


if __name__ == "__main__":
    unittest.main()
