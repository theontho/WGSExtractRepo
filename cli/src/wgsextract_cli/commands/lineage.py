import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, verify_paths_exist

def register(subparsers, base_parser):
    parser = subparsers.add_parser("lineage", help="Executes Yleaf or Haplogrep.")
    lin_subs = parser.add_subparsers(dest="lin_cmd", required=True)

    ydna_parser = lin_subs.add_parser("y-dna", parents=[base_parser], help="Run Yleaf on Y-BAM.")
    ydna_parser.add_argument("--yleaf-path", required=True, help="Path to yleaf.py")
    ydna_parser.add_argument("--pos-file", required=True, help="Yleaf position file")
    ydna_parser.set_defaults(func=cmd_ydna)

    mtdna_parser = lin_subs.add_parser("mt-dna", parents=[base_parser], help="Run Haplogrep on MT-VCF.")
    mtdna_parser.add_argument("--haplogrep-path", required=True, help="Path to haplogrep.jar")
    mtdna_parser.set_defaults(func=cmd_mtdna)

def cmd_ydna(args):
    verify_dependencies(["python3"])
    if not verify_paths_exist({'--input': args.input, '--yleaf-path': args.yleaf_path, '--pos-file': args.pos_file}):
        return

    logging.info(f"Running Yleaf lineage analysis on {args.input}")
    try:
        run_command(["python3", args.yleaf_path, "-input", args.input, "-pos", args.pos_file, "-out", args.outdir])
    except Exception as e:
        logging.error(f"Yleaf failed: {e}")

def cmd_mtdna(args):
    verify_dependencies(["java"])
    if not verify_paths_exist({'--input': args.input, '--haplogrep-path': args.haplogrep_path}):
        return

    out_file = os.path.join(args.outdir, "haplogrep_results.txt")
    logging.info(f"Running Haplogrep lineage analysis on {args.input}")
    try:
        run_command(["java", "-jar", args.haplogrep_path, "classify", "--format", "vcf", "--in", args.input, "--out", out_file])
    except Exception as e:
        logging.error(f"Haplogrep failed: {e}")
