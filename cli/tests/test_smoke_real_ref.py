import os
import shutil

import pytest

from tests.smoke_utils import check_tool, ensure_fake_data, run_cli

# Base directory for the CLI project
CLI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_DIR = os.path.join(CLI_ROOT, "out/fake_30x")


@pytest.fixture(scope="session", autouse=True)
def shared_fake_data():
    """Ensure fake data exists for all tests in this session."""
    ensure_fake_data(FAKE_DIR)


class TestRefBasicsSmoke:
    """Ported from test_ref_basics.sh and test_ref_download_index.sh"""

    @pytest.fixture(autouse=True)
    def setup_ref(self, tmp_path):
        self.outdir = str(tmp_path)
        self.ref = os.path.join(FAKE_DIR, "fake_ref.fa")
        self.local_ref = os.path.join(self.outdir, "test_ref.fa")
        shutil.copy(self.ref, self.local_ref)

    @pytest.mark.skipif(not check_tool("samtools"), reason="samtools missing")
    def test_ref_index_verify(self):
        # 1. Index
        rc, stdout, stderr = run_cli(["ref", "index", "--ref", self.local_ref])
        assert rc == 0
        assert os.path.exists(self.local_ref + ".fai")

        # 2. Verify
        rc, stdout, stderr = run_cli(["ref", "verify", "--ref", self.local_ref])
        assert rc == 0
        assert "valid" in stdout or "valid" in stderr


class TestRefLibrarySmoke:
    """Ported from test_ref_library_basics.sh and test_ref_databases.sh"""

    @pytest.fixture(autouse=True)
    def setup_lib(self, tmp_path):
        self.outdir = str(tmp_path)
        # Mock a small library structure
        self.reflib = os.path.join(self.outdir, "reflib")
        os.makedirs(os.path.join(self.reflib, "genomes"), exist_ok=True)
        os.makedirs(os.path.join(self.reflib, "ref"), exist_ok=True)

    def test_ref_gene_map(self):
        # Changed from download-genes to gene-map
        rc, stdout, stderr = run_cli(["ref", "gene-map", "--outdir", self.outdir])
        # Success depends on network, but we check if it starts correctly
        assert "Downloading" in stdout or "Downloading" in stderr or rc == 0

    def test_ref_databases_list(self):
        # The CLI 'ref' command doesn't have 'databases --list', it has individual dl commands or library-list
        rc, stdout, stderr = run_cli(["ref", "library-list"])
        assert rc == 0
        assert "GRCh38" in stdout
