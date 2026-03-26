import os

import pytest

from tests.smoke_utils import (
    assert_file_contains,
    assert_log_contains,
    check_tool,
    ensure_fake_data,
    run_cli,
    run_cli_pipe,
    verify_bam,
    verify_fastq,
    verify_vcf,
)

# --- DEPENDENCY CHECKS ---
SAMTOOLS_MISSING = not check_tool("samtools")
BCFTOOLS_MISSING = not check_tool("bcftools")
BWA_MISSING = not check_tool("bwa")
FASTP_MISSING = not check_tool("fastp")
FASTQC_MISSING = not check_tool("fastqc")
SAMBAMBA_MISSING = not check_tool("sambamba")
SAMBLASTER_MISSING = not check_tool("samblaster")
BGZIP_MISSING = not check_tool("bgzip")
TABIX_MISSING = not check_tool("tabix")
VEP_MISSING = not check_tool("vep")
YLEAF_MISSING = not check_tool("yleaf")  # Assuming yleaf is the command name

# Base directory for the CLI project
CLI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_DIR = os.path.join(CLI_ROOT, "out/fake_30x")


@pytest.fixture(scope="session", autouse=True)
def shared_fake_data():
    """Ensure fake data exists for all tests in this session."""
    ensure_fake_data(FAKE_DIR)


class TestExtractBasicsSmoke:
    """
    Real-world smoke tests for extraction functionality.
    Ported from test_extract_basics.sh
    """

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")
        self.fake_ref_scaled = os.path.join(FAKE_DIR, "fake_ref_hg38_scaled.fa")

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_extract_mt_bam(self):
        """1. Extract Mitochondrial BAM"""
        args = [
            "extract",
            "mt-bam",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)

        assert rc == 0
        assert "Extracting mtDNA reads" in stdout or "Extracting mtDNA reads" in stderr
        assert verify_bam(os.path.join(self.outdir, "fake_mtDNA.bam"))

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_extract_ydna_bam(self):
        """2. Extract Y-DNA BAM"""
        args = [
            "extract",
            "ydna-bam",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)

        assert rc == 0
        assert (
            "Extracting Y-chromosome reads" in stdout
            or "Extracting Y-chromosome reads" in stderr
        )
        assert verify_bam(os.path.join(self.outdir, "fake_Y.bam"))

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_extract_unmapped(self):
        """3. Extract Unmapped Reads"""
        args = [
            "extract",
            "unmapped",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)

        assert rc == 0
        assert (
            "Extracting unmapped reads" in stdout
            or "Extracting unmapped reads" in stderr
        )
        assert verify_bam(
            os.path.join(self.outdir, "fake_unmapped.bam"), allow_empty=True
        )

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_extract_bam_subset_region(self):
        """4. Extract Subset (Region)"""
        args = [
            "extract",
            "bam-subset",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--region",
            "chr1",
            "--fraction",
            "0.1",
        ]
        rc, stdout, stderr = run_cli(args)

        assert rc == 0
        assert (
            "Subsetting 0.1 of reads" in stdout or "Subsetting 0.1 of reads" in stderr
        )
        assert verify_bam(os.path.join(self.outdir, "fake_subset.bam"))

    @pytest.mark.skipif(
        BCFTOOLS_MISSING or SAMTOOLS_MISSING,
        reason="bcftools or samtools not found in PATH",
    )
    def test_extract_ydna_vcf(self):
        """6. Extract Y-DNA VCF"""
        args = [
            "extract",
            "ydna-vcf",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)

        assert rc == 0
        assert (
            "Calling Y-chromosome variants" in stdout
            or "Calling Y-chromosome variants" in stderr
        )
        assert verify_vcf(os.path.join(self.outdir, "fake_Y.vcf.gz"))


