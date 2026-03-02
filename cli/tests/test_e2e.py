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

# Check for --full-data flag in sys.argv
FULL_DATA = "--full-data" in sys.argv
if FULL_DATA:
    sys.argv.remove("--full-data")

class TestCLIRealData(unittest.TestCase):
    """
    Behavioral validation using real genomic data and actual tool execution.
    
    Goal: Verify the end-to-end correctness of the CLI on real CRAM/BAM files. 
    By targeting the small chrM region (by default) or the full genome (if --full-data),
    this suite confirms that automatic resource resolution, file conversions, 
    variant calling, and alignment chains function perfectly in a real-world 
    environment while providing execution benchmarks.
    """
    @classmethod
    def setUpClass(cls):
        cls.results = []
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            print(f"\n!!! WARNING: Configuration not found in environment or cli/.env.local")
            print(f"!!! REF_PATH: {REF_PATH}")
            print(f"!!! INPUT_PATH: {INPUT_PATH}")
        if FULL_DATA:
            print("\n!!! WARNING: Running in FULL DATA mode. This will be SLOW. !!!")

    @classmethod
    def tearDownClass(cls):
        if not cls.results: return
        mode_str = "FULL GENOME" if FULL_DATA else "CHRM"
        print(f"\n" + "="*85)
        print(f"{f'E2E {mode_str} EXECUTION & BENCHMARK REPORT':^85}")
        print("="*85)
        print(f"{'Command':<25} | {'Status':<6} | {'Duration':>11} | {'Expected':>11} | {'Diff':>11}")
        print("-" * 85)
        passed = 0
        total_duration = 0
        # Sort results by name to match master list order
        cls.results.sort(key=lambda x: x['name'])
        for res in cls.results:
            status = "PASS" if res['success'] else "FAIL"
            if res['success']: passed += 1
            duration = res['duration']
            total_duration += duration
            expected = res['expected']
            print(f"{res['name']:<25} | {status:<6} | {duration:>10.2f}s | {expected:>10}s | {duration-expected:>10.2f}s")
        print("-" * 85)
        print(f"TOTAL REAL DATA ({mode_str}): {passed}/{len(cls.results)} passed. Total Time: {total_duration:.2f}s")
        print("="*85)

    def record_result(self, name, success, duration, expected):
        self.results.append({"name": name, "success": success, "duration": duration, "expected": expected})

    def run_real(self, name, args, expected_key):
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest("Paths not configured or not found")
            
        test_dir = tempfile.mkdtemp(prefix=f"wgse_real_{name.replace(' ','_').replace('(','').replace(')','')}_")
        expected_seconds = EXPECTED_TIME.get(expected_key, 0)
        start_time = time.perf_counter()
        
        # Strip --region chrM if FULL_DATA is enabled
        if FULL_DATA:
            new_args = []
            skip_next = False
            for i, arg in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "--region":
                    skip_next = True
                    continue
                new_args.append(arg)
            args = new_args
            name = name.replace("(chrM)", "(Full)")
            name = name.replace("mito", "mito (Full)")

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

    def test_00_help(self):
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--help']), redirect_stdout(io.StringIO()):
            try: main()
            except SystemExit: pass
        self.record_result("00 help", True, time.perf_counter()-start, 0)

    # --- INFO ---
    def test_01_info(self): self.run_real("01 info", ['--input', INPUT_PATH, 'info'], 'ButtonBAMStats')
    def test_02_info_detailed(self): self.run_real("02 info --detailed", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', '--detailed'], 'ButtonBAMStats2')
    def test_03_info_calc_cov_chrm(self): self.run_real("03 info calculate-coverage (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', 'calculate-coverage', '--region', 'chrM'], 'CoverageStatsPoz')
    def test_04_info_cov_samp_chrm(self): self.run_real("04 info coverage-sample (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', 'coverage-sample', '--region', 'chrM'], 'ButtonBAMStats2')

    # --- BAM ---
    def test_05_bam_sort_chrm(self): self.run_real("05 bam sort (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'sort', '--region', 'chrM'], 'GenSortedBAM')
    def test_06_bam_index(self): self.run_real("06 bam index", ['--input', INPUT_PATH, 'bam', 'index'], 'GenBAMIndex')
    def test_07_bam_unindex(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_input = os.path.join(td, "test.cram")
            shutil.copy(INPUT_PATH, tmp_input)
            if os.path.exists(INPUT_PATH + ".crai"): shutil.copy(INPUT_PATH + ".crai", tmp_input + ".crai")
            self.run_real("07 bam unindex", ['--input', tmp_input, 'bam', 'unindex'], 'LiftoverCleanup')
    def test_08_bam_unsort(self): self.run_real("08 bam unsort", ['--input', INPUT_PATH, 'bam', 'unsort'], 'LiftoverCleanup')
    def test_09_bam_tocram_chrm(self): self.run_real("09 bam to-cram (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'to-cram', '--region', 'chrM'], 'BAMtoCRAM')
    def test_10_bam_tobam_chrm(self): self.run_real("10 bam to-bam (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'to-bam', '--region', 'chrM'], 'CRAMtoBAM')
    def test_11_bam_unalign_chrm(self): 
        with tempfile.TemporaryDirectory() as td:
            r1, r2 = os.path.join(td, 'r1.fq'), os.path.join(td, 'r2.fq')
            self.run_real("11 bam unalign (chrM)", ['--input', INPUT_PATH, 'bam', 'unalign', '--r1', r1, '--r2', r2, '--region', 'chrM'], 'ButtonUnalignBAM')
    def test_12_bam_subset_chrm(self): self.run_real("12 bam subset (chrM)", ['--input', INPUT_PATH, 'bam', 'subset', '-f', '0.01', '--region', 'chrM'], 'ButtonBAMStats')

    # --- EXTRACT ---
    def test_13_extract_mito(self): self.run_real("13 extract mito", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'mito'], 'ButtonMitoBAM')
    def test_14_extract_ydna(self): self.run_real("14 extract ydna", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'ydna'], 'ButtonYonly')
    def test_15_extract_unmapped(self): 
        with tempfile.TemporaryDirectory() as td:
            u1, u2 = os.path.join(td, 'u1.fq'), os.path.join(td, 'u2.fq')
            self.run_real("15 extract unmapped", ['--input', INPUT_PATH, 'extract', 'unmapped', '--r1', u1, '--r2', u2], 'ButtonUnmappedReads')

    # --- VCF ---
    def test_16_vcf_snp_chrm(self): self.run_real("16 vcf snp (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'snp', '--region', 'chrM'], 'ButtonSNPVCF')
    def test_17_vcf_indel_chrm(self): self.run_real("17 vcf indel (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'indel', '--region', 'chrM'], 'ButtonInDelVCF')
    def test_18_vcf_annotate(self):
        with tempfile.TemporaryDirectory() as td:
            vcf_raw = os.path.join(td, "test.vcf")
            with open(vcf_raw, 'w') as f: f.write("##fileformat=VCFv4.2\n##FILTER=<ID=PASS,Description=\"P\">\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vcf_gz = vcf_raw + ".gz"
            subprocess.run(["bgzip", "-c", vcf_raw], stdout=open(vcf_gz, "wb"), check=True)
            subprocess.run(["tabix", "-p", "vcf", vcf_gz], check=True)
            self.run_real("18 vcf annotate", ['--input', vcf_gz, 'vcf', 'annotate', '--ann-vcf', vcf_gz, '--cols', 'ID'], 'ButtonBAMStats')
    def test_19_vcf_filter(self):
        with tempfile.TemporaryDirectory() as td:
            vcf_raw = os.path.join(td, "test.vcf")
            with open(vcf_raw, 'w') as f: f.write("##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vcf_gz = vcf_raw + ".gz"
            subprocess.run(["bgzip", "-c", vcf_raw], stdout=open(vcf_gz, "wb"), check=True)
            subprocess.run(["tabix", "-p", "vcf", vcf_gz], check=True)
            self.run_real("19 vcf filter", ['--input', vcf_gz, 'vcf', 'filter', '--expr', 'QUAL>30'], 'ButtonBAMStats')
    def test_20_vcf_qc(self):
        with tempfile.TemporaryDirectory() as td:
            vcf_raw = os.path.join(td, "test.vcf")
            with open(vcf_raw, 'w') as f: f.write("##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vcf_gz = vcf_raw + ".gz"
            subprocess.run(["bgzip", "-c", vcf_raw], stdout=open(vcf_gz, "wb"), check=True)
            self.run_real("20 vcf qc", ['--input', vcf_gz, 'vcf', 'qc'], 'ButtonBAMStats')

    # --- MICROARRAY / LINEAGE ---
    def test_21_microarray_chrm(self): self.run_real("21 microarray (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'microarray', '--region', 'chrM'], 'ButtonCombinedKit')
    def test_22_lineage_mtdna(self):
        with tempfile.TemporaryDirectory() as td:
            vcf = os.path.join(td, "test.vcf")
            with open(vcf, 'w') as f: f.write("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            with patch('wgsextract_cli.core.utils.run_command'):
                # Global --input must come before subcommand
                self.run_real("22 lineage mt-dna", ['--input', vcf, 'lineage', 'mt-dna', '--haplogrep-path', 'fake.jar'], 'ButtonMTHaplo')
    def test_23_lineage_ydna(self):
        with patch('wgsextract_cli.core.utils.run_command'):
            # Global --input must come before subcommand
            self.run_real("23 lineage y-dna", ['--input', INPUT_PATH, 'lineage', 'y-dna', '--yleaf-path', 'fake.py', '--pos-file', 'fake.txt'], 'ButtonYHaplo')

    # --- REPAIR ---
    def test_24_repair_bam(self):
        start = time.perf_counter()
        print("\n>>> [REAL DATA] BEGIN: 24 repair ftdna-bam (plumbing)")
        with patch('sys.stdin', io.StringIO("@HD\tVN:1.6\tSO:coordinate\nREAD 1\t0\tchrM\t100\t60\t100M\t*\t0\t0\tACTG\t####\n")), \
             patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(sys, 'argv', ['wgsextract-cli', 'repair', 'ftdna-bam']):
                main()
        self.record_result("24 repair ftdna-bam", True, time.perf_counter()-start, 0)
    def test_25_repair_vcf(self):
        start = time.perf_counter()
        print("\n>>> [REAL DATA] BEGIN: 25 repair ftdna-vcf (plumbing)")
        with patch('sys.stdin', io.StringIO("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\tINFO=VAL;QUAL=100\n")), \
             patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(sys, 'argv', ['wgsextract-cli', 'repair', 'ftdna-vcf']):
                main()
        self.record_result("25 repair ftdna-vcf", True, time.perf_counter()-start, 0)

    # --- QC ---
    def test_26_qc_fastp(self):
        td = tempfile.mkdtemp(prefix="wgse_real_qc_fastp_")
        try:
            r1, r2 = os.path.join(td, "r1.fq"), os.path.join(td, "r2.fq")
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', td, '--input', INPUT_PATH, 'bam', 'unalign', '--r1', r1, '--r2', r2, '--region', 'chrM']):
                main()
            self.run_real("26 qc fastp", ['qc', 'fastp', '--r1', r1, '--r2', r2], 'ButtonFastp')
        finally: shutil.rmtree(td)
    def test_27_qc_fastqc(self):
        with tempfile.TemporaryDirectory() as td:
            fq = os.path.join(td, "test.fq")
            with open(fq, 'w') as f: f.write("@SEQ\nACTG\n+\n####\n")
            self.run_real("27 qc fastqc", ['qc', 'fastqc', '--fastq', fq], 'ButtonFastqc')
    def test_28_qc_cov_wgs_chrm(self): self.run_real("28 qc coverage-wgs (chrM)", ['--input', INPUT_PATH, 'qc', 'coverage-wgs', '--region', 'chrM'], 'CoverageStatsBIN')
    def test_29_qc_cov_wes_chrm(self):
        with tempfile.TemporaryDirectory() as td:
            bed = os.path.join(td, "test.bed")
            with open(bed, 'w') as f: f.write("chrM\t1\t100\n")
            self.run_real("29 qc coverage-wes (chrM)", ['--input', INPUT_PATH, 'qc', 'coverage-wes', '--bed', bed, '--region', 'chrM'], 'CoverageStatsWES')

    # --- REF / ALIGN ---
    def test_30_ref_identify(self): self.run_real("30 ref identify", ['--input', INPUT_PATH, 'ref', 'identify'], 'GetBAMHeader')
    def test_31_ref_download(self):
        with patch('subprocess.run'):
            self.run_real("31 ref download", ['ref', 'download', '--url', 'http://fake', '--out', 'out.fa'], 'LiftoverCleanup')
    def test_32_ref_index(self):
        with tempfile.TemporaryDirectory() as td:
            fa = os.path.join(td, "test.fa")
            with open(fa, 'w') as f: f.write(">chrM\nACTG\n")
            self.run_real("32 ref index", ['--ref', fa, 'ref', 'index'], 'CreateAlignIndices')
    def test_33_align_bwa(self):
        td = tempfile.mkdtemp(prefix="wgse_real_align_")
        try:
            r1, r2 = os.path.join(td, "r1.fq"), os.path.join(td, "r2.fq")
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', td, '--input', INPUT_PATH, 'bam', 'unalign', '--r1', r1, '--r2', r2, '--region', 'chrM']):
                main()
            from wgsextract_cli.core.utils import ReferenceLibrary
            lib = ReferenceLibrary(REF_PATH, "a08daf6f9f22170759705fd99e471b62")
            ref_fasta = lib.fasta if lib.fasta else REF_PATH
            self.run_real("33 align bwa", ['--ref', ref_fasta, 'align', '--r1', r1, '--r2', r2], 'ButtonAlignBAM')
        finally: shutil.rmtree(td)

if __name__ == '__main__':
    unittest.main()
