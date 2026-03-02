import time
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
from wgsextract_cli.core.warnings import EXPECTED_TIME

# Get paths from environment (typically loaded from cli/.env.local)
REF_PATH = os.environ.get('WGSE_REF')
INPUT_PATH = os.environ.get('WGSE_INPUT')

class TestCLISmoke(unittest.TestCase):
    """
    Rapid Smoke Tests covering ALL subcommand combinations.
    Heavy processing is mocked to verify CLI 'plumbing' and path resolution.
    """
    @classmethod
    def setUpClass(cls):
        cls.results = []
        if not REF_PATH or not INPUT_PATH:
            print("\n!!! WARNING: WGSE_REF or WGSE_INPUT not set in environment or cli/.env.local")
            print("!!! Smoke tests will use dummy values where possible but may skip others.")
            
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
        print("\n" + "="*60)
        print("COMPREHENSIVE SMOKE TEST REPORT (MOCKED)")
        print("="*60)
        passed = 0
        for res in cls.results:
            status = "PASS" if res['success'] else "FAIL"
            if res['success']: passed += 1
            print(f"{res['name']:<30}: {status} {res.get('message','')}")
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
        header_cache = {}

        def popen_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if '-H' in cmd_str or 'idxstats' in cmd_str:
                if 'header' not in header_cache:
                    try:
                        p = real_popen(*args, **kwargs)
                        out, err = p.communicate(timeout=2)
                        header_cache['header'] = (out, err, p.returncode)
                    except:
                        header_cache['header'] = (b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrM\tLN:16569\n", b"", 0)
                out, err, ret = header_cache['header']
                mock_proc = MagicMock()
                mock_proc.communicate.return_value = (out, err)
                mock_proc.returncode = ret
                mock_proc.stdout = io.BytesIO(out)
                return mock_proc
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b'', b'')
            mock_proc.returncode = 0
            return mock_proc

        success = False
        message = ""
        with patch('subprocess.Popen', side_effect=popen_side_effect), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            try:
                # Use absolute paths if available
                processed_args = []
                for a in args:
                    if a == 'INPUT_PATH_PLACEHOLDER': processed_args.append(INPUT_PATH if INPUT_PATH else self.dummy_fastq)
                    elif a == 'REF_PATH_PLACEHOLDER': processed_args.append(REF_PATH if REF_PATH else self.test_dir)
                    else: processed_args.append(a)

                full_args = ['wgsextract-cli', '--outdir', self.test_dir] + processed_args
                with patch.object(sys, 'argv', full_args), \
                     redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    main()
                success = True
            except SystemExit as e:
                success = (e.code == 0)
                message = f"Exit {e.code}" if not success else ""
            except Exception as e:
                message = f"Crashed: {type(e).__name__}"
        
        status = "PASS" if success else "FAIL"
        self.record_result(name, success, message)
        print(f"<<< [SMOKE] DONE: {name} ({status})")

    def test_smoke_01_info(self): self.run_sub("info", ['--ref', 'REF_PATH_PLACEHOLDER', '--input', 'INPUT_PATH_PLACEHOLDER', 'info'])
    def test_smoke_02_info_detailed(self): self.run_sub("info --detailed", ['--ref', 'REF_PATH_PLACEHOLDER', '--input', 'INPUT_PATH_PLACEHOLDER', 'info', '--detailed'])
    def test_smoke_03_bam_sort(self): self.run_sub("bam sort", ['--input', 'INPUT_PATH_PLACEHOLDER', 'bam', 'sort'])
    def test_smoke_04_bam_index(self): self.run_sub("bam index", ['--input', 'INPUT_PATH_PLACEHOLDER', 'bam', 'index'])
    def test_smoke_05_extract_mito(self): self.run_sub("extract mito", ['--ref', 'REF_PATH_PLACEHOLDER', '--input', 'INPUT_PATH_PLACEHOLDER', 'extract', 'mito'])
    def test_smoke_06_vcf_snp(self): self.run_sub("vcf snp", ['--ref', 'REF_PATH_PLACEHOLDER', '--input', 'INPUT_PATH_PLACEHOLDER', 'vcf', 'snp'])
    def test_smoke_07_vcf_annotate(self): self.run_sub("vcf annotate", ['--input', self.dummy_vcf, 'vcf', 'annotate', '--ann-vcf', self.dummy_vcf, '--cols', 'ID'])
    def test_smoke_08_microarray(self): self.run_sub("microarray", ['--ref', 'REF_PATH_PLACEHOLDER', '--input', 'INPUT_PATH_PLACEHOLDER', 'microarray'])
    def test_smoke_09_ref_identify(self): self.run_sub("ref identify", ['--input', 'INPUT_PATH_PLACEHOLDER', 'ref', 'identify'])
    def test_smoke_10_align_bwa(self): self.run_sub("align bwa", ['--ref', 'REF_PATH_PLACEHOLDER', 'align', '--r1', self.dummy_fastq, '--r2', self.dummy_fastq])

