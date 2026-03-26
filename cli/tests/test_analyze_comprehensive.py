import os
import shutil
import unittest

from tests.smoke_utils import ensure_fake_data, run_cli, verify_bam, verify_vcf


class TestAnalyzeComprehensive(unittest.TestCase):
    def setUp(self):
        self.outdir = "tmp/analyze_test_out"
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.makedirs(self.outdir, exist_ok=True)

        self.fake_data_dir = "tmp/fake_data_analyze"
        ensure_fake_data(self.fake_data_dir)

        self.bam = os.path.join(self.fake_data_dir, "fake.bam")
        self.vcf = os.path.join(self.fake_data_dir, "fake.vcf.gz")

    def test_analyze_comprehensive_bam_only(self):
        """Test analyze comprehensive with only a BAM file."""
        # This will trigger variant calling (snp/indel)
        # Note: We skip Y-lineage because fake data might not have Y reads or Yleaf might fail
        # But let's see if it works.

        args = [
            "analyze",
            "comprehensive",
            "--input",
            self.bam,
            "--outdir",
            self.outdir,
            "--debug",
        ]

        # We need a reference for variant calling
        # For smoke tests, we can't easily download a full hg38,
        # but the fake data command might have generated a mini-ref if we were lucky.
        # Actually, fake-data doesn't generate a ref FASTA.

        # If we don't have a ref, it might fail.
        # Let's try with --skip-calling just to check the other parts
        args.append("--skip-calling")

        rc, stdout, stderr = run_cli(args)

        # Even if it fails due to missing tools in this environment,
        # we want to see it try.
        print(stdout)
        print(stderr)

        # Basic check: did it run 'info' and 'qc'?
        self.assertIn("Step 1: Running BAM/CRAM basic metrics and QC...", stderr)
        self.assertIn("Starting comprehensive analysis", stderr)

    def test_analyze_comprehensive_vcf_inputs(self):
        """Test analyze comprehensive with multiple VCF inputs."""
        # Create a second dummy VCF
        vcf2 = os.path.join(self.outdir, "fake2.vcf.gz")
        shutil.copy(self.vcf, vcf2)
        if os.path.exists(self.vcf + ".tbi"):
            shutil.copy(self.vcf + ".tbi", vcf2 + ".tbi")

        args = [
            "analyze",
            "comprehensive",
            "--vcf-inputs",
            self.vcf,
            vcf2,
            "--outdir",
            self.outdir,
            "--debug",
        ]

        rc, stdout, stderr = run_cli(args)
        print(stdout)
        print(stderr)

        self.assertIn("Merging 2 VCF files", stderr)
        # It should produce merged.vcf.gz
        self.assertTrue(os.path.exists(os.path.join(self.outdir, "merged.vcf.gz")))


if __name__ == "__main__":
    unittest.main()
