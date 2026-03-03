import sys
import os

def register(subparsers, base_parser):
    parser = subparsers.add_parser("repair", help="Repair formatting violations in FTDNA files.")
    repair_subs = parser.add_subparsers(dest="repair_cmd", required=True)
    
    bam_parser = repair_subs.add_parser("ftdna-bam", parents=[base_parser], help="Fix QNAME spaces in FTDNA BigY BAM files (reads/writes SAM on stdin/stdout).")
    bam_parser.set_defaults(func=repair_bam)
    
    vcf_parser = repair_subs.add_parser("ftdna-vcf", parents=[base_parser], help="Fix malformed genotype lines in FTDNA VCF files.")
    vcf_parser.set_defaults(func=repair_vcf)

def repair_bam(args):
    prog_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../program"))
    sys.path.append(prog_dir)
    from fixFTDNAbam import fix_ftdna_bam
    fix_ftdna_bam()

def repair_vcf(args):
    if not args.input:
        print("Error: --input is required for VCF repair.")
        return
    
    prog_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../program"))
    sys.path.append(prog_dir)
    from fixFTDNAvcf import fix_ftdna_vcf
    
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    base_name = os.path.basename(args.input).replace(".vcf", "")
    out_vcf = os.path.join(outdir, f"{base_name}_fixed.vcf")
    
    fix_ftdna_vcf(args.input, out_vcf)
