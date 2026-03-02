import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist
from wgsextract_cli.core.warnings import print_warning, check_free_space

def register(subparsers):
    parser = subparsers.add_parser("align", help="Aligns FASTQs to reference, fixmates, sorts, and marks duplicates.")
    parser.add_argument("--r1", required=True, help="Read 1 FASTQ file")
    parser.add_argument("--r2", help="Read 2 FASTQ file")
    parser.add_argument("--long-read", action="store_true", help="Use minimap2 for long reads instead of BWA")
    parser.set_defaults(func=run)

def get_base_args(args):
    threads, memory = get_resource_defaults(args.threads, args.memory)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.r1))
    
    # Usually for align we just use the ref path as is if it's a file
    resolved_ref = resolve_reference(args.ref, "") 

    paths_to_check = {'--r1': args.r1}
    if args.r2: paths_to_check['--r2'] = args.r2
    if resolved_ref: paths_to_check['--ref'] = resolved_ref

    if not verify_paths_exist(paths_to_check):
        return None

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

    # Warnings and space checks
    fastq_size = os.path.getsize(args.r1)
    if args.r2:
        fastq_size += os.path.getsize(args.r2)
        
    print_warning('infoFreeSpace', app_name='Alignment', file_size=fastq_size, is_cram=False)
    print_warning('ButtonAlignBAM', threads=threads)
    
    # Calculate needed space to perform check_free_space
    from wgsextract_cli.core.warnings import get_free_space_needed
    temp_needed, final_needed = get_free_space_needed(fastq_size, "Coord", False)
    check_free_space(outdir, temp_needed + final_needed)

    out_bam = os.path.join(outdir, "aligned.bam")
    
    if args.long_read:
        logging.info(f"Aligning with minimap2 to {out_bam}")
        p1 = subprocess.Popen(["minimap2", "-ax", "map-ont", "-t", threads, ref, args.r1], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["samtools", "sort", "-m", memory, "-@", threads, "-o", out_bam], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()
    else:
        logging.info(f"Aligning with bwa mem to {out_bam}")
        r2_args = [args.r2] if args.r2 else []
        p1 = subprocess.Popen(["bwa", "mem", "-t", threads, ref, args.r1] + r2_args, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["samtools", "sort", "-m", memory, "-@", threads, "-o", out_bam], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

    logging.info("Indexing...")
    subprocess.run(["samtools", "index", out_bam], check=True)
