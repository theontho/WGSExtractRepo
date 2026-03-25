import os
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from wgsextract_cli.core.dependencies import verify_dependencies  # noqa: E402


class TestOptionalDependencies(unittest.TestCase):
    """Tests the new optional dependency handling."""

    @patch("wgsextract_cli.core.dependencies.get_tool_path")
    @patch("wgsextract_cli.core.dependencies.get_jar_dir", return_value="/tmp")
    @patch("sys.exit")
    @patch("logging.error")
    @patch("logging.info")
    def test_verify_optional_missing(
        self, mock_info, mock_error, mock_exit, mock_jar, mock_tool_path
    ):
        # Simulate 'minimap2' (optional) is missing
        mock_tool_path.side_effect = (
            lambda x: None if x == "minimap2" else "/usr/bin/" + x
        )

        try:
            verify_dependencies(["minimap2"])
        except SystemExit:
            pass

        # Check that it called logging.error with the optional message
        mock_error.assert_any_call(
            "Required optional tool(s) missing for this feature:"
        )
        mock_error.assert_any_call(" - minimap2")

        # Check for generic installation advice
        args, _ = mock_info.call_args
        self.assertIn("package manager", args[0])
        self.assertIn("brew, apt, conda", args[0])

        mock_exit.assert_called_with(1)

    @patch("wgsextract_cli.core.dependencies.get_tool_path")
    @patch("wgsextract_cli.core.dependencies.get_jar_dir", return_value="/tmp")
    @patch("sys.exit")
    @patch("logging.error")
    def test_verify_mandatory_missing(
        self, mock_error, mock_exit, mock_jar, mock_tool_path
    ):
        # Simulate 'samtools' (mandatory) is missing
        mock_tool_path.side_effect = (
            lambda x: None if x == "samtools" else "/usr/bin/" + x
        )

        try:
            verify_dependencies(["samtools"])
        except SystemExit:
            pass

        # Check that it called logging.error with the fatal message
        mock_error.assert_any_call(
            "Fatal Error: Missing required core tools or JAR files."
        )
        mock_error.assert_any_call(" - samtools")
        mock_exit.assert_called_with(1)

    @patch("wgsextract_cli.core.dependencies.MANDATORY_TOOLS", ["samtools"])
    @patch("wgsextract_cli.core.dependencies.OPTIONAL_TOOLS", ["minimap2"])
    @patch("wgsextract_cli.core.dependencies.get_tool_path")
    @patch("wgsextract_cli.core.dependencies.get_tool_version", return_value="1.0")
    def test_deps_check_output(self, mock_version, mock_tool_path):
        from wgsextract_cli.commands.deps import run

        # samtools present, minimap2 missing
        mock_tool_path.side_effect = (
            lambda x: "/usr/bin/" + x if x == "samtools" else None
        )

        with patch("sys.stdout", new=StringIO()) as fake_out:
            args = MagicMock()
            args.tool = None
            run(args)
            output = fake_out.getvalue()

            self.assertIn("Python Runtime", output)
            self.assertIn("✅ samtools", output)
            self.assertIn("⚠️  minimap2", output)
            self.assertIn("Mandatory Tools:", output)
            self.assertIn("Optional Tools:", output)


if __name__ == "__main__":
    unittest.main()
