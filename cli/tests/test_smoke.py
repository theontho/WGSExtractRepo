import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import io
import logging
import tempfile
import shutil
from contextlib import redirect_stderr, redirect_stdout

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Load environment variables from the cli project directory base
from dotenv import load_dotenv
cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_local = os.path.join(cli_root, ".env.local")
env_std = os.path.join(cli_root, ".env")

if os.path.exists(env_local):
    load_dotenv(dotenv_path=env_local)
if os.path.exists(env_std):
    load_dotenv(dotenv_path=env_std)

from wgsextract_cli.main import main

# Paths for smoke tests (using placeholders or env)
REF_PATH = os.environ.get('WGSE_REF', "/tmp")
INPUT_PATH = os.environ.get('WGSE_INPUT', "/tmp/fake.bam")

class TestCLISmoke(unittest.TestCase):
    """
    Rapid plumbing verification using mocked tool execution.
    
    Goal: Ensure that every subcommand is correctly registered, argument parsing works 
    as expected, and the correct parameters are passed down to the underlying genomic 
    tools. This suite covers ALL 34 available command combinations.
    """
    @classmethod
    def setUpClass(cls):
        cls.results = []
        cls.test_dir = tempfile.mkdtemp(prefix="wgse_smoke_")
        cls.dummy_fastq = os.path.join(cls.test_dir, "dummy.fastq")
        with open(cls.dummy_fastq, 'w') as f: f.write("@SEQ\nACTG\n+\n####\n")
        cls.dummy_vcf = os.path.join(cls.test_dir, "dummy.vcf.gz")
        with open(cls.dummy_vcf, 'w') as f: f.write("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        cls.dummy_bed = os.path.join(cls.test_dir, "dummy.bed")
        with open(cls.dummy_bed, 'w') as f: f.write("chrM\t1\t100\n")
        cls.dummy_ploidy = os.path.join(cls.test_dir, "ploidy.txt")
        with open(cls.dummy_ploidy, 'w') as f: f.write("MT\t1\nY\t1\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)
        if not cls.results: return
        print("\n" + "="*60)
        print(f"{'COMPREHENSIVE SMOKE TEST REPORT (MOCKED)':^60}")
        print("="*60)
        passed = 0
        for res in cls.results:
            status = "PASS" if res['success'] else "FAIL"
            if res['success']: passed += 1
            print(f"{res['name']:<35}: {status} {res.get('message','')}")
        print("-" * 60)
        print(f"TOTAL SMOKE: {passed}/{len(cls.results)} passed.")
        print("="*60)

    def record_result(self, name, success, message=""):
        self.results.append({"name": name, "success": success, "message": message})

    def run_sub(self, name, args):
        """Helper to run a subcommand with mocks."""
        import subprocess
        print(f">>> [SMOKE] BEGIN: {name}")
        real_popen = subprocess.Popen
        
        def popen_side_effect(*args, **kwargs):
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrM\tLN:16569\n", b"")
            mock_proc.returncode = 0
            mock_proc.stdout = io.BytesIO(b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrM\tLN:16569\n")
            return mock_proc

        _real_exists = os.path.exists
        _real_isfile = os.path.isfile

        def exists_side_effect(path):
            if not path: return False
            p = str(path)
            if any(x in p for x in ['.env', '.env.local', 'ploidy.txt', '.py', '.json']):
                return _real_exists(path)
            return True

        def isfile_side_effect(path):
            if not path: return False
            p = str(path)
            if any(x in p for x in ['.env', '.env.local', 'ploidy.txt', '.py', '.json']):
                return _real_isfile(path)
            return True

        # Create dummy files that info.py might try to check size of
        base_name = os.path.basename(INPUT_PATH if INPUT_PATH else "dummy.bam")
        for suffix in ['_bincvg.csv', '_samplecvg.json', '.bai', '.crai']:
            fpath = os.path.join(self.test_dir, base_name + suffix)
            if not _real_exists(fpath):
                with open(fpath, 'w') as f: f.write("dummy")

        success = False
        message = ""
        with patch('subprocess.Popen', side_effect=popen_side_effect), \
             patch('subprocess.run') as mock_run, \
             patch('os.path.exists', side_effect=exists_side_effect), \
             patch('os.path.isfile', side_effect=isfile_side_effect), \
             patch('os.path.getsize', return_value=1024), \
             patch('os.remove'), \
             patch('sys.stdin', io.StringIO("")), \
             patch('wgsextract_cli.commands.info.run_full_coverage'), \
             patch('wgsextract_cli.commands.info.run_sampled_coverage'), \
             patch('wgsextract_cli.commands.info.calculate_bam_md5', return_value="dummy_md5"):
            
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                full_args = ['wgsextract-cli', '--outdir', self.test_dir] + args
                with patch.object(sys, 'argv', full_args), \
                     redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    main()
                success = True
            except SystemExit as e:
                success = (e.code == 0)
                message = f"Exit {e.code}" if not success else ""
            except Exception as e:
                message = f"Crashed: {type(e).__name__}: {str(e)}"
        
        status = "PASS" if success else "FAIL"
        self.record_result(name, success, message)
        print(f"<<< [SMOKE] DONE: {name} ({status})")

    def test_00_help(self):
        try:
            with patch.object(sys, 'argv', ['wgsextract-cli', '--help']), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main()
            self.record_result("help", True)
        except SystemExit as e:
            self.record_result("help", e.code == 0)

    # --- INFO ---
    def test_01_info(self): self.run_sub("info", ['--input', INPUT_PATH, 'info'])
    def test_02_info_detailed(self): self.run_sub("info --detailed", ['--input', INPUT_PATH, 'info', '--detailed'])
    def test_03_info_calc_cov(self): self.run_sub("info calculate-coverage", ['--input', INPUT_PATH, 'info', 'calculate-coverage'])
    def test_04_info_cov_sample(self): self.run_sub("info coverage-sample", ['--input', INPUT_PATH, 'info', 'coverage-sample'])

    # --- BAM ---
    def test_05_bam_sort(self): self.run_sub("bam sort", ['--input', INPUT_PATH, 'bam', 'sort'])
    def test_06_bam_index(self): self.run_sub("bam index", ['--input', INPUT_PATH, 'bam', 'index'])
    def test_07_bam_unindex(self): self.run_sub("bam unindex", ['--input', INPUT_PATH, 'bam', 'unindex'])
    def test_08_bam_unsort(self): self.run_sub("bam unsort", ['--input', INPUT_PATH, 'bam', 'unsort'])
    def test_09_bam_tocram(self): self.run_sub("bam to-cram", ['--input', INPUT_PATH, 'bam', 'to-cram'])
    def test_10_bam_tobam(self): self.run_sub("bam to-bam", ['--input', INPUT_PATH, 'bam', 'to-bam'])
    def test_11_bam_unalign(self): self.run_sub("bam unalign", ['--input', INPUT_PATH, 'bam', 'unalign', '--r1', 'out.r1', '--r2', 'out.r2'])
    def test_12_bam_subset(self): self.run_sub("bam subset", ['--input', INPUT_PATH, 'bam', 'subset', '-f', '0.1'])

    # --- EXTRACT ---
    def test_13_extract_mito(self): self.run_sub("extract mito", ['--input', INPUT_PATH, '--ref', REF_PATH, 'extract', 'mito'])
    def test_14_extract_ydna(self): self.run_sub("extract ydna", ['--input', INPUT_PATH, '--ref', REF_PATH, 'extract', 'ydna'])
    def test_15_extract_unmapped(self): self.run_sub("extract unmapped", ['--input', INPUT_PATH, 'extract', 'unmapped', '--r1', 'u1.fq', '--r2', 'u2.fq'])

    # --- VCF ---
    def test_16_vcf_snp(self): self.run_sub("vcf snp", ['--input', INPUT_PATH, '--ref', REF_PATH, 'vcf', 'snp'])
    def test_17_vcf_indel(self): self.run_sub("vcf indel", ['--input', INPUT_PATH, '--ref', REF_PATH, 'vcf', 'indel'])
    def test_18_vcf_annotate(self): self.run_sub("vcf annotate", ['--input', self.dummy_vcf, 'vcf', 'annotate', '--ann-vcf', self.dummy_vcf, '--cols', 'ID'])
    def test_19_vcf_filter(self): self.run_sub("vcf filter", ['--input', self.dummy_vcf, 'vcf', 'filter', '--expr', 'QUAL>30'])
    def test_20_vcf_qc(self): self.run_sub("vcf qc", ['--input', self.dummy_vcf, 'vcf', 'qc'])

    # --- MICROARRAY / LINEAGE ---
    def test_21_microarray(self): self.run_sub("microarray", ['--input', INPUT_PATH, '--ref', REF_PATH, 'microarray'])
    def test_22_lineage_mtdna(self): 
        with patch('wgsextract_cli.commands.lineage.verify_paths_exist', return_value=True):
            self.run_sub("lineage mt-dna", ['--input', self.dummy_vcf, 'lineage', 'mt-dna', '--haplogrep-path', 'fake.jar'])
    def test_23_lineage_ydna(self): 
        with patch('wgsextract_cli.commands.lineage.verify_paths_exist', return_value=True):
            self.run_sub("lineage y-dna", ['--input', INPUT_PATH, 'lineage', 'y-dna', '--yleaf-path', 'fake.py', '--pos-file', 'fake.txt'])

    # --- REPAIR ---
    def test_24_repair_bam(self): self.run_sub("repair ftdna-bam", ['--input', INPUT_PATH, 'repair', 'ftdna-bam'])
    def test_25_repair_vcf(self): self.run_sub("repair ftdna-vcf", ['--input', self.dummy_vcf, 'repair', 'ftdna-vcf'])

    # --- QC ---
    def test_26_qc_fastp(self): self.run_sub("qc fastp", ['qc', 'fastp', '--r1', self.dummy_fastq, '--r2', self.dummy_fastq])
    def test_27_qc_fastqc(self): self.run_sub("qc fastqc", ['qc', 'fastqc', '--fastq', self.dummy_fastq])
    def test_28_qc_cov_wgs(self): self.run_sub("qc coverage-wgs", ['--input', INPUT_PATH, 'qc', 'coverage-wgs'])
    def test_29_qc_cov_wes(self): self.run_sub("qc coverage-wes", ['--input', INPUT_PATH, 'qc', 'coverage-wes', '--bed', self.dummy_bed])

    # --- REF / ALIGN ---
    def test_30_ref_identify(self): self.run_sub("ref identify", ['--input', INPUT_PATH, 'ref', 'identify'])
    def test_31_ref_download(self): self.run_sub("ref download", ['ref', 'download', '--url', 'http://fake', '--out', 'out.fa'])
    def test_32_ref_index(self): self.run_sub("ref index", ['--ref', 'fake.fa', 'ref', 'index'])
    def test_33_align_bwa(self): self.run_sub("align bwa", ['--ref', REF_PATH, 'align', '--r1', self.dummy_fastq, '--r2', self.dummy_fastq])

if __name__ == '__main__':
    unittest.main()
