import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Load environment variables
from dotenv import load_dotenv  # noqa: E402

cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_local = os.path.join(cli_root, ".env.local")
env_std = os.path.join(cli_root, ".env")

if os.path.exists(env_local):
    load_dotenv(dotenv_path=env_local)
if os.path.exists(env_std):
    load_dotenv(dotenv_path=env_std)

from wgsextract_cli.main import main  # noqa: E402

# Paths for smoke tests (using placeholders or env)
REF_PATH = os.environ.get("WGSE_REF", "/tmp")
INPUT_PATH = os.environ.get("WGSE_INPUT", "/tmp/fake.bam")


class TestCLISmoke(unittest.TestCase):
    """
    Rapid plumbing verification using mocked tool execution.
    """

    @classmethod
    def setUpClass(cls):
        cls.results = []
        cls.test_dir = tempfile.mkdtemp(prefix="wgse_smoke_")
        cls.dummy_fastq = os.path.join(cls.test_dir, "dummy.fastq")
        with open(cls.dummy_fastq, "w") as f:
            f.write("@SEQ\nACTG\n+\n####\n")
        cls.dummy_vcf = os.path.join(cls.test_dir, "dummy.vcf.gz")
        with open(cls.dummy_vcf, "w") as f:
            f.write(
                "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            )
        cls.dummy_bed = os.path.join(cls.test_dir, "dummy.bed")
        with open(cls.dummy_bed, "w") as f:
            f.write("chrM\t1\t100\n")
        cls.dummy_ploidy = os.path.join(cls.test_dir, "ploidy.txt")
        with open(cls.dummy_ploidy, "w") as f:
            f.write("MT\t1\nY\t1\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)
        if not cls.results:
            return
        print("\n" + "=" * 60)
        print(f"{'COMPREHENSIVE SMOKE TEST REPORT (MOCKED)':^60}")
        print("=" * 60)
        passed = 0
        for res in cls.results:
            status = "PASS" if res["success"] else "FAIL"
            if res["success"]:
                passed += 1
            print(f"{res['name']:<35}: {status} {res.get('message', '')}")
        print("-" * 60)
        print(f"TOTAL SMOKE: {passed}/{len(cls.results)} passed.")
        print("=" * 60)

    def record_result(self, name, success, message=""):
        self.results.append({"name": name, "success": success, "message": message})

    def run_sub(self, name, args):
        """Helper to run a subcommand with mocks."""
        print(f">>> [SMOKE] BEGIN: {name}")

        def popen_side_effect(*args, **kwargs):
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (
                b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrM\tLN:16569\n",
                b"",
            )
            mock_proc.returncode = 0
            mock_proc.stdout = io.BytesIO(
                b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrM\tLN:16569\n"
            )
            return mock_proc

        _real_exists = os.path.exists
        _real_isfile = os.path.isfile

        def exists_side_effect(path):
            if not path:
                return False
            p = str(path)
            if any(
                x in p
                for x in [
                    ".env",
                    ".env.local",
                    "ploidy.txt",
                    ".py",
                    ".json",
                    ".tsv",
                    "ref/",
                ]
            ):
                return _real_exists(path)
            return True

        def isfile_side_effect(path):
            if not path:
                return False
            p = str(path)
            if any(
                x in p
                for x in [".env", ".env.local", "ploidy.txt", ".py", ".json", ".tsv"]
            ):
                return _real_isfile(path)
            return True

        success = False
        message = ""
        # Create dummy index files
        base_name = os.path.basename(INPUT_PATH)
        for s in [".bai", ".crai"]:
            with open(os.path.join(self.test_dir, base_name + s), "w") as f:
                f.write("d")

        # Command list for patching verify_dependencies in all modules
        cmds = [
            "bam",
            "vcf",
            "extract",
            "microarray",
            "lineage",
            "qc",
            "ref",
            "align",
            "vep",
            "info",
        ]
        patches = [
            patch(f"wgsextract_cli.commands.{c}.verify_dependencies") for c in cmds
        ]

        with patch("subprocess.Popen", side_effect=popen_side_effect), patch(
            "subprocess.run"
        ) as mock_run, patch("os.path.exists", side_effect=exists_side_effect), patch(
            "os.path.isfile", side_effect=isfile_side_effect
        ), patch("os.path.getsize", return_value=1024), patch("os.remove"), patch(
            "sys.stdin", io.StringIO("")
        ), patch("wgsextract_cli.core.dependencies.verify_dependencies"), patch(
            "wgsextract_cli.commands.info.run_full_coverage"
        ), patch("wgsextract_cli.commands.info.run_sampled_coverage"), patch(
            "wgsextract_cli.commands.info.calculate_bam_md5", return_value="dummy_md5"
        ):
            # Activate sub-module patches
            for p in patches:
                p.start()

            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                full_args = ["wgsextract-cli", "--outdir", self.test_dir] + args
                with patch.object(sys, "argv", full_args), redirect_stdout(
                    io.StringIO()
                ), redirect_stderr(io.StringIO()):
                    main()
                success = True
            except SystemExit as e:
                success = e.code == 0
                message = f"Exit {e.code}" if not success else ""
            except Exception as e:
                import traceback

                traceback.print_exc()
                message = f"Crashed: {type(e).__name__}: {str(e)}"
            finally:
                for p in patches:
                    p.stop()

        status = "PASS" if success else "FAIL"
        self.record_result(name, success, message)
        print(f"<<< [SMOKE] DONE: {name} ({status})")

    def test_00_help(self):
        try:
            with patch.object(
                sys, "argv", ["wgsextract-cli", "--help"]
            ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main()
            self.record_result("help", True)
        except SystemExit as e:
            self.record_result("help", e.code == 0)

    # --- INFO ---
    def test_01_info(self):
        self.run_sub("info", ["info", "--input", INPUT_PATH])

    def test_02_info_detailed(self):
        self.run_sub("info --detailed", ["info", "--input", INPUT_PATH, "--detailed"])

    def test_03_info_calc_cov(self):
        self.run_sub(
            "info calculate-coverage",
            ["info", "calculate-coverage", "--input", INPUT_PATH],
        )

    def test_04_info_cov_sample(self):
        self.run_sub(
            "info coverage-sample", ["info", "coverage-sample", "--input", INPUT_PATH]
        )

    # --- BAM ---
    def test_05_bam_sort(self):
        self.run_sub("bam sort", ["bam", "sort", "--input", INPUT_PATH])

    def test_06_bam_index(self):
        self.run_sub("bam index", ["bam", "index", "--input", INPUT_PATH])

    def test_07_bam_unindex(self):
        self.run_sub("bam unindex", ["bam", "unindex", "--input", INPUT_PATH])

    def test_08_bam_unsort(self):
        self.run_sub("bam unsort", ["bam", "unsort", "--input", INPUT_PATH])

    def test_09_bam_tocram(self):
        self.run_sub("bam to-cram", ["bam", "to-cram", "--input", INPUT_PATH])

    def test_10_bam_tobam(self):
        self.run_sub("bam to-bam", ["bam", "to-bam", "--input", INPUT_PATH])

    def test_11_bam_unalign(self):
        self.run_sub(
            "bam unalign",
            [
                "bam",
                "unalign",
                "--input",
                INPUT_PATH,
                "--r1",
                "out.r1",
                "--r2",
                "out.r2",
            ],
        )

    def test_12_bam_subset(self):
        self.run_sub(
            "bam subset", ["bam", "subset", "--input", INPUT_PATH, "-f", "0.1"]
        )

    # --- EXTRACT ---
    def test_13_extract_mito(self):
        self.run_sub(
            "extract mito",
            ["extract", "mito", "--input", INPUT_PATH, "--ref", REF_PATH],
        )

    def test_14_extract_y(self):
        self.run_sub(
            "extract y", ["extract", "y", "--input", INPUT_PATH, "--ref", REF_PATH]
        )

    def test_15_extract_unmapped(self):
        self.run_sub("extract unmapped", ["extract", "unmapped", "--input", INPUT_PATH])

    # --- VCF ---
    def test_16_vcf_snp(self):
        self.run_sub(
            "vcf snp", ["vcf", "snp", "--input", INPUT_PATH, "--ref", REF_PATH]
        )

    def test_17_vcf_indel(self):
        self.run_sub(
            "vcf indel", ["vcf", "indel", "--input", INPUT_PATH, "--ref", REF_PATH]
        )

    def test_18_vcf_annotate(self):
        self.run_sub(
            "vcf annotate",
            [
                "vcf",
                "annotate",
                "--input",
                self.dummy_vcf,
                "--ann-vcf",
                self.dummy_vcf,
                "--cols",
                "ID",
            ],
        )

    def test_19_vcf_filter(self):
        self.run_sub(
            "vcf filter",
            ["vcf", "filter", "--input", self.dummy_vcf, "--expr", "QUAL>30"],
        )

    def test_20_vcf_qc(self):
        self.run_sub("vcf qc", ["vcf", "qc", "--input", self.dummy_vcf])

    # --- MICROARRAY / LINEAGE ---
    def test_21_microarray(self):
        self.run_sub(
            "microarray", ["microarray", "--input", INPUT_PATH, "--ref", REF_PATH]
        )

    def test_22_lineage_mtdna(self):
        self.run_sub(
            "lineage mt-dna",
            [
                "lineage",
                "mt-dna",
                "--input",
                self.dummy_vcf,
                "--haplogrep-path",
                "fake.jar",
            ],
        )

    def test_23_lineage_ydna(self):
        self.run_sub(
            "lineage y-dna",
            [
                "lineage",
                "y-dna",
                "--input",
                INPUT_PATH,
                "--yleaf-path",
                "fake.py",
                "--pos-file",
                "fake.txt",
            ],
        )

    # --- REPAIR ---
    def test_24_repair_bam(self):
        self.run_sub("repair ftdna-bam", ["repair", "ftdna-bam", "--input", INPUT_PATH])

    def test_25_repair_vcf(self):
        self.run_sub(
            "repair ftdna-vcf", ["repair", "ftdna-vcf", "--input", self.dummy_vcf]
        )

    # --- QC ---
    def test_26_qc_fastp(self):
        self.run_sub(
            "qc fastp",
            ["qc", "fastp", "--r1", self.dummy_fastq, "--r2", self.dummy_fastq],
        )

    def test_27_qc_fastqc(self):
        self.run_sub("qc fastqc", ["qc", "fastqc", "--input", INPUT_PATH])

    # --- REF / ALIGN ---
    def test_30_ref_identify(self):
        self.run_sub("ref identify", ["ref", "identify", "--input", INPUT_PATH])

    def test_31_ref_download(self):
        self.run_sub(
            "ref download",
            ["ref", "download", "--url", "http://fake", "--out", "out.fa"],
        )

    def test_32_ref_index(self):
        self.run_sub("ref index", ["ref", "index", "--ref", "fake.fa"])

    def test_33_align_bwa(self):
        self.run_sub(
            "align bwa",
            [
                "align",
                "--ref",
                REF_PATH,
                "--r1",
                self.dummy_fastq,
                "--r2",
                self.dummy_fastq,
            ],
        )

    @patch("builtins.input", side_effect=["0"])
    @patch("wgsextract_cli.commands.ref.download_and_process_genome")
    def test_34_ref_library(self, mock_dl, mock_input):
        self.run_sub("ref library", ["ref", "library"])

    # --- NEW FEATURES ---
    def test_35_vep(self):
        self.run_sub("vep", ["vep", "--input", self.dummy_vcf, "--format", "vcf"])

    def test_36_vep_download(self):
        self.run_sub("vep download", ["vep", "download", "--assembly", "GRCh38"])

    def test_37_vcf_cnv(self):
        self.run_sub(
            "vcf cnv", ["vcf", "cnv", "--input", INPUT_PATH, "--ref", REF_PATH]
        )

    def test_38_vcf_sv(self):
        self.run_sub("vcf sv", ["vcf", "sv", "--input", INPUT_PATH, "--ref", REF_PATH])

    def test_39_vcf_freebayes(self):
        self.run_sub(
            "vcf freebayes",
            ["vcf", "freebayes", "--input", INPUT_PATH, "--ref", REF_PATH],
        )

    def test_40_vcf_trio(self):
        self.run_sub(
            "vcf trio",
            [
                "vcf",
                "trio",
                "--proband",
                self.dummy_vcf,
                "--mother",
                self.dummy_vcf,
                "--father",
                self.dummy_vcf,
                "--mode",
                "denovo",
            ],
        )

    def test_41_bam_mt_extract(self):
        self.run_sub(
            "bam mt-extract",
            ["bam", "mt-extract", "--input", INPUT_PATH, "--ref", REF_PATH],
        )

    def test_42_ref_download_genes(self):
        self.run_sub("ref download-genes", ["ref", "download-genes"])

    def test_43_vcf_filter_gene(self):
        gene_dir = os.path.join(self.test_dir, "ref")
        os.makedirs(gene_dir, exist_ok=True)
        with open(os.path.join(gene_dir, "genes_hg38.tsv"), "w") as f:
            f.write("symbol\tchrom\tstart\tend\nBRCA1\tchr17\t43044294\t43125364\n")
        self.run_sub(
            "vcf filter --gene",
            [
                "vcf",
                "filter",
                "--input",
                self.dummy_vcf,
                "--ref",
                self.test_dir,
                "--gene",
                "BRCA1",
            ],
        )


if __name__ == "__main__":
    unittest.main()
