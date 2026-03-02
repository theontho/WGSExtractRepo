import unittest
import os
import tempfile
import shutil
from pathlib import Path

# Ensure cli/src is in sys.path
import sys
cli_src = Path(__file__).resolve().parent.parent / "src"
if str(cli_src) not in sys.path:
    sys.path.insert(0, str(cli_src))

from wgsextract_cli.core.microarray_utils import liftover_hg38_to_hg19, convert_to_vendor_format

class TestMicroarrayTranslation(unittest.TestCase):
    """
    Focused test for the translation logic from hg38 to hg19.
    Verifies coordinate shifts and chromosome normalization.
    """
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wgse_trans_test_")
        
        # We need a real chain file for pyliftover to work. 
        # We'll try to find it in the environment or workspace.
        self.chain_file = os.environ.get('WGSE_REF', '')
        if self.chain_file:
            self.chain_file = os.path.join(self.chain_file, "hg38ToHg19.over.chain.gz")
        
        if not os.path.exists(self.chain_file):
            # Fallback to standard workspace location
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.chain_file = str(repo_root / "reference" / "hg38ToHg19.over.chain.gz")

        if not os.path.exists(self.chain_file):
            self.skipTest(f"Liftover chain file not found at {self.chain_file}. Skipping translation verification.")

        # Templates dir for vendor formatting
        self.templates_dir = os.environ.get('WGSE_REF', '')
        if self.templates_dir:
            if not os.path.exists(os.path.join(self.templates_dir, "microarray", "raw_file_templates")):
                if not os.path.exists(os.path.join(self.templates_dir, "raw_file_templates")):
                    repo_root = Path(__file__).resolve().parent.parent.parent
                    self.templates_dir = str(repo_root / "reference" / "microarray")
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.templates_dir = str(repo_root / "reference" / "microarray")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_hg38_to_hg19_coordinate_shift(self):
        """
        Verify that specific hg38 coordinates are shifted to correct hg19 positions.
        """
        # Create a mock hg38 CombinedKit.txt
        # Format: ID, CHROM, POS, RESULT
        # rs3094315: hg38=817186 -> hg19=752566
        # rs12124819: hg38=841166 -> hg19=776546
        input_txt = os.path.join(self.test_dir, "input_hg38.txt")
        with open(input_txt, "w") as f:
            f.write("rs3094315\t1\t817186\tAG\n")
            f.write("rs12124819\t1\t841166\tAA\n")
            f.write("mt_test\tMT\t100\tCC\n") 
        
        output_txt = os.path.join(self.test_dir, "output_hg19.txt")
        
        # Run liftover
        liftover_hg38_to_hg19(input_txt, output_txt, self.chain_file)
        
        # Verify results
        with open(output_txt, "r") as f:
            lines = [l.strip().split("\t") for l in f if not l.startswith("#")]
        
        results = {l[0]: l for l in lines}
        
        self.assertIn("rs3094315", results)
        self.assertEqual(results["rs3094315"][2], "752566", "hg19 coordinate mismatch for rs3094315")
        self.assertEqual(results["rs3094315"][1], "1", "Chromosome normalization failed")
        
        self.assertIn("rs12124819", results)
        self.assertEqual(results["rs12124819"][2], "776546", "hg19 coordinate mismatch for rs12124819")
        
        self.assertIn("mt_test", results)
        self.assertEqual(results["mt_test"][1], "MT", "Mito chromosome normalization failed")

    def test_vendor_formatting_preservation(self):
        """
        Verify that genotypes and RSIDs are preserved when converting to vendor format.
        """
        # Templates root resolution (matching microarray_utils logic)
        templates_root = self.templates_dir
        if os.path.isdir(os.path.join(templates_root, "microarray", "raw_file_templates")):
            templates_root = os.path.join(templates_root, "microarray")
        
        if not os.path.exists(os.path.join(templates_root, "raw_file_templates")):
            self.skipTest(f"Microarray templates not found in {templates_root}. Skipping vendor format check.")

        # Create a mock hg19 CombinedKit.txt (what liftover produces)
        input_hg19 = os.path.join(self.test_dir, "kit_hg19.txt")
        with open(input_hg19, "w") as f:
            f.write("rs3094315\t1\t752566\tAG\n")
            f.write("rs3131972\t1\t752721\tGG\n")
        
        out_23andme = os.path.join(self.test_dir, "23andme_v3.txt")
        
        # Run formatting
        convert_to_vendor_format("23andMe_V3", input_hg19, out_23andme, templates_root)
        
        # Verify content
        with open(out_23andme, "r") as f:
            lines = f.readlines()
            
        data = [l.strip().split("\t") for l in lines if not l.startswith("#")]
        results = {l[0]: l for l in data}
        
        self.assertIn("rs3094315", results)
        self.assertEqual(results["rs3094315"][3], "AG", "Genotype lost in vendor conversion")
        self.assertEqual(results["rs3094315"][2], "752566", "Position mismatch in vendor output")
        
        self.assertIn("rs3131972", results)
        self.assertEqual(results["rs3131972"][3], "GG", "Genotype lost in vendor conversion")

if __name__ == "__main__":
    unittest.main()
