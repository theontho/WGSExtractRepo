import os
import sys
import subprocess
import logging
import tempfile
import argparse
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist, ReferenceLibrary
from wgsextract_cli.core.warnings import print_warning
from wgsextract_cli.core.microarray_utils import liftover_hg38_to_hg19, convert_to_vendor_format

def register(subparsers):
    format_help = """Comma-separated list of formats to generate (default: all).
Available formats:
  Everything:
    all (Combined file of ALL SNPs for GEDMATCH)
  23andMe:
    23andme_v3, 23andme_v4, 23andme_v5, 23andme_v3+v5, 23andme_api
  AncestryDNA:
    ancestry_v1, ancestry_v2
  Family Tree DNA:
    ftdna_v2, ftdna_v3
  Living DNA:
    ldna_v1, ldna_v2
  MyHeritage:
    myheritage_v1, myheritage_v2
  Other Vendors:
    mthfr_uk (MTHFR Genetics UK), genera_br (Genera BR), meudna_br (meuDNA BR)
  Reich Lab:
    reich_aadr (AADR 1240K), reich_human_origins (Human Origins v1), reich_combined
"""
    parser = subparsers.add_parser("microarray", 
                                   help="Generates microarray simulation CombinedKit.",
                                   formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--formats", default="all", help=format_help)
    parser.add_argument("--parallel", action="store_true", help="Enable per-chromosome parallel variant calling")
    parser.add_argument("--ref-vcf-tab", help="Master tabulated list of all consumer microarray SNPs (auto-resolved from --ref if possible)")
    parser.add_argument("--ploidy-file", help="File defining ploidy per chromosome (auto-resolved from --ref if possible)")
    parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    parser.set_defaults(func=run)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    
    md5_sig = calculate_bam_md5(args.input, None)
    lib = ReferenceLibrary(args.ref, md5_sig)
    
    if not args.ref_vcf_tab: args.ref_vcf_tab = lib.ref_vcf_tab
    if not args.ploidy_file: args.ploidy_file = lib.ploidy_file
    
    resolved_ref = lib.fasta

    paths_to_check = {'--input': args.input}
    if resolved_ref: paths_to_check['--ref'] = resolved_ref
    
    if not verify_paths_exist(paths_to_check): return None

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error("--ref is required (and must be a file) for microarray.")
        return None
    return threads, outdir, resolved_ref, lib

def run(args):
    verify_dependencies(["bcftools", "tabix", "sed", "sort", "cat", "zip"])
    base = get_base_args(args)
    if not base: return
    threads, outdir, ref, lib = base
    
    if not args.ref_vcf_tab:
        logging.error("--ref-vcf-tab is required and could not be auto-resolved from --ref.")
        return
    if not args.ploidy_file:
        logging.error("--ploidy-file is required and could not be auto-resolved from --ref.")
        return

    if not verify_paths_exist({
        '--ref-vcf-tab': args.ref_vcf_tab,
        '--ploidy-file': args.ploidy_file
    }): return

    print_warning('ButtonCombinedKit', threads=threads)

    out_vcf = os.path.join(outdir, "CombinedKit.vcf.gz")
    out_txt = os.path.join(outdir, "CombinedKit.txt")

    if args.parallel:
        logging.info("Running parallel microarray generation...")
        logging.info("Parallel mode placeholder - executing standard instead")
    
    logging.info(f"Generating CombinedKit VCF at {out_vcf}...")
    region_args = ["-r", args.region] if args.region else []
    p1 = subprocess.Popen(["bcftools", "mpileup", "-B", "-I", "-C", "50", "-T", args.ref_vcf_tab, "-f", ref, "-Ou"] + region_args + [args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["bcftools", "call", "--ploidy-file", args.ploidy_file, "-V", "indels", "-m", "-P", "0", "--threads", threads, "-Oz", "-o", out_vcf], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    # Index the VCF before annotation
    subprocess.run(["tabix", "-f", "-p", "vcf", out_vcf], check=True)

    logging.info("Extracting and formatting text output...")
    with tempfile.TemporaryDirectory() as tempdir:
        temp_annotated = os.path.join(tempdir, "temp_annotated.vcf.gz")
        temp_tab = os.path.join(tempdir, "temp.tab")
        
        subprocess.run(["bcftools", "annotate", "-Oz", "-a", args.ref_vcf_tab, "-c", "CHROM,POS,ID", out_vcf], stdout=open(temp_annotated, "w"), check=True)
        subprocess.run(["bcftools", "query", "-f", "%ID\t%CHROM\t%POS[\t%TGT]\n", temp_annotated], stdout=open(temp_tab, "w"), check=True)
        
        # Format strings logic
        p_sed = subprocess.Popen(["sed", "s/chr//; s/\tM\t/\tMT\t/g; s/\\///; s/\\.\\.$/--/; s/TA$/AT/; s/TC$/CT/; s/TG$/GT/; s/GA$/AG/; s/GC$/CG/; s/CA$/AC/", temp_tab], stdout=subprocess.PIPE)
        p_sort = subprocess.Popen(["sort", "-t", "\t", "-k2,3", "-V"], stdin=p_sed.stdout, stdout=open(out_txt, "w"))
        p_sed.stdout.close()
        p_sort.communicate()

    # Liftover if build 38
    if lib.build in ['hg38', 'GRCh38', 'hs38DH'] or "38" in ref:
        if lib.liftover_chain:
            logging.info(f"Performing liftover to hg19 using {lib.liftover_chain}...")
            liftover_hg38_to_hg19(out_txt, out_txt, lib.liftover_chain, lib.cma_dir)
        else:
            logging.warning("Liftover chain not found, skipping liftover.")

    logging.info(f"CombinedKit generation complete: {out_txt}")
    
    # Subsetting logic
    if args.formats == "none":
        return

    formats = []
    if args.formats == "all":
        formats = [
            '23andMe_V3', '23andMe_V4', '23andMe_V5', '23andMe_SNPs_API', '23andMe_V35',
            'Ancestry_V1', 'Ancestry_V2', 'FTDNA_V2', 'FTDNA_V3', 'LDNA_V1', 'LDNA_V2',
            'MyHeritage_V1', 'MyHeritage_V2'
        ]
    else:
        # Map user friendly names to kits names
        format_map = {
            '23andme_v3': '23andMe_V3', '23andme_v4': '23andMe_V4', '23andme_v5': '23andMe_V5',
            '23andme_api': '23andMe_SNPs_API', '23andme_v35': '23andMe_V35',
            'ancestry_v1': 'Ancestry_V1', 'ancestry_v2': 'Ancestry_V2',
            'ftdna_v2': 'FTDNA_V2', 'ftdna_v3': 'FTDNA_V3',
            'ldna_v1': 'LDNA_V1', 'ldna_v2': 'LDNA_V2',
            'myheritage_v1': 'MyHeritage_V1', 'myheritage_v2': 'MyHeritage_V2'
        }
        for f in args.formats.split(","):
            f = f.strip().lower()
            if f in format_map:
                formats.append(format_map[f])
            elif f in [k.lower() for k in format_map.values()]:
                # find the original casing
                for k in format_map.values():
                    if f == k.lower():
                        formats.append(k)
                        break

    if not formats:
        return

    if not lib.cma_dir:
        logging.error("Microarray template directory (cma_dir) not found. Cannot perform subsetting.")
        return

    for fmt in formats:
        suffix = ".csv" if ("FTDNA" in fmt or "MyHeritage" in fmt) else ".txt"
        out_fmt = os.path.join(outdir, f"CombinedKit_{fmt}{suffix}")
        out_zip = os.path.join(outdir, f"CombinedKit_{fmt}.zip")
        
        logging.info(f"Generating microarray file for format {fmt}...")
        convert_to_vendor_format(fmt, out_txt, out_fmt, lib.cma_dir)
        
        if os.path.exists(out_fmt):
            subprocess.run(["zip", "-mj", out_zip, out_fmt])
