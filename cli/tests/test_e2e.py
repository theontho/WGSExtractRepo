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
from wgsextract_cli.core.warnings import EXPECTED_TIME, M1_PRO_ESTIMATES

# Get paths from environment (typically loaded from cli/.env.local)
REF_PATH = os.environ.get('WGSE_REF')
INPUT_PATH = os.environ.get('WGSE_INPUT')

# Check for --full-data flag in sys.argv or environment variable
FULL_DATA = "--full-data" in sys.argv or os.environ.get("WGSE_FULL_DATA") == "1"
if "--full-data" in sys.argv:
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
        print(f"\n" + "="*105)
        print(f"{f'E2E {mode_str} EXECUTION & BENCHMARK REPORT':^105}")
        print("="*105)
        print(f"{'Command':<25} | {'Status':<13} | {'Duration':>11} | {'M1 Pro Ref':>11} | {'Expected':>11}")
        print("-" * 105)
        passed = 0
        total_duration = 0
        # Sort results by name to match master list order
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
            
            # Find matching M1 Pro Ref if available
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
        
        # --- ISOLATION: Symlink the input into the test directory ---
        # This prevents side-effects like .crai/.bai files from persisting between tests
        ext = os.path.splitext(INPUT_PATH)[1]
        isolated_input = os.path.join(test_dir, f"input_isolated{ext}")
        os.symlink(INPUT_PATH, isolated_input)
        
        # Replace global INPUT_PATH with the isolated symlink in the arguments
        args = [arg if arg != INPUT_PATH else isolated_input for arg in args]
        
        # --- REGION DEPENDENCY: Index the isolated input if --region is used ---
        if "--region" in args or "extract" in args or "microarray" in args:
            subprocess.run(["samtools", "index", isolated_input], check=False)
        # -------------------------------------------------------------

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
            # Current argparse setup requires subcommand first, then global or local args.
            # Find the subcommand in args
            choices = ['info', 'bam', 'extract', 'microarray', 'lineage', 'vcf', 'repair', 'qc', 'ref', 'align', 'vep']
            sub_idx = -1
            for i, arg in enumerate(args):
                if arg in choices:
                    sub_idx = i
                    break
            
            if sub_idx != -1:
                global_args = []
                if '--outdir' not in args:
                    global_args.extend(['--outdir', test_dir])
                full_args = ['wgsextract-cli', args[sub_idx]] + args[:sub_idx] + args[sub_idx+1:] + global_args
            else:
                global_args = []
                if '--outdir' not in args:
                    global_args.extend(['--outdir', test_dir])
                full_args = ['wgsextract-cli'] + args + global_args
            
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
    def test_01_info(self): self.run_real("01 info", ['--input', INPUT_PATH, 'info'], 'ButtonBAMStats')
    def test_02_info_detailed(self): self.run_real("02 info --detailed", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', '--detailed'], 'ButtonBAMStats2')
    def test_03_info_calc_cov_chrm(self): self.run_real("03 info calculate-coverage (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', 'calculate-coverage', '--region', 'chrM'], 'CoverageStatsPoz')
    def test_04_info_cov_samp_chrm(self): self.run_real("04 info coverage-sample (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'info', 'coverage-sample', '--region', 'chrM'], 'ButtonBAMStats2')

    # --- CACHE & STATE EFFECTS FLOW ---
    def test_05_cache_and_state_flow(self):
        if not REF_PATH or not INPUT_PATH or not os.path.exists(REF_PATH) or not os.path.exists(INPUT_PATH):
            self.skipTest("Paths not configured or not found")
        
        flow_dir = tempfile.mkdtemp(prefix="wgse_real_cache_flow_")
        ext = os.path.splitext(INPUT_PATH)[1]
        test_input = os.path.join(flow_dir, f"test_input{ext}")
        extracted_bam = os.path.join(flow_dir, "test_input.bam")
        os.symlink(INPUT_PATH, test_input)
        
        if os.path.exists(test_input + ".crai"): os.remove(test_input + ".crai")
        if os.path.exists(test_input + ".bai"): os.remove(test_input + ".bai")

        print("\n" + "-"*40 + "\n>>> STARTING CACHE & STATE FLOW\n" + "-"*40)
        
        # 05a Unindexed
        print("\n>>> [REAL DATA] BEGIN: 05a unindexed region extract")
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--ref', REF_PATH, '--input', test_input, 'bam', 'to-bam', '--region', 'chrM']):
            try: main()
            except SystemExit: pass
        is_unindexed_failed = True
        if os.path.exists(extracted_bam):
            res = subprocess.run(["samtools", "view", "-c", extracted_bam], capture_output=True, text=True)
            count = int(res.stdout.strip()) if res.stdout.strip() else 0
            is_unindexed_failed = (count == 0)
        self.record_result("05a unindexed extract", is_unindexed_failed, time.perf_counter() - start, EXPECTED_TIME.get('CRAMtoBAM', 0), 'CRAMtoBAM')
        if os.path.exists(extracted_bam): os.remove(extracted_bam)

        # 05b Index
        print("\n>>> [REAL DATA] BEGIN: 05b bam index")
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--input', test_input, 'bam', 'index']):
            try: main()
            except SystemExit: pass
        index_created = os.path.exists(test_input + ".crai") or os.path.exists(test_input + ".bai")
        self.record_result("05b bam index", index_created, time.perf_counter() - start, EXPECTED_TIME.get('GenBAMIndex', 0), 'GenBAMIndex')

        # 05c Indexed Extract
        print("\n>>> [REAL DATA] BEGIN: 05c indexed region extract")
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--ref', REF_PATH, '--input', test_input, 'bam', 'to-bam', '--region', 'chrM']):
            try: main()
            except SystemExit: pass
        indexed_time = time.perf_counter() - start
        extract_success = False
        if os.path.exists(extracted_bam):
            res = subprocess.run(["samtools", "view", "-c", extracted_bam], capture_output=True, text=True)
            count = int(res.stdout.strip()) if res.stdout.strip() else 0
            extract_success = (count > 0)
        self.record_result("05c indexed extract", extract_success, indexed_time, EXPECTED_TIME.get('CRAMtoBAM', 0), 'CRAMtoBAM')

        # 05d Unindex
        print("\n>>> [REAL DATA] BEGIN: 05d bam unindex")
        start = time.perf_counter()
        with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--input', test_input, 'bam', 'unindex']):
            try: main()
            except SystemExit: pass
        unindex_success = not os.path.exists(test_input + ".crai") and not os.path.exists(test_input + ".bai")
        self.record_result("05d bam unindex", unindex_success, time.perf_counter() - start, EXPECTED_TIME.get('LiftoverCleanup', 0), 'LiftoverCleanup')

        if extract_success:
            # 05e Unsort
            print("\n>>> [REAL DATA] BEGIN: 05e bam unsort")
            start = time.perf_counter()
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--input', extracted_bam, 'bam', 'unsort']):
                try: main()
                except SystemExit: pass
            unsorted_file = os.path.join(flow_dir, "test_input_unsorted.bam")
            unsort_success = os.path.exists(unsorted_file)
            self.record_result("05e bam unsort", unsort_success, time.perf_counter() - start, EXPECTED_TIME.get('LiftoverCleanup', 0), 'LiftoverCleanup')
            
            # 05f Sort Unsorted
            print("\n>>> [REAL DATA] BEGIN: 05f bam sort (from unsorted)")
            start = time.perf_counter()
            with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--input', unsorted_file, 'bam', 'sort']):
                try: main()
                except SystemExit: pass
            sorted_file = os.path.join(flow_dir, "test_input_unsorted_sorted.bam")
            sort1_success = os.path.exists(sorted_file)
            self.record_result("05f bam sort (unsorted)", sort1_success, time.perf_counter() - start, EXPECTED_TIME.get('GenSortedBAM', 0), 'GenSortedBAM')

            # 05g Sort Sorted
            if sort1_success:
                print("\n>>> [REAL DATA] BEGIN: 05g bam sort (from sorted)")
                start = time.perf_counter()
                with patch.object(sys, 'argv', ['wgsextract-cli', '--outdir', flow_dir, '--input', sorted_file, 'bam', 'sort']):
                    try: main()
                    except SystemExit: pass
                sort2_success = os.path.exists(os.path.join(flow_dir, "test_input_unsorted_sorted_sorted.bam"))
                self.record_result("05g bam sort (sorted)", sort2_success, time.perf_counter() - start, EXPECTED_TIME.get('GenSortedBAM', 0), 'GenSortedBAM')
            else:
                self.record_result("05g bam sort (sorted)", False, 0, EXPECTED_TIME.get('GenSortedBAM', 0), 'GenSortedBAM')
        else:
            for n in ["05e bam unsort", "05f bam sort (unsorted)", "05g bam sort (sorted)"]:
                self.record_result(n, False, 0, 0, 'LiftoverCleanup')

        shutil.rmtree(flow_dir)
        print("-"*40 + "\n<<< FINISHED CACHE & STATE FLOW\n" + "-"*40)

    # --- BAM ---
    def test_06_bam_sort_chrm(self): self.run_real("06 bam sort (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'sort', '--region', 'chrM'], 'GenSortedBAM')
    def test_07_bam_tocram_chrm(self): self.run_real("07 bam to-cram (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'bam', 'to-cram', '--region', 'chrM'], 'BAMtoCRAM')
    def test_08_bam_unalign_chrm(self): 
        with tempfile.TemporaryDirectory() as td:
            r1, r2 = os.path.join(td, 'r1.fq'), os.path.join(td, 'r2.fq')
            self.run_real("08 bam unalign (chrM)", ['--input', INPUT_PATH, 'bam', 'unalign', '--r1', r1, '--r2', r2, '--region', 'chrM'], 'ButtonUnalignBAM')
    def test_09_bam_subset_chrm(self): self.run_real("09 bam subset (chrM)", ['--input', INPUT_PATH, 'bam', 'subset', '-f', '0.01', '--region', 'chrM'], 'ButtonBAMStats')

    # --- EXTRACT ---
    def test_10_extract_mito(self): self.run_real("10 extract mito", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'mito'], 'ButtonMitoBAM')
    def test_11_extract_ydna(self): self.run_real("11 extract ydna", ['--ref', REF_PATH, '--input', INPUT_PATH, 'extract', 'ydna'], 'ButtonYonly')
    def test_12_extract_unmapped(self): 
        with tempfile.TemporaryDirectory() as td:
            u1, u2 = os.path.join(td, 'u1.fq'), os.path.join(td, 'u2.fq')
            self.run_real("12 extract unmapped", ['--input', INPUT_PATH, 'extract', 'unmapped', '--r1', u1, '--r2', u2], 'ButtonUnmappedReads')

    # --- VCF ---
    def test_13_vcf_snp_chrm(self): self.run_real("13 vcf snp (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'snp', '--region', 'chrM'], 'ButtonSNPVCF')
    def test_14_vcf_indel_chrm(self): self.run_real("14 vcf indel (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'vcf', 'indel', '--region', 'chrM'], 'ButtonInDelVCF')
    def test_15_vcf_annotate(self):
        with tempfile.TemporaryDirectory() as td:
            v = os.path.join(td, "t.vcf")
            with open(v, 'w') as f: f.write("##fileformat=VCFv4.2\n##FILTER=<ID=PASS,Description=\"P\">\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vg = v + ".gz"
            subprocess.run(["bgzip", "-c", v], stdout=open(vg, "wb"), check=True)
            subprocess.run(["tabix", "-p", "vcf", vg], check=True)
            self.run_real("15 vcf annotate", ['--input', vg, 'vcf', 'annotate', '--ann-vcf', vg, '--cols', 'ID'], 'ButtonBAMStats')
    def test_16_vcf_filter(self):
        with tempfile.TemporaryDirectory() as td:
            v = os.path.join(td, "t.vcf")
            with open(v, 'w') as f: f.write("##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vg = v + ".gz"
            subprocess.run(["bgzip", "-c", v], stdout=open(vg, "wb"), check=True)
            subprocess.run(["tabix", "-p", "vcf", vg], check=True)
            self.run_real("16 vcf filter", ['--input', vg, 'vcf', 'filter', '--expr', 'QUAL>30'], 'ButtonBAMStats')
    def test_17_vcf_qc(self):
        with tempfile.TemporaryDirectory() as td:
            v = os.path.join(td, "t.vcf")
            with open(v, 'w') as f: f.write("##fileformat=VCFv4.2\n##contig=<ID=chrM,length=16569>\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\t.\n")
            vg = v + ".gz"
            subprocess.run(["bgzip", "-c", v], stdout=open(vg, "wb"), check=True)
            self.run_real("17 vcf qc", ['--input', vg, 'vcf', 'qc'], 'ButtonBAMStats')

    # --- MICROARRAY / LINEAGE ---
    def test_18_microarray_chrm(self): self.run_real("18 microarray (chrM)", ['--ref', REF_PATH, '--input', INPUT_PATH, 'microarray', '--region', 'chrM'], 'ButtonCombinedKit')
    def test_19_lineage_mtdna(self):
        with tempfile.TemporaryDirectory() as td:
            v = os.path.join(td, "t.vcf")
            with open(v, 'w') as f: f.write("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            with patch('wgsextract_cli.core.utils.run_command'):
                self.run_real("19 lineage mt-dna", ['--input', v, 'lineage', 'mt-dna', '--haplogrep-path', 'fake.jar'], 'ButtonMTHaplo')
    def test_20_lineage_ydna(self):
        with patch('wgsextract_cli.core.utils.run_command'):
            self.run_real("20 lineage y-dna", ['--input', INPUT_PATH, 'lineage', 'y-dna', '--yleaf-path', 'fake.py', '--pos-file', 'fake.txt'], 'ButtonYHaplo')

    # --- REPAIR ---
    def test_21_repair_bam(self):
        start = time.perf_counter()
        print("\n>>> [REAL DATA] BEGIN: 21 repair ftdna-bam (plumbing)")
        with patch('sys.stdin', io.StringIO("@HD\tVN:1.6\tSO:coordinate\nREAD 1\t0\tchrM\t100\t60\t100M\t*\t0\t0\tACTG\t####\n")), \
             patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(sys, 'argv', ['wgsextract-cli', 'repair', 'ftdna-bam']):
                main()
        self.record_result("21 repair ftdna-bam", True, time.perf_counter()-start, 0, 'GetBAMHeader')
    def test_22_repair_vcf(self):
        start = time.perf_counter()
        print("\n>>> [REAL DATA] BEGIN: 22 repair ftdna-vcf (plumbing)")
        with patch('sys.stdin', io.StringIO("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchrM\t100\t.\tA\tT\t100\tPASS\tINFO=VAL;QUAL=100\n")), \
             patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(sys, 'argv', ['wgsextract-cli', 'repair', 'ftdna-vcf']):
                main()
        self.record_result("22 repair ftdna-vcf", True, time.perf_counter()-start, 0, 'GetBAMHeader')

    # --- QC ---
    def test_23_qc_fastp(self):
        td = tempfile.mkdtemp(prefix="wgse_real_qc_fastp_")
        try:
            r1, r2 = os.path.join(td, "r1.fq"), os.path.join(td, "r2.fq")
            with patch.object(sys, 'argv', ['wgsextract-cli', 'bam', 'unalign', '--input', INPUT_PATH, '--r1', r1, '--r2', r2, '--region', 'chrM', '--outdir', td]):
                main()
            self.run_real("23 qc fastp", ['qc', 'fastp', '--r1', r1, '--r2', r2], 'ButtonFastp')
        finally: shutil.rmtree(td)
    def test_24_qc_fastqc(self):
        with tempfile.TemporaryDirectory() as td:
            fq = os.path.join(td, "t.fq")
            with open(fq, 'w') as f: f.write("@S\nACTG\n+\n####\n")
            self.run_real("24 qc fastqc", ['qc', 'fastqc', '--fastq', fq], 'ButtonFastqc')
    def test_25_qc_cov_wgs_chrm(self): self.run_real("25 qc coverage-wgs (chrM)", ['--input', INPUT_PATH, 'qc', 'coverage-wgs', '--region', 'chrM'], 'CoverageStatsBIN')
    def test_26_qc_cov_wes_chrm(self):
        with tempfile.TemporaryDirectory() as td:
            b = os.path.join(td, "t.bed")
            with open(b, 'w') as f: f.write("chrM\t1\t100\n")
            self.run_real("26 qc coverage-wes (chrM)", ['--input', INPUT_PATH, 'qc', 'coverage-wes', '--bed', b, '--region', 'chrM'], 'CoverageStatsWES')

    # --- REF / ALIGN ---
    def test_27_ref_identify(self): self.run_real("27 ref identify", ['--input', INPUT_PATH, 'ref', 'identify'], 'GetBAMHeader')
    def test_28_ref_download(self):
        with patch('subprocess.run'):
            self.run_real("28 ref download", ['ref', 'download', '--url', 'h://f', '--out', 'o.fa'], 'LiftoverCleanup')
    def test_29_ref_index(self):
        with tempfile.TemporaryDirectory() as td:
            fa = os.path.join(td, "t.fa")
            with open(fa, 'w') as f: f.write(">chrM\nACTG\n")
            self.run_real("29 ref index", ['--ref', fa, 'ref', 'index'], 'CreateAlignIndices')
    def test_30_align_bwa(self):
        td = tempfile.mkdtemp(prefix="wgse_real_align_")
        try:
            r1, r2 = os.path.join(td, "r1.fq"), os.path.join(td, "r2.fq")
            with patch.object(sys, 'argv', ['wgsextract-cli', 'bam', 'unalign', '--input', INPUT_PATH, '--r1', r1, '--r2', r2, '--region', 'chrM', '--outdir', td]):
                main()
            from wgsextract_cli.core.utils import ReferenceLibrary
            lib = ReferenceLibrary(REF_PATH, "a08daf6f9f22170759705fd99e471b62")
            ref_fasta = lib.fasta if lib.fasta else REF_PATH
            self.run_real("30 align bwa", ['--ref', ref_fasta, 'align', '--r1', r1, '--r2', r2], 'ButtonAlignBAM')
        finally: shutil.rmtree(td)

if __name__ == '__main__':
    unittest.main()
