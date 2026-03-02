import unittest
from unittest.mock import patch, MagicMock
import logging
import os
import sys

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wgsextract_cli.core.warnings import print_warning, check_free_space, format_time, EXPECTED_TIME, MESSAGES, get_free_space_needed

class TestWarnings(unittest.TestCase):
    """
    Verification of user communication and safety utilities.
    
    Goal: Ensure the correctness of time-estimation logic for long tasks, accurate 
    formatting of wait times, and precise calculation of disk space requirements 
    to prevent process failure due to insufficient storage.
    """

    def test_format_time(self):
        self.assertEqual(format_time(30), "30 seconds")
        self.assertEqual(format_time(120), "2 minutes")
        self.assertEqual(format_time(3600), "1.0 hours")
        self.assertEqual(format_time(7200), "2.0 hours")

    @patch('logging.warning')
    def test_print_warning_expected_time(self, mock_warning):
        # Test a standard action
        print_warning('GenBAMIndex')
        wait_time = EXPECTED_TIME['GenBAMIndex']
        time_str = format_time(wait_time)
        expected_msg = f"!!! WARNING: {MESSAGES['ExpectedWait'].format(time=time_str)} !!!"
        mock_warning.assert_any_call(expected_msg)

    @patch('logging.warning')
    def test_print_warning_with_threads(self, mock_warning):
        # Test parallelizable action
        action = 'ButtonAlignBAM'
        original_time = EXPECTED_TIME[action]
        
        # 1 thread
        print_warning(action, threads=1)
        time_str_1 = format_time(original_time)
        mock_warning.assert_any_call(f"!!! WARNING: {MESSAGES['ExpectedWait'].format(time=time_str_1)} !!!")
        
        # 8 threads
        mock_warning.reset_mock()
        print_warning(action, threads=8)
        # 8 ** 0.7 = 4.28
        adjusted_time = int(original_time / (8 ** 0.7))
        time_str_8 = format_time(adjusted_time)
        mock_warning.assert_any_call(f"!!! WARNING: {MESSAGES['ExpectedWait'].format(time=time_str_8)} !!!")

    @patch('logging.warning')
    def test_print_warning_free_space(self, mock_warning):
        # Manual values
        print_warning('infoFreeSpace', app_name='Sort', size_gb=100, final_gb=50)
        expected_msg = f"!!! {MESSAGES['infoFreeSpace'].format(app='Sort', size=100, final=50)} !!!"
        mock_warning.assert_any_call(expected_msg)
        
        # Dynamic calculation (60GB file)
        mock_warning.reset_mock()
        file_size = 60 * 10**9
        temp_needed, final_needed = get_free_space_needed(file_size, "Coord", False)
        # isize_gb = 60; temp_needed = 60*1 + 60 = 120; final_needed = 60
        self.assertEqual(temp_needed, 120)
        self.assertEqual(final_needed, 60)
        
        print_warning('infoFreeSpace', app_name='Coord Sort', file_size=file_size, is_cram=False)
        expected_msg_dynamic = f"!!! {MESSAGES['infoFreeSpace'].format(app='Coord Sort', size=120, final=60)} !!!"
        mock_warning.assert_any_call(expected_msg_dynamic)

    @patch('logging.warning')
    def test_print_warning_realign(self, mock_warning):
        print_warning('RealignBAMTimeWarnMesg', threads=4)
        cpus = 4
        estimated_hours = 5 + 160/cpus
        expected_msg = f"!!! {MESSAGES['RealignBAMTimeWarnMesg'].format(time=f'{estimated_hours:.1f}')} !!!"
        mock_warning.assert_any_call(expected_msg)

    @patch('logging.warning')
    def test_new_warnings(self, mock_warning):
        # Yoruba
        print_warning('YorubaWarning')
        mock_warning.assert_any_call(f"!!! {MESSAGES['YorubaWarning']} !!!")
        
        # Low Coverage
        mock_warning.reset_mock()
        print_warning('LowCoverageWarning')
        mock_warning.assert_any_call(f"!!! {MESSAGES['LowCoverageWarning']} !!!")
        
        # Long Read
        mock_warning.reset_mock()
        print_warning('LongReadSequenceWarning')
        mock_warning.assert_any_call(f"!!! {MESSAGES['LongReadSequenceWarning']} !!!")

    @patch('shutil.disk_usage')
    @patch('logging.warning')
    def test_check_free_space(self, mock_warning, mock_disk_usage):
        # Mock 10GB free
        mock_disk_usage.return_value = (100*1024**3, 90*1024**3, 10*1024**3)
        
        # Enough space
        self.assertTrue(check_free_space('.', 5))
        mock_warning.assert_not_called()
        
        # Not enough space
        self.assertFalse(check_free_space('.', 20))
        mock_warning.assert_called()

if __name__ == '__main__':
    unittest.main()
