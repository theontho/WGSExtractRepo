import glob
import os

import pytest

from tests.smoke_utils import check_tool, run_cli, verify_bam, verify_vcf


@pytest.mark.skipif(
    not os.environ.get("WGSE_PET_R1")
    or not os.environ.get("WGSE_PET_R2")
    or not os.environ.get("WGSE_PET_REF"),
    reason="WGSE_PET_R1/R2/REF environment variables not set",
)
class TestPetAlignSmoke:
    """Ported from test_pet_align_full.sh"""

    @pytest.fixture(autouse=True)
    def setup_pet(self, tmp_path):
        self.outdir = str(tmp_path)
        self.r1 = os.environ.get("WGSE_PET_R1")
        self.r2 = os.environ.get("WGSE_PET_R2")
        self.ref = os.environ.get("WGSE_PET_REF")

    @pytest.mark.skipif(
        not check_tool("bwa") and not check_tool("bwa-mem2"),
        reason="bwa or bwa-mem2 missing",
    )
    def test_pet_align_full(self):
        args = [
            "pet-align",
            "--r1",
            self.r1,
            "--r2",
            self.r2,
            "--ref",
            self.ref,
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0

        # Check for BAM/CRAM output
        align_files = glob.glob(os.path.join(self.outdir, "*.bam")) + glob.glob(
            os.path.join(self.outdir, "*.cram")
        )
        assert len(align_files) > 0
        assert verify_bam(align_files[0])

        # Check for VCF output
        vcf_files = glob.glob(os.path.join(self.outdir, "*.vcf.gz"))
        assert len(vcf_files) > 0
        assert verify_vcf(vcf_files[0])
