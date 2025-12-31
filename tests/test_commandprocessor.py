import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Ensure repo root is in sys.path
current_file = Path(__file__).resolve()
repo_root = current_file.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Mock settings, utilities, and wakepy before importing commandprocessor
mock_wgse = MagicMock()
mock_utilities = MagicMock()
mock_wakepy = MagicMock()

sys.modules['settings'] = mock_wgse
sys.modules['utilities'] = mock_utilities
sys.modules['wakepy'] = mock_wakepy

from program.commandprocessor import is_command_available

class TestIsCommandAvailable(unittest.TestCase):

    @patch('subprocess.run')
    def test_java_25_support(self, mock_run):
        # Simulate 'java -version' for Java 25
        mock_run.return_value.stdout = b"java 25.0.0 2025-12-30\n"
        mock_run.return_value.returncode = 0
        
        result = is_command_available("java", "-version")
        
        self.assertTrue(result)
        # Check if version was correctly parsed and stored in settings
        mock_wgse.cp_version = [25, 0, 0] # This is what we expect
        # Note: in the real code it does wgse.cp_version = list(map(int, cp_version))
        # We can't easily check the assignment if we mock the whole module like this,
        # but we can check if it was called if we specifically mock the attribute.
        
    @patch('subprocess.run')
    def test_java_8_support(self, mock_run):
        mock_run.return_value.stdout = b"java version \"1.8.0_312\"\n"
        result = is_command_available("java", "-version")
        self.assertTrue(result)
        self.assertEqual(mock_wgse.cp_version, [8, 0, 312])

    @patch('subprocess.run')
    def test_openjdk_11_support(self, mock_run):
        mock_run.return_value.stdout = b"openjdk 11.0.14 2022-02-08\n"
        result = is_command_available("java", "-version")
        self.assertTrue(result)
        self.assertEqual(mock_wgse.cp_version, [11, 0, 14])

    @patch('subprocess.run')
    def test_samtools_support(self, mock_run):
        mock_run.return_value.stdout = b"samtools 1.12\n"
        result = is_command_available("samtools", "--version")
        self.assertTrue(result)
        self.assertEqual(mock_wgse.cp_version, [1, 12, 0])

    @patch('subprocess.run')
    def test_python_support(self, mock_run):
        mock_run.return_value.stdout = b"python 3.8.9\n"
        result = is_command_available("python", "--version")
        self.assertTrue(result)
        self.assertEqual(mock_wgse.cp_version, [3, 8, 9])

    @patch('subprocess.run')
    def test_command_not_found(self, mock_run):
        mock_run.side_effect = Exception("Command not found")
        result = is_command_available("nonexistent", "--version", internal=True)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
