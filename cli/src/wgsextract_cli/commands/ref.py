import os
import subprocess
import logging
import sys
import hashlib
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import calculate_bam_md5, resolve_reference, verify_paths_exist
from wgsextract_cli.core.ref_library import download_and_process_genome, get_available_genomes, load_genomes_from_csv, GENOME_DATA

def register(subparsers, base_parser):
    parser = subparsers.add_parser("ref", help="Reference Data Management commands.")
    ref_subs = parser.add_subparsers(dest="ref_cmd", required=True)

    ident_parser = ref_subs.add_parser("identify", parents=[base_parser], help="Runs MD5 check on BAM header to identify reference genome.")
    ident_parser.set_defaults(func=cmd_identify)

    dl_parser = ref_subs.add_parser("download", parents=[base_parser], help="Fetches FASTA from NIH/EBI.")
    dl_parser.add_argument("--url", required=True, help="URL to download from")
    dl_parser.add_argument("--out", required=True, help="Output FASTA file path")
    dl_parser.set_defaults(func=cmd_download)

    index_parser = ref_subs.add_parser("index", parents=[base_parser], help="Runs faidx and dict on reference FASTA.")
    index_parser.set_defaults(func=cmd_index)

    cntns_parser = ref_subs.add_parser("count-ns", parents=[base_parser], help="Analyzes reference FASTA to count N segments (using countingNs.py).")
    cntns_parser.set_defaults(func=cmd_count_ns)

    verify_parser = ref_subs.add_parser("verify", parents=[base_parser], help="Verify integrity of reference FASTA file.")
    verify_parser.set_defaults(func=cmd_ref_verify)

    lib_parser = ref_subs.add_parser("library", parents=[base_parser], help="Interactive reference library manager to download genomes.")
    lib_parser.set_defaults(func=cmd_library)

    dlgenes_parser = ref_subs.add_parser("download-genes", parents=[base_parser], help="Downloads lightweight gene mapping files (hg19/hg38).")
    dlgenes_parser.set_defaults(func=cmd_download_genes)

def cmd_identify(args):
    verify_dependencies(["samtools"])
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not verify_paths_exist({'--input': args.input}): return

    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")
        
    md5_sig = calculate_bam_md5(args.input, resolved_ref)
    logging.info(f"MD5 Signature for {args.input}: {md5_sig}")

