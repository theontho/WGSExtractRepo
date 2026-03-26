import gzip
import os
import subprocess

import pytest

from tests.smoke_utils import check_tool, ensure_fake_data, run_cli, verify_vcf

# Base directory for the CLI project
CLI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_DIR = os.path.join(CLI_ROOT, "out/fake_30x")


@pytest.fixture(scope="session", autouse=True)
def shared_fake_data():
    """Ensure fake data exists for all tests in this session."""
    ensure_fake_data(FAKE_DIR)


class TestVcfAnnotationSmoke:
    """Ported from various vcf/test_vcf_*.sh scripts"""

    @pytest.fixture(autouse=True)
    def setup_vcf_data(self, tmp_path):
        self.outdir = str(tmp_path)
        self.refdir = os.path.join(self.outdir, "fake_ref")
        os.makedirs(os.path.join(self.refdir, "ref"), exist_ok=True)
        os.makedirs(os.path.join(self.refdir, "genomes"), exist_ok=True)

        # Create dummy hg38 ref
        self.fake_hg38 = os.path.join(self.refdir, "genomes", "hg38.fa")
        with open(self.fake_hg38, "w") as f:
            f.write(">chr1\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n")

        # Create a dummy .dict file so ReferenceLibrary can find SN count
        self.fake_dict = self.fake_hg38.replace(".fa", ".dict")
        with open(self.fake_dict, "w") as f:
            f.write("@HD\tVN:1.6\tSO:coordinate\n")
            # hg38 has many contigs, let's add 195 to trigger hg38 heuristic if needed,
            # but ReferenceLibrary also checks filenames.
            for i in range(1, 200):
                f.write(f"@SQ\tSN:chr{i}\tLN:1000\n")

        if check_tool("bgzip"):
            subprocess.run(
                f"bgzip -c {self.fake_hg38} > {self.fake_hg38}.gz", shell=True
            )
            if check_tool("samtools"):
                subprocess.run(["samtools", "faidx", f"{self.fake_hg38}.gz"])
            # Set the reference path to the one we just created
            self.ref_to_use = self.fake_hg38 + ".gz"
        else:
            self.ref_to_use = self.fake_hg38

        # Create dummy input VCF
        self.input_vcf = os.path.join(self.outdir, "input.vcf.gz")
        raw_vcf = os.path.join(self.outdir, "input.vcf")
        with open(raw_vcf, "w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write('##FILTER=<ID=PASS,Description="All filters passed">\n')
            f.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
            f.write("##contig=<ID=chr1,length=1000>\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
            f.write("chr1\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n")
            f.write("chr1\t200\t.\tC\tT\t100\tPASS\t.\tGT\t0/1\n")

        if check_tool("bgzip"):
            subprocess.run(["bgzip", "-f", raw_vcf])
            if check_tool("tabix"):
                subprocess.run(["tabix", "-p", "vcf", self.input_vcf])

    def _create_ann_file(self, filename, header, rows, tbx_args):
        path = os.path.join(self.refdir, "ref", filename)
        raw_path = path.replace(".gz", "")
        with open(raw_path, "w") as f:
            f.write(header + "\n")
            for r in rows:
                f.write(r + "\n")
        if check_tool("bgzip"):
            subprocess.run(["bgzip", "-f", raw_path])
            if check_tool("tabix"):
                subprocess.run(["tabix", "-f"] + tbx_args + [path])
        return path

    @pytest.mark.skipif(
        not check_tool("bcftools") or not check_tool("bgzip"),
        reason="bcftools/bgzip missing",
    )
    def test_vcf_revel(self):
        # Create dummy REVEL
        revel_file = self._create_ann_file(
            "revel_hg38.tsv.gz",
            "#Chr\tStart\tEnd\tRef\tAlt\tScore",
            ["chr1\t100\t100\tA\tG\t0.85", "chr1\t200\t200\tC\tT\t0.45"],
            ["-s", "1", "-b", "2", "-e", "3"],
        )

        # 1. Annotation
        rc, stdout, stderr = run_cli(
            [
                "vcf",
                "revel",
                "--vcf-input",
                self.input_vcf,
                "--revel-file",
                revel_file,
                "--ref",
                self.ref_to_use,
                "--outdir",
                self.outdir,
                "--debug",
            ]
        )
        assert rc == 0
        out_vcf = os.path.join(self.outdir, "revel_annotated.vcf.gz")
        assert verify_vcf(out_vcf)

        with gzip.open(out_vcf, "rt") as f:
            content = f.read()
            assert "REVEL=0.85" in content

        # 2. Filtering
        rc, stdout, stderr = run_cli(
            [
                "vcf",
                "revel",
                "--vcf-input",
                self.input_vcf,
                "--revel-file",
                revel_file,
                "--ref",
                self.ref_to_use,
                "--outdir",
                self.outdir,
                "--min-score",
                "0.5",
                "--debug",
            ]
        )
        assert rc == 0
        filt_vcf = os.path.join(self.outdir, "revel_gt_0.5.vcf.gz")
        assert verify_vcf(filt_vcf)
        # Should only have 1 variant
        res = subprocess.run(
            f"bcftools view -H {filt_vcf} | wc -l",
            shell=True,
            capture_output=True,
            text=True,
        )
        assert res.stdout.strip() == "1"

    @pytest.mark.skipif(
        not check_tool("bcftools") or not check_tool("bgzip"),
        reason="bcftools/bgzip missing",
    )
    def test_vcf_clinvar(self):
        # Create dummy ClinVar - MUST include CLNDN if the CLI requests it
        clinvar_file = self._create_ann_file(
            "clinvar_hg38.vcf.gz",
            '##fileformat=VCFv4.2\n##INFO=<ID=CLNSIG,Number=.,Type=String,Description="S">\n##INFO=<ID=CLNDN,Number=.,Type=String,Description="D">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO',
            [
                "chr1\t100\t.\tA\tG\t.\t.\tCLNSIG=Pathogenic;CLNDN=Disease",
                "chr1\t200\t.\tC\tT\t.\t.\tCLNSIG=Benign;CLNDN=Healthy",
            ],
            ["-p", "vcf"],
        )

        rc, stdout, stderr = run_cli(
            [
                "vcf",
                "clinvar",
                "--vcf-input",
                self.input_vcf,
                "--clinvar-file",
                clinvar_file,
                "--ref",
                self.ref_to_use,
                "--outdir",
                self.outdir,
                "--debug",
            ]
        )
        assert rc == 0
        out_vcf = os.path.join(self.outdir, "clinvar_annotated.vcf.gz")
        assert verify_vcf(out_vcf)
        with gzip.open(out_vcf, "rt") as f:
            content = f.read()
            assert "CLNSIG=Pathogenic" in content

    @pytest.mark.skipif(
        not check_tool("bcftools") or not check_tool("bgzip"),
        reason="bcftools/bgzip missing",
    )
    def test_vcf_phylop(self):
        # Create dummy PhyloP - use VCF format to avoid tsv-to-vcf crash if any
        phylop_file = self._create_ann_file(
            "phylop_hg38.vcf.gz",
            '##fileformat=VCFv4.2\n##INFO=<ID=PHYLOP,Number=1,Type=Float,Description="P">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO',
            [
                "chr1\t100\t.\tA\tG\t.\t.\tPHYLOP=2.5",
                "chr1\t200\t.\tC\tT\t.\t.\tPHYLOP=-1.2",
            ],
            ["-p", "vcf"],
        )

        rc, stdout, stderr = run_cli(
            [
                "vcf",
                "phylop",
                "--vcf-input",
                self.input_vcf,
                "--phylop-file",
                phylop_file,
                "--ref",
                self.ref_to_use,
                "--outdir",
                self.outdir,
                "--debug",
            ]
        )
        assert rc == 0
        out_vcf = os.path.join(self.outdir, "phylop_annotated.vcf.gz")
        assert verify_vcf(out_vcf)
        with gzip.open(out_vcf, "rt") as f:
            content = f.read()
            assert "PHYLOP=2.5" in content


class TestVcfChainAnnotateSmoke:
    """Ported from test_vcf_chain_annotate.sh"""

    @pytest.fixture(autouse=True)
    def setup_data(self, tmp_path):
        # Similar setup to above but for multiple tools
        self.outdir = str(tmp_path)
        self.refdir = os.path.join(self.outdir, "fake_ref")
        os.makedirs(os.path.join(self.refdir, "ref"), exist_ok=True)
        os.makedirs(os.path.join(self.refdir, "genomes"), exist_ok=True)

        # Reference (MUST have hg38 in name)
        # Place it in genomes/ so it matches ReferenceLibrary logic
        self.ref_to_use = os.path.join(self.refdir, "genomes", "hg38.fa")
        with open(self.ref_to_use, "w") as f:
            f.write(">chr1\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n")

        dict_path = self.ref_to_use.replace(".fa", ".dict")
        with open(dict_path, "w") as f:
            f.write("@HD\tVN:1.6\tSO:coordinate\n")
            for i in range(1, 200):
                f.write(f"@SQ\tSN:chr{i}\tLN:1000\n")

        subprocess.run(
            f"bgzip -f {self.ref_to_use} && samtools faidx {self.ref_to_use}.gz",
            shell=True,
        )
        self.ref_to_use += ".gz"

        # VCF
        self.input_vcf = os.path.join(self.outdir, "input.vcf.gz")
        raw_vcf = os.path.join(self.outdir, "input.vcf")
        with open(raw_vcf, "w") as f:
            f.write(
                '##fileformat=VCFv4.2\n##contig=<ID=chr1,length=1000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\nchr1\t100\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n'
            )
        subprocess.run(
            f"bgzip -f {raw_vcf} && tabix -f -p vcf {self.input_vcf}", shell=True
        )

    @pytest.mark.skipif(not check_tool("bcftools"), reason="bcftools missing")
    def test_chain_annotate(self):
        # We need to place files where ReferenceLibrary(ref) can find them
        # ref is genomes/hg38.fa.gz, so it looks in ../ref/ relative to genomes/
        ref_subdir = os.path.join(self.refdir, "ref")
        os.makedirs(ref_subdir, exist_ok=True)

        # REVEL
        revel_chain = os.path.join(ref_subdir, "revel_hg38.tsv.gz")
        with open(os.path.join(ref_subdir, "revel_hg38.tsv"), "w") as f:
            f.write("#Chr\tStart\tEnd\tRef\tAlt\tScore\nchr1\t100\t100\tA\tG\t0.9\n")
        subprocess.run(
            f"bgzip -f {os.path.join(ref_subdir, 'revel_hg38.tsv')} && tabix -f -s 1 -b 2 -e 3 {revel_chain}",
            shell=True,
        )

        # ClinVar
        clinvar_chain = os.path.join(ref_subdir, "clinvar_hg38.vcf.gz")
        with open(os.path.join(ref_subdir, "clinvar_hg38.vcf"), "w") as f:
            f.write(
                '##fileformat=VCFv4.2\n##INFO=<ID=CLNSIG,Number=.,Type=String,Description="S">\n##INFO=<ID=CLNDN,Number=.,Type=String,Description="D">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr1\t100\t.\tA\tG\t.\t.\tCLNSIG=Pathogenic;CLNDN=Disease\n'
            )
        subprocess.run(
            f"bgzip -f {os.path.join(ref_subdir, 'clinvar_hg38.vcf')} && tabix -f -p vcf {clinvar_chain}",
            shell=True,
        )

        args = [
            "vcf",
            "chain-annotate",
            "--vcf-input",
            self.input_vcf,
            "--ref",
            self.refdir,  # Use the directory containing 'genomes/' and 'ref/'
            "--outdir",
            self.outdir,
            "--annotations",
            "revel,clinvar",
            "--debug",
        ]
        rc, stdout, stderr = run_cli(args)
        assert rc == 0
        out_vcf = os.path.join(self.outdir, "chain_annotated.vcf.gz")
        assert verify_vcf(out_vcf)
        with gzip.open(out_vcf, "rt") as f:
            content = f.read()
            assert "REVEL=0.9" in content
            assert "CLNSIG=Pathogenic" in content
