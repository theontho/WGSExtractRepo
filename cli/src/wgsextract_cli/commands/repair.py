import sys
import os
import subprocess
import logging

def register(subparsers, base_parser):
    parser = subparsers.add_parser("repair", help="Repair formatting violations in FTDNA files.")
    repair_subs = parser.add_subparsers(dest="repair_cmd", required=True)
    
    bam_parser = repair_subs.add_parser("ftdna-bam", parents=[base_parser], help="Fix QNAME spaces in FTDNA BigY BAM files (reads/writes SAM on stdin/stdout).")
    bam_parser.set_defaults(func=repair_bam)
    
    vcf_parser = repair_subs.add_parser("ftdna-vcf", parents=[base_parser], help="Fix malformed genotype lines in FTDNA VCF files (reads/writes VCF on stdin/stdout).")
    vcf_parser.set_defaults(func=repair_vcf)

def get_script_path(script_name):
    prog_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../program"))
    return os.path.join(prog_dir, script_name)

def repair_bam(args):
    script = get_script_path("fixFTDNAbam.py")
    logging.info("Repairing FTDNA BAM (SAM) from stdin to stdout...")
    try:
        # Note: This is designed to be part of a pipe: samtools view -h in.bam | wgsextract-cli repair ftdna-bam | samtools view -b > out.bam
        subprocess.run([sys.executable, script], check=True)
    except Exception as e:
        logging.error(f"Repair failed: {e}")

def repair_vcf(args):
    script = get_script_path("fixFTDNAvcf.py")
    logging.info("Repairing FTDNA VCF from stdin to stdout...")
    try:
        # Note: Designed to be part of a pipe: bcftools view in.vcf | wgsextract-cli repair ftdna-vcf > out.vcf
        subprocess.run([sys.executable, script], check=True)
    except Exception as e:
        logging.error(f"Repair failed: {e}")
