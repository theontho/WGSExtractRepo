import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, get_chr_name, get_resource_defaults, calculate_bam_md5, resolve_reference, verify_paths_exist, get_ref_mito, ensure_vcf_indexed
from wgsextract_cli.core.warnings import print_warning

def register(subparsers, base_parser):
    parser = subparsers.add_parser("extract", help="Extract specific chromosomes or unmapped reads.")
    ext_subs = parser.add_subparsers(dest="ext_cmd", required=True)

    mito_parser = ext_subs.add_parser("mito", parents=[base_parser], help="Extracts MT reads, generates VCF, and creates a consensus FASTA.")
    mito_parser.set_defaults(func=cmd_mito)

    y_parser = ext_subs.add_parser("y", parents=[base_parser], help="Extracts Y-chromosome reads and generates a VCF.")
    y_parser.set_defaults(func=cmd_y)

    unmapped_parser = ext_subs.add_parser("unmapped", parents=[base_parser], help="Extracts all unmapped reads to a separate BAM.")
    unmapped_parser.set_defaults(func=cmd_unmapped)

def get_base_args(args):
    if not args.input:
        logging.error("--input is required.")
        return None
    
    if not verify_paths_exist({'--input': args.input}):
        return None

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    
    md5_sig = calculate_bam_md5(args.input, None)
    resolved_ref = resolve_reference(args.ref, md5_sig)

    paths_to_check = {}
    if resolved_ref:
        paths_to_check['--ref'] = resolved_ref
        
    if not verify_paths_exist(paths_to_check):
        return None

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    return threads, outdir, cram_opt, resolved_ref

def cmd_mito(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    threads, outdir, cram_opt, resolved_ref = base
    
    if not resolved_ref:
        logging.error("--ref is required for mitochondrial extraction.")
        return

    print_warning('ButtonMitoBAM', threads=threads)
    
    chr_m = get_chr_name(args.input, "MT", cram_opt)
    base_name = os.path.basename(args.input).split('.')[0]
    out_bam = os.path.join(outdir, f"{base_name}_MT.bam")
    out_vcf = os.path.join(outdir, f"{base_name}_MT.vcf.gz")
    out_fasta = os.path.join(outdir, f"{base_name}_MT.fasta")

    logging.info(f"Extracting mtDNA reads ({chr_m}) to {out_bam}")
    try:
        # Extract BAM
        run_command(["samtools", "view", "-bh"] + cram_opt + ["-@", threads, "-o", out_bam, args.input, chr_m])
        run_command(["samtools", "index", out_bam])
        
        # Generate VCF
        # Identify mito ref type (logic from program/bamfiles.py)
        mito_ref_type = get_ref_mito(args.input, cram_opt)
        logging.info(f"Detected mitochondrial reference type: {mito_ref_type}")
        
        p1 = subprocess.Popen(["bcftools", "mpileup", "-Ou", "-f", resolved_ref, out_bam], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["bcftools", "call", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()
        ensure_vcf_indexed(out_vcf)
        
        # Generate Consensus FASTA
        # Need to handle rCRS/Yoruba variants from VCF
        logging.info(f"Generating consensus FASTA to {out_fasta}")
        # Placeholder for complex consensus logic
        with open(out_fasta, "w") as f:
            f.write(f">MT_{base_name}\n")
            # In real tool, we'd use bcftools consensus
            subprocess.run(["bcftools", "consensus", "-f", resolved_ref, "-H", "1", out_vcf], stdout=f, check=True)

    except Exception as e:
        logging.error(f"Mito extraction failed: {e}")

def cmd_y(args):
    verify_dependencies(["samtools", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base: return
    threads, outdir, cram_opt, resolved_ref = base
    
    if not resolved_ref:
        logging.error("--ref is required for Y extraction.")
        return

    print_warning('ButtonYOnlyBAM', threads=threads)
    
    chr_y = get_chr_name(args.input, "Y", cram_opt)
    base_name = os.path.basename(args.input).split('.')[0]
    out_bam = os.path.join(outdir, f"{base_name}_Y.bam")
    out_vcf = os.path.join(outdir, f"{base_name}_Y.vcf.gz")

    logging.info(f"Extracting Y-chromosome reads ({chr_y}) to {out_bam}")
    try:
        run_command(["samtools", "view", "-bh"] + cram_opt + ["-@", threads, "-o", out_bam, args.input, chr_y])
        run_command(["samtools", "index", out_bam])
        
        # Simple Y variant calling
        p1 = subprocess.Popen(["bcftools", "mpileup", "-Ou", "-f", resolved_ref, out_bam], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["bcftools", "call", "-mv", "-Oz", "-o", out_vcf], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()
        ensure_vcf_indexed(out_vcf)
        
    except Exception as e:
        logging.error(f"Y extraction failed: {e}")

def cmd_unmapped(args):
    verify_dependencies(["samtools"])
    base = get_base_args(args)
    if not base: return
    threads, outdir, cram_opt, resolved_ref = base
    
    print_warning('ButtonUnmappedBAM', threads=threads)

    base_name = os.path.basename(args.input).split('.')[0]
    out_bam = os.path.join(outdir, f"{base_name}_unmapped.bam")

    logging.info(f"Extracting unmapped reads to {out_bam}")
    try:
        # -f 4 gets unmapped reads
        run_command(["samtools", "view", "-bh", "-f", "4"] + cram_opt + ["-@", threads, "-o", out_bam, args.input])
    except Exception as e:
        logging.error(f"Unmapped extraction failed: {e}")
