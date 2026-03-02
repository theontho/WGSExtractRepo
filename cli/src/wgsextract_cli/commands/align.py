import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("align", help="Align FASTQ reads to a reference model.")
    parser.add_argument("--r1", required=True, help="Read 1 FASTQ file")
    parser.add_argument("--r2", help="Read 2 FASTQ file (optional)")
    parser.add_argument("--long-read", action="store_true", help="Use minimap2 for long-read alignment")
    parser.set_defaults(func=run)

def get_base_args(args):
    threads, memory = get_resource_defaults(args.threads, args.memory)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.r1))
    
    # Path validation for inputs
    paths_to_check = {'--r1': args.r1}
    if args.r2: paths_to_check['--r2'] = args.r2
    if not verify_paths_exist(paths_to_check): return None

    # Reference resolution
    # Alignment usually needs a direct fasta
    resolved_ref = resolve_reference(args.ref, "")
    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for alignment.")
        return None
        
    return threads, memory, outdir, resolved_ref

def run(args):
    if args.long_read:
        verify_dependencies(["minimap2", "samtools"])
    else:
        verify_dependencies(["bwa", "samtools"])
        
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, ref = base
    
    print_warning('RealignBAMTimeWarnMesg', threads=threads)
    print_warning('ButtonAlignBAM', threads=threads)

    out_bam = os.path.join(outdir, "aligned.bam")
    
    if args.long_read:
        logging.info(f"Aligning with minimap2 to {out_bam}")
        p1 = subprocess.Popen(["minimap2", "-ax", "map-ont", "-t", str(threads), ref, args.r1], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["samtools", "sort", "-m", memory, "-@", str(threads), "-o", out_bam], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()
    else:
        logging.info(f"Aligning with bwa mem to {out_bam}")
        cmd = ["bwa", "mem", "-t", str(threads), ref, args.r1]
        if args.r2:
            cmd.append(args.r2)
            
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["samtools", "sort", "-m", memory, "-@", str(threads), "-o", out_bam], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

    logging.info("Indexing...")
    try:
        subprocess.run(["samtools", "index", out_bam], check=True)
    except Exception as e:
        logging.error(f"Indexing failed: {e}")