class TestCLIRealData(unittest.TestCase):
    """
    Actual End-to-End Tests using real data (chrM) with benchmarking.
    """
    @classmethod
    def setUpClass(cls):
        cls.results = []
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            print(f"\n!!! SKIP REAL DATA: Configuration not found in environment or cli/.env.local")
            print(f"!!! REF_PATH: {REF_PATH}")
            print(f"!!! INPUT_PATH: {INPUT_PATH}")

    @classmethod
    def tearDownClass(cls):
        if not cls.results: return
        print(f"\n{'='*85}")
        print(f"{'E2E CHRM EXECUTION & BENCHMARK REPORT':^85}")
        print("="*85)
        print(f"{'Command':<25} | {'Status':<6} | {'Duration':>11} | {'Expected':>11} | {'Diff':>11}")
        print("-" * 85)
        passed = 0
        total_duration = 0
        for res in cls.results:
            status = "PASS" if res['success'] else "FAIL"
            if res['success']: passed += 1
            duration = res['duration']
            total_duration += duration
            expected = res['expected']
            print(f"{res['name']:<25} | {status:<6} | {duration:>10.2f}s | {expected:>10}s | {duration-expected:>10.2f}s")
        print("-" * 85)
        print(f"TOTAL REAL DATA: {passed}/{len(cls.results)} passed. Total Time: {total_duration:.2f}s")
        print("="*85)

    def record_result(self, name, success, duration, expected):
        self.results.append({"name": name, "success": success, "duration": duration, "expected": expected})

    def run_real(self, name, args, expected_key):
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest("Paths not configured or not found")
            
        test_dir = tempfile.mkdtemp(prefix=f"wgse_real_{name.replace(' ','_')}_")
        expected_seconds = EXPECTED_TIME.get(expected_key, 0)
        start_time = time.perf_counter()
        
        print(f"\n>>> [REAL DATA] BEGIN: {name} (Expected: ~{expected_seconds}s)")

        success = False
        try:
            full_args = ['wgsextract-cli', '--outdir', test_dir] + args
            with patch.object(sys, 'argv', full_args):
                main()
                success = True
        except SystemExit as e:
            success = (e.code == 0)
        except Exception as e:
            print(f"Error in {name}: {e}")
        finally:
            duration = time.perf_counter() - start_time
            self.record_result(name, success, duration, expected_seconds)
            shutil.rmtree(test_dir)
            status = "PASS" if success else "FAIL"
            print(f"<<< [REAL DATA] DONE: {name} ({status}) in {duration:.2f}s")

    def test_real_01_ref_identify(self): self.run_real("ref identify", ['--input', INPUT_PATH, 'ref', 'identify'], 'GetBAMHeader')
    def test_real_02_info_detailed(self): self.run_real("info --detailed", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', '--detailed'], 'ButtonBAMStats2')
    def test_real_03_extract_mito(self): self.run_real("extract mito", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'mito'], 'ButtonMitoBAM')
    def test_real_04_bam_sort_chrm(self): self.run_real("bam sort (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'sort', '--region', 'chrM'], 'GenSortedBAM')
    def test_real_05_microarray_chrm(self): self.run_real("microarray (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'microarray', '--region', 'chrM'], 'ButtonCombinedKit')
    def test_real_06_vcf_snp_chrm(self): self.run_real("vcf snp (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'snp', '--region', 'chrM'], 'ButtonSNPVCF')
    def test_real_07_vcf_indel_chrm(self): self.run_real("vcf indel (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'indel', '--region', 'chrM'], 'ButtonInDelVCF')
    
    def test_real_08_bam_index(self): self.run_real("bam index", ['--input', INPUT_PATH, 'bam', 'index'], 'GenBAMIndex')
    def test_real_09_bam_to_cram_chrm(self): self.run_real("bam to-cram (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'to-cram', '--region', 'chrM'], 'BAMtoCRAM')
    def test_real_10_bam_to_bam_chrm(self): self.run_real("bam to-bam (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'to-bam', '--region', 'chrM'], 'CRAMtoBAM')
    def test_real_11_bam_subset_chrm(self): self.run_real("bam subset (chrM)", ['--input', INPUT_PATH, 'bam', 'subset', '-f', '0.01', '--region', 'chrM'], 'ButtonBAMStats')
    
    def test_real_12_extract_ydna(self): self.run_real("extract ydna", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'ydna'], 'ButtonYonly')
    def test_real_13_qc_cov_wgs_chrm(self): self.run_real("qc coverage-wgs (chrM)", ['--input', INPUT_PATH, 'qc', 'coverage-wgs', '--region', 'chrM'], 'CoverageStatsBIN')
    
    def test_real_14_vcf_qc(self):
        # Create a dummy VCF for QC test
        with tempfile.TemporaryDirectory() as td:
            vcf = os.path.join(td, "test.vcf")
            with open(vcf, 'w') as f: f.write("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            self.run_real("vcf qc", ['--input', vcf, 'vcf', 'qc'], 'ButtonBAMStats')

    def test_real_15_fastq_chain(self):
        """Chain: unalign (chrM) -> fastp -> align."""
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest("Paths not configured")
        
        td = tempfile.mkdtemp(prefix="wgse_real_chain_")
        start_time = time.perf_counter()
        try:
            print("\n>>> [REAL DATA] BEGIN: fastq chain (unalign -> fastp -> align)")
            r1, r2 = os.path.join(td, "r1.fq"), os.path.join(td, "r2.fq")
            
            # Resolve indexed fasta (hs38DH)
            from wgsextract_cli.core.utils import ReferenceLibrary
            md5_sig = "a08daf6f9f22170759705fd99e471b62"
            lib = ReferenceLibrary(REF_PATH, md5_sig)
            ref_fasta = lib.fasta if lib.fasta else REF_PATH

            # 1. Unalign (chrM)
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', td, '--input', INPUT_PATH, 'bam', 'unalign', '--r1', r1, '--r2', r2, '--region', 'chrM']):
                main()
            # 2. Fastp
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', td, 'qc', 'fastp', '--r1', r1, '--r2', r2]):
                main()
            # 3. Align (Use indexed FASTA)
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', td, '--ref', ref_fasta, 'align', '--r1', r1, '--r2', r2]):
                main()
            self.record_result("fastq chain", True, time.perf_counter() - start_time, 0)
            print(f"<<< [REAL DATA] DONE: fastq chain (PASS)")
        except Exception as e:
            print(f"Chain failed: {e}")
            self.record_result("fastq chain", False, time.perf_counter() - start_time, 0)
            print(f"<<< [REAL DATA] DONE: fastq chain (FAIL)")
        finally:
            shutil.rmtree(td)

if __name__ == '__main__':
    unittest.main()
