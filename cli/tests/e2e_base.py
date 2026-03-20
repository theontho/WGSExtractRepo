import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Load environment variables
from dotenv import load_dotenv  # noqa: E402
from wgsextract_cli.core.utils import ensure_vcf_indexed  # noqa: E402
from wgsextract_cli.core.warnings import EXPECTED_TIME, M1_PRO_ESTIMATES  # noqa: E402
from wgsextract_cli.main import main  # noqa: E402

cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_local = os.path.join(cli_root, ".env.local")
env_std = os.path.join(cli_root, ".env")

if os.path.exists(env_local):
    load_dotenv(dotenv_path=env_local)
if os.path.exists(env_std):
    load_dotenv(dotenv_path=env_std)

# Get paths from environment
REF_PATH = os.environ.get("WGSE_REF")
INPUT_PATH = os.environ.get("WGSE_INPUT")


class TestE2EBase(unittest.TestCase):
    """
    Base class for E2E tests. Subclasses define REGION and MODE.
    """

    REGION = "chrM"  # Default to focused
    MODE = "CHRM"

    @classmethod
    def setUpClass(cls):
        cls.results = []
        if (
            not REF_PATH
            or not INPUT_PATH
            or not os.path.exists(REF_PATH)
            or not os.path.exists(INPUT_PATH)
        ):
            print(
                "\n!!! WARNING: Configuration not found in environment or cli/.env.local"
            )
        print(f"\n!!! Running in {cls.MODE} mode. !!!")

    @classmethod
    def tearDownClass(cls):
        if not cls.results:
            return
        print("\n" + "=" * 105)
        print(f"{f'E2E {cls.MODE} EXECUTION & BENCHMARK REPORT':^105}")
        print("=" * 105)
        print(
            f"{'Command':<25} | {'Status':<13} | {'Duration':>11} | {'M1 Pro Ref':>11} | {'Expected':>11}"
        )
        print("-" * 105)
        passed = 0
        total_duration = 0
        cls.results.sort(key=lambda x: x["name"])
        for res in cls.results:
            if res["name"] == "05a unindexed extract":
                status = "EXPECTED_FAIL" if res["success"] else "UNEXPECTED_PASS"
            else:
                status = "PASS" if res["success"] else "FAIL"

            if res["success"]:
                passed += 1
            duration = res["duration"]
            total_duration += duration
            expected = res["expected"]

            m1_ref = "N/A"
            for key, val in M1_PRO_ESTIMATES.items():
                if key == res["expected_key"]:
                    m1_ref = f"{val:.2f}s"
                    break

            print(
                f"{res['name']:<25} | {status:<13} | {duration:>10.2f}s | {m1_ref:>11} | {expected:>10}s"
            )
        print("-" * 105)
        print(
            f"TOTAL REAL DATA ({cls.MODE}): {passed}/{len(cls.results)} passed. Total Time: {total_duration:.2f}s"
        )
        print("=" * 105)

    def record_result(self, name, success, duration, expected, expected_key=""):
        self.results.append(
            {
                "name": name,
                "success": success,
                "duration": duration,
                "expected": expected,
                "expected_key": expected_key,
            }
        )

    def run_real(self, name, args, expected_key, min_duration=0):
        if (
            not REF_PATH
            or not INPUT_PATH
            or not os.path.exists(REF_PATH)
            or not os.path.exists(INPUT_PATH)
        ):
            self.skipTest("Paths not configured or not found")

        test_dir = tempfile.mkdtemp(
            prefix=f"wgse_real_{name.replace(' ', '_').replace('(', '').replace(')', '')}_"
        )
        ext = os.path.splitext(INPUT_PATH)[1]
        isolated_input = os.path.join(test_dir, f"input_isolated{ext}")
        os.symlink(INPUT_PATH, isolated_input)

        # In Full mode, we remove region filters
        if self.REGION is None:
            new_args = []
            skip_next = False
            for _i, arg in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "--region" or arg == "-r":
                    skip_next = True
                    continue
                new_args.append(arg)
            args = new_args
            name = name.replace("(chrM)", "(Full)")
        else:
            # In focused mode, ensure the region is set if the command supports it
            if "-r" in args or "--region" in args:
                # Replace whatever region was there with self.REGION
                for i, arg in enumerate(args):
                    if arg == "-r" or arg == "--region":
                        args[i + 1] = self.REGION

        if (
            "--region" in args
            or "-r" in args
            or "extract" in args
            or "microarray" in args
        ):
            subprocess.run(["samtools", "index", isolated_input], check=False)

        expected_seconds = EXPECTED_TIME.get(expected_key, 0)
        start_time = time.perf_counter()

        print(f"\n>>> [REAL DATA] BEGIN: {name} (Expected: ~{expected_seconds}s)")

        success = False
        duration = 0
        start_time = time.perf_counter()
        try:
            full_args = ["wgsextract-cli", "--outdir", test_dir] + args
            full_args = [
                arg if arg != INPUT_PATH else isolated_input for arg in full_args
            ]

            with patch.object(sys, "argv", full_args):
                main()
                duration = time.perf_counter() - start_time
                if duration < min_duration:
                    print(
                        f"Error: {name} finished too fast ({duration:.2f}s < {min_duration}s)"
                    )
                    success = False
                else:
                    success = True
        except SystemExit as e:
            duration = time.perf_counter() - start_time
            if e.code == 0:
                if duration < min_duration:
                    print(
                        f"Error: {name} finished too fast ({duration:.2f}s < {min_duration}s)"
                    )
                    success = False
                else:
                    success = True
            else:
                print(f"Error: {name} exited with code {e.code}")
                success = False
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"Error in {name}: {e}")
            success = False
        finally:
            self.record_result(name, success, duration, expected_seconds, expected_key)
            shutil.rmtree(test_dir)
            status = "PASS" if success else "FAIL"
            print(f"<<< [REAL DATA] DONE: {name} ({status}) in {duration:.2f}s")

    def test_00_help(self):
        start = time.perf_counter()
        with (
            patch.object(sys, "argv", ["wgsextract-cli", "--help"]),
            redirect_stdout(io.StringIO()),
        ):
            try:
                main()
            except SystemExit:
                pass
        self.record_result(
            "00 help", True, time.perf_counter() - start, 0, "GetBAMHeader"
        )

    # --- INFO ---
    def test_01_info(self):
        self.run_real("01 info", ["info", "--input", INPUT_PATH], "ButtonBAMStats")

    def test_02_info_detailed(self):
        self.run_real(
            "02 info --detailed",
            ["info", "--detailed", "--input", INPUT_PATH, "--ref", REF_PATH],
            "ButtonBAMStats2",
        )

    # --- BAM ---
    def test_06_bam_sort_chrm(self):
        min_d = 300 if self.REGION is None else 0
        self.run_real(
            "06 bam sort (chrM)",
            [
                "bam",
                "sort",
                "--region",
                "chrM",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "GenSortedBAM",
            min_duration=min_d,
        )

    def test_07_bam_tocram_chrm(self):
        min_d = 60 if self.REGION is None else 0
        self.run_real(
            "07 bam to-cram (chrM)",
            [
                "bam",
                "to-cram",
                "--region",
                "chrM",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "BAMtoCRAM",
            min_duration=min_d,
        )

    # --- EXTRACT ---
    def test_10_extract_mito(self):
        self.run_real(
            "10 extract mito",
            ["extract", "mito", "--input", INPUT_PATH, "--ref", REF_PATH],
            "ButtonMitoBAM",
        )

    # --- VCF ---
    def test_13_vcf_snp_chrm(self):
        min_d = 1800 if self.REGION is None else 0
        self.run_real(
            "13 vcf snp (chrM)",
            [
                "vcf",
                "snp",
                "--region",
                "chrM",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "ButtonSNPVCF",
            min_duration=min_d,
        )

    # --- NEW FEATURES ---

    def test_31_extract_mt_bam(self):
        self.run_real(
            "31 extract mt-bam",
            ["extract", "mt-bam", "--input", INPUT_PATH, "--ref", REF_PATH],
            "ButtonMitoBAM",
        )

    def test_32_vcf_freebayes_chrm(self):
        min_d = 1800 if self.REGION is None else 0
        self.run_real(
            "32 vcf freebayes (chrM)",
            [
                "vcf",
                "freebayes",
                "-r",
                "chrM",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "ButtonSNPVCF",
            min_duration=min_d,
        )

    def test_37_vcf_gatk_chrm(self):
        # Only run if GATK jar is present
        from wgsextract_cli.core.dependencies import get_jar_path

        if not get_jar_path("gatk-package-4.1.9.0-local.jar"):
            self.skipTest("GATK jar not found")
        min_d = 3600 if self.REGION is None else 0
        self.run_real(
            "37 vcf gatk (chrM)",
            ["vcf", "gatk", "-r", "chrM", "--input", INPUT_PATH, "--ref", REF_PATH],
            "ButtonSNPVCF",
            min_duration=min_d,
        )

    def test_38_vcf_deepvariant_chrm(self):
        # Only run if run_deepvariant is in PATH
        if shutil.which("run_deepvariant") is None:
            self.skipTest("run_deepvariant not found in PATH")
        min_d = 3600 if self.REGION is None else 0
        self.run_real(
            "38 vcf deepvariant (chrM)",
            [
                "vcf",
                "deepvariant",
                "-r",
                "chrM",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "ButtonSNPVCF",
            min_duration=min_d,
        )

    def test_33_vcf_filter_gene(self):
        self.run_real(
            "33 vcf filter --gene BRCA1",
            [
                "vcf",
                "filter",
                "--gene",
                "BRCA1",
                "--input",
                INPUT_PATH,
                "--ref",
                REF_PATH,
            ],
            "ButtonBAMStats",
        )

    def test_34_vcf_trio_denovo(self):
        td = tempfile.mkdtemp()
        try:
            vcf_header = '##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n'
            vcf_line = "chrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t"

            with open(os.path.join(td, "child.vcf"), "w") as f:
                f.write(vcf_header + vcf_line + "0/1\n")
            with open(os.path.join(td, "mom.vcf"), "w") as f:
                f.write(vcf_header + vcf_line + "0/0\n")
            with open(os.path.join(td, "dad.vcf"), "w") as f:
                f.write(vcf_header + vcf_line + "0/0\n")

            for f in ["child.vcf", "mom.vcf", "dad.vcf"]:
                subprocess.run(["bgzip", os.path.join(td, f)], check=True)
                ensure_vcf_indexed(os.path.join(td, f + ".gz"))

            self.run_real(
                "34 vcf trio denovo",
                [
                    "vcf",
                    "trio",
                    "--proband",
                    os.path.join(td, "child.vcf.gz"),
                    "--mother",
                    os.path.join(td, "mom.vcf.gz"),
                    "--father",
                    os.path.join(td, "dad.vcf.gz"),
                    "--mode",
                    "denovo",
                ],
                "ButtonBAMStats",
            )
        finally:
            shutil.rmtree(td)

    def test_35_vcf_cnv_chrm(self):
        min_d = 300 if self.REGION is None else 0
        self.run_real(
            "35 vcf cnv (chrM)",
            ["vcf", "cnv", "--input", INPUT_PATH, "--ref", REF_PATH],
            "ButtonBAMStats2",
            min_duration=min_d,
        )

    def test_36_vep_chrm_offline(self):
        cache_dir = os.path.expanduser("~/.vep")
        if not os.path.exists(cache_dir):
            self.skipTest("VEP cache not found, skipping offline E2E test")

        td = tempfile.mkdtemp()
        try:
            vcf = os.path.join(td, "test.vcf.gz")
            p1 = subprocess.Popen(
                [
                    "bcftools",
                    "mpileup",
                    "-r",
                    "chrM:1-1000",
                    "-f",
                    REF_PATH,
                    INPUT_PATH,
                    "-Ou",
                ],
                stdout=subprocess.PIPE,
            )
            p2 = subprocess.Popen(
                ["bcftools", "call", "-mv", "-Oz", "-o", vcf], stdin=p1.stdout
            )
            p1.stdout.close()
            p2.communicate()

            if not os.path.exists(vcf) or os.path.getsize(vcf) < 100:
                self.skipTest("Could not generate variants for VEP test slice")

            ensure_vcf_indexed(vcf)
            self.run_real(
                "36 vep offline (chrM)",
                ["vep", "--input", vcf, "--ref", REF_PATH, "--format", "vcf"],
                "ButtonBAMStats2",
            )
        finally:
            shutil.rmtree(td)
