import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from wgsextract_cli.main import main


class TestInfoCommand(unittest.TestCase):
    """
    Unit testing for the 'info' metric calculation and rendering logic.
    """

    def setUp(self):
        os.environ["WGSE_SKIP_DOTENV"] = "1"
        # Clear any other potentially interfering env vars
        self.env_vars = [
            "WGSE_INPUT",
            "WGSE_OUTDIR",
            "WGSE_REF",
            "WGSE_THREADS",
            "WGSE_MEMORY",
        ]
        self.old_env = {v: os.environ.get(v) for v in self.env_vars}
        for v in self.env_vars:
            if v in os.environ:
                del os.environ[v]

    def tearDown(self):
        for v, val in self.old_env.items():
            if val is not None:
                os.environ[v] = val
            elif v in os.environ:
                del os.environ[v]

    @patch("wgsextract_cli.commands.info.verify_dependencies")
    @patch("wgsextract_cli.commands.info.get_bam_header")
    @patch("wgsextract_cli.commands.info.calculate_bam_md5")
    @patch("wgsextract_cli.commands.info.is_sorted")
    @patch("wgsextract_cli.commands.info.get_file_stats")
    @patch("wgsextract_cli.commands.info.run_body_sample")
    @patch("wgsextract_cli.commands.info.parse_idxstats")
    @patch("wgsextract_cli.commands.info.os.path.exists")
    def test_info_fast_mode(
        self,
        mock_exists,
        mock_idxstats,
        mock_body,
        mock_stats,
        mock_sorted,
        mock_md5,
        mock_header,
        mock_verify,
    ):
        mock_header.return_value = "@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:1\tLN:248956422"
        mock_md5.return_value = "bd894134bddba260df88a90123a2ee9c"  # hg38
        mock_sorted.return_value = True
        mock_stats.return_value = (50.0, True)  # 50GB, Indexed
        mock_exists.side_effect = lambda p: False if ".wgse_info.json" in p else True
        mock_body.return_value = (
            1000,
            150.0,
            2.0,
            300.0,
            50.0,
            True,
            "A00910:1:ABCDEFGHI:1:1:1:1",
        )
        mock_idxstats.return_value = (
            [
                {"name": "1", "length": 248956422, "mapped": 1000000, "unmapped": 0},
            ],
            248956422,
            1000000,
            0,
        )

        test_args = ["wgsextract-cli", "info", "--input", "sample.bam"]

        f = io.StringIO()
        with redirect_stdout(f):
            with patch.object(sys, "argv", test_args):
                main()

        output = f.getvalue()
        self.assertIn("Reference Genome: hg38 (Chr), rCRS, 1 SNs", output)
        self.assertIn("File Stats: Sorted, Indexed, 50.0 GBs", output)
        self.assertIn("Avg Read Length: 150 bp", output)
        self.assertIn("Avg Insert Size: 300 bp", output)
        self.assertIn("Sequencer: Illumina NS 6000 (Dante)", output)

    @patch("wgsextract_cli.commands.info.verify_dependencies")
    @patch("wgsextract_cli.commands.info.get_bam_header")
    @patch("wgsextract_cli.commands.info.calculate_bam_md5")
    @patch("wgsextract_cli.commands.info.is_sorted")
    @patch("wgsextract_cli.commands.info.get_file_stats")
    @patch("wgsextract_cli.commands.info.run_body_sample")
    @patch("wgsextract_cli.commands.info.parse_idxstats")
    @patch("wgsextract_cli.commands.info.os.path.exists")
    @patch("wgsextract_cli.commands.info.os.path.getsize")
    @patch("wgsextract_cli.commands.info.open", create=True)
    def test_info_detailed_mode(
        self,
        mock_open,
        mock_getsize,
        mock_exists,
        mock_idxstats,
        mock_body,
        mock_stats,
        mock_sorted,
        mock_md5,
        mock_header,
        mock_verify,
    ):
        mock_header.return_value = "@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:1\tLN:248956422"
        mock_md5.return_value = "bd894134bddba260df88a90123a2ee9c"  # hg38
        mock_sorted.return_value = True
        mock_stats.return_value = (50.0, True)
        mock_exists.side_effect = lambda p: False if ".wgse_info.json" in p else True
        mock_getsize.return_value = 0  # So it doesn't try to read CSV

        # count, avg_len, std_len, avg_tlen, std_tlen, is_paired, first_qname
        # Dante QNAME pattern: r'^(A00910|A00925|A00966|A01245):\d+:[a-zA-Z0-9]{9}:\d:\d+:\d+:\d+$'
        mock_body.return_value = (
            1000,
            150.0,
            2.0,
            300.0,
            50.0,
            True,
            "A00910:1:ABCDEFGHI:1:1:1:1",
        )

        # stats, genome_len, total_mapped, total_unmapped
        mock_idxstats.return_value = (
            [
                {"name": "1", "length": 248956422, "mapped": 1000000, "unmapped": 0},
                {"name": "X", "length": 155270560, "mapped": 1000000, "unmapped": 0},
                {"name": "Y", "length": 57227415, "mapped": 500000, "unmapped": 0},
            ],
            600000000,
            2500000,
            0,
        )

        test_args = ["wgsextract-cli", "info", "--input", "sample.bam", "--detailed"]

        f = io.StringIO()
        with redirect_stdout(f):
            with patch.object(sys, "argv", test_args):
                main()

        output = f.getvalue()
        self.assertIn("Reference Genome", output)
        self.assertIn("hg38 (Chr), rCRS, 1 SNs", output)
        self.assertIn("Avg Read Length", output)
        self.assertIn("150 bp", output)
        self.assertIn("Bio Gender", output)
        self.assertIn("Male", output)
        self.assertIn("Sequencer", output)
        self.assertIn("Illumina NS 6000 (Dante)", output)

    @patch("wgsextract_cli.commands.info.verify_dependencies")
    @patch("wgsextract_cli.commands.info.get_bam_header")
    @patch("wgsextract_cli.commands.info.calculate_bam_md5")
    @patch("wgsextract_cli.commands.info.is_sorted")
    @patch("wgsextract_cli.commands.info.get_file_stats")
    @patch("wgsextract_cli.commands.info.run_body_sample")
    @patch("wgsextract_cli.commands.info.parse_idxstats")
    @patch("wgsextract_cli.commands.info.os.path.exists")
    @patch("wgsextract_cli.commands.info.os.path.getsize")
    @patch("wgsextract_cli.commands.info.open", create=True)
    def test_info_csv_mode(
        self,
        mock_open,
        mock_getsize,
        mock_exists,
        mock_idxstats,
        mock_body,
        mock_stats,
        mock_sorted,
        mock_md5,
        mock_header,
        mock_verify,
    ):
        mock_header.return_value = "@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:1\tLN:248956422"
        mock_md5.return_value = "bd894134bddba260df88a90123a2ee9c"
        mock_sorted.return_value = True
        mock_stats.return_value = (50.0, True)
        mock_exists.side_effect = lambda p: False if ".wgse_info.json" in p else True
        mock_getsize.return_value = 0
        mock_body.return_value = (1000, 150.0, 2.0, 300.0, 50.0, True, "QNAME")
        mock_idxstats.return_value = (
            [{"name": "1", "length": 100, "mapped": 10, "unmapped": 0}],
            100,
            10,
            0,
        )

        test_args = [
            "wgsextract-cli",
            "info",
            "--input",
            "sample.bam",
            "--detailed",
            "--csv",
        ]

        f = io.StringIO()
        with redirect_stdout(f):
            with patch.object(sys, "argv", test_args):
                main()

        output = f.getvalue()
        self.assertIn(
            "Seq Name,Model Len,Model N Len,# Segs Map,Map Gbases,Map ARD,Breadth Coverage",
            output,
        )
        self.assertIn("1,100", output)


if __name__ == "__main__":
    unittest.main()
