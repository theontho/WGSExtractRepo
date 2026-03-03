import os
import subprocess
import tempfile
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, get_resource_defaults, verify_paths_exist, calculate_bam_md5, resolve_reference, get_chr_name
from wgsextract_cli.core.warnings import print_warning, check_free_space

def register(subparsers):
    parser = subparsers.add_parser("bam", help="BAM/CRAM management commands.")
    bam_subs = parser.add_subparsers(dest="bam_cmd", required=True)

    sort_parser = bam_subs.add_parser("sort", help="Sort a BAM or CRAM file by coordinate.")
    sort_parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    sort_parser.set_defaults(func=cmd_sort)

    index_parser = bam_subs.add_parser("index", help="Creates a BAM or CRAM index file.")
    index_parser.set_defaults(func=cmd_index)

    unindex_parser = bam_subs.add_parser("unindex", help="Deletes the .bai or .crai file associated with the BAM/CRAM.")
    unindex_parser.set_defaults(func=cmd_unindex)

    unsort_parser = bam_subs.add_parser("unsort", help="Changes the coordinate-sorted status in the BAM header to 'unsorted'.")
    unsort_parser.set_defaults(func=cmd_unsort)

    tocram_parser = bam_subs.add_parser("to-cram", help="Convert BAM to CRAM.")
    tocram_parser.add_argument("-r", "--region", help="Chromosomal region")
    tocram_parser.set_defaults(func=cmd_tocram)

    tobam_parser = bam_subs.add_parser("to-bam", help="Convert CRAM to BAM.")
    tobam_parser.add_argument("-r", "--region", help="Chromosomal region")
    tobam_parser.set_defaults(func=cmd_tobam)

    unalign_parser = bam_subs.add_parser("unalign", help="Converts aligned reads back to raw paired-end or single-end FASTQ files.")
    unalign_parser.add_argument("--r1", required=True, help="Output Read 1 FASTQ")
    unalign_parser.add_argument("--r2", required=True, help="Output Read 2 FASTQ")
    unalign_parser.add_argument("--se", help="Output Single-End FASTQ")
    unalign_parser.add_argument("-r", "--region", help="Chromosomal region")
    unalign_parser.set_defaults(func=cmd_unalign)

    subset_parser = bam_subs.add_parser("subset", help="Creates a random subset of a BAM file.")
    subset_parser.add_argument("--fraction", "-f", required=True, type=float, help="Decimal percentage (e.g. 0.1 for 10%%)")
    subset_parser.add_argument("-r", "--region", help="Chromosomal region")
    subset_parser.set_defaults(func=cmd_subset)

    mtextract_parser = bam_subs.add_parser("mt-extract", help="Extract mitochondrial (mtDNA) reads to a separate BAM.")
    mtextract_parser.set_defaults(func=cmd_mtextract)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    
    if not verify_paths_exist({'--input': args.input}):
        return None

    threads, memory = get_resource_defaults(args.threads, args.memory)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    
    try:
        md5_sig = calculate_bam_md5(args.input, None)
        resolved_ref = resolve_reference(args.ref, md5_sig)
    except Exception as e:
        logging.error(f"Failed to initialize reference resolution: {e}")
        return None

    paths_to_check = {}
    if resolved_ref:
        paths_to_check['--ref'] = resolved_ref
        
    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, memory, outdir, cram_opt, resolved_ref

def cmd_sort(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    file_size = os.path.getsize(args.input)
    is_cram = args.input.lower().endswith(".cram")
    print_warning('infoFreeSpace', app_name='Coord Sort', file_size=file_size, is_cram=is_cram)
    print_warning('GenSortedBAM', threads=threads)
    
    # Calculate needed space to perform check_free_space
    from wgsextract_cli.core.warnings import get_free_space_needed
    temp_needed, final_needed = get_free_space_needed(file_size, "Coord", is_cram)
    check_free_space(outdir, temp_needed + final_needed)

    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".bam", "").replace(".cram", "") + "_sorted.bam")
    with tempfile.TemporaryDirectory() as tempdir:
        region_args = [args.region] if args.region else []
        view_cmd = ["samtools", "view", "-uh", "--no-PG"] + cram_opt + [args.input] + region_args
        sort_cmd = ["samtools", "sort", "-T", tempdir, "-m", memory, "-@", threads, "-o", out_file]
        
        logging.info(f"Sorting {args.input} to {out_file}")
        try:
            p1 = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(sort_cmd, stdin=p1.stdout)
            p1.stdout.close()
            p2.communicate()
            if p2.returncode != 0:
                logging.error("Sort failed.")
        except Exception as e:
            logging.error(f"Execution failed: {e}")

def cmd_index(args):
    verify_dependencies(["samtools"])
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not verify_paths_exist({'--input': args.input}): return
    
    print_warning('GenBAMIndex')

    logging.info(f"Indexing {args.input}")
    try:
        run_command(["samtools", "index", args.input])
    except Exception as e:
        logging.error(f"Indexing failed: {e}")

