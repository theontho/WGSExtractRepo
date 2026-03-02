import os
import subprocess
import logging
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import run_command, verify_paths_exist
from wgsextract_cli.core.warnings import print_warning

def register(subparsers):
    parser = subparsers.add_parser("qc", help="Runs quality control or calculates coverage.")
    qc_subs = parser.add_subparsers(dest="qc_cmd", required=True)

    fastp_parser = qc_subs.add_parser("fastp", help="Rapid QC and preprocessing for FASTQ files.")
    fastp_parser.add_argument("--r1", required=True, help="Input Read 1 FASTQ")
    fastp_parser.add_argument("--r2", help="Input Read 2 FASTQ")
    fastp_parser.set_defaults(func=cmd_fastp)

    fastqc_parser = qc_subs.add_parser("fastqc", help="Detailed java-based QC for FASTQ files.")
    fastqc_parser.add_argument("--fastq", required=True, help="Input FASTQ")
    fastqc_parser.set_defaults(func=cmd_fastqc)

    cov_wgs_parser = qc_subs.add_parser("coverage-wgs", help="Calculates binned coverage for WGS.")
    cov_wgs_parser.add_argument("-r", "--region", help="Chromosomal region")
    cov_wgs_parser.set_defaults(func=cmd_cov_wgs)

    cov_wes_parser = qc_subs.add_parser("coverage-wes", help="Calculates targeted coverage for WES.")
    cov_wes_parser.add_argument("--bed", required=True, help="BED file defining target regions")
    cov_wes_parser.add_argument("-r", "--region", help="Chromosomal region")
    cov_wes_parser.set_defaults(func=cmd_cov_wes)

def get_base_args(args):
    if hasattr(args, "outdir") and args.outdir:
        return args.outdir
    if hasattr(args, "input") and args.input:
        return os.path.dirname(os.path.abspath(args.input))
    if hasattr(args, "fastq") and args.fastq:
        return os.path.dirname(os.path.abspath(args.fastq))
    if hasattr(args, "r1") and args.r1:
        return os.path.dirname(os.path.abspath(args.r1))
    return os.getcwd()

def cmd_fastp(args):
    verify_dependencies(["fastp"])
    outdir = get_base_args(args)
    
    paths_to_check = {'--r1': args.r1}
    if args.r2: paths_to_check['--r2'] = args.r2
    if not verify_paths_exist(paths_to_check): return

    print_warning('ButtonFastp')

    html_out = os.path.join(outdir, "fastp_report.html")
    json_out = os.path.join(outdir, "fastp_report.json")
    
    cmd = ["fastp", "-i", args.r1]
    if args.r2:
        cmd.extend(["-I", args.r2])
    cmd.extend(["-h", html_out, "-j", json_out])
    
    logging.info(f"Running fastp QC to {html_out}")
    run_command(cmd)

def cmd_fastqc(args):
    verify_dependencies(["fastqc"])
    outdir = get_base_args(args)
    
    if not verify_paths_exist({'--fastq': args.fastq}): return

    print_warning('ButtonFastqc')

    logging.info(f"Running FastQC on {args.fastq}")
    run_command(["fastqc", "-o", outdir, args.fastq])

def cmd_cov_wgs(args):
    verify_dependencies(["samtools", "awk"])
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not verify_paths_exist({'--input': args.input}): return

    print_warning('CoverageStatsBIN')

    outdir = get_base_args(args)
    out_csv = os.path.join(outdir, "wgs_coverage.csv")
    
    awk_script = """
    { names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; 
    if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else 
    {n3[$1]++ ; sumn3[$1]+=$3} } } } END {
    printf("%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n",
      "chr","zero","nonzero","sum nz","fract nz","avg nz","avg all",
      "TotalBC","Bet1-3","sum Bet1-3","Bet4-7","sum Bet4-7","Gtr7","sum Gtr7");
    for (x in names) { totalbc = zero[x]+nz[x]+1 ; 
      printf("%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",
      x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,
      totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }
    """
    
    logging.info(f"Calculating WGS coverage to {out_csv}")
    region_args = ["-r", args.region] if args.region else []
    p1 = subprocess.Popen(["samtools", "depth", "-aa"] + region_args + [args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["awk", awk_script], stdin=p1.stdout, stdout=open(out_csv, "w"))
    p1.stdout.close()
    p2.communicate()

def cmd_cov_wes(args):
    verify_dependencies(["samtools", "awk"])
    if not args.input:
        logging.error("--input is required.")
        return
    
    if not verify_paths_exist({'--input': args.input, '--bed': args.bed}): return

    print_warning('CoverageStatsWES')

    outdir = get_base_args(args)
    out_csv = os.path.join(outdir, "wes_coverage.csv")
    
    awk_script = """
    { names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; 
    if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else 
    {n3[$1]++ ; sumn3[$1]+=$3} } } } END {
    printf("%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n",
      "chr","zero","nonzero","sum nz","fract nz","avg nz","avg all",
      "TotalBC","Bet1-3","sum Bet1-3","Bet4-7","sum Bet4-7","Gtr7","sum Gtr7");
    for (x in names) { totalbc = zero[x]+nz[x]+1 ; 
      printf("%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",
      x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,
      totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }
    """
    
    logging.info(f"Calculating WES coverage to {out_csv}")
    region_args = ["-r", args.region] if args.region else []
    p1 = subprocess.Popen(["samtools", "depth", "-a", "-b", args.bed] + region_args + [args.input], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["awk", awk_script], stdin=p1.stdout, stdout=open(out_csv, "w"))
    p1.stdout.close()
    p2.communicate()
