import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import io
import logging
from contextlib import redirect_stderr

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wgsextract_cli.main import main
from wgsextract_cli.core.utils import get_bam_header

class TestRobustness(unittest.TestCase):

    @patch('wgsextract_cli.commands.extract.verify_dependencies')
    @patch('wgsextract_cli.core.utils.calculate_bam_md5')
    @patch('wgsextract_cli.core.utils.run_command')
    @patch('wgsextract_cli.core.utils.os.path.isdir')
    @patch('wgsextract_cli.core.utils.os.path.isfile')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    def test_extract_mito_with_directory_ref(self, mock_exists, mock_isfile, mock_isdir, mock_run, mock_md5, mock_verify):
        """Test that passing a directory to --ref doesn't crash the app."""
        mock_md5.return_value = "unknown_md5"
        mock_isdir.return_value = True  # Pretend --ref is a directory
        mock_isfile.return_value = False # And not a file
        mock_exists.return_value = True # sample.bam exists
        mock_isfile.side_effect = lambda x: x == "sample.bam"
        
        # We need to mock get_chr_name too
        with patch('wgsextract_cli.commands.extract.get_chr_name') as mock_gcn:
            mock_gcn.return_value = "MT"
            
            test_args = ['wgsextract-cli', '--ref', '/some/dir/', '--input', 'sample.bam', 'extract', 'mito']
            
            stderr_buf = io.StringIO()
            # Capture logging too
            root = logging.getLogger()
            for handler in root.handlers[:]: root.removeHandler(handler)
            handler = logging.StreamHandler(stderr_buf)
            root.addHandler(handler)

            with redirect_stderr(stderr_buf):
                with patch.object(sys, 'argv', test_args):
                    main()
            
            output = stderr_buf.getvalue()
            # It should NOT have a traceback
            self.assertNotIn("Traceback", output)
            # It should have our error message
            self.assertIn("--ref is required (and must be a file)", output)
            root.removeHandler(handler)

    @patch('wgsextract_cli.core.utils.subprocess.run')
    def test_get_bam_header_no_file(self, mock_run):
        """Test that get_bam_header returns empty string on failure instead of crashing."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, 'samtools')
        
        header = get_bam_header("nonexistent.bam")
        self.assertEqual(header, "")

    @patch('wgsextract_cli.commands.info.verify_dependencies')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    def test_info_no_input_file(self, mock_exists, mock_verify):
        """Test that info command handles missing input file gracefully."""
        mock_exists.return_value = False # nonexistent.bam really doesn't exist
        test_args = ['wgsextract-cli', '--input', 'nonexistent.bam', 'info']
        
        stderr_buf = io.StringIO()
        root = logging.getLogger()
        for handler in root.handlers[:]: root.removeHandler(handler)
        handler = logging.StreamHandler(stderr_buf)
        root.addHandler(handler)

        with redirect_stderr(stderr_buf):
            with patch.object(sys, 'argv', test_args):
                main()
        
        output = stderr_buf.getvalue()
        self.assertIn("Required file for --input not found", output)
        self.assertNotIn("Traceback", output)
        root.removeHandler(handler)

if __name__ == '__main__':
    unittest.main()
