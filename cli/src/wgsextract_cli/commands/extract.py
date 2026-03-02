import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, get_chr_name, get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist, get_ref_mito
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("extract", help="Extract specific chromosomes or unmapped reads.")
    ext_subs = parser.add_subparsers(dest="ext_cmd", required=True)

    mito_parser = ext_subs.add_parser("mito", help="Extracts MT reads, generates VCF, and creates a consensus FASTA.")
    mito_parser.set_defaults(func=cmd_mito)

    ydna_parser = ext_subs.add_parser("ydna", help="Extracts Y reads and annotates variants with ISOGG/HG names.")
    ydna_parser.add_argument("--ref-vcf", help="Reference VCF for annotation")
    ydna_parser.add_argument("--ann-col", help="Annotation columns (e.g. CHROM,POS,ID,INFO/HG)")
    ydna_parser.set_defaults(func=cmd_ydna)

    unmapped_parser = ext_subs.add_parser("unmapped", help="Extracts non-aligning reads for microbiome analysis.")
    unmapped_parser.add_argument("--r1", required=True, help="Output Read 1 FASTQ")
    unmapped_parser.add_argument("--r2", required=True, help="Output Read 2 FASTQ")
    unmapped_parser.set_defaults(func=cmd_unmapped)

    wes_parser = ext_subs.add_parser("wes", help="Extracts Whole Exome Sequencing reads using a BED file.")
    wes_parser.add_argument("--bed", help="BED file defining target regions (auto-resolved from --ref if possible)")
    wes_parser.set_defaults(func=cmd_wes)

    ymt_parser = ext_subs.add_parser("ymt", help="Extracts both Y and MT reads to a single BAM.")
    ymt_parser.set_defaults(func=cmd_ymt)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    threads, memory = get_resource_defaults(args.threads, args.memory)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    
    md5_sig = calculate_bam_md5(args.input, None)
    resolved_ref = resolve_reference(args.ref, md5_sig)
    
    # Assert requirements exist
    paths_to_check = {'--input': args.input}
    if resolved_ref:
        paths_to_check['--ref'] = resolved_ref
    
    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, memory, outdir, cram_opt, resolved_ref

def cmd_mito(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for mito extraction.")
        return

    if get_ref_mito(args.input, cram_opt) == "Yoruba":
        print_warning('YorubaWarning')

    chr_m = get_chr_name(args.input, "MT", cram_opt)
    out_bam = os.path.join(outdir, "mito_extracted.bam")
    out_vcf = os.path.join(outdir, "mito_variants.vcf.gz")
    out_fasta = os.path.join(outdir, "mito_consensus.fasta")

    logging.info(f"Extracting {chr_m} to {out_bam}")
    run_command(["samtools", "view", "-bh"] + cram_opt + [args.input, chr_m, "-o", out_bam])
    
    logging.info("Calling variants...")
    p1 = subprocess.Popen(["bcftools", "mpileup", "-r", chr_m, "-f", resolved_ref, args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["bcftools", "call", "--ploidy", "1", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    logging.info(f"Indexing {out_vcf}...")
    run_command(["tabix", "-f", "-p", "vcf", out_vcf])

    logging.info("Generating consensus FASTA...")
    p3 = subprocess.Popen(["samtools", "faidx", resolved_ref, chr_m], stdout=subprocess.PIPE)
    p4 = subprocess.Popen(["bcftools", "consensus", out_vcf, "-o", out_fasta], stdin=p3.stdout)
    p3.stdout.close()
    p4.communicate()

def cmd_ydna(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for ydna extraction.")
        return

    # Assert annotation requirements upfront if user provided either
    if (args.ref_vcf or args.ann_col) and not (args.ref_vcf and args.ann_col):
        logging.error("Both --ref-vcf and --ann-col are required for Y-DNA annotation.")
        return
    
    if args.ref_vcf and not verify_paths_exist({'--ref-vcf': args.ref_vcf}):
        return

    chr_y = get_chr_name(args.input, "Y", cram_opt)
    out_bam = os.path.join(outdir, "ydna_extracted.bam")
    out_vcf = os.path.join(outdir, "ydna_annotated.vcf.gz")

    logging.info(f"Extracting {chr_y} to {out_bam}")
    run_command(["samtools", "view", "-bh"] + cram_opt + [args.input, chr_y, "-o", out_bam])
    
    if args.ref_vcf and args.ann_col:
        logging.info("Calling and annotating variants...")
        p1 = subprocess.Popen(["bcftools", "mpileup", "-T", args.ref_vcf, "-f", resolved_ref, out_bam], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["bcftools", "call", "--ploidy", "1", "-m"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        p3 = subprocess.Popen(["bcftools", "annotate", "-a", args.ref_vcf, "-c", args.ann_col, "-Oz", "-o", out_vcf], stdin=p2.stdout)
        p2.stdout.close()
        p3.communicate()
        
        logging.info(f"Indexing {out_vcf}...")
        run_command(["tabix", "-f", "-p", "vcf", out_vcf])
    else:
        logging.info("Skipping annotation, missing --ref-vcf and --ann-col")

def cmd_unmapped(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base

    logging.info(f"Extracting unmapped reads to {args.r1} and {args.r2}")
    p1 = subprocess.Popen(["samtools", "view", "-bh"] + cram_opt + [args.input, "*"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["samtools", "sort", "-n"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    p3 = subprocess.Popen(["samtools", "fastq", "-1", args.r1, "-2", args.r2, "-"], stdin=p2.stdout)
    p2.stdout.close()
    p3.communicate()

def cmd_wes(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    # Use ReferenceLibrary to resolve BED if not provided
    md5_sig = calculate_bam_md5(args.input, None)
    lib = ReferenceLibrary(args.ref, md5_sig)
    
    bed = args.bed if args.bed else lib.wes_bed
    
    if not bed or not os.path.exists(bed):
        logging.error("BED file is required for WES extraction and could not be auto-resolved.")
        return

    print_warning('ExtractWES', threads=threads)
    
    out_bam = os.path.join(outdir, "wes_extracted.bam")
    logging.info(f"Extracting WES regions from {bed} to {out_bam}")
    try:
        run_command(["samtools", "view", "-bh", "-L", bed] + cram_opt + ["-@", threads, "-o", out_bam, args.input])
        logging.info("Indexing...")
        run_command(["samtools", "index", out_bam])
    except Exception as e:
        logging.error(f"WES extraction failed: {e}")

def cmd_ymt(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, memory, outdir, cram_opt, resolved_ref = base
    
    chr_y = get_chr_name(args.input, "Y", cram_opt)
    chr_m = get_chr_name(args.input, "MT", cram_opt)
    
    out_bam = os.path.join(outdir, "ymt_extracted.bam")
    logging.info(f"Extracting {chr_y} and {chr_m} to {out_bam}")
    try:
        run_command(["samtools", "view", "-bh"] + cram_opt + ["-@", threads, "-o", out_bam, args.input, chr_y, chr_m])
        logging.info("Indexing...")
        run_command(["samtools", "index", out_bam])
    except Exception as e:
        logging.error(f"Y+MT extraction failed: {e}")
