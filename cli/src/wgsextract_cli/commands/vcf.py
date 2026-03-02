import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist, ReferenceLibrary
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("vcf", help="Variant calling and processing using bcftools.")
    vcf_subs = parser.add_subparsers(dest="vcf_cmd", required=True)

    snp_parser = vcf_subs.add_parser("snp", help="Generates a VCF file containing single nucleotide polymorphisms.")
    snp_group = snp_parser.add_mutually_exclusive_group(required=False)
    snp_group.add_argument("--ploidy-file", help="File defining ploidy per chromosome (auto-resolved from --ref if possible)")
    snp_group.add_argument("--ploidy", help="Predefined ploidy name or value")
    snp_parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    snp_parser.set_defaults(func=cmd_snp)

    indel_parser = vcf_subs.add_parser("indel", help="Generates a normalized VCF file containing insertions and deletions.")
    indel_group = indel_parser.add_mutually_exclusive_group(required=False)
    indel_group.add_argument("--ploidy-file", help="File defining ploidy per chromosome (auto-resolved from --ref if possible)")
    indel_group.add_argument("--ploidy", help="Predefined ploidy name or value")
    indel_parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    indel_parser.set_defaults(func=cmd_indel)

    annotate_parser = vcf_subs.add_parser("annotate", help="Annotate VCF file.")
    annotate_parser.add_argument("--ann-vcf", required=True, help="Annotation VCF file")
    annotate_parser.add_argument("--cols", required=True, help="Columns to annotate (e.g. ID,INFO/HG)")
    annotate_parser.set_defaults(func=cmd_annotate)

    filter_parser = vcf_subs.add_parser("filter", help="Filter VCF file.")
    filter_parser.add_argument("--expr", required=True, help="bcftools filter expression")
    filter_parser.set_defaults(func=cmd_filter)
    
    qc_parser = vcf_subs.add_parser("qc", help="VCF QC using bcftools stats.")
    qc_parser.set_defaults(func=cmd_qc)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    
    md5_sig = calculate_bam_md5(args.input, None)
    lib = ReferenceLibrary(args.ref, md5_sig)
    
    if not hasattr(args, 'ploidy') or args.ploidy is None:
        if not hasattr(args, 'ploidy_file') or args.ploidy_file is None:
            args.ploidy_file = lib.ploidy_file

    resolved_ref = lib.fasta

    paths_to_check = {'--input': args.input}
    if resolved_ref: paths_to_check['--ref'] = resolved_ref
    
    if not verify_paths_exist(paths_to_check):
        return None

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for variant calling.")
        return None
    return threads, outdir, resolved_ref

def cmd_snp(args):
    verify_dependencies(["bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    
    threads, outdir, ref = base
    
    print_warning('ButtonSNPVCF', threads=threads)

    out_vcf = os.path.join(outdir, "snps.vcf.gz")
    
    logging.info(f"Calling SNPs to {out_vcf}")
    region_args = ["-r", args.region] if args.region else []
    
    ploidy_args = []
    if args.ploidy_file:
        if not verify_paths_exist({'--ploidy-file': args.ploidy_file}): return
        ploidy_args = ["--ploidy-file", args.ploidy_file]
    elif args.ploidy:
        ploidy_args = ["--ploidy", args.ploidy]
    else:
        logging.error("Ploidy (--ploidy or --ploidy-file) is required and could not be auto-resolved from --ref.")
        return

    p1 = subprocess.Popen(["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", ref, "-Ou"] + region_args + [args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["bcftools", "call"] + ploidy_args + ["-V", "indels", "-v", "-m", "-P", "0", "--threads", threads, "-Oz", "-o", out_vcf], stdin=p1.stdout, stderr=subprocess.PIPE)
    p1.stdout.close()
    _, stderr = p2.communicate()
    
    if p2.returncode != 0:
        logging.error(f"bcftools call failed with return code {p2.returncode}")
        if stderr:
            logging.error(stderr.decode())
        return

    subprocess.run(["tabix", "-f", "-p", "vcf", out_vcf], check=True)

def cmd_indel(args):
    verify_dependencies(["bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    
    threads, outdir, ref = base
    
    print_warning('ButtonInDelVCF', threads=threads)

    out_vcf = os.path.join(outdir, "indels.vcf.gz")
    
    logging.info(f"Calling InDels to {out_vcf}")
    region_args = ["-r", args.region] if args.region else []

    ploidy_args = []
    if args.ploidy_file:
        if not verify_paths_exist({'--ploidy-file': args.ploidy_file}): return
        ploidy_args = ["--ploidy-file", args.ploidy_file]
    elif args.ploidy:
        ploidy_args = ["--ploidy", args.ploidy]
    else:
        logging.error("Ploidy (--ploidy or --ploidy-file) is required and could not be auto-resolved from --ref.")
        return

    p1 = subprocess.Popen(["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", ref, "-Ou"] + region_args + [args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["bcftools", "call"] + ploidy_args + ["-V", "snps", "-v", "-m", "-P", "0", "--threads", threads, "-Ou"], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1.stdout.close()
    stdout, stderr = p2.communicate()

    if p2.returncode != 0:
        logging.error(f"bcftools call failed with return code {p2.returncode}")
        if stderr:
            logging.error(stderr.decode())
        return

    p3 = subprocess.Popen(["bcftools", "norm", "-f", ref, "--threads", threads, "-Oz", "-o", out_vcf], stdin=subprocess.PIPE)
    p3.communicate(input=stdout)
    
    if p3.returncode != 0:
        logging.error(f"bcftools norm failed with return code {p3.returncode}")
        return

    subprocess.run(["tabix", "-f", "-p", "vcf", out_vcf], check=True)

def cmd_annotate(args):
    verify_dependencies(["bcftools"])
    if not args.input: return logging.error("--input is required.")
    
    if not verify_paths_exist({'--input': args.input, '--ann-vcf': args.ann_vcf}): return

    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    out_vcf = os.path.join(outdir, "annotated.vcf.gz")
    
    logging.info(f"Annotating {args.input} to {out_vcf}")
    try:
        subprocess.run(["bcftools", "annotate", "-a", args.ann_vcf, "-c", args.cols, "-Oz", "-o", out_vcf, args.input], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Annotation failed: {e}")

def cmd_filter(args):
    verify_dependencies(["bcftools"])
    if not args.input: return logging.error("--input is required.")
    
    if not verify_paths_exist({'--input': args.input}): return

    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    out_vcf = os.path.join(outdir, "filtered.vcf.gz")
    
    logging.info(f"Filtering {args.input} to {out_vcf}")
    try:
        subprocess.run(["bcftools", "filter", "-i", args.expr, "-Oz", "-o", out_vcf, args.input], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Filtering failed: {e}")

def cmd_qc(args):
    verify_dependencies(["bcftools"])
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not verify_paths_exist({'--input': args.input}): return

    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    out_stats = os.path.join(outdir, "vcf_stats.txt")
    
    logging.info(f"Running bcftools stats on {args.input} to {out_stats}")
    try:
        with open(out_stats, "w") as f:
            subprocess.run(["bcftools", "stats", args.input], stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"VCF stats failed: {e}")
