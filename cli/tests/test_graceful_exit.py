import unittest
from unittest.mock import patch
import sys
import io
import logging
from contextlib import redirect_stderr, redirect_stdout

# Ensure cli/src is in sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wgsextract_cli.main import main

class TestGracefulExit(unittest.TestCase):

    def check_command(self, cmd_args):
        """Helper to run a command and verify it exits gracefully (no traceback)."""
        full_args = ['wgsextract-cli'] + cmd_args
        stderr_buf = io.StringIO()
        stdout_buf = io.StringIO()
        
        # Reset logging to use our StringIO if needed, but usually logging.error goes to stderr
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        handler = logging.StreamHandler(stderr_buf)
        root.addHandler(handler)

        try:
            with redirect_stderr(stderr_buf), redirect_stdout(stdout_buf):
                with patch.object(sys, 'argv', full_args):
                    main()
            # If it returns normally, it might be an internal check returning None
        except SystemExit as e:
            # argparse exit (2) or explicit sys.exit
            pass
        except Exception as e:
            self.fail(f"Command {' '.join(cmd_args)} crashed with {type(e).__name__}: {e}")
        
        error_output = stderr_buf.getvalue() + stdout_buf.getvalue()
        
        # We expect SOME error message if it's an invalid command/missing args
        self.assertTrue(len(error_output) > 0, f"Command {' '.join(cmd_args)} produced no output")
        self.assertNotIn("Traceback", error_output)
        
        # Clean up logging handler
        root.removeHandler(handler)

    def test_base_command(self):
        self.check_command([])

    def test_info(self):
        self.check_command(['info']) # missing --input

    def test_bam_sort(self):
        self.check_command(['bam', 'sort']) # missing --input

    def test_vcf_snp(self):
        self.check_command(['vcf', 'snp']) # missing --input

    def test_qc_fastp(self):
        self.check_command(['qc', 'fastp']) # missing --r1

    def test_align(self):
        self.check_command(['align']) # missing --r1

    def test_microarray(self):
        self.check_command(['microarray']) # missing --ref-vcf-tab

if __name__ == '__main__':
    unittest.main()
