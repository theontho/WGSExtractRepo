import os
import sys
import unittest
import tempfile
import shutil
import time
import subprocess
from unittest.mock import patch
from pathlib import Path
from dotenv import load_dotenv

# Path to the directory where this test is located (cli/tests/)
this_dir = Path(__file__).resolve().parent
# cli/ root (parent of tests/)
cli_root = this_dir.parent
# repo root (parent of cli/)
repo_root = cli_root.parent

# Ensure cli/src is in sys.path
cli_src = cli_root / "src"
if str(cli_src) not in sys.path:
    sys.path.insert(0, str(cli_src))

# Path to aconv.py
ACONV_PY = repo_root / "program" / "aconv.py"

# Load environment variables
env_local = cli_root / ".env.local"
env_std = cli_root / ".env"

if env_local.exists():
    load_dotenv(dotenv_path=env_local)
elif env_std.exists():
    load_dotenv(dotenv_path=env_std)

from wgsextract_cli.main import main

# Get paths from environment
REF_PATH = os.environ.get('WGSE_REF')
INPUT_PATH = os.environ.get('WGSE_INPUT')

# Check for --full-data flag in sys.argv
FULL_DATA = "--full-data" in sys.argv
if FULL_DATA:
    sys.argv.remove("--full-data")

class TestMicroarrayRealData(unittest.TestCase):
    """
    End-to-end test for microarray command using real genomic data.
    """
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wgse_microarray_real_")
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest(f"Real data paths not configured or missing: REF={REF_PATH}, INPUT={INPUT_PATH}")
        if FULL_DATA:
            print("\n!!! WARNING: Running in FULL DATA mode. This will be SLOW. !!!")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_microarray_generation_and_subsetting_real(self):
        """
        Test generating CombinedKit using real BAM/CRAM,
        and then subsetting it using aconv.py.
        """
        # 1. Generate CombinedKit
        args = [
            'wgsextract-cli', 
            '--outdir', self.test_dir, 
            '--ref', REF_PATH, 
            '--input', INPUT_PATH, 
            'microarray', 
        ]
        
        mode_str = "Full Genome" if FULL_DATA else "chrM"
        if not FULL_DATA:
            args.extend(['--region', 'chrM'])
        
        print(f"\n>>> Running microarray on real data ({mode_str})...")
        start_time = time.time()
        
        with patch.object(sys, 'argv', args):
            try:
                main()
            except SystemExit as e:
                self.assertEqual(e.code, 0, "CLI exited with non-zero code")
        
        duration = time.time() - start_time
        print(f"<<< CombinedKit generated in {duration:.2f}s")
        
        combined_txt = os.path.join(self.test_dir, "CombinedKit.txt")
        self.assertTrue(os.path.exists(combined_txt))
        
        # 2. Subset using aconv.py for 23andMe_V3
        # aconv.py usage: vendor_version source target microarray_reference_dir
        # It expects microarray_reference_dir to contain raw_file_templates/
        
        # We need to locate the microarray reference directory. 
        # In our project it is reference/microarray/
        # But we should use the one from REF_PATH if possible.
        microarray_ref = os.path.join(REF_PATH, "microarray")
        if not os.path.exists(microarray_ref):
            # Fallback to local if not in REF_PATH
            microarray_ref = str(repo_root / "reference" / "microarray")

        target_base = os.path.join(self.test_dir, "23andMe_V3_test")
        
        print(f">>> Subsetting CombinedKit for 23andMe_V3...")
        aconv_cmd = [
            sys.executable,
            str(ACONV_PY),
            "23andMe_V3",
            combined_txt,
            target_base,
            microarray_ref + "/"
        ]
        
        res = subprocess.run(aconv_cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"aconv.py failed: {res.stderr}")
        
        output_file = target_base + "_23andMe_V3.txt"
        self.assertTrue(os.path.exists(output_file), f"Subsetting output missing: {output_file}")
        self.assertGreater(os.path.getsize(output_file), 0, "Subsetting output is empty")
        
        with open(output_file, "r") as f:
            lines = f.readlines()
            header_count = sum(1 for line in lines if line.startswith("#"))
            data_count = len(lines) - header_count
            print(f"Generated 23andMe_V3 file with {data_count} SNPs")
            self.assertGreater(header_count, 0)

if __name__ == "__main__":
    unittest.main()