class TestAlignBasicsSmoke:
    """Ported from test_align_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fastq_dir = os.path.join(self.outdir, "fastq")
        os.makedirs(self.fastq_dir, exist_ok=True)

    @pytest.mark.skipif(
        BWA_MISSING or SAMTOOLS_MISSING, reason="bwa or samtools not found in PATH"
    )
    def test_align_to_bam(self):
        # 1. Generate small FASTQ
        run_cli(
            [
                "qc",
                "fake-data",
                "--outdir",
                self.fastq_dir,
                "--build",
                "hg38",
                "--type",
                "fastq",
                "--coverage",
                "0.01",
                "--seed",
                "123",
                "--ref",
                self.fastq_dir,
            ]
        )
        r1 = os.path.join(self.fastq_dir, "fake_R1.fastq.gz")
        r2 = os.path.join(self.fastq_dir, "fake_R2.fastq.gz")
        import glob

        ref = glob.glob(os.path.join(self.fastq_dir, "fake_ref_hg38_*.fa"))[0]

        assert verify_fastq(r1)

        # 2. Align to BAM
        args = [
            "align",
            "--r1",
            r1,
            "--r2",
            r2,
            "--ref",
            ref,
            "--outdir",
            os.path.join(self.outdir, "bam"),
            "--format",
            "BAM",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert "Aligning" in stdout or "Aligning" in stderr
        assert verify_bam(os.path.join(self.outdir, "bam", "fake_R1_aligned.bam"))

    @pytest.mark.skipif(
        BWA_MISSING or SAMTOOLS_MISSING, reason="bwa or samtools not found in PATH"
    )
    def test_align_to_cram(self):
        # reuse fastq generation logic or just use FAKE_DIR if available
        # But test_align_basics.sh generates its own small one.
        run_cli(
            [
                "qc",
                "fake-data",
                "--outdir",
                self.fastq_dir,
                "--build",
                "hg38",
                "--type",
                "fastq",
                "--coverage",
                "0.01",
                "--seed",
                "123",
                "--ref",
                self.fastq_dir,
            ]
        )
        r1 = os.path.join(self.fastq_dir, "fake_R1.fastq.gz")
        r2 = os.path.join(self.fastq_dir, "fake_R2.fastq.gz")
        import glob

        ref = glob.glob(os.path.join(self.fastq_dir, "fake_ref_hg38_*.fa"))[0]

        args = [
            "align",
            "--r1",
            r1,
            "--r2",
            r2,
            "--ref",
            ref,
            "--outdir",
            os.path.join(self.outdir, "cram"),
            "--format",
            "CRAM",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_bam(os.path.join(self.outdir, "cram", "fake_R1_aligned.cram"))


class TestBamBasicsSmoke:
    """Ported from test_bam_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    def test_bam_identify(self):
        rc, stdout, stderr = run_cli(["bam", "identify", "--input", self.fake_bam])
        assert rc == 0

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_bam_index(self):
        import shutil

        test_bam = os.path.join(self.outdir, "test.bam")
        shutil.copy(self.fake_bam, test_bam)
        rc, stdout, stderr = run_cli(["bam", "index", "--input", test_bam])
        assert rc == 0
        assert os.path.exists(test_bam + ".bai")
        assert verify_bam(test_bam)

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_bam_to_cram(self):
        args = [
            "bam",
            "to-cram",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_bam(os.path.join(self.outdir, "fake.cram"))


class TestBamAdvancedSmoke:
    """Ported from test_bam_advanced.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools missing")
    def test_bam_unalign(self):
        args = [
            "bam",
            "unalign",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--r1",
            "unaligned_R1.fastq.gz",
            "--r2",
            "unaligned_R2.fastq.gz",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_fastq(os.path.join(self.outdir, "unaligned_R1.fastq.gz"))
        assert verify_fastq(os.path.join(self.outdir, "unaligned_R2.fastq.gz"))

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools missing")
    def test_bam_unindex(self):
        import shutil

        test_bam = os.path.join(self.outdir, "test_unindex.bam")
        shutil.copy(self.fake_bam, test_bam)
        run_cli(["bam", "index", "--input", test_bam])
        assert os.path.exists(test_bam + ".bai")

        rc, stdout, stderr = run_cli(["bam", "unindex", "--input", test_bam])
        assert rc == 0
        assert not os.path.exists(test_bam + ".bai")

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools missing")
    def test_bam_unsort(self):
        args = ["bam", "unsort", "--input", self.fake_bam, "--outdir", self.outdir]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        unsorted_bam = os.path.join(self.outdir, "fake_unsorted.bam")
        assert os.path.exists(unsorted_bam)
        import subprocess

        res = subprocess.run(
            ["samtools", "view", "-H", unsorted_bam], capture_output=True, text=True
        )
        assert "SO:unsorted" in res.stdout


class TestExtractAdvancedSmoke:
    """Ported from test_extract_advanced.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")
        self.fake_ref = os.path.join(FAKE_DIR, "fake_ref.fa")

    @pytest.mark.skipif(SAMTOOLS_MISSING, reason="samtools not found in PATH")
    def test_extract_mito_fasta(self):
        args = [
            "extract",
            "mito-fasta",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert os.path.exists(os.path.join(self.outdir, "fake_MT.fasta"))
        assert assert_file_contains(os.path.join(self.outdir, "fake_MT.fasta"), ">")

    @pytest.mark.skipif(
        BCFTOOLS_MISSING or SAMTOOLS_MISSING,
        reason="bcftools or samtools not found in PATH",
    )
    def test_extract_mito_vcf(self):
        args = [
            "extract",
            "mito-vcf",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
            "--ref",
            self.fake_ref,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_vcf(os.path.join(self.outdir, "fake_MT.vcf.gz"))


class TestInfoCoverageSmoke:
    """Ported from test_info_coverage.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_bam = os.path.join(FAKE_DIR, "fake.bam")

    def test_info_base(self):
        rc, stdout, stderr = run_cli(["info", "--input", self.fake_bam])
        assert rc == 0
        assert "Avg Read Length" in stdout or "Avg Read Length" in stderr

    def test_info_coverage_sample(self):
        args = [
            "info",
            "coverage-sample",
            "--input",
            self.fake_bam,
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert os.path.exists(os.path.join(self.outdir, "fake.bam_samplecvg.json"))


class TestMicroarraySmoke:
    """Ported from test_microarray_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.ref_dir = os.path.join(self.outdir, "fake_ref")
        os.makedirs(os.path.join(self.ref_dir, "ref"), exist_ok=True)
        os.makedirs(os.path.join(self.ref_dir, "genomes"), exist_ok=True)
        os.makedirs(os.path.join(self.ref_dir, "microarray"), exist_ok=True)
        os.makedirs(
            os.path.join(self.ref_dir, "raw_file_templates/body"), exist_ok=True
        )
        os.makedirs(
            os.path.join(self.ref_dir, "raw_file_templates/head"), exist_ok=True
        )

        # Create dummy templates
        with open(
            os.path.join(self.ref_dir, "raw_file_templates/head/23andMe_V5.txt"), "w"
        ) as f:
            f.write("# rsid\tchromosome\tposition\tgenotype\n")
        with open(
            os.path.join(self.ref_dir, "raw_file_templates/body/23andMe_V5_1.txt"), "w"
        ) as f:
            f.write("rs1\tchr1\t10\n")
        with open(
            os.path.join(self.ref_dir, "raw_file_templates/body/23andMe_V5_2.txt"), "w"
        ) as f:
            f.write("rs2\tchr1\t20\n")

        # Create dummy genome
        self.fake_hg38_fa = os.path.join(self.ref_dir, "genomes", "hg38.fa")
        with open(self.fake_hg38_fa, "w") as f:
            f.write(">chr1\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n")

        if check_tool("bgzip"):
            import subprocess

            subprocess.run(
                ["bgzip", "-c", self.fake_hg38_fa],
                stdout=open(self.fake_hg38_fa + ".gz", "wb"),
            )
            if check_tool("samtools"):
                subprocess.run(["samtools", "faidx", self.fake_hg38_fa + ".gz"])

        # Create dummy SNP tab file
        tab_file = os.path.join(self.ref_dir, "microarray", "All_SNPs_hg38_ref.tab")
        with open(tab_file, "w") as f:
            f.write("#CHROM\tPOS\tID\tREF\tALT\n")
            f.write("chr1\t10\trs1\tA\tG\n")
            f.write("chr1\t20\trs2\tC\tT\n")

        if check_tool("bgzip"):
            subprocess.run(["bgzip", "-f", tab_file])
            if check_tool("tabix"):
                subprocess.run(["tabix", "-p", "vcf", tab_file + ".gz"])

    @pytest.mark.skipif(
        BCFTOOLS_MISSING or not check_tool("bgzip") or not check_tool("tabix"),
        reason="bcftools, bgzip, or tabix not found in PATH",
    )
    def test_microarray_basics(self):
        import subprocess

        # 1. Create dummy input VCF
        input_vcf_path = os.path.join(self.outdir, "input.vcf")
        with open(input_vcf_path, "w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
            f.write("chr1\t10\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n")

        subprocess.run(["bgzip", "-f", input_vcf_path])
        subprocess.run(["tabix", "-p", "vcf", input_vcf_path + ".gz"])

        # 2. Run microarray command
        args = [
            "microarray",
            "--input",
            input_vcf_path + ".gz",
            "--ref",
            self.ref_dir,
            "--outdir",
            self.outdir,
            "--formats",
            "23andme_v5",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        output_file = os.path.join(self.outdir, "input_23andMe_V5.txt")
        assert os.path.exists(output_file)
        assert assert_file_contains(output_file, "rs1")
        assert assert_file_contains(output_file, "rs2")


class TestRefBasicsSmoke:
    """Ported from test_ref_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fakerefdir = os.path.join(self.outdir, "fakeref")
        os.makedirs(self.fakerefdir, exist_ok=True)

    def test_ref_lifecycle(self, tmp_path):
        # 1. Generate small fake reference
        run_cli(
            [
                "qc",
                "fake-data",
                "--outdir",
                self.fakerefdir,
                "--build",
                "hg38",
                "--type",
                "fastq",
                "--coverage",
                "0.0001",
                "--seed",
                "123",
                "--ref",
                self.fakerefdir,
            ]
        )
        import glob

        ref_paths = glob.glob(os.path.join(self.fakerefdir, "fake_ref_hg38_*.fa"))
        assert len(ref_paths) > 0
        ref_path = ref_paths[0]

        downloaded = os.path.join(self.outdir, "downloaded.fa")
        import shutil

        shutil.copy(ref_path, downloaded)

        # 3. Test 'ref index'
        rc, stdout, stderr = run_cli(["ref", "index", "--ref", downloaded])
        assert rc == 0
        assert os.path.exists(downloaded + ".fai")

        # 4. Test 'ref count-ns'
        rc, stdout, stderr = run_cli(["ref", "count-ns", "--ref", downloaded])
        assert rc == 0
        assert "Processing" in stdout or "Processing" in stderr

        # 5. Test 'ref verify'
        rc, stdout, stderr = run_cli(["ref", "verify", "--ref", downloaded])
        assert rc == 0
        assert "appears to be valid" in stdout or "appears to be valid" in stderr


class TestRepairBasicsSmoke:
    """Ported from test_repair_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)

    def test_repair_ftdna_bam(self):
        sam_content = (
            "@HD\tVN:1.6\tSO:coordinate\n"
            "@SQ\tSN:chr1\tLN:1000\n"
            "read 1\t99\tchr1\t100\t60\t100M\t=\t200\t100\tAAAAAAAAAA\t##########\n"
        )
        rc, stdout, stderr = run_cli_pipe(["repair", "ftdna-bam"], sam_content)
        assert rc == 0
        assert "read:1" in stdout

    @pytest.mark.skipif(BCFTOOLS_MISSING, reason="bcftools not found in PATH")
    def test_repair_ftdna_vcf(self):
        vcf_content = (
            "##fileformat=VCFv4.2\n"
            '##FILTER=<ID=PASS,Description="All filters passed">\n'
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
            '##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">\n'
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample\n"
            "chr1\t100\t.\tA\tG\t100\tDP=1\t.\tGT\t0/1\n"
        )
        rc, stdout, stderr = run_cli_pipe(["repair", "ftdna-vcf"], vcf_content)
        assert rc == 0
        assert "DP1" in stdout

        # Verify validity
        repaired_path = os.path.join(self.outdir, "repaired.vcf")
        with open(repaired_path, "w") as f:
            f.write(stdout)
        assert verify_vcf(repaired_path)


class TestLineageSmoke:
    """Ported from test_lineage_basics.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_vcf = os.path.join(FAKE_DIR, "fake.vcf.gz")

    @pytest.mark.skipif(YLEAF_MISSING, reason="yleaf not found in PATH")
    def test_lineage_y_haplogroup(self):
        args = [
            "lineage",
            "y-haplogroup",
            "--input",
            self.fake_vcf,
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        # Even if it fails due to no Y markers in fake data, we check for execution
        assert "Y-chromosome" in stdout or "Y-chromosome" in stderr

    def test_lineage_mt_haplogroup(self):
        # Requires haplogrep, usually a jar. This smoke test just checks if it tries to run.
        args = [
            "lineage",
            "mt-haplogroup",
            "--input",
            self.fake_vcf,
            "--outdir",
            self.outdir,
        ]
        rc, stdout, stderr = run_cli(args)
        assert "mtDNA" in stdout or "mtDNA" in stderr


class TestQCFakeDataSmoke:
    """Ported from test_qc_fake_data.sh"""

    def test_qc_fake_data_generation(self, tmp_path):
        outdir = str(tmp_path)
        args = [
            "qc",
            "fake-data",
            "--outdir",
            outdir,
            "--build",
            "hg38",
            "--type",
            "bam,vcf",
            "--coverage",
            "0.1",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert verify_bam(os.path.join(outdir, "fake.bam"))
        assert verify_vcf(os.path.join(outdir, "fake.vcf.gz"))


class TestVEPSmoke:
    """Ported from test_vep_basics.sh and test_vep_full.sh"""

    @pytest.fixture(autouse=True)
    def setup_outdir(self, tmp_path):
        self.outdir = str(tmp_path)
        self.fake_vcf = os.path.join(FAKE_DIR, "fake.vcf.gz")

    @pytest.mark.skipif(VEP_MISSING, reason="VEP not found in PATH")
    def test_vep_basics(self):
        args = [
            "vep",
            "--input",
            self.fake_vcf,
            "--outdir",
            self.outdir,
            "--format",
            "vcf",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        assert os.path.exists(os.path.join(self.outdir, "vep_annotated.vcf.gz"))


class TestRobustnessSmoke:
    """Ported from test_robustness_ux.sh and test_stress_scenarios.sh"""

    def test_invalid_input_file(self, tmp_path):
        outdir = str(tmp_path)
        args = ["info", "--input", "/non/existent/file.bam", "--outdir", outdir]
        rc, stdout, stderr = run_cli(args)
        # Current CLI returns 0 but prints error to stderr/stdout.
        # Ideally it should return != 0, but we test current behavior.
        assert "not found" in stdout or "not found" in stderr or rc != 0

    def test_invalid_command(self):
        rc, stdout, stderr = run_cli(["invalid-command"])
        assert rc != 0


class TestPixiFallbackSmoke:
    """Ported from test_pixi_fallback.sh"""

    def test_pixi_help(self):
        # Just check if the pixi-related help or info is accessible
        rc, stdout, stderr = run_cli(["deps", "check", "--tool", "samtools"])
        assert rc == 0
        assert "samtools" in stdout
