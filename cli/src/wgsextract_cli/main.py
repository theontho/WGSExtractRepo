#!/usr/bin/env python3

import argparse
import sys
import logging
import os
from dotenv import load_dotenv

from .commands import (
    info,
    bam,
    extract,
    microarray,
    lineage,
    vcf,
    repair,
    qc,
    ref,
    align,
    vep
)

def main():
    # Load environment variables from the cli project directory base
    # Find the 'cli' directory (two levels up from this file in src/wgsextract_cli/)
    if os.environ.get("WGSE_SKIP_DOTENV") != "1":
        cli_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        
        env_local = os.path.join(cli_root, ".env.local")
        env_std = os.path.join(cli_root, ".env")
        
        if os.path.exists(env_local):
            load_dotenv(dotenv_path=env_local)
        if os.path.exists(env_std):
            load_dotenv(dotenv_path=env_std)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    parser = argparse.ArgumentParser(
        description="WGS Extract Command-Line Interface (CLI)"
    )
    
    # Global arguments with environment variable fallbacks
    parser.add_argument("--input", "-i", 
                        default=os.environ.get("WGSE_INPUT"),
                        help="Path to the input BAM/CRAM or FASTQ file. (Env: WGSE_INPUT)")
    parser.add_argument("--outdir", "-o", 
                        default=os.environ.get("WGSE_OUTDIR"),
                        help="Destination directory for outputs. (Env: WGSE_OUTDIR)")
    parser.add_argument("--ref", "-r", 
                        default=os.environ.get("WGSE_REF"),
                        help="Path to the reference genome FASTA. (Env: WGSE_REF)")
    parser.add_argument("--threads", "-t", type=int, 
                        default=os.environ.get("WGSE_THREADS"),
                        help="CPU threads to use. (Env: WGSE_THREADS)")
    parser.add_argument("--memory", "-m", 
                        default=os.environ.get("WGSE_MEMORY"),
                        help="Memory limit per thread (e.g., '2G'). (Env: WGSE_MEMORY)")
    
    subparsers = parser.add_subparsers(dest="command", required=True, title="subcommands")
    
    # Register subcommands
    info.register(subparsers)
    bam.register(subparsers)
    extract.register(subparsers)
    microarray.register(subparsers)
    lineage.register(subparsers)
    vcf.register(subparsers)
    repair.register(subparsers)
    qc.register(subparsers)
    ref.register(subparsers)
    align.register(subparsers)
    vep.register(subparsers)
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
    
    # Call the appropriate handler
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
