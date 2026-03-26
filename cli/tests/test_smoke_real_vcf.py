import os
import shutil
import subprocess

import pytest

from tests.smoke_utils import check_tool, ensure_fake_data, run_cli, verify_vcf

# --- DEPENDENCY CHECKS ---
BCFTOOLS_MISSING = not check_tool("bcftools")
SAMTOOLS_MISSING = not check_tool("samtools")
FREEBAYES_MISSING = not check_tool("freebayes")
TABIX_MISSING = not check_tool("tabix")
BGZIP_MISSING = not check_tool("bgzip")

# Base directory for the CLI project
CLI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_DIR = os.path.join(CLI_ROOT, "out/fake_30x")


@pytest.fixture(scope="session", autouse=True)
def shared_fake_data():
    """Ensure fake data exists for all tests in this session."""
    ensure_fake_data(FAKE_DIR)


class TestVcfBasicsSmoke:
    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_vcf = os.path.join(FAKE_DIR, "fake.vcf.gz")
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    @pytest.mark.skipif(BCFTOOLS_MISSING, reason="bcftools missing")
    def test_vcf_annotate(self):
        args = [
            "vcf",
            "annotate",
            "--input",
            self.fake_vcf,
            "--ann-vcf",
            self.fake_vcf,
            "--cols",
            "ID,QUAL",
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(os.path.join(self.outdir, "annotated.vcf.gz"))

    @pytest.mark.skipif(BCFTOOLS_MISSING, reason="bcftools missing")
    def test_vcf_filter(self):
        args = [
            "vcf",
            "filter",
            "--input",
            self.fake_vcf,
            "--expr",
            "QUAL>10",
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(
            os.path.join(self.outdir, "filtered.vcf.gz"), allow_empty=True
        )


class TestVcfCallingSmoke:
    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    @pytest.mark.skipif(FREEBAYES_MISSING or SAMTOOLS_MISSING, reason="tools missing")
    def test_vcf_freebayes(self):
        args = [
            "vcf",
            "freebayes",
            "--input",
            self.fake_bam,
            "--ref",
            self.fake_ref,
            "--outdir",
            self.outdir,
            "--region",
            "chrM",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(
            os.path.join(self.outdir, "freebayes.vcf.gz"), allow_empty=True
        )


class TestVcfTrioSmoke:
    @pytest.fixture(autouse=True)
    def setup_trio_data(self, tmp_path):
        self.outdir = str(tmp_path)
        vcf_header = '##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="G">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT'
        self.child_vcf, self.mom_vcf, self.dad_vcf = (
            os.path.join(self.outdir, f"{n}.vcf.gz") for n in ["c", "m", "f"]
        )
        for n, gt, p in [
            ("PROBAND", "0/1", self.child_vcf),
            ("MOTHER", "0/0", self.mom_vcf),
            ("FATHER", "0/0", self.dad_vcf),
        ]:
            raw = p.replace(".gz", "")
            with open(raw, "w") as f:
                f.write(
                    f"{vcf_header}\t{n}\nchrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t{gt}\n"
                )
            if check_tool("bgzip"):
                subprocess.run(["bgzip", "-f", raw])
                if check_tool("tabix"):
                    subprocess.run(["tabix", "-f", "-p", "vcf", p])

    @pytest.mark.skipif(BCFTOOLS_MISSING, reason="bcftools missing")
    def test_vcf_trio_denovo(self):
        args = [
            "vcf",
            "trio",
            "--proband",
            self.child_vcf,
            "--mother",
            self.mom_vcf,
            "--father",
            self.dad_vcf,
            "--mode",
            "denovo",
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(
            os.path.join(self.outdir, "trio_denovo.vcf.gz"), allow_empty=True
        )
