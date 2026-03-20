import os
import sys
import unittest

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


class TestGracefulExit(unittest.TestCase):
    """
    Verification of CLI resilience against invalid user input.

    Goal: Ensure that the CLI handles missing arguments, incorrect commands, and other
    usage errors gracefully by providing informative error messages instead of
    crashing with a Python traceback.
    Tests run as subprocesses with a strict timeout to ensure immediate exit.
    """

    def check_command(self, cmd_args):
        """Helper to run a command as a subprocess and verify it exits fast and gracefully."""
        import subprocess

        # Ensure cli/src is in PYTHONPATH for the subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../src")
        )
        env["WGSE_SKIP_DOTENV"] = "1"

        # Strip any existing WGSE vars from current shell env
        for k in list(env.keys()):
            if k.startswith("WGSE_") and k != "WGSE_SKIP_DOTENV":
                del env[k]

        cmd = [sys.executable, "-m", "wgsextract_cli.main"] + cmd_args

        try:
            # Strict 3 second timeout as requested.
            # We pass empty input to stdin to avoid hangs in commands that read from stdin (repair).
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3, env=env, input=""
            )
            output = res.stdout + res.stderr

            # The main goal is no traceback and fast exit
            self.assertNotIn(
                "Traceback",
                output,
                f"Traceback found in output of {' '.join(cmd_args)}",
            )

            # Streaming tools (repair) might produce no output if stdin is empty, which is fine.
            # Others should at least print help or an error.
            if "repair" not in cmd_args:
                self.assertTrue(
                    len(output) > 0, f"Command {' '.join(cmd_args)} produced no output"
                )

        except subprocess.TimeoutExpired:
            self.fail(
                f"Command {' '.join(cmd_args)} timed out after 3s (should have exited immediately)"
            )
        except Exception as e:
            self.fail(f"Command {' '.join(cmd_args)} failed to run: {e}")

    def test_00_help(self):
        self.check_command(["--help"])

    def test_01_info(self):
        self.check_command(["info"])

    def test_02_info_detailed(self):
        self.check_command(["info", "--detailed"])

    def test_03_info_calc_cov(self):
        self.check_command(["info", "calculate-coverage"])

    def test_04_info_cov_samp(self):
        self.check_command(["info", "coverage-sample"])

    def test_05_bam_sort(self):
        self.check_command(["bam", "sort"])

    def test_06_bam_index(self):
        self.check_command(["bam", "index"])

    def test_07_bam_unindex(self):
        self.check_command(["bam", "unindex"])

    def test_08_bam_unsort(self):
        self.check_command(["bam", "unsort"])

    def test_09_bam_tocram(self):
        self.check_command(["bam", "to-cram"])

    def test_10_bam_tobam(self):
        self.check_command(["bam", "to-bam"])

    def test_11_bam_unalign(self):
        self.check_command(["bam", "unalign"])

    def test_12_extract_bam_subset(self):
        self.check_command(["extract", "bam-subset"])

    def test_13_extract_mito(self):
        self.check_command(["extract", "mito"])

    def test_14_extract_ydna(self):
        self.check_command(["extract", "ydna"])

    def test_15_extract_unmapped(self):
        self.check_command(["extract", "unmapped"])

    def test_16_vcf_snp(self):
        self.check_command(["vcf", "snp"])

    def test_17_vcf_indel(self):
        self.check_command(["vcf", "indel"])

    def test_18_vcf_annotate(self):
        self.check_command(["vcf", "annotate"])

    def test_19_vcf_filter(self):
        self.check_command(["vcf", "filter"])

    def test_20_qc_vcf(self):
        self.check_command(["qc", "vcf"])

    def test_21_microarray(self):
        self.check_command(["microarray"])

    def test_22_lineage_mtdna(self):
        self.check_command(["lineage", "mt-haplogroup"])

    def test_23_lineage_ydna(self):
        self.check_command(["lineage", "y-haplogroup"])

    def test_24_repair_bam(self):
        self.check_command(["repair", "ftdna-bam"])

    def test_25_repair_vcf(self):
        self.check_command(["repair", "ftdna-vcf"])

    def test_26_qc_fastp(self):
        self.check_command(["qc", "fastp"])

    def test_27_qc_fastqc(self):
        self.check_command(["qc", "fastqc"])

    def test_28_qc_cov_wgs(self):
        self.check_command(["qc", "coverage-wgs"])

    def test_29_qc_cov_wes(self):
        self.check_command(["qc", "coverage-wes"])

    def test_30_pet_align(self):
        self.check_command(["pet-align"])

    def test_31_bam_identify(self):
        self.check_command(["bam", "identify"])

    def test_32_ref_download(self):
        self.check_command(["ref", "download"])

    def test_33_ref_index(self):
        self.check_command(["ref", "index"])

    def test_34_align(self):
        self.check_command(["align"])


if __name__ == "__main__":
    unittest.main()
