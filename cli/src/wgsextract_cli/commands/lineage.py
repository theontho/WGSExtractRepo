import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, verify_paths_exist

def register(subparsers):
    parser = subparsers.add_parser("lineage", help="Executes Yleaf or Haplogrep.")
    lin_subs = parser.add_subparsers(dest="lin_cmd", required=True)

    ydna_parser = lin_subs.add_parser("y-dna", help="Run Yleaf on Y-BAM.")
    ydna_parser.add_argument("--yleaf-path", required=True, help="Path to yleaf.py")
    ydna_parser.add_argument("--pos-file", required=True, help="Yleaf position file")
    ydna_parser.set_defaults(func=cmd_ydna)

    mtdna_parser = lin_subs.add_parser("mt-dna", help="Run Haplogrep on MT-VCF.")
    mtdna_parser.add_argument("--haplogrep-path", required=True, help="Path to haplogrep.jar")
    mtdna_parser.set_defaults(func=cmd_mtdna)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    if not verify_paths_exist({'--input': args.input}): return None
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    return outdir

def cmd_ydna(args):
    verify_dependencies(["python3"])
    outdir = get_base_args(args)
    if not outdir: return
    
    if not verify_paths_exist({'--yleaf-path': args.yleaf_path, '--pos-file': args.pos_file}): return

    logging.info(f"Running Yleaf on {args.input} to {outdir}")
    run_command(["python3", args.yleaf_path, "-bam", args.input, "-pos", args.pos_file, "-out", outdir, "-r", "1", "-q", "20"])

def cmd_mtdna(args):
    verify_dependencies(["java"])
    outdir = get_base_args(args)
    if not outdir: return
    
    if not verify_paths_exist({'--haplogrep-path': args.haplogrep_path}): return

    out_txt = os.path.join(outdir, "haplogrep_report.txt")
    
    logging.info(f"Running Haplogrep on {args.input} to {out_txt}")
    run_command(["java", "-jar", args.haplogrep_path, "classify", "--in", args.input, "--format", "vcf", "--out", out_txt])
