import os
import subprocess
import logging
import tempfile
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, verify_paths_exist, ReferenceLibrary, run_command
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("vep", help="Run Ensembl Variant Effect Predictor (VEP) on VCF or BAM/CRAM.")
    
    # Input/Output
    parser.add_argument("--vep-cache", help="Path to VEP cache directory (e.g., $HOME/.vep)")
    parser.add_argument("--vep-assembly", choices=["GRCh37", "GRCh38"], help="Reference assembly for VEP (GRCh37 or GRCh38)")
    parser.add_argument("--vep-args", help="Additional raw arguments to pass to VEP (e.g., '--everything --pick')")
    parser.add_argument("--format", choices=["vcf", "tab", "json"], default="vcf", help="Output format (default: vcf)")
    
    # Variant Calling (if BAM/CRAM input)
    parser.add_argument("--ploidy-file", help="File defining ploidy per chromosome (auto-resolved if possible)")
    parser.add_argument("--ploidy", help="Predefined ploidy name or value (e.g., 'human')")
    parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    
    parser.set_defaults(func=cmd_vep)

def cmd_vep(args):
    # Determine input type
    if not args.input:
        logging.error("--input is required.")
        return
    
    is_vcf = args.input.lower().endswith((".vcf", ".vcf.gz", ".bcf"))
    is_bam = args.input.lower().endswith((".bam", ".cram"))
    
    if not is_vcf and not is_bam:
        logging.error("Input must be a VCF, BAM, or CRAM file.")
        return

    # Check dependencies
    deps = ["vep"]
    if is_bam:
        deps.extend(["bcftools", "tabix"])
    verify_dependencies(deps)

    # Setup resources and paths
    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    os.makedirs(outdir, exist_ok=True)
    
    md5_sig = calculate_bam_md5(args.input, None) if is_bam else None
    lib = ReferenceLibrary(args.ref, md5_sig)
    resolved_ref = lib.fasta
    
    if is_bam and not resolved_ref:
        logging.error("--ref is required (and must be a file) for variant calling from BAM/CRAM.")
        return

    # 1. Generate VCF if input is BAM/CRAM
    temp_vcf = None
    input_vcf = args.input
    
    if is_bam:
        logging.info("Input is BAM/CRAM. Performing variant calling first...")
        temp_dir = tempfile.mkdtemp(dir=outdir)
        temp_vcf = os.path.join(temp_dir, "variants.vcf.gz")
        
        region_args = ["-r", args.region] if args.region else []
        
        ploidy_args = []
        if args.ploidy_file:
            ploidy_args = ["--ploidy-file", args.ploidy_file]
        elif args.ploidy:
            ploidy_args = ["--ploidy", args.ploidy]
        elif lib.ploidy_file:
            ploidy_args = ["--ploidy-file", lib.ploidy_file]
        else:
            # Fallback to human ploidy if not specified and not auto-resolved
            ploidy_args = ["--ploidy", "human"]
            logging.info("Using default 'human' ploidy for variant calling.")

        # Run variant calling (SNPs + Indels)
        try:
            p1 = subprocess.Popen(["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", resolved_ref, "-Ou"] + region_args + [args.input], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["bcftools", "call"] + ploidy_args + ["-mv", "-P", "0", "--threads", threads, "-Oz", "-o", temp_vcf], stdin=p1.stdout, stderr=subprocess.PIPE)
            p1.stdout.close()
            _, stderr = p2.communicate()
            
            if p2.returncode != 0:
                logging.error(f"Variant calling failed: {stderr.decode() if stderr else 'Unknown error'}")
                return
            
            subprocess.run(["tabix", "-f", "-p", "vcf", temp_vcf], check=True)
            input_vcf = temp_vcf
            logging.info(f"Variant calling complete. VCF generated at {temp_vcf}")
        except Exception as e:
            logging.error(f"Failed during variant calling: {e}")
            return

    # 2. Run VEP
    base_name = os.path.basename(args.input).split('.')[0]
    out_ext = ".vcf" if args.format == "vcf" else ".txt" if args.format == "tab" else ".json"
    output_file = os.path.join(outdir, f"{base_name}_vep{out_ext}")
    
    vep_cmd = ["vep", "-i", input_vcf, "-o", output_file, "--fork", threads]
    
    if args.format == "vcf":
        vep_cmd.append("--vcf")
    elif args.format == "json":
        vep_cmd.append("--json")
    else:
        vep_cmd.append("--tab")

    if args.vep_cache:
        vep_cmd.extend(["--dir_cache", args.vep_cache, "--cache"])
    
    if args.vep_assembly:
        vep_cmd.extend(["--assembly", args.vep_assembly])
    elif lib.build:
        # Try to map lib.build to VEP assembly
        if "38" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh38"])
        elif "37" in lib.build or "19" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh37"])

    if args.vep_args:
        import shlex
        vep_cmd.extend(shlex.split(args.vep_args))
    else:
        # Default helpful args if none provided
        vep_cmd.extend(["--everything", "--offline"])

    logging.info(f"Running VEP: {' '.join(vep_cmd)}")
    try:
        run_command(vep_cmd)
        logging.info(f"VEP analysis complete. Results saved to {output_file}")
    except Exception as e:
        logging.error(f"VEP failed: {e}")
    finally:
        # Cleanup temp VCF if created
        if temp_vcf and os.path.exists(temp_vcf):
            try:
                import shutil
                shutil.rmtree(os.path.dirname(temp_vcf))
            except Exception:
                pass
