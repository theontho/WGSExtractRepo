import os
import subprocess
import logging
import tempfile
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist, ReferenceLibrary
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("microarray", help="Generates microarray simulation CombinedKit.")
    parser.add_argument("--formats", default="all", help="Comma-separated list of formats, e.g., 23andMe_v5,Ancestry_v2,all")
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
    return threads, outdir, resolved_ref

def run(args):
    verify_dependencies(["bcftools", "tabix", "sed", "sort", "cat", "zip"])
    base = get_base_args(args)
    if not base: return
    
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

    threads, outdir, ref = base
    
    print_warning('ButtonCombinedKit', threads=threads)

    out_vcf = os.path.join(outdir, "CombinedKit.vcf.gz")
    out_txt = os.path.join(outdir, "CombinedKit.txt")

    if args.parallel:
        logging.info("Running parallel microarray generation...")
        # Placeholder for complex parallel logic which would iterate chromosomes
        # using -r $chrom and concatenate results
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

    logging.info(f"CombinedKit generation complete: {out_txt}")
    # The actual format subsetting (23andMe, etc) logic goes here.
    # We would write subset files depending on the --formats argument.