def cmd_download(args):
    verify_dependencies(["wget"])
    logging.info(f"Downloading {args.url} to {args.out}")
    try:
        subprocess.run(["wget", "-O", args.out, args.url], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Download failed: {e}")

def cmd_index(args):
    verify_dependencies(["samtools"])
    if not args.ref:
        logging.error("--ref is required.")
        return
    
    if not verify_paths_exist({'--ref': args.ref}): return
        
    logging.info(f"Indexing {args.ref} with faidx")
    try:
        subprocess.run(["samtools", "faidx", args.ref], check=True)
        out_dict = os.path.splitext(args.ref)[0] + ".dict"
        logging.info(f"Creating dict {out_dict}")
        subprocess.run(["samtools", "dict", args.ref, "-o", out_dict], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Indexing failed: {e}")

def cmd_count_ns(args):
    verify_dependencies(["python3"])
    if not args.ref:
        logging.error("--ref is required.")
        return
    
    if not verify_paths_exist({'--ref': args.ref}): return
        
    prog_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../program"))
    script = os.path.join(prog_dir, "countingNs.py")
    if not os.path.exists(script):
        logging.error("countingNs.py script not found.")
        return

    logging.info(f"Analyzing N segments in {args.ref}")
    try:
        subprocess.run([sys.executable, script, args.ref], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"N-counting failed: {e}")

def cmd_ref_verify(args):
    verify_dependencies(["gzip", "samtools"])
    if not args.ref:
        logging.error("--ref is required.")
        return
    
    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")
    if not os.path.exists(resolved_ref):
        logging.error(f"Reference file not found: {resolved_ref}")
        return

    logging.info(f"Verifying integrity of {resolved_ref}...")
    
    # 1. MD5 Checksum (if known)
    filename = os.path.basename(resolved_ref)
    expected_md5 = None
    for g in GENOME_DATA:
        if g['final'] == filename:
            expected_md5 = g.get('md5')
            break
    
    if expected_md5:
        logging.info(f"Verifying MD5 checksum for {filename}...")
        hash_md5 = hashlib.md5()
        try:
            with open(resolved_ref, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            calculated = hash_md5.hexdigest()
            if calculated == expected_md5:
                logging.info("MD5 checksum: OK")
            else:
                logging.error(f"MD5 checksum FAILED!")
                logging.error(f"Expected: {expected_md5}")
                logging.error(f"Calculated: {calculated}")
                # We continue to show other potential errors (like gzip eof)
        except Exception as e:
            logging.error(f"MD5 verification failed to run: {e}")

    # 2. Check gzip integrity
    if resolved_ref.endswith(".gz"):
        logging.info("Running gzip integrity test...")
        try:
            subprocess.run(["gzip", "-t", resolved_ref], check=True, stderr=subprocess.PIPE)
            logging.info("Gzip integrity: OK")
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode() if e.stderr else "Unexpected end of file"
            logging.error(f"Gzip integrity FAILED: {msg}")
            return
        except Exception as e:
            logging.error(f"Gzip test failed: {e}")
            return

    # 2. Check samtools faidx
    logging.info("Running samtools faidx check...")
    try:
        # Check if index exists, if not try to create/verify
        res = subprocess.run(["samtools", "faidx", resolved_ref], capture_output=True, text=True)
        if res.returncode == 0:
            logging.info("Samtools faidx: OK")
        else:
            logging.error(f"Samtools faidx FAILED: {res.stderr}")
            return
    except Exception as e:
        logging.error(f"Samtools faidx check failed: {e}")
        return

    logging.info(f"Reference {os.path.basename(resolved_ref)} appears to be valid.")

def cmd_library(args):
    """Interactive library manager."""
    verify_dependencies(["curl", "samtools", "bcftools", "tabix", "bgzip", "htsfile"])
    
    # Try to find seed_genomes.csv
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    csv_path = os.path.join(prog_root, "base_reference", "seed_genomes.csv")
    
    genomes = load_genomes_from_csv(csv_path)
    if not genomes:
        # Fallback to hardcoded list if CSV missing
        genomes = get_available_genomes()

    # Determine reference library directory
    reflib_dir = args.ref if args.ref else os.path.join(prog_root, "reference")
    reflib_dir = os.path.abspath(reflib_dir)

    print("\n" + "="*80)
    print("WGS Extract Reference Library Manager")
    print(f"Library Path: {reflib_dir}")
    print("="*80)
    print("Select an option:")
    print(" 0) Exit")
    print(" G) Download Gene Mapping Database (hg19/hg38)")
    
    # Check for installed genomes
    for i, g in enumerate(genomes, 1):
        status = ""
        # Check both 'genomes' and 'genome' subfolders
        for sub in ["genomes", "genome"]:
            if os.path.exists(os.path.join(reflib_dir, sub, g['final'])):
                status = " [Installed]"
                break
        print(f" {i:2}) {g['label']}{status}")
    print("="*80)

    try:
        choice = input("\nEnter choice (number or G): ").strip().upper()
        if not choice or choice == "0":
            print("Exiting library manager.")
            return

        if choice == "G":
            from wgsextract_cli.core.gene_map import download_gene_maps
            download_gene_maps(reflib_dir)
            return

        idx = int(choice) - 1
        if 0 <= idx < len(genomes):
            if not os.path.exists(reflib_dir):
                os.makedirs(reflib_dir, exist_ok=True)
            
            download_and_process_genome(idx, reflib_dir, genomes_list=genomes)
        else:
            print("Invalid choice.")
    except (ValueError, EOFError, KeyboardInterrupt):
        print("\nExiting library manager.")

def cmd_download_genes(args):
    from wgsextract_cli.core.gene_map import download_gene_maps
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = args.ref if args.ref else os.path.join(prog_root, "reference")
    if download_gene_maps(reflib):
        print(f"Gene maps installed to {reflib}/ref")
    else:
        print("Failed to download gene maps.")
