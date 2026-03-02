import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import calculate_bam_md5, resolve_reference, verify_paths_exist

def register(subparsers):
    parser = subparsers.add_parser("ref", help="Reference Data Management commands.")
    ref_subs = parser.add_subparsers(dest="ref_cmd", required=True)

    ident_parser = ref_subs.add_parser("identify", help="Runs MD5 check on BAM header to identify reference genome.")
    ident_parser.set_defaults(func=cmd_identify)

    dl_parser = ref_subs.add_parser("download", help="Fetches FASTA from NIH/EBI.")
    dl_parser.add_argument("--url", required=True, help="URL to download from")
    dl_parser.add_argument("--out", required=True, help="Output FASTA file path")
    dl_parser.set_defaults(func=cmd_download)

    index_parser = ref_subs.add_parser("index", help="Runs faidx and dict on reference FASTA.")
    index_parser.set_defaults(func=cmd_index)

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