def cmd_unindex(args):
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not os.path.exists(args.input) or os.path.isdir(args.input):
        logging.error(f"Input is not a valid file: {args.input}")
        return

    bai = args.input + ".bai"
    crai = args.input + ".crai"
    if os.path.exists(bai):
        os.remove(bai)
        logging.info(f"Removed {bai}")
    if os.path.exists(crai):
        os.remove(crai)
        logging.info(f"Removed {crai}")

def cmd_unsort(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".bam", "").replace(".cram", "") + "_unsorted.bam")
    with tempfile.TemporaryDirectory() as tempdir:
        newhead = os.path.join(tempdir, "newhead.sam")
        
        view_cmd = ["samtools", "view", "-H"] + cram_opt + [args.input]
        try:
            res = subprocess.run(view_cmd, capture_output=True, text=True, check=True)
            header = res.stdout
            header = header.replace("SO:coordinate", "SO:unsorted")
            
            with open(newhead, "w") as f:
                f.write(header)
                
            logging.info(f"Unsorting to {out_file}")
            run_command(["samtools", "reheader", newhead, args.input], stdout=open(out_file, "w"))
        except (subprocess.CalledProcessError, Exception) as e:
            logging.error(f"Failed to unsort {args.input}: {e}")

def cmd_tocram(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    print_warning('BAMtoCRAM', threads=threads)

    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".bam", "") + ".cram")
    logging.info(f"Converting to {out_file}")
    try:
        region_args = [args.region] if args.region else []
        run_command(["samtools", "view", "-Ch"] + cram_opt + ["-@", threads, "-o", out_file, args.input] + region_args)
        run_command(["samtools", "index", out_file])
    except Exception as e:
        logging.error(f"Conversion to CRAM failed: {e}")

def cmd_tobam(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    print_warning('CRAMtoBAM', threads=threads)

    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".cram", "") + ".bam")
    logging.info(f"Converting to {out_file}")
    try:
        region_args = [args.region] if args.region else []
        run_command(["samtools", "view", "-bh"] + cram_opt + ["-@", threads, "-o", out_file, args.input] + region_args)
        run_command(["samtools", "index", out_file])
    except Exception as e:
        logging.error(f"Conversion to BAM failed: {e}")

def cmd_unalign(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    file_size = os.path.getsize(args.input)
    is_cram = args.input.lower().endswith(".cram")
    print_warning('infoFreeSpace', app_name='Name Sort', file_size=file_size, is_cram=is_cram)
    print_warning('ButtonUnalignBAM', threads=threads)
    
    # Calculate needed space to perform check_free_space
    from wgsextract_cli.core.warnings import get_free_space_needed
    temp_needed, final_needed = get_free_space_needed(file_size, "Name", is_cram)
    check_free_space(outdir, temp_needed + final_needed)

    se_arg = ["-0", args.se] if args.se else ["-0", "/dev/null"]
    
    with tempfile.TemporaryDirectory() as tempdir:
        region_args = [args.region] if args.region else []
        view_cmd = ["samtools", "view", "-uh", "--no-PG"] + cram_opt + [args.input] + region_args
        sort_cmd = ["samtools", "sort", "-n", "-T", tempdir, "-m", memory, "-@", threads, "-O", "sam"]
        fastq_cmd = ["samtools", "fastq", "-1", args.r1, "-2", args.r2] + se_arg + ["-s", "/dev/null", "-n", "-@", threads, "-"]
        
        logging.info("Unaligning reads to FASTQ...")
        try:
            p1 = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(sort_cmd, stdin=p1.stdout, stdout=subprocess.PIPE)
            p1.stdout.close()
            p3 = subprocess.Popen(fastq_cmd, stdin=p2.stdout)
            p2.stdout.close()
            p3.communicate()
        except Exception as e:
            logging.error(f"Unalign failed: {e}")

def cmd_subset(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".bam", "").replace(".cram", "") + "_subset.bam")
    logging.info(f"Subsetting {args.fraction} of reads to {out_file}")
    try:
        region_args = [args.region] if args.region else []
        run_command(["samtools", "view", "-bh", "-s", str(args.fraction)] + cram_opt + ["-o", out_file, args.input] + region_args)
    except Exception as e:
        logging.error(f"Subsetting failed: {e}")

def cmd_mtextract(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    mt_chr = get_chr_name(args.input, "MT", cram_opt)
    
    out_file = os.path.join(outdir, os.path.basename(args.input).replace(".bam", "").replace(".cram", "") + "_mtDNA.bam")
    
    logging.info(f"Extracting mtDNA reads ({mt_chr}) to {out_file}")
    try:
        run_command(["samtools", "view", "-bh"] + cram_opt + ["-@", threads, "-o", out_file, args.input, mt_chr])
        run_command(["samtools", "index", out_file])
    except Exception as e:
        logging.error(f"mtDNA extraction failed: {e}")
