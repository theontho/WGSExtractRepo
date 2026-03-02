import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wgsextract_cli.main import main

class TestCommandsIntegration(unittest.TestCase):

    @patch('wgsextract_cli.commands.align.verify_dependencies')
    @patch('wgsextract_cli.commands.align.print_warning')
    @patch('wgsextract_cli.commands.align.check_free_space')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    @patch('wgsextract_cli.core.utils.os.path.isfile')
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_align_calls_warning(self, mock_run, mock_popen, mock_isfile, mock_exists, mock_check_space, mock_print_warn, mock_verify):
        mock_exists.return_value = True
        mock_isfile.return_value = True 
        test_args = ['wgsextract-cli', '--ref', 'hg38.fa', 'align', '--r1', 'test.fastq']
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_print_warn.assert_any_call('ButtonAlignBAM', threads=unittest.mock.ANY)
        mock_check_space.assert_called()

    @patch('wgsextract_cli.commands.bam.verify_dependencies')
    @patch('wgsextract_cli.commands.bam.print_warning')
    @patch('wgsextract_cli.commands.bam.check_free_space')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    @patch('wgsextract_cli.core.utils.calculate_bam_md5')
    @patch('subprocess.Popen')
    def test_bam_sort_calls_warning(self, mock_popen, mock_md5, mock_exists, mock_check_space, mock_print_warn, mock_verify):
        mock_exists.return_value = True
        mock_md5.return_value = "dummy"
        mock_popen.return_value.returncode = 0
        test_args = ['wgsextract-cli', '--input', 'test.bam', 'bam', 'sort']
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_print_warn.assert_any_call('GenSortedBAM', threads=unittest.mock.ANY)
        mock_check_space.assert_called_with(unittest.mock.ANY, 100)

    @patch('wgsextract_cli.commands.vcf.verify_dependencies')
    @patch('wgsextract_cli.commands.vcf.print_warning')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    @patch('wgsextract_cli.core.utils.os.path.isfile')
    @patch('wgsextract_cli.core.utils.calculate_bam_md5')
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_vcf_snp_calls_warning(self, mock_run, mock_popen, mock_md5, mock_isfile, mock_exists, mock_print_warn, mock_verify):
        mock_exists.return_value = True
        mock_isfile.return_value = True 
        mock_md5.return_value = "dummy"
        test_args = ['wgsextract-cli', '--input', 'test.bam', '--ref', 'hg38.fa', 'vcf', 'snp', '--ploidy-file', 'p.txt']
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_print_warn.assert_any_call('ButtonSNPVCF', threads=unittest.mock.ANY)

    @patch('wgsextract_cli.commands.qc.verify_dependencies')
    @patch('wgsextract_cli.commands.qc.print_warning')
    @patch('wgsextract_cli.commands.qc.run_command')
    @patch('wgsextract_cli.core.utils.os.path.exists')
    def test_qc_fastp_calls_warning(self, mock_exists, mock_run_cmd, mock_print_warn, mock_verify):
        mock_exists.return_value = True
        test_args = ['wgsextract-cli', 'qc', 'fastp', '--r1', 'test.fastq']
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_print_warn.assert_any_call('ButtonFastp')

if __name__ == '__main__':
    unittest.main()
