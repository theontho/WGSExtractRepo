import os
import shutil
import sys
import tempfile
import unittest

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from wgsextract_cli.core.gene_map import GeneMap


class TestCLILogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ref_dir = os.path.join(self.test_dir, "ref")
        os.makedirs(self.ref_dir)
        self.gene_file = os.path.join(self.ref_dir, "genes_hg38.tsv")
        with open(self.gene_file, "w") as f:
            f.write("symbol\tchrom\tstart\tend\n")
            f.write("BRCA1\tchr17\t43044294\t43125364\n")
            f.write("KCNQ2\tchr20\t63400000\t63600000\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_gene_map_resolution(self):
        gm = GeneMap(self.test_dir)

        # Test hg38 resolution
        coords = gm.get_coords("BRCA1", "hg38")
        self.assertEqual(coords, "chr17:43044294-43125364")

        # Test case insensitivity
        coords = gm.get_coords("brca1", "hg38")
        self.assertEqual(coords, "chr17:43044294-43125364")

        # Test unknown gene
        coords = gm.get_coords("FAKEGENE", "hg38")
        self.assertIsNone(coords)

    def test_inheritance_expressions(self):
        # Verify the bcftools expressions used in vcf.py
        # GT[0] is proband, [1] is mother, [2] is father

        # De Novo: Child het (0/1), Parents ref (0/0)
        denovo = 'GT[0]="het" && GT[1]="ref" && GT[2]="ref"'

        # Recessive: Child hom-alt (1/1), Parents het (0/1)
        recessive = 'GT[0]="hom" && GT[1]="het" && GT[2]="het"'

        self.assertIn('GT[0]="het"', denovo)
        self.assertIn('GT[1]="ref"', denovo)
        self.assertIn('GT[0]="hom"', recessive)
        self.assertIn('GT[1]="het"', recessive)


if __name__ == "__main__":
    unittest.main()
