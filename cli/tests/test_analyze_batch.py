import csv
import os
import shutil
import unittest

from tests.smoke_utils import ensure_fake_data, run_cli


class TestAnalyzeBatch(unittest.TestCase):
    def setUp(self):
        self.outdir = "tmp/analyze_batch_test"
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.makedirs(self.outdir, exist_ok=True)

        self.scan_dir = os.path.join(self.outdir, "scan_dir")
        os.makedirs(self.scan_dir, exist_ok=True)

        # Create dummy sample files
        # Sample A: BAM + VCF
        os.makedirs(os.path.join(self.scan_dir, "sampleA"), exist_ok=True)
        self.sampleA_bam = os.path.join(self.scan_dir, "sampleA", "sampleA.bam")
        self.sampleA_vcf = os.path.join(self.scan_dir, "sampleA", "sampleA.vcf.gz")
        with open(self.sampleA_bam, "w") as f:
            f.write("dummy")
        with open(self.sampleA_vcf, "w") as f:
            f.write("dummy")

        # Sample B: CRAM
        os.makedirs(os.path.join(self.scan_dir, "sampleB"), exist_ok=True)
        self.sampleB_cram = os.path.join(self.scan_dir, "sampleB", "sampleB.cram")
        with open(self.sampleB_cram, "w") as f:
            f.write("dummy")

    def test_batch_gen(self):
        """Test generating a batch file from a directory."""
        batch_file = os.path.join(self.outdir, "batch.csv")
        args = [
            "analyze",
            "batch-gen",
            "--directory",
            self.scan_dir,
            "--output",
            batch_file,
        ]

        rc, stdout, stderr = run_cli(args)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(batch_file))

        with open(batch_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)

            # Check sampleA
            sampleA = next(r for r in rows if r["name"] == "sampleA")
            self.assertEqual(sampleA["input"], os.path.abspath(self.sampleA_bam))
            self.assertEqual(sampleA["vcf"], os.path.abspath(self.sampleA_vcf))

            # Check sampleB
            sampleB = next(r for r in rows if r["name"] == "sampleB")
            self.assertEqual(sampleB["input"], os.path.abspath(self.sampleB_cram))
            self.assertEqual(sampleB["vcf"], "")

    def test_batch_execution_mock(self):
        """Test that comprehensive --batch correctly iterates (mock/smoke)."""
        batch_file = os.path.join(self.outdir, "run_batch.csv")
        with open(batch_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "input", "vcf"])
            # Use real fake data to avoid immediate exit
            fake_dir = "tmp/fake_data_batch"
            ensure_fake_data(fake_dir)
            bam = os.path.abspath(os.path.join(fake_dir, "fake.bam"))
            vcf = os.path.abspath(os.path.join(fake_dir, "fake.vcf.gz"))

            writer.writerow(["Sample1", bam, vcf])
            writer.writerow(["Sample2", bam, ""])

        # Run with --skip-calling to avoid needing a full ref
        args = [
            "analyze",
            "comprehensive",
            "--batch",
            batch_file,
            "--outdir",
            self.outdir,
            "--skip-calling",
            "--debug",
        ]

        rc, stdout, stderr = run_cli(args)

        # Check logs for batch processing headers
        self.assertIn("### BATCH PROCESSING: Sample1", stdout)
        self.assertIn("### BATCH PROCESSING: Sample2", stdout)

        # Check that output directories were created
        self.assertTrue(os.path.exists(os.path.join(self.outdir, "Sample1")))
        self.assertTrue(os.path.exists(os.path.join(self.outdir, "Sample2")))


if __name__ == "__main__":
    unittest.main()
