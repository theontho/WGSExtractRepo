import os
import shutil
import subprocess

import pytest

from tests.smoke_utils import (
    assert_log_contains,
    check_tool,
    ensure_fake_data,
    run_cli,
    verify_bam,
    verify_vcf,
)

# Base directory for the CLI project
CLI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_DIR = os.path.join(CLI_ROOT, "out/fake_30x")


@pytest.fixture(scope="session", autouse=True)
def shared_fake_data():
    """Ensure fake data exists for all tests in this session."""
    ensure_fake_data(FAKE_DIR)


class TestPerformanceBoostSmoke:
    """Ported from test_perf_boost.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.r1 = os.path.join(self.outdir, "fake_R1.fastq.gz")
        self.r2 = os.path.join(self.outdir, "fake_R2.fastq.gz")

        # Generate small FASTQ
        run_cli(
            [
                "qc",
                "fake-data",
                "--outdir",
                self.outdir,
                "--build",
                "hg38",
                "--type",
                "fastq",
                "--coverage",
                "0.01",
                "--seed",
                "42",
                "--ref",
                self.outdir,
            ]
        )
        import glob

        self.ref = glob.glob(os.path.join(self.outdir, "fake_ref_hg38_*.fa"))[0]

    @pytest.mark.skipif(
        not check_tool("bwa") or not check_tool("samtools"),
        reason="bwa or samtools missing",
    )
    def test_performance_boost_usage(self):
        # Run alignment and check if optimized tools are used
        rc, stdout, stderr = run_cli(
            [
                "align",
                "--r1",
                self.r1,
                "--r2",
                self.r2,
                "--ref",
                self.ref,
                "--outdir",
                self.outdir,
                "--debug",
            ]
        )
        assert rc == 0
        assert verify_bam(os.path.join(self.outdir, "fake_R1_aligned.bam"))

        # Check for sambamba and samblaster in logs if they are installed
        if check_tool("sambamba") and os.uname().sysname != "Darwin":
            assert "sambamba sort" in stdout or "sambamba sort" in stderr

        if check_tool("samblaster"):
            assert "Using samblaster" in stdout or "Using samblaster" in stderr


class TestExpertScenariosSmoke:
    """Ported from test_expert_scenarios.sh"""

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        self.bam = os.path.join(FAKE_DIR, "fake.bam")
        self.vcf = os.path.join(FAKE_DIR, "fake.vcf.gz")
        self.ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    def test_quiet_mode(self):
        # Verify quiet mode suppresses informational logs
        rc, stdout, stderr = run_cli(["info", "--input", self.bam, "--quiet"])
        assert rc == 0
        # Check that common info icons/tags are NOT present
        assert "ℹ️" not in stdout and "ℹ️" not in stderr

    @pytest.mark.skipif(not check_tool("samtools"), reason="samtools missing")
    def test_multi_region_extract(self, tmp_path):
        outdir = str(tmp_path)
        region = "chr1:1-1000,chr1:5000-6000"
        args = [
            "extract",
            "custom",
            "--input",
            self.bam,
            "--outdir",
            outdir,
            "--region",
            region,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        expected_bam = os.path.join(outdir, "fake_chr1_1-1000_chr1_5000-6000.bam")
        assert os.path.exists(expected_bam)
        assert verify_bam(expected_bam)

    @pytest.mark.skipif(not check_tool("bcftools"), reason="bcftools missing")
    def test_complex_vcf_filter(self, tmp_path):
        outdir = str(tmp_path)
        expr = "QUAL>10 && (POS<5000 || POS>10000)"
        args = [
            "vcf",
            "filter",
            "--input",
            self.vcf,
            "--outdir",
            outdir,
            "--expr",
            expr,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(os.path.join(outdir, "filtered.vcf.gz"), allow_empty=True)

    @pytest.mark.skipif(not check_tool("samtools"), reason="samtools missing")
    def test_bam_cram_consistency(self, tmp_path):
        outdir = str(tmp_path)
        cram = os.path.join(outdir, "consistency.cram")
        # Convert BAM to CRAM
        run_cli(
            [
                "bam",
                "to-cram",
                "--input",
                self.bam,
                "--ref",
                self.ref,
                "--outdir",
                outdir,
            ]
        )
        shutil.move(os.path.join(outdir, "fake.cram"), cram)

        # Run info and compare MD5
        rc1, out1, err1 = run_cli(["info", "--input", self.bam, "--quiet"])
        rc2, out2, err2 = run_cli(
            ["info", "--input", cram, "--ref", self.ref, "--quiet"]
        )

        import re

        def get_md5(text):
            m = re.search(r"MD5 Signature:\s+([a-f0-9]+)", text)
            return m.group(1) if m else None

        md5_bam = get_md5(out1)
        md5_cram = get_md5(out2)

        assert md5_bam is not None
        assert md5_bam == md5_cram


class TestSpecialPathsSmoke:
    """Ported from test_special_paths.sh"""

    def test_space_and_special_chars(self, tmp_path):
        # Create a directory with spaces and @#
        special_dir = os.path.join(tmp_path, "space dir @#")
        os.makedirs(special_dir)

        # Copy fake data there
        special_bam = os.path.join(special_dir, "fake data.bam")
        shutil.copy(os.path.join(FAKE_DIR, "fake.bam"), special_bam)

        rc, stdout, stderr = run_cli(["info", "--input", special_bam])
        assert rc == 0
        assert "Avg Read Length" in stdout or "Avg Read Length" in stderr


class TestMixedNamingSmoke:
    """Ported from test_mixed_chrom_naming.sh"""

    @pytest.mark.skipif(not check_tool("samtools"), reason="samtools missing")
    def test_mixed_chrom_naming_handling(self, tmp_path):
        outdir = str(tmp_path)
        # Create a BAM with '1' instead of 'chr1'
        alt_bam = os.path.join(outdir, "alt_naming.bam")
        header = os.path.join(outdir, "header.sam")
        with open(header, "w") as f:
            f.write("@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:1\tLN:1000000\n")

        subprocess.run(
            ["samtools", "view", "-H", os.path.join(FAKE_DIR, "fake.bam")],
            stdout=open(os.path.join(outdir, "orig_h.sam"), "w"),
        )
        # Replace chr1 with 1 in original BAM (this is a simplified mock of the scenario)
        subprocess.run(
            f"samtools view -h {os.path.join(FAKE_DIR, 'fake.bam')} | sed 's/chr1/1/g' | samtools view -b - > {alt_bam}",
            shell=True,
        )
        subprocess.run(["samtools", "index", alt_bam])

        # Reference still uses 'chr1'
        ref = os.path.join(FAKE_DIR, "fake_ref.fa")

        # Test if extract handles the mismatch (it should normalize)
        rc, stdout, stderr = run_cli(
            [
                "extract",
                "custom",
                "--input",
                alt_bam,
                "--outdir",
                outdir,
                "--region",
                "1:1-1000",
            ]
        )
        assert rc == 0
        assert verify_bam(os.path.join(outdir, "alt_naming_1_1-1000.bam"))
