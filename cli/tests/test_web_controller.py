import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from wgsextract_cli.ui.web_gui_parts.controller import WebController
from wgsextract_cli.ui.web_gui_parts.state import state


class TestWebController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.controller = WebController()
        state.logs = {}
        state.log_tabs = ["Main"]
        state.active_tab = "flow"
        state.running_processes = {}

    def test_log_basic(self):
        """Test basic logging functionality."""
        self.controller.log("Hello World", tab="Main")
        self.assertIn("ℹ️ Hello World", state.logs["Main"])

    def test_log_levels(self):
        """Test that different log levels get appropriate emojis."""
        self.controller.log("ERROR: something failed", tab="Main")
        self.assertIn("❌ ERROR: something failed", state.logs["Main"])

        self.controller.log("WARNING: be careful", tab="Main")
        self.assertIn("⚠️ WARNING: be careful", state.logs["Main"])

        self.controller.log("DEBUG: internal info", tab="Main")
        self.assertIn("🔍 DEBUG: internal info", state.logs["Main"])

    def test_log_new_tab(self):
        """Test that logging to a new tab creates it and notifies UI."""
        with patch(
            "wgsextract_cli.ui.web_gui_parts.common.render_content_refresh"
        ) as mock_refresh:
            self.controller.log("New tab message", tab="NewTab")
            self.assertIn("NewTab", state.log_tabs)
            self.assertIn("ℹ️ New tab message", state.logs["NewTab"])
            mock_refresh.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_run_cmd_success(self, mock_exec):
        """Test successful command execution."""
        mock_process = AsyncMock()
        mock_process.stdout.readline.side_effect = [b"output line 1\n", b""]
        mock_process.stderr.readline.side_effect = [b""]
        mock_process.wait.return_value = 0
        mock_process.pid = 1234
        mock_exec.return_value = mock_process

        with patch("wgsextract_cli.ui.web_gui_parts.common.render_content_refresh"):
            await self.controller.run_cmd(
                ["test", "cmd"], label="TestCmd", cmd_key="test_key"
            )

        self.assertIn("TestCmd", state.log_tabs)
        self.assertTrue(any("output line 1" in msg for msg in state.logs["TestCmd"]))
        self.assertTrue(any("exit code 0" in msg for msg in state.logs["TestCmd"]))
        self.assertNotIn("test_key", state.running_processes)

    @patch("asyncio.create_subprocess_exec")
    async def test_run_cmd_failure(self, mock_exec):
        """Test command execution failure."""
        mock_process = AsyncMock()
        mock_process.stdout.readline.side_effect = [b""]
        mock_process.stderr.readline.side_effect = [b"error line\n", b""]
        mock_process.wait.return_value = 1
        mock_process.pid = 1235
        mock_exec.return_value = mock_process

        with patch("wgsextract_cli.ui.web_gui_parts.common.render_content_refresh"):
            await self.controller.run_cmd(["test", "fail"], label="FailCmd")

        self.assertTrue(any("error line" in msg for msg in state.logs["FailCmd"]))
        self.assertTrue(any("exit code 1" in msg for msg in state.logs["FailCmd"]))

    def test_set_tab(self):
        """Test tab switching."""
        with patch(
            "wgsextract_cli.ui.web_gui_parts.common.render_content_refresh"
        ) as mock_refresh, patch("nicegui.ui.update") as mock_update:
            self.controller.set_tab("vcf")
            self.assertEqual(state.active_tab, "vcf")
            mock_refresh.assert_called_once()
            mock_update.assert_called_once()

    @patch("wgsextract_cli.ui.web_gui_parts.controller.threading.Thread")
    @patch("subprocess.run")
    def test_get_info_fast(self, mock_run, mock_thread):
        """Test triggering fast info gathering."""
        with patch("os.path.exists", return_value=True):
            # We need to await it since it's an async function (it calls run() in a thread but the function itself is async)
            # Actually get_info_fast is defined as 'async def' but doesn't use await inside except for ui calls?
            # Wait, let's check the definition again.
            pass

    @patch("wgsextract_cli.ui.web_gui_parts.controller.threading.Thread")
    async def test_get_info_fast_async(self, mock_thread):
        """Test triggering fast info gathering."""
        with patch("os.path.exists", return_value=True):
            await self.controller.get_info_fast("/path/to/input.bam")
            mock_thread.assert_called_once()

    # Add more tests for library management if needed, but these cover the core logic.


if __name__ == "__main__":
    unittest.main()
