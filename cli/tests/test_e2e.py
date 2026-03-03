import time
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import io
import logging
import tempfile
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout

# Ensure cli/src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Load environment variables
from dotenv import load_dotenv
cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_local = os.path.join(cli_root, ".env.local")
env_std = os.path.join(cli_root, ".env")

if os.path.exists(env_local):
    load_dotenv(dotenv_path=env_local)
if os.path.exists(env_std):
    load_dotenv(dotenv_path=env_std)

from wgsextract_cli.main import main
from wgsextract_cli.core.warnings import EXPECTED_TIME, M1_PRO_ESTIMATES
from wgsextract_cli.core.utils import ensure_vcf_indexed

# Get paths from environment
REF_PATH = os.environ.get('WGSE_REF')
INPUT_PATH = os.environ.get('WGSE_INPUT')

# Check for --full-data flag
FULL_DATA = "--full-data" in sys.argv or os.environ.get("WGSE_FULL_DATA") == "1"
if "--full-data" in sys.argv:
    sys.argv.remove("--full-data")

class TestCLIRealData(unittest.TestCase):
    """
    Behavioral validation using real genomic data and actual tool execution.
    """
    @classmethod
    def setUpClass(cls):
        cls.results = []
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            print(f"\n!!! WARNING: Configuration not found in environment or cli/.env.local")
        if FULL_DATA:
            print("\n!!! WARNING: Running in FULL DATA mode. This will be SLOW. !!!")

    @classmethod
    def tearDownClass(cls):
        if not cls.results: return
        mode_str = "FULL GENOME" if FULL_DATA else "CHRM"
        print(f"\n" + "="*105)
        print(f"{f'E2E {mode_str} EXECUTION & BENCHMARK REPORT':^105}")
        print("="*105)
        print(f"{'Command':<25} | {'Status':<13} | {'Duration':>11} | {'M1 Pro Ref':>11} | {'Expected':>11}")
        print("-" * 105)
        passed = 0
        total_duration = 0
        cls.results.sort(key=lambda x: x['name'])
        for res in cls.results:
            # For the special cache flow test 05a, "FAIL" actually means it passed our expectation of failure
            if res['name'] == "05a unindexed extract":
                status = "EXPECTED_FAIL" if res['success'] else "UNEXPECTED_PASS"
            else:
                status = "PASS" if res['success'] else "FAIL"
            
            if res['success']: passed += 1
            duration = res['duration']
            total_duration += duration
            expected = res['expected']
            
            m1_ref = "N/A"
            for key, val in M1_PRO_ESTIMATES.items():
                if key == res['expected_key']:
                    m1_ref = f"{val:.2f}s"
                    break

            print(f"{res['name']:<25} | {status:<13} | {duration:>10.2f}s | {m1_ref:>11} | {expected:>10}s")
        print("-" * 105)
        print(f"TOTAL REAL DATA ({mode_str}): {passed}/{len(cls.results)} passed. Total Time: {total_duration:.2f}s")
        print("="*105)

    def record_result(self, name, success, duration, expected, expected_key=""):
        self.results.append({"name": name, "success": success, "duration": duration, "expected": expected, "expected_key": expected_key})

    def run_real(self, name, args, expected_key):
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest("Paths not configured or not found")
            
        test_dir = tempfile.mkdtemp(prefix=f"wgse_real_{name.replace(' ','_').replace('(','').replace(')','')}_")
        ext = os.path.splitext(INPUT_PATH)[1]
        isolated_input = os.path.join(test_dir, f"input_isolated{ext}")
        os.symlink(INPUT_PATH, isolated_input)
        
        if "--region" in args or "-r" in args or "extract" in args or "microarray" in args:
            subprocess.run(["samtools", "index", isolated_input], check=False)

        expected_seconds = EXPECTED_TIME.get(expected_key, 0)
        start_time = time.perf_counter()
        
        if FULL_DATA:
            new_args = []
            skip_next = False
            for i, arg in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "--region" or arg == "-r":
                    skip_next = True
                    continue
                new_args.append(arg)
            args = new_args
            name = name.replace("(chrM)", "(Full)")

        print(f"\n>>> [REAL DATA] BEGIN: {name} (Expected: ~{expected_seconds}s)")

        success = False
        try:
            full_args = ['wgsextract-cli', '--outdir', test_dir] + args
            full_args = [arg if arg != INPUT_PATH else isolated_input for arg in full_args]
            
            with patch.object(sys, 'argv', full_args):
                main()
                success = True
        except SystemExit as e:
            success = (e.code == 0)
        except Exception as e:
            print(f"Error in {name}: {e}")
        finally:
            duration = time.perf_counter() - start_time
            self.record_result(name, success, duration, expected_seconds, expected_key)
            shutil.rmtree(test_dir)
            status = "PASS" if success else "FAIL"
            print(f"<<< [REAL DATA] DONE: {name} ({status}) in {duration:.2f}s")

    def test_00_help(self):
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--help']), redirect_stdout(io.StringIO()):
            try: main()
            except SystemExit: pass
        self.record_result("00 help", True, time.perf_counter()-start, 0, 'GetBAMHeader')

    # --- INFO ---
    def test_01_info(self): self.run_real("01 info", ['info', '--input', INPUT_PATH], 'ButtonBAMStats')
    def test_02_info_detailed(self): self.run_real("02 info --detailed", ['info', '--detailed', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonBAMStats2')
    
    # --- BAM ---
    def test_06_bam_sort_chrm(self): self.run_real("06 bam sort (chrM)", ['bam', 'sort', '--region', 'chrM', '--input', INPUT_PATH, '--ref', REF_PATH], 'GenSortedBAM')
    def test_07_bam_tocram_chrm(self): self.run_real("07 bam to-cram (chrM)", ['bam', 'to-cram', '--region', 'chrM', '--input', INPUT_PATH, '--ref', REF_PATH], 'BAMtoCRAM')

    # --- EXTRACT ---
    def test_10_extract_mito(self): self.run_real("10 extract mito", ['extract', 'mito', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonMitoBAM')

    # --- VCF ---
    def test_13_vcf_snp_chrm(self): self.run_real("13 vcf snp (chrM)", ['vcf', 'snp', '--region', 'chrM', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonSNPVCF')
    
    # --- NEW FEATURES ---
    
    def test_31_bam_mt_extract(self):
        self.run_real("31 bam mt-extract", ['bam', 'mt-extract', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonMitoBAM')

    def test_32_vcf_freebayes_chrm(self):
        self.run_real("32 vcf freebayes (chrM)", ['vcf', 'freebayes', '-r', 'chrM', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonSNPVCF')

    def test_33_vcf_filter_gene(self):
        # Use BRCA1 as it is more likely to be in the UCSC database than mitochondrial ones
        self.run_real("33 vcf filter --gene BRCA1", ['vcf', 'filter', '--gene', 'BRCA1', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonBAMStats')

    def test_34_vcf_trio_denovo(self):
        td = tempfile.mkdtemp()
        try:
            # Must have proper header with FORMAT/GT for bcftools to work
            vcf_header = "##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
            vcf_line = "chrM\t100\t.\tA\tG\t100\tPASS\t.\tGT\t"
            
            with open(os.path.join(td, "child.vcf"), 'w') as f: f.write(vcf_header + vcf_line + "0/1\n")
            with open(os.path.join(td, "mom.vcf"), 'w') as f: f.write(vcf_header + vcf_line + "0/0\n")
            with open(os.path.join(td, "dad.vcf"), 'w') as f: f.write(vcf_header + vcf_line + "0/0\n")
            
            for f in ["child.vcf", "mom.vcf", "dad.vcf"]:
                subprocess.run(["bgzip", os.path.join(td, f)], check=True)
                ensure_vcf_indexed(os.path.join(td, f+".gz"))
            
            self.run_real("34 vcf trio denovo", ['vcf', 'trio', '--proband', os.path.join(td, "child.vcf.gz"), '--mother', os.path.join(td, "mom.vcf.gz"), '--father', os.path.join(td, "dad.vcf.gz"), '--mode', 'denovo'], 'ButtonBAMStats')
        finally: shutil.rmtree(td)

    def test_35_vcf_cnv_chrm(self):
        self.run_real("35 vcf cnv (chrM)", ['vcf', 'cnv', '--input', INPUT_PATH, '--ref', REF_PATH], 'ButtonBAMStats2')

    def test_36_vep_chrm_offline(self):
        cache_dir = os.path.expanduser("~/.vep")
        if not os.path.exists(cache_dir):
            self.skipTest("VEP cache not found, skipping offline E2E test")
        
        td = tempfile.mkdtemp()
        try:
            vcf = os.path.join(td, "test.vcf.gz")
            # Generate a tiny VCF slice to annotate
            p1 = subprocess.Popen(["bcftools", "mpileup", "-r", "chrM:1-1000", "-f", REF_PATH, INPUT_PATH, "-Ou"], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["bcftools", "call", "-mv", "-Oz", "-o", vcf], stdin=p1.stdout)
            p1.stdout.close()
            p2.communicate()
            
            if not os.path.exists(vcf) or os.path.getsize(vcf) < 100:
                self.skipTest("Could not generate variants for VEP test slice")

            ensure_vcf_indexed(vcf)
            
            self.run_real("36 vep offline (chrM)", ['vep', '--input', vcf, '--ref', REF_PATH, '--format', 'vcf'], 'ButtonBAMStats2')
        finally: shutil.rmtree(td)

if __name__ == '__main__':
    unittest.main()
